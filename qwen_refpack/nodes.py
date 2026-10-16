"""Qwen Image reference manager: image inputs only, no prompt generation."""
from __future__ import annotations
import hashlib
import json
import os
from . import media, refs, scaling

DEFAULT_MAX_REFERENCE_EDGE = 2048

def _signature(reference_set: refs.ReferenceSet, input_dir: str) -> str:
    digest = hashlib.sha256()
    for ref in reference_set.references:
        path = refs.reference_path(input_dir, ref.file)
        try:
            stat = os.stat(path)
            digest.update(
                f"{ref.file}:{stat.st_mtime_ns}:{stat.st_size}:{ref.to_dict()}".encode()
            )
        except OSError:
            digest.update(f"{ref.file}:missing".encode())
    return digest.hexdigest()

class QwenImageReferencePack:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}, "optional": {
            "references_json": ("STRING", {"multiline": True, "dynamicPrompts": False, "default": "", "tooltip": "Reference list written by the image manager. Do not hand-edit."}),
            "max_reference_edge": ("INT", {"default": DEFAULT_MAX_REFERENCE_EDGE, "min": 0, "max": 8192, "step": 64, "tooltip": "Downscale references whose long edge exceeds this. 0 disables the cap."}),
        }}

    MAX_IMAGES = 10
    RETURN_TYPES = ("IMAGE",) * 10
    RETURN_NAMES = tuple(f"image_{i}" for i in range(1, 11))
    FUNCTION = "build"
    CATEGORY = "Qwen Image"

    @classmethod
    def IS_CHANGED(cls, references_json="", max_reference_edge=DEFAULT_MAX_REFERENCE_EDGE, **kwargs):
        import folder_paths
        reference_set = refs.ReferenceSet.from_json(references_json, max_images=cls.MAX_IMAGES)
        return _signature(reference_set, folder_paths.get_input_directory()) + f"|{max_reference_edge}"

    def build(self, references_json="", max_reference_edge=DEFAULT_MAX_REFERENCE_EDGE, **kwargs):
        import folder_paths
        input_dir = folder_paths.get_input_directory()
        reference_set = refs.ReferenceSet.from_json(references_json, max_images=self.MAX_IMAGES)
        missing = reference_set.missing_files(input_dir)
        if missing: raise ValueError("reference file(s) not found in the ComfyUI input directory: " + ", ".join(missing))
        outputs = [None] * self.MAX_IMAGES
        for index, reference in enumerate(reference_set.references):
            outputs[index] = media.load_image(str(refs.reference_path(input_dir, reference.file)), crop=reference.crop, max_edge=max_reference_edge, rotation=reference.rotation, mirror=reference.mirror)
        return tuple(outputs)

class OmnicharImagesReferencesManager(QwenImageReferencePack):
    """Nine named slots: removing a reference never moves another role or slot."""

    MAX_IMAGES = 9
    RETURN_TYPES = ("IMAGE",) * 9
    RETURN_NAMES = ("face", "face_2", "face_3", "body", "body_2", "body_3",
                    "cloths", "cloths_2", "cloths_3")
    DESCRIPTION = "Three rows of three uploads: face, body and clothes. Connect matching outputs to Omnichar Encode Character."

    @classmethod
    def _slots(cls, references_json):
        try:
            raw = json.loads(references_json) if references_json else {"slots": {}}
        except (TypeError, json.JSONDecodeError) as error:
            raise refs.ReferenceError("references_json is not valid JSON") from error
        slots = raw.get("slots") if isinstance(raw, dict) else None
        if not isinstance(slots, dict) or any(key not in cls.RETURN_NAMES for key in slots):
            raise refs.ReferenceError("Expected named face, body and cloths slots")
        result = []
        for name in cls.RETURN_NAMES:
            item = slots.get(name)
            if item is None:
                result.append(None)
            elif not isinstance(item, dict) or item.get("kind", "image") != "image":
                raise refs.ReferenceError(f"{name} must contain an image reference")
            else:
                result.append(refs.Reference.from_dict(item))
        return result

    @classmethod
    def IS_CHANGED(cls, references_json="", max_reference_edge=DEFAULT_MAX_REFERENCE_EDGE, **kwargs):
        import folder_paths
        slots = cls._slots(references_json)
        present = refs.ReferenceSet([ref for ref in slots if ref is not None])
        layout = [ref.to_dict() if ref is not None else None for ref in slots]
        return _signature(present, folder_paths.get_input_directory()) + repr((layout, max_reference_edge))

    def build(self, references_json="", max_reference_edge=DEFAULT_MAX_REFERENCE_EDGE, **kwargs):
        import folder_paths
        input_dir = folder_paths.get_input_directory()
        outputs = []
        for name, reference in zip(self.RETURN_NAMES, self._slots(references_json)):
            if reference is None:
                outputs.append(None)
                continue
            path = refs.reference_path(input_dir, reference.file)
            if not path.is_file():
                raise refs.ReferenceError(f"{name}: reference file not found: {reference.file}")
            outputs.append(media.load_image(str(path), crop=reference.crop,
                           max_edge=max_reference_edge, rotation=reference.rotation,
                           mirror=reference.mirror))
        return tuple(outputs)


class OmnicharLocalInputImagesReferencesManager(OmnicharImagesReferencesManager):
    DESCRIPTION = "Choose nine face, body and clothes references from ComfyUI/input, including subfolders."


