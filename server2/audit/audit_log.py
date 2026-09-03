"""应用层审计日志：按天 JSONL 追加，线程安全。

字段约定: timestamp(ISO-8601) / event / actor / 业务标识(project_id, task_id,
result_id, data_type...)。每条事件一行 JSON, 便于 Elasticsearch 摄入(180天保留
由部署层 ES 生命周期策略实现)。本模块只负责落盘, 不连接外部服务。
"""
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
            # local time with tz offset: ops-friendly (China Standard Time in this deployment)
            "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "event": event,
        }
        if actor is not None:
            entry["actor"] = actor
        entry.update(details)
        path = self.directory / f"audit-{entry['timestamp'][:10]}.jsonl"
        line = json.dumps(entry, ensure_ascii=False)
        with self._lock:
            with path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
        return entry
