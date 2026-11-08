"""Resolution selection with optional original image dimensions."""


class LSResolutionSelector:
    @classmethod
    def INPUT_TYPES(cls):
        from comfy_extras.nodes_resolution import AspectRatio

        return {
            "required": {
                "aspect_ratio": ([ratio.value for ratio in AspectRatio], {"default": AspectRatio.SQUARE.value}),
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
    DESCRIPTION = "Native resolution selection with an option to use the original input image dimensions."

    def select(self, aspect_ratio, megapixels, multiple, use_original_image_resolution=False, image=None):
        if use_original_image_resolution:
            import torch

            if not isinstance(image, torch.Tensor) or image.ndim != 4 or min(image.shape) < 1:
                raise ValueError("Use original image resolution requires a non-empty IMAGE input.")
            width = max(multiple, round(image.shape[2] / multiple) * multiple)
            height = max(multiple, round(image.shape[1] / multiple) * multiple)
            return {"result": (width, height), "ui": {"width": [width], "height": [height]}}

        from comfy_extras.nodes_resolution import ResolutionSelector

        result = ResolutionSelector.execute(aspect_ratio, megapixels, multiple)
        return {"result": (result[0], result[1]), "ui": {"width": [result[0]], "height": [result[1]]}}
