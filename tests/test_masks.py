import json
import sys
from types import SimpleNamespace

import pytest

from image_refpack import media, nodes


@pytest.fixture
def image_deps():
    # Pixel tests run with the ComfyUI imaging dependencies installed.
    return (pytest.importorskip("PIL.Image"), pytest.importorskip("numpy"),
            pytest.importorskip("torch"))


@pytest.mark.parametrize("rotation,mirror,crop,cap", [
    (0, False, None, 0), (90, True, None, 0),
    (270, False, [0.25, 0, 0.5, 1], 0),
    (180, True, [0, 0.25, 1, 0.5], 3),
])
def test_mask_pixels_follow_image_transforms(image_deps, tmp_path, rotation, mirror, crop, cap):
    Image, np, torch = image_deps
    pixels = np.zeros((8, 12, 4), dtype=np.uint8)
    pixels[:, :6, :3] = 255
    # Red channel equals the expected mask, so alignment can be checked pixelwise.
    pixels[:, :, 3] = 255 - pixels[:, :, 0]
    path = tmp_path / "masked.png"
    Image.fromarray(pixels).save(path)
    options = dict(rotation=rotation, mirror=mirror, crop=crop, max_edge=cap)
    image = media.load_image(str(path), **options)
    mask = media.load_mask(str(path), **options)
    assert mask.shape == image.shape[:3]
    assert mask.dtype == torch.float32
    assert torch.allclose(mask, image[..., 0], atol=1 / 255)
    assert 0 <= mask.min() <= mask.max() <= 1


def test_opaque_image_has_zero_mask_of_matching_size(image_deps, tmp_path):
    Image, _, torch = image_deps
    path = tmp_path / "opaque.jpg"
    Image.new("RGB", (13, 7), "red").save(path)
    mask = media.load_mask(str(path))
    assert tuple(mask.shape) == (1, 7, 13)
    assert torch.count_nonzero(mask) == 0


@pytest.mark.parametrize("node_class", [nodes.LSImageReferenceManager, nodes.LSImageReferenceManagerUpload])
def test_saved_mask_bundle_and_workflow_reload(image_deps, tmp_path, monkeypatch, node_class):
    Image, _, torch = image_deps
    monkeypatch.setitem(sys.modules, "folder_paths", SimpleNamespace(get_input_directory=lambda: str(tmp_path)))
    Image.new("RGBA", (12, 8), (255, 0, 0, 0)).save(tmp_path / "mask.png")
    Image.new("RGB", (7, 9), "blue").save(tmp_path / "plain.png")
    workflow_value = json.dumps({"references": [
        {"kind": "image", "file": "mask.png", "rotation": 90},
        {"kind": "image", "file": "plain.png"},
    ]})
    images, masks = node_class().build(workflow_value)
    split = nodes.LSMaskSplitter().split(masks)
    assert split[0].shape == images[0].shape[:3] == (1, 12, 8)
    assert torch.all(split[0] == 1)
    assert split[1].shape == images[1].shape[:3] == (1, 9, 7)
    assert torch.all(split[1] == 0)
    assert split[2:] == (None,) * 8
    restored_images, restored_masks = node_class().build(workflow_value)
    assert torch.equal(restored_masks[0], masks[0])
    assert torch.equal(restored_images[0], images[0])


@pytest.mark.parametrize("invalid", [None, (), (None,) * 9, (None,) * 11, "invalid"])
def test_mask_splitter_rejects_invalid_bundles(invalid):
    with pytest.raises(ValueError, match="ten mask slots"):
        nodes.LSMaskSplitter().split(invalid)
