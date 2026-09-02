from __future__ import annotations

from pathlib import Path
from typing import Callable


class UnsupportedDLGFormatError(RuntimeError):
    pass


class DLGWatermarkRegistry:
    """DLG format registry; unknown formats are rejected, never rewritten."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[Path, Path, str, bytes], None]] = {}

    def register(self, format_name: str, handler: Callable[[Path, Path, str, bytes], None]) -> None:
        if not format_name or not callable(handler):
            raise ValueError("format_name and callable handler are required")
        self._handlers[format_name.lower()] = handler

    def embed(self, source: Path, destination: Path, format_name: str, watermark_text: str, key: bytes) -> None:
        handler = self._handlers.get(format_name.lower())
        if handler is None:
            raise UnsupportedDLGFormatError(f"DLG format is not registered: {format_name}")
        handler(Path(source), Path(destination), watermark_text, key)


def embed_dlg_watermark(source: Path, destination: Path, watermark_text: str, key: bytes, format_name: str = "unknown") -> None:
    """Entry point that refuses unverified DLG formats."""
    registry = DLGWatermarkRegistry()
    registry.embed(source, destination, format_name, watermark_text, key)
