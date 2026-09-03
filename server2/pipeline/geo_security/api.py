from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .pipeline import LocalProcessingPipeline, OutputNotReadyError, UnknownResultError
from .processing import ProcessingService, UnsupportedDataTypeError

try:  # audit_log lives in server2/audit; caller must put that dir on sys.path
    import audit_log  # type: ignore

    _HAS_AUDIT = True
except Exception:  # noqa: BLE001
    _HAS_AUDIT = False


class ApproveRequest(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=128)


class TaskRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=128)
    user_id: str = Field(min_length=1, max_length=128)
    data_type: str = Field(min_length=1, max_length=32)
    source_path: str = Field(min_length=1, max_length=2048)
    watermark_text: str = Field(min_length=1, max_length=512)
    precision_decimals: int | None = Field(default=None, ge=0, le=15)


def _service_token() -> str:
    return os.environ.get("GEO_SECURITY_SERVER1_TOKEN", "server1-local")


def _require_service_token(value: str | None) -> None:
    if not value or not secrets.compare_digest(value, _service_token()):
        raise HTTPException(status_code=401, detail="service authentication required")


def _parse_watermark_int(text: str) -> int:
    cleaned = text.strip()
    try:
        return int(cleaned, 16) if cleaned.lower().startswith("0x") else int(cleaned)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"watermark_text must be a 32-bit integer or 0x hex, got: {text!r}") from exc


