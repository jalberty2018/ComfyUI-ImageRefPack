"""Resolution selection with optional original image dimensions or aspect ratio."""

import math


class LSResolutionSelector:
    ORIGINAL_ASPECT_RATIO = "Use original aspect ratio"

    @classmethod
    def INPUT_TYPES(cls):
        from comfy_extras.nodes_resolution import AspectRatio

        return {
            "required": {
                "aspect_ratio": ([cls.ORIGINAL_ASPECT_RATIO] + [ratio.value for ratio in AspectRatio], {"default": AspectRatio.SQUARE.value}),
                "megapixels": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 16.0, "step": 0.1}),
                "multiple": ("INT", {"default": 8, "min": 8, "max": 128, "step": 4}),
                "use_original_image_resolution": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Round the input image's width and height to the nearest multiple, ignoring aspect_ratio and megapixels.",
                }),
            },
            "optional": {"image": ("IMAGE",)},
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")
    FUNCTION = "select"
    CATEGORY = "Image"
    DESCRIPTION = "Select dimensions using a preset or the input image's aspect ratio, or keep its original dimensions."

    def select(self, aspect_ratio, megapixels, multiple, use_original_image_resolution=False, image=None):
        if use_original_image_resolution or aspect_ratio == self.ORIGINAL_ASPECT_RATIO:
            import torch

            if not isinstance(image, torch.Tensor) or image.ndim != 4 or min(image.shape) < 1:
                mode = "Use original image resolution" if use_original_image_resolution else self.ORIGINAL_ASPECT_RATIO
                raise ValueError(f"{mode} requires a non-empty IMAGE input.")
            height, width = image.shape[1:3]
            if not use_original_image_resolution:
                scale = math.sqrt(megapixels * 1_000_000 / (width * height))
                width *= scale
                height *= scale
            width = max(multiple, round(width / multiple) * multiple)
            height = max(multiple, round(height / multiple) * multiple)
            return {"result": (width, height), "ui": {"width": [width], "height": [height]}}

        from comfy_extras.nodes_resolution import ResolutionSelector

        result = ResolutionSelector.execute(aspect_ratio, megapixels, multiple)
        return {"result": (result[0], result[1]), "ui": {"width": [result[0]], "height": [result[1]]}}
