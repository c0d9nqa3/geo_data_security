"""Durable application audit log used by server2 APIs."""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path


class AuditLog:
    def __init__(self, directory: Path | str):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(self, event: str, actor: str | None = None, **details) -> dict:
        entry = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "event": event,
        }
        if actor is not None:
            entry["actor"] = actor
        entry.update(details)
        path = self.directory / f"audit-{entry['timestamp'][:10]}.jsonl"
        with self._lock:
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry
