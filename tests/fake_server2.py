"""Minimal Server2 stand-in used by Server1 Java dispatch self-test.

Implements the same calls the Java client makes:
health, chunked upload, task submit/status, result approve/trace.
"""
from __future__ import annotations

import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "fake_server2_inbox"
ROOT.mkdir(parents=True, exist_ok=True)
CHUNKS: dict[str, dict[int, bytes]] = {}
META: dict[str, dict] = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print("[fake-server2]", fmt % args)

    def _send(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send(200, {"status": "ok", "role": "processing_storage_readonly_output"})
            return
        if self.path.startswith("/internal/tasks/"):
            self._send(200, {"task_id": "task-live", "status": "COMPLETED", "result_id": "res-live"})
            return
        if self.path.endswith("/trace"):
            self._send(200, {"result_id": "res-live", "trace": "ok"})
            return
        self._send(404, {"detail": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if self.path == "/internal/uploads":
            data = json.loads(body.decode("utf-8") or "{}")
            upload_id = "up-live"
            META[upload_id] = data
            CHUNKS[upload_id] = {}
            self._send(200, {"upload_id": upload_id, "chunk_size": 8 * 1024 * 1024})
            return
        if self.path.endswith("/complete"):
            upload_id = self.path.split("/")[3]
            blob = b"".join(CHUNKS.get(upload_id, {}).get(i, b"") for i in range(len(CHUNKS.get(upload_id, {}))))
            meta = META.get(upload_id, {})
            file_id = meta.get("file_id", "unknown")
            name = meta.get("file_name", "payload.bin")
            dest_dir = ROOT / file_id
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / name
            dest.write_bytes(blob)
            (dest_dir / "meta.json").write_text(json.dumps({
                **meta,
                "sha256": hashlib.sha256(blob).hexdigest(),
                "bytes": len(blob),
                "source_path": str(dest),
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            self._send(200, {"source_path": str(dest), "sha256": hashlib.sha256(blob).hexdigest()})
            return
        if self.path == "/internal/tasks":
            data = json.loads(body.decode("utf-8") or "{}")
            (ROOT / "last_task.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self._send(202, {"task_id": "task-live", "status": "COMPLETED", "result_id": "res-live"})
            return
        if self.path.endswith("/approve"):
            self._send(200, {"result_id": "res-live", "approval_status": "APPROVED"})
            return
        self._send(404, {"detail": "not found"})

    def do_PUT(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        parts = self.path.strip("/").split("/")
        # internal/uploads/{id}/chunks/{index}
        upload_id = parts[2]
        index = int(parts[4])
        CHUNKS.setdefault(upload_id, {})[index] = body
        self._send(200, {"ok": True})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 19081), Handler)
    print("fake server2 listening on http://127.0.0.1:19081")
    server.serve_forever()
