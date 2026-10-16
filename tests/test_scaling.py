import json
import sys
from types import SimpleNamespace

import pytest

from image_refpack import nodes, scaling


@pytest.mark.parametrize("source,options,expected", [
    ((1920, 1080), {}, (1360, 768)),
    ((1080, 1920), {}, (768, 1360)),
    ((1920, 1080), {"megapixels": 0, "multiple_of": 32}, (1920, 1056)),
    ((1920, 1080), {"width": 1000, "height": 700, "multiple_of": 32}, (992, 672)),
    ((1920, 1080), {"width": 1000, "height": 0}, (1360, 768)),
    ((7, 3), {"megapixels": 0, "multiple_of": 16}, (16, 16)),
    ((23, 17), {"megapixels": 0, "multiple_of": 1}, (23, 17)),
])
def test_dimensions_match_advanced_scaler(source, options, expected):
    assert scaling.target_size(*source, **options) == expected


@pytest.mark.parametrize("node_class", [nodes.LSImageUploadFirstLastReferencePack, nodes.LSImageLocalInputFirstLastReferencePack])
def test_first_last_scaling_and_dimensions(node_class, tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "folder_paths", SimpleNamespace(get_input_directory=lambda: str(tmp_path)))
    for name in ("first.png", "last.png"):
        (tmp_path / name).touch()
    references = json.dumps([{"file": "first.png", "rotation": 90}, {"file": "last.png"}])
    loaded = []
    def load(path, **options):
        loaded.append(options)
        return path
    monkeypatch.setattr(nodes.media, "load_image", load)
    calls = []
    def scale(image, *settings):
        calls.append(settings)
        return image, *((640, 480) if image.endswith("first.png") else (480, 640))
    monkeypatch.setattr(scaling, "scale_image", scale)
    node = node_class()
    result = node.build(references, megapixels=2, multiple_of=32, resize_mode="pad",
                        upscale_method="area", width=0, height=0)
    assert result[:2] == (str(tmp_path / "first.png"), str(tmp_path / "last.png"))
    assert result[2:] == (640, 480, 480, 640)
    assert calls == [(2, 32, "pad", "area", 0, 0)] * 2
    assert all(item["max_edge"] == 0 for item in loaded)
    assert loaded[0]["rotation"] == 90
    assert node.build() == (None, None, 0, 0, 0, 0)
    single = node.build(json.dumps([{"file": "first.png"}]))
    assert single[1:] == (None, 640, 480, 0, 0)
    schema = node.INPUT_TYPES()["optional"]
    assert "max_reference_edge" not in schema
    assert set(schema) == {"references_json", "megapixels", "multiple_of", "resize_mode", "upscale_method", "width", "height"}
    for setting in ({"megapixels": 2}, {"multiple_of": 32}, {"resize_mode": "pad"},
                    {"upscale_method": "area"}, {"width": 640}, {"height": 480}):
        assert node.IS_CHANGED(references) != node.IS_CHANGED(references, **setting)
