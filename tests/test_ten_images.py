import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from image_refpack import nodes
from image_refpack.refs import ReferenceError


def test_shared_image_loader_order_and_empty_slots(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "folder_paths", SimpleNamespace(get_input_directory=lambda: str(tmp_path)))
    nested = tmp_path / "nested"
    nested.mkdir()
    for i in range(10):
        (nested / f"{i}.png").touch()
    monkeypatch.setattr(nodes.media, "load_image", lambda path, **kwargs: path)
    refs = [{"file": f"nested/{i}.png"} for i in range(10)]
    node = nodes.ImageReferencePackBase()
    assert node.RETURN_TYPES == ("IMAGE",) * 10
    assert node.RETURN_NAMES == tuple(f"image_{i}" for i in range(1, 11))
    result = node.build(json.dumps(refs))
    assert result == tuple(str(nested / f"{i}.png") for i in range(10))
    assert node.build(json.dumps(refs[:1]))[1:] == (None,) * 9
    assert node.build() == (None,) * 10
    assert node.IS_CHANGED(json.dumps(refs)) != node.IS_CHANGED(json.dumps(refs[:9]))
    with pytest.raises(ReferenceError, match="at most 10"):
        node.build(json.dumps(refs + refs[:1]))
    with pytest.raises(ReferenceError, match="at most 2"):
        nodes.LSImageUploadFirstLastReferencePack().build(json.dumps(refs))


def test_manager_and_first_last_contracts():
    manager = nodes.NODE_CLASS_MAPPINGS["LSImageReferenceManager"]
    assert manager.RETURN_NAMES == ("references", "masks")
    assert list(manager.INPUT_TYPES()["optional"]) == ["references_json", "max_reference_edge"]
    for name in ("LSImageUploadFirstLastReferencePack", "LSImageLocalInputFirstLastReferencePack"):
        variant = nodes.NODE_CLASS_MAPPINGS[name]
        assert variant.RETURN_NAMES == ("First image", "Last image", "first_width", "first_height", "last_width", "last_height")
        assert variant.MAX_IMAGES == 2
    assert len(set(nodes.NODE_DISPLAY_NAME_MAPPINGS.values())) == len(nodes.NODE_CLASS_MAPPINGS)


def test_only_current_node_ids_are_registered():
    expected = {
        "LSImageReferenceManager",
        "LSImageReferenceManagerUpload",
        "LSReferenceSpitter",
        "LSMaskSplitter",
        "LSReferenceCombiner",
        "LSMaskCombiner",
        "LSOmnicharImagesReferencesManager",
        "LSOmnicharLocalInputImagesReferencesManager",
        "LSImageUploadFirstLastReferencePack",
        "LSImageLocalInputFirstLastReferencePack",
    }
    assert set(nodes.NODE_CLASS_MAPPINGS) == expected
    assert set(nodes.NODE_DISPLAY_NAME_MAPPINGS) == expected


@pytest.mark.parametrize("count", [0, 1, 10])
@pytest.mark.parametrize("node_class", [nodes.LSImageReferenceManager, nodes.LSImageReferenceManagerUpload])
def test_reference_bundle_round_trip(count, node_class, tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "folder_paths", SimpleNamespace(get_input_directory=lambda: str(tmp_path)))
    images = [object() for _ in range(count)]
    for i in range(count):
        (tmp_path / f"{i}.png").touch()
    calls = []

    def load_image(path, **kwargs):
        calls.append(kwargs)
        return images[int(Path(path).stem)]

    monkeypatch.setattr(nodes.media, "load_image", load_image)
    monkeypatch.setattr(nodes.media, "load_mask", load_image)
    payload = json.dumps([{"file": f"{i}.png", "rotation": 90, "mirror": True} for i in range(count)])
    manager = node_class()
    splitter = nodes.LSReferenceSpitter()
    assert manager.RETURN_TYPES[:1] == splitter.INPUT_TYPES()["required"]["references"]
    result = manager.build(payload, max_reference_edge=512)
    assert len(result) == 2
    outputs = splitter.split(result[0])
    assert all(outputs[i] is images[i] for i in range(count))
    assert outputs[count:] == (None,) * (10 - count)
    mask_splitter = nodes.LSMaskSplitter()
    assert manager.RETURN_TYPES[1:] == mask_splitter.INPUT_TYPES()["required"]["masks"]
    masks = mask_splitter.split(result[1])
    assert all(masks[i] is images[i] for i in range(count))
    assert masks[count:] == (None,) * (10 - count)
    assert all(call["max_edge"] == 512 and call["rotation"] == 90 and call["mirror"] for call in calls)
    assert manager.IS_CHANGED(payload, 512) != manager.IS_CHANGED(payload, 1024)
