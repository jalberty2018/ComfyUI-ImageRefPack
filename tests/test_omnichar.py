import json
import sys
from types import SimpleNamespace

import pytest

from image_refpack import nodes
from image_refpack.refs import ReferenceError


@pytest.fixture(params=[nodes.LSOmnicharImagesReferencesManager, nodes.LSOmnicharLocalInputImagesReferencesManager])
def manager(tmp_path, monkeypatch, request):
    monkeypatch.setitem(sys.modules, "folder_paths", SimpleNamespace(get_input_directory=lambda: str(tmp_path)))
    for name in ("face.png", "body.png", "clothes.png"):
        (tmp_path / name).touch()
    monkeypatch.setattr(nodes.media, "load_image", lambda path, **kwargs: (path, kwargs))
    return request.param(), tmp_path


def state(**slots):
    return json.dumps({"version": 1, "slots": slots})


def test_nine_outputs_match_encode_character(manager):
    node, _ = manager
    assert node.RETURN_NAMES == ("face", "face_2", "face_3", "body", "body_2", "body_3", "cloths", "cloths_2", "cloths_3")
    assert node.RETURN_TYPES == ("IMAGE",) * 9
    assert node.build() == (None,) * 9
    assert nodes.NODE_DISPLAY_NAME_MAPPINGS["LSOmnicharImagesReferencesManager"] == "LS Omnichar Images References Manager (Upload)"


def test_sparse_roles_and_deleted_slots_do_not_shift(manager):
    node, root = manager
    slots = {"face_3": {"file": "face.png"}, "body_2": {"file": "body.png"}, "cloths": {"file": "clothes.png"}}
    result = node.build(state(**slots))
    assert [i for i, item in enumerate(result) if item is not None] == [2, 4, 6]
    assert result[4][0] == str(root / "body.png")
    del slots["face_3"]
    assert node.build(state(**slots))[3:] == result[3:]


def test_same_image_can_fill_multiple_roles_and_cache_tracks_slot(manager):
    node, _ = manager
    ref = {"file": "face.png"}
    result = node.build(state(face=ref, body=ref, cloths_3=ref))
    assert result[0] == result[3] == result[8]
    assert node.IS_CHANGED(state(face=ref)) != node.IS_CHANGED(state(body=ref))
    assert node.IS_CHANGED(state(face=ref), 512) != node.IS_CHANGED(state(face=ref), 1024)


def test_reference_transforms_and_scaling_reach_loader(manager):
    node, _ = manager
    result = node.build(state(body={"file": "body.png", "crop": [0, 0, 0.5, 1], "rotation": 90, "mirror": True}), 768)
    assert result[3][1] == {"crop": [0, 0, 0.5, 1], "rotation": 90, "mirror": True, "max_edge": 768}


@pytest.mark.parametrize("value", ['{', '[]', '{"slots":[]}', '{"slots":{"image_10":{}}}', '{"slots":{"face":"bad"}}'])
def test_invalid_state_rejected(manager, value):
    with pytest.raises(ReferenceError):
        manager[0].build(value)


def test_missing_files_and_traversal_rejected(manager):
    node, _ = manager
    with pytest.raises(ReferenceError, match="body_2: reference file not found"):
        node.build(state(body_2={"file": "missing.png"}))
    with pytest.raises(ReferenceError, match="relative"):
        node.build(state(cloths={"file": "../outside.png"}))
