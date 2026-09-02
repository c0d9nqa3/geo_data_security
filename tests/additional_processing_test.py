import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.dlg_watermark import UnsupportedDLGFormatError, embed_dlg_watermark
from geo_security.osgb_texture_watermark import embed_texture_watermark, extract_texture_watermark
from geo_security.precision import reduce_geojson_precision


def test_osgb_texture_watermark_changes_pixels_not_image_shape(tmp_path):
    source = tmp_path / "texture.png"
    destination = tmp_path / "texture_wm.png"
    pixels = np.zeros((128, 128, 3), dtype=np.uint8)
    pixels[:, :, 0] = np.arange(128, dtype=np.uint8)[:, None]
    pixels[:, :, 1] = np.arange(128, dtype=np.uint8)[None, :]
    Image.fromarray(pixels, "RGB").save(source)

    embed_texture_watermark(source, destination, 0x12345678)
    with Image.open(source) as before, Image.open(destination) as after:
        assert before.size == after.size
        assert before.mode == after.mode
        assert np.array_equal(np.asarray(before), pixels)
        assert not np.array_equal(np.asarray(after), pixels)
    assert extract_texture_watermark(destination) == 0x12345678


def test_dlg_adapter_rejects_unknown_format_instead_of_modifying_file(tmp_path):
    source = tmp_path / "unknown.dlg"
    source.write_bytes(b"not a validated DLG format")
    destination = tmp_path / "out.dlg"

    try:
        embed_dlg_watermark(source, destination, "user-1|project-1", b"key")
    except UnsupportedDLGFormatError:
        pass
    else:
        raise AssertionError("unknown DLG format was accepted")
    assert not destination.exists()


def test_geojson_precision_reduction_only_changes_coordinates(tmp_path):
    source = tmp_path / "source.geojson"
    destination = tmp_path / "reduced.geojson"
    source.write_text('{"type":"Feature","properties":{"name":"保留"},"geometry":{"type":"Point","coordinates":[117.123456,40.654321]}}', encoding="utf-8")
    reduce_geojson_precision(source, destination, decimals=3)
    text = destination.read_text(encoding="utf-8")
    assert "保留" in text
    assert "117.123" in text
    assert "40.654" in text