def create_app(
    workspace: Path,
    key: bytes,
    allowed_input_roots: list[Path] | None = None,
    processing_service: ProcessingService | None = None,
    audit_log_dir: Path | str | None = None,
) -> FastAPI:
    app = FastAPI(title="Geo Data Security Server2")
    pipeline = LocalProcessingPipeline(Path(workspace), key)
    service = processing_service or ProcessingService(Path(workspace), key)
    audit = None
    if audit_log_dir is not None and _HAS_AUDIT:
        audit = audit_log.AuditLog(audit_log_dir)
    app.state.pipeline = pipeline
    app.state.processing_service = service
    app.state.audit = audit
    app.state.tasks: dict[str, dict] = {}
    app.state.artifacts: dict[str, dict] = {}
    roots = [(Path(item).resolve()) for item in (allowed_input_roots or [Path.cwd()])]

    def audit_record(event: str, actor: str | None = None, **details) -> None:
        if audit is not None:
            audit.record(event, actor=actor, **details)

    def check_input_path(source_path: str, expect_dir: bool = False) -> Path:
        candidate = Path(source_path).resolve()
        exists_ok = candidate.is_dir() if expect_dir else candidate.is_file()
        if not exists_ok:
            raise HTTPException(status_code=404, detail="input path not found")
        if not any(candidate == root or root in candidate.parents for root in roots):
            raise HTTPException(status_code=403, detail="input path is outside allowed roots")
        return candidate

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "role": "processing_storage_readonly_output"}

    def require_service_header(service_token: Annotated[str | None, Header(alias="X-Service-Token")] = None) -> None:
        try:
            _require_service_token(service_token)
        except HTTPException:
            audit_record("AUTH_DENIED", actor=service_token or "<missing>", action="internal_api")
            raise

    @app.post("/internal/tasks", status_code=202, dependencies=[Depends(require_service_header)])
    def submit_task(request: TaskRequest) -> dict[str, str]:
        normalized = request.data_type.upper()
        source = check_input_path(request.source_path, expect_dir=normalized in {"TEXTURES", "OSGB_TEXTURES", "OSGB"})
        task_id = secrets.token_hex(16)
        try:
            artifact = _process_task(request, source, app.state.processing_service)
        except UnsupportedDataTypeError as exc:
            audit_record("TASK_REJECTED", actor=request.user_id, project_id=request.project_id,
                         data_type=request.data_type, reason=str(exc))
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except (KeyError, ValueError) as exc:
            audit_record("TASK_REJECTED", actor=request.user_id, project_id=request.project_id,
                         data_type=request.data_type, reason=str(exc))
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:  # processing failure: mark task FAILED, artifact dir already cleaned by service
            audit_record("TASK_FAILED", actor=request.user_id, project_id=request.project_id,
                         data_type=request.data_type, task_id=task_id, reason=str(exc))
            app.state.tasks[task_id] = {
                "task_id": task_id,
                "status": "FAILED",
                "project_id": request.project_id,
                "user_id": request.user_id,
                "error": str(exc),
            }
            return {"task_id": task_id, "status": "FAILED", "result_id": ""}
        audit_record("TASK_SUBMITTED", actor=request.user_id, project_id=request.project_id,
                     data_type=request.data_type, task_id=task_id, source_path=str(source))
        app.state.artifacts[artifact.artifact_id] = {"artifact": artifact, "user_id": request.user_id, "project_id": request.project_id}
        app.state.tasks[task_id] = {"task_id": task_id, "status": "COMPLETED", "result_id": artifact.artifact_id, "project_id": request.project_id, "user_id": request.user_id}
        audit_record("TASK_COMPLETED", actor=request.user_id, project_id=request.project_id,
                     data_type=request.data_type, task_id=task_id, result_id=artifact.artifact_id)
        return {"task_id": task_id, "status": "COMPLETED", "result_id": artifact.artifact_id}

    @app.get("/internal/tasks/{task_id}")
    def task_status(task_id: str, service_token: Annotated[str | None, Header(alias="X-Service-Token")] = None) -> dict:
        _require_service_token(service_token)
        task = app.state.tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="task not found")
        return task
    @app.post("/internal/results/{result_id}/approve")
    def approve(result_id: str, request: ApproveRequest, service_token: Annotated[str | None, Header(alias="X-Service-Token")] = None) -> dict[str, str]:
        _require_service_token(service_token)
        artifact_record = app.state.artifacts.get(result_id)
        if not artifact_record:
            raise HTTPException(status_code=404, detail="result not found")
        artifact = artifact_record["artifact"]
        artifact_record["artifact"] = artifact.__class__(artifact.artifact_id, artifact.data_type, artifact.source, artifact.output, artifact.files_processed, "APPROVED")
        audit_record("RESULT_APPROVED", actor=request.reviewer_id, result_id=result_id, project_id=artifact_record["project_id"])
        return {"result_id": result_id, "approval_status": "APPROVED"}

    @app.get("/readonly/results/{result_id}/manifest")
    def manifest(result_id: str, user_id: str, project_id: str) -> dict:
        artifact_record = app.state.artifacts.get(result_id)
        if not artifact_record or artifact_record["user_id"] != user_id or artifact_record["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="result not found")
        if artifact_record["artifact"].status != "APPROVED":
            raise HTTPException(status_code=403, detail="result is not approved")
        audit_record("RESULT_MANIFEST_READ", actor=user_id, result_id=result_id, project_id=project_id)
        return artifact_record["artifact"].__dict__

    @app.get("/readonly/results/{result_id}/file")
    def result_file(result_id: str, user_id: str, project_id: str, filename: str) -> FileResponse:
        artifact_record = app.state.artifacts.get(result_id)
        if not artifact_record or artifact_record["user_id"] != user_id or artifact_record["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="result not found")
        artifact = artifact_record["artifact"]
        if artifact.status != "APPROVED":
            raise HTTPException(status_code=403, detail="result is not approved")
        output_path = Path(artifact.output)
        result_dir = output_path if output_path.is_dir() else output_path.parent
        candidate = (result_dir / filename).resolve()
        if candidate.parent != result_dir.resolve() or not candidate.is_file():
            raise HTTPException(status_code=404, detail="file not found")
        audit_record("RESULT_FILE_DOWNLOADED", actor=user_id, result_id=result_id, project_id=project_id, filename=filename)
        return FileResponse(candidate, filename=candidate.name)

    return app


def _process_task(request: TaskRequest, source: Path, service: ProcessingService):
    normalized = request.data_type.upper()
    if normalized in {"GEOJSON", "SHP"}:
        return service.process(
            request.project_id,
            "GeoJSON",
            source,
            user_id=request.user_id,
            timestamp="task",
            decimals=request.precision_decimals,
        )
    if normalized in {"GEOTIFF", "GTIFF"}:
        watermark = _parse_watermark_int(request.watermark_text)
        return service.process(request.project_id, "GeoTIFF", source, watermark=watermark)
    if normalized in {"TEXTURES", "OSGB_TEXTURES", "OSGB"}:
        watermark = _parse_watermark_int(request.watermark_text)
        return service.process(request.project_id, "TEXTURES", source, watermark=watermark)
    raise UnsupportedDataTypeError(f"task data type not implemented: {request.data_type}")
