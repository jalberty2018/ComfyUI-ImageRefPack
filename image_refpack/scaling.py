"""Total-pixel scaling compatible with BigStationW's ImageScaleToTotalPixelsX.

Algorithm reference:
https://github.com/BigStationW/ComfyUi-Scale-Image-to-Total-Pixels-Advanced
"""
from __future__ import annotations

import math

UPSCALE_METHODS = ["nearest-exact", "bilinear", "area", "bicubic", "lanczos"]
RESIZE_MODES = ["stretch", "crop", "pad"]


def target_size(original_width, original_height, megapixels=1.05, multiple_of=16,
                width=0, height=0):
    """Manual dimensions override megapixels; zero keeps the source pixel count."""
    if not math.isfinite(megapixels) or not 0 <= megapixels <= 16:
        raise ValueError("megapixels must be between 0 and 16")
    if not isinstance(multiple_of, int) or not 1 <= multiple_of <= 128:
        raise ValueError("multiple_of must be an integer between 1 and 128")
    width, height = width or 0, height or 0
    if width < 0 or height < 0:
        raise ValueError("width and height must be non-negative")
    if width > 0 and height > 0:
        w, h = int(width), int(height)
    elif megapixels == 0:
        w, h = original_width, original_height
    else:
        factor = math.sqrt(int(megapixels * 1_000_000) / (original_width * original_height))
        w, h = round(original_width * factor), round(original_height * factor)
    return (max(multiple_of, w - w % multiple_of),
            max(multiple_of, h - h % multiple_of))


def scale_image(image, megapixels=1.05, multiple_of=16, resize_mode="crop",
                upscale_method="lanczos", width=0, height=0):
    import torch.nn.functional as F

    if resize_mode not in RESIZE_MODES:
        raise ValueError(f"Unknown resize mode: {resize_mode}")
    if upscale_method not in UPSCALE_METHODS:
        raise ValueError(f"Unknown upscale method: {upscale_method}")
    _, oh, ow, _ = image.shape
    tw, th = target_size(ow, oh, megapixels, multiple_of, width, height)
    rw, rh = tw, th
    if resize_mode != "stretch":
        ratio = (min if resize_mode == "pad" else max)(tw / ow, th / oh)
        rw, rh = max(1, round(ow * ratio)), max(1, round(oh * ratio))
    samples = image.permute(0, 3, 1, 2)
    if upscale_method == "lanczos":
        from comfy.utils import lanczos
        result = lanczos(samples, rw, rh)
    else:
        result = F.interpolate(samples, size=(rh, rw), mode=upscale_method)
    if resize_mode == "pad":
        left, top = (tw - rw) // 2, (th - rh) // 2
        result = F.pad(result, (left, tw - rw - left, top, th - rh - top), value=0)
    elif resize_mode == "crop":
        left, top = (rw - tw) // 2, (rh - th) // 2
        result = result[:, :, top:top + th, left:left + tw]
    result = result.permute(0, 2, 3, 1).clamp(0, 1)
    return result, int(result.shape[2]), int(result.shape[1])