class QwenImageUploadFirstLastReferencePack(QwenImageReferencePack):
    """Fork-specific first/last-frame upload manager."""

    MAX_IMAGES = 2
    RETURN_TYPES = ("IMAGE", "IMAGE", "INT", "INT", "INT", "INT")
    RETURN_NAMES = ("First image", "Last image", "first_width", "first_height", "last_width", "last_height")

    @classmethod
    def INPUT_TYPES(cls):
        # Keep references first for positional workflow serialization.
        inputs = super().INPUT_TYPES()
        inputs["optional"].pop("max_reference_edge")
        inputs["optional"].update({
            "megapixels": ("FLOAT", {"default": 1.05, "min": 0.0, "max": 16.0, "step": 0.01,
                "tooltip": "Target megapixels per image. 0 disables megapixel scaling."}),
            "multiple_of": ("INT", {"default": 16, "min": 1, "max": 128, "step": 1}),
            "resize_mode": (scaling.RESIZE_MODES, {"default": "crop"}),
            "upscale_method": (scaling.UPSCALE_METHODS, {"default": "lanczos"}),
            "width": ("INT", {"default": 0, "min": 0, "max": 16384,
                "tooltip": "Set both width and height above 0 to override megapixels for both images."}),
            "height": ("INT", {"default": 0, "min": 0, "max": 16384,
                "tooltip": "Set both width and height above 0 to override megapixels for both images."}),
        })
        return inputs

    @classmethod
    def IS_CHANGED(cls, references_json="", megapixels=1.05, multiple_of=16,
                   resize_mode="crop", upscale_method="lanczos", width=0, height=0, **kwargs):
        signature = super().IS_CHANGED(references_json, max_reference_edge=0)
        return signature + repr((megapixels, multiple_of, resize_mode, upscale_method, width, height))

    def build(self, references_json="", megapixels=1.05, multiple_of=16,
              resize_mode="crop", upscale_method="lanczos", width=0, height=0, **kwargs):
        images = super().build(references_json, max_reference_edge=0)
        outputs, dimensions = [], []
        for image in images:
            if image is None:
                outputs.append(None)
                dimensions.extend((0, 0))
            else:
                image, w, h = scaling.scale_image(image, megapixels, multiple_of,
                                                resize_mode, upscale_method, width, height)
                outputs.append(image)
                dimensions.extend((w, h))
        return tuple(outputs + dimensions)


class QwenImageLocalInputFirstLastReferencePack(QwenImageUploadFirstLastReferencePack):
    """Fork-specific first/last-frame manager using ComfyUI/input."""


class QwenImageLocalInput10ReferencePack(QwenImageReferencePack):
    """Fork-specific ten-image manager using ComfyUI/input."""


class ImageReferenceManager(QwenImageLocalInput10ReferencePack):
    """Carry ten independently sized images over a single connection."""

    RETURN_TYPES = ("QWEN_IMAGE_REFERENCES",)
    RETURN_NAMES = ("references",)
    DESCRIPTION = "Manage up to ten local input images and bundle them for Reference spitter."

    def build(self, references_json="", max_reference_edge=DEFAULT_MAX_REFERENCE_EDGE, **kwargs):
        return (super().build(references_json, max_reference_edge, **kwargs),)


class ImageReferenceManagerUpload(ImageReferenceManager):
    """Upload variant of the single-output reference manager."""

    DESCRIPTION = "Upload up to ten images and bundle them for Reference spitter."


class ReferenceSpitter:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"references": ("QWEN_IMAGE_REFERENCES",)}}

    RETURN_TYPES = ("IMAGE",) * 10
    RETURN_NAMES = tuple(f"image_{i}" for i in range(1, 11))
    FUNCTION = "split"
    CATEGORY = "Qwen Image"
    DESCRIPTION = "Split Image reference manager's bundle into ten images. Empty slots return None."

    def split(self, references):
        if not isinstance(references, (tuple, list)) or len(references) != 10:
            raise ValueError("Expected ten image slots from Image reference manager")
        return tuple(references)


NODE_CLASS_MAPPINGS = {
    "ImageReferenceManagerUpload": ImageReferenceManagerUpload,
    "ImageReferenceManager": ImageReferenceManager,
    "ReferenceSpitter": ReferenceSpitter,
    "OmnicharLocalInputImagesReferencesManager": OmnicharLocalInputImagesReferencesManager,
    "OmnicharImagesReferencesManager": OmnicharImagesReferencesManager,
    "QwenImageReferencePack": QwenImageReferencePack,
    "QwenImageUploadFirstLastReferencePack": QwenImageUploadFirstLastReferencePack,
    "QwenImageLocalInputFirstLastReferencePack": QwenImageLocalInputFirstLastReferencePack,
    "QwenImageLocalInput10ReferencePack": QwenImageLocalInput10ReferencePack,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageReferenceManagerUpload": "Image reference manager (Upload)",
    "ImageReferenceManager": "Image reference manager (Local)",
    "ReferenceSpitter": "Reference spitter",
    "OmnicharLocalInputImagesReferencesManager": "Omnichar Images References Manager (Local Input)",
    "OmnicharImagesReferencesManager": "Omnichar Images References Manager",
    "QwenImageReferencePack": "Qwen Image References Manager",
    "QwenImageUploadFirstLastReferencePack": "Qwen Image References Manager (Upload, First/Last)",
    "QwenImageLocalInputFirstLastReferencePack": "Qwen Image References Manager (Local Input, First/Last)",
    "QwenImageLocalInput10ReferencePack": "Qwen Image References Manager (Local Input, 10 Images)",
}
