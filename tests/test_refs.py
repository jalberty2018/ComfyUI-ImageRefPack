import pytest

from image_refpack.refs import MAX_IMAGES, ReferenceError, ReferenceSet, output_names


def test_contract_has_two_image_outputs_only():
    assert MAX_IMAGES == 2
    assert output_names() == ("First image", "Last image")


def test_rejects_video_and_audio_references():
    with pytest.raises(ReferenceError, match="must be images"):
        ReferenceSet.from_obj({"references": [{"kind": "video", "file": "clip.mp4"}]})


def test_rejects_more_than_two_images():
    with pytest.raises(ReferenceError, match="at most 2"):
        ReferenceSet.from_obj({"references": [{"kind": "image", "file": f"{i}.png"} for i in range(3)]})

