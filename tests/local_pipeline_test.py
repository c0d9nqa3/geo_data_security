from pathlib import Path
import sys

import shapefile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "server2" / "pipeline"
sys.path.insert(0, str(PACKAGE))

from geo_security.pipeline import LocalProcessingPipeline
from geo_security.processing import ProcessingService
from geo_security.readonly_output import OutputNotReadyError, UnknownResultError

DATASET = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/k50c004003/k50c004003")


def test_real_shapefile_pipeline_preserves_geometry_and_encrypts_watermark(tmp_path):
    pipeline = LocalProcessingPipeline(tmp_path / "workspace", b"test-key-material")

    result = pipeline.process_shapefile_dataset(
        project_id="project-001",
        source_dir=DATASET,
        user_id="user-001",
        watermark_text="user-001|project-001",
    )

    assert result.approval_status == "PENDING"
    assert result.result_id
    assert result.files_processed == 9
    assert result.geometry_digest_before == result.geometry_digest_after
    assert result.watermark_field_count == 9
    expected_records = sum(len(shapefile.Reader(str(path), encoding="gbk", encodingErrors="replace")) for path in DATASET.glob("*.shp"))
    assert result.encrypted_watermark_count == expected_records


def test_result_cannot_be_read_before_approval(tmp_path):
    pipeline = LocalProcessingPipeline(tmp_path / "workspace", b"test-key-material")
    result = pipeline.process_shapefile_dataset(
        "project-002", DATASET, "user-002", "user-002|project-002"
    )

    try:
        pipeline.read_result(result.result_id, "user-002", "project-002")
    except OutputNotReadyError:
        pass
    else:
        raise AssertionError("pending result was readable")


def test_approved_result_is_read_only_and_project_scoped(tmp_path):
    pipeline = LocalProcessingPipeline(tmp_path / "workspace", b"test-key-material")
    result = pipeline.process_shapefile_dataset(
        "project-003", DATASET, "user-003", "user-003|project-003"
    )
    pipeline.approve_result(result.result_id, "reviewer-001")

    files = pipeline.read_result(result.result_id, "user-003", "project-003")
    assert len(files) == 9
    assert all(Path(path).exists() for path in files)

    try:
        pipeline.read_result(result.result_id, "user-003", "other-project")
    except UnknownResultError:
        pass
    else:
        raise AssertionError("result crossed project boundary")


def test_audit_events_cover_processing_and_approval(tmp_path):
    pipeline = LocalProcessingPipeline(tmp_path / "workspace", b"test-key-material")
    result = pipeline.process_shapefile_dataset(
        "project-004", DATASET, "user-004", "user-004|project-004"
    )
    pipeline.approve_result(result.result_id, "reviewer-002")

    event_types = [event["event_type"] for event in pipeline.audit_events]
    assert event_types == [
        "PROCESSING_STARTED",
        "WATERMARK_EMBEDDED",
        "PROCESSING_COMPLETED",
        "RESULT_APPROVED",
    ]
