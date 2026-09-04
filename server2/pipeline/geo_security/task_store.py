"""SQLite-backed task and artifact state for server2.

The database stores workflow metadata only. Large source/result files remain in the
configured workspace and are referenced by absolute paths in the artifact record.
SQLite is the local/default backend; a future deployment can replace this boundary
with PostgreSQL without changing the API layer.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .processing import ProcessingArtifact


class TaskStore:
    """Durable task/artifact repository with atomic status updates."""

    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

    def _create_schema(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    result_id TEXT NOT NULL DEFAULT '',
                    error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    data_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    output TEXT NOT NULL,
                    files_processed INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
                CREATE INDEX IF NOT EXISTS idx_artifacts_project_user ON artifacts(project_id, user_id);
                """
            )

    @staticmethod
    def artifact_to_dict(artifact: ProcessingArtifact) -> dict[str, Any]:
        return asdict(artifact)

    def save_task(self, task: dict[str, Any]) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO tasks(task_id,status,project_id,user_id,result_id,error)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(task_id) DO UPDATE SET status=excluded.status,
                     project_id=excluded.project_id,user_id=excluded.user_id,
                     result_id=excluded.result_id,error=excluded.error,
                     updated_at=CURRENT_TIMESTAMP""",
                (task["task_id"], task["status"], task.get("project_id", ""),
                 task.get("user_id", ""), task.get("result_id", ""), task.get("error")),
            )

    def save_artifact(self, artifact: ProcessingArtifact, *, project_id: str, user_id: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO artifacts(artifact_id,data_type,source,output,files_processed,
                   status,project_id,user_id)
                   VALUES(?,?,?,?,?,?,?,?)
                   ON CONFLICT(artifact_id) DO UPDATE SET status=excluded.status,
                     output=excluded.output,files_processed=excluded.files_processed,
                     updated_at=CURRENT_TIMESTAMP""",
                (artifact.artifact_id, artifact.data_type, artifact.source, artifact.output,
                 artifact.files_processed, artifact.status, project_id, user_id),
            )

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        return dict(row) if row else None

    def get_artifact_record(self, artifact_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute("SELECT * FROM artifacts WHERE artifact_id=?", (artifact_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["artifact"] = ProcessingArtifact(
            result["artifact_id"], result["data_type"], result["source"], result["output"],
            result["files_processed"], result["status"],
        )
        return result

    def set_artifact_status(self, artifact_id: str, status: str) -> ProcessingArtifact | None:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE artifacts SET status=?, updated_at=CURRENT_TIMESTAMP WHERE artifact_id=?",
                (status, artifact_id),
            )
        record = self.get_artifact_record(artifact_id)
        return record["artifact"] if record else None

    def load_tasks(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute("SELECT * FROM tasks").fetchall()
        return {row["task_id"]: dict(row) for row in rows}

    def load_artifacts(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute("SELECT * FROM artifacts").fetchall()
        result = {}
        for row in rows:
            item = dict(row)
            item["artifact"] = ProcessingArtifact(
                item["artifact_id"], item["data_type"], item["source"], item["output"],
                item["files_processed"], item["status"],
            )
            result[item["artifact_id"]] = item
        return result

    def close(self) -> None:
        with self._lock:
            self._connection.close()
