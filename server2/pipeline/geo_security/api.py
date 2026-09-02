from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .pipeline import LocalProcessingPipeline, OutputNotReadyError, UnknownResultError


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


def create_app(workspace: Path, key: bytes, allowed_input_roots: list[Path] | None = None) -> FastAPI:
    app = FastAPI(title="Geo Data Security Server2")
    pipeline = LocalProcessingPipeline(Path(workspace), key)
    app.state.pipeline = pipeline
    app.state.tasks: dict[str, dict] = {}
    app.state.artifacts: dict[str, dict] = {}
    roots = [(Path(item).resolve()) for item in (allowed_input_roots or [Path.cwd()])]

    def check_input_path(source_path: str) -> Path:
        candidate = Path(source_path).resolve()
        if not candidate.is_file():
            raise HTTPException(status_code=404, detail="input file not found")
        if not any(candidate == root or root in candidate.parents for root in roots):
            raise HTTPException(status_code=403, detail="input path is outside allowed roots")
        return candidate

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "role": "processing_storage_readonly_output"}

    def require_service_header(service_token: Annotated[str | None, Header(alias="X-Service-Token")] = None) -> None:
        _require_service_token(service_token)

    @app.post("/internal/tasks", status_code=202, dependencies=[Depends(require_service_header)])
    def submit_task(request: TaskRequest) -> dict[str, str]:
        source = check_input_path(request.source_path)
        task_id = secrets.token_hex(16)
        try:
            artifact = _process_task(request, source, pipeline)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        app.state.artifacts[artifact.artifact_id] = {"artifact": artifact, "user_id": request.user_id, "project_id": request.project_id}
        app.state.tasks[task_id] = {"task_id": task_id, "status": "COMPLETED", "result_id": artifact.artifact_id, "project_id": request.project_id, "user_id": request.user_id}
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
        return {"result_id": result_id, "approval_status": "APPROVED"}

    @app.get("/readonly/results/{result_id}/manifest")
    def manifest(result_id: str, user_id: str, project_id: str) -> dict:
        artifact_record = app.state.artifacts.get(result_id)
        if not artifact_record or artifact_record["user_id"] != user_id or artifact_record["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="result not found")
        if artifact_record["artifact"].status != "APPROVED":
            raise HTTPException(status_code=403, detail="result is not approved")
        return artifact_record["artifact"].__dict__

    @app.get("/readonly/results/{result_id}/file")
    def result_file(result_id: str, user_id: str, project_id: str, filename: str) -> FileResponse:
        artifact_record = app.state.artifacts.get(result_id)
        if not artifact_record or artifact_record["user_id"] != user_id or artifact_record["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="result not found")
        artifact = artifact_record["artifact"]
        if artifact.status != "APPROVED":
            raise HTTPException(status_code=403, detail="result is not approved")
        result_dir = Path(artifact.output).parent
        candidate = (result_dir / filename).resolve()
        if candidate.parent != result_dir.resolve() or not candidate.is_file():
            raise HTTPException(status_code=404, detail="file not found")
        return FileResponse(candidate, filename=candidate.name)

    return app


def _process_task(request: TaskRequest, source: Path, pipeline: LocalProcessingPipeline):
    if request.data_type.upper() == "GEOJSON":
        from .processing import ProcessingService
        return ProcessingService(pipeline.root, pipeline.key).process(
            request.project_id,
            request.data_type,
            source,
            user_id=request.user_id,
            timestamp="task",
            decimals=request.precision_decimals,
        )
    raise HTTPException(status_code=422, detail=f"task data type not implemented: {request.data_type}")
