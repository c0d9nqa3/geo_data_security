from __future__ import annotations

import hashlib
from pathlib import Path

import shapefile

from .crypto import decrypt_text, encrypt_text


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def geometry_digest(path: Path) -> str:
    reader = shapefile.Reader(str(path), encoding="gbk", encodingErrors="replace")
    digest = hashlib.sha256()
    digest.update(str(reader.shapeType).encode())
    for shape in reader.iterShapes():
        digest.update(repr(shape.points).encode("utf-8"))
        digest.update(repr(shape.parts).encode("utf-8"))
    return digest.hexdigest()


def embed_shapefile_watermark(source: Path, destination: Path, text: str, key: bytes) -> tuple[str, str]:
    reader = shapefile.Reader(str(source), encoding="gbk", encodingErrors="replace")
    fields = list(reader.fields[1:])
    field_names = {field[0].upper() for field in fields}
    watermark_name = "_wm"
    if watermark_name.upper() in field_names:
        raise ValueError(f"source already contains reserved field {watermark_name}")
    writer = shapefile.Writer(str(destination), shapeType=reader.shapeType)
    writer.fields = fields + [(watermark_name, "C", 254, 0)]
    for shape, record in zip(reader.iterShapes(), reader.iterRecords()):
        writer.shape(shape)
        writer.record(*list(record), encrypt_text(text, key))
    writer.close()
    for suffix in (".prj", ".cpg"):
        sidecar = source.with_suffix(suffix)
        if sidecar.exists():
            destination.with_suffix(suffix).write_bytes(sidecar.read_bytes())
    return sha256_file(destination), watermark_name


def extract_shapefile_watermark(path: Path, key: bytes) -> list[str]:
    reader = shapefile.Reader(str(path), encoding="gbk", encodingErrors="replace")
    names = [field[0] for field in reader.fields[1:]]
    try:
        index = next(i for i, name in enumerate(names) if name.lower() == "_wm")
    except StopIteration as exc:
        raise ValueError("watermark field not found") from exc
    return [decrypt_text(record[index], key) for record in reader.iterRecords()]
