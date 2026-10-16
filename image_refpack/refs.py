"""Validated image-reference state and the two-output first/last image contract."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any

MAX_IMAGES = 2

class ReferenceError(ValueError):
    pass

def reference_path(input_dir: str | os.PathLike[str], file_name: str) -> Path:
    if not isinstance(file_name, str) or not file_name.strip():
        raise ReferenceError("reference is missing a file name")
    name = file_name.strip()
    candidate_name = Path(name)
    windows = PureWindowsPath(name)
    if "\x00" in name or "\\" in name or os.path.isabs(name) or candidate_name.is_absolute() or windows.is_absolute() or bool(windows.drive) or ".." in candidate_name.parts:
        raise ReferenceError(f"reference file must be relative to the ComfyUI input directory: {file_name!r}")
    base = Path(input_dir).resolve()
    candidate = (base / candidate_name).resolve()
    if os.path.commonpath((str(base), str(candidate))) != str(base):
        raise ReferenceError(f"reference resolves outside the ComfyUI input directory: {file_name!r}")
    return candidate

def _crop(crop: Any) -> list[float]:
    if not isinstance(crop, (list, tuple)) or len(crop) != 4 or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in crop):
        raise ReferenceError(f"crop must be [x, y, w, h], got {crop!r}")
    x, y, w, h = map(float, crop)
    if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > 1.000000001 or y + h > 1.000000001:
        raise ReferenceError(f"crop must be a positive rectangle inside 0..1, got {crop!r}")
    return [x, y, w, h]

@dataclass
class Reference:
    file: str
    crop: list[float] | None = None
    rotation: int = 0
    mirror: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Reference":
        file = value.get("file")
        if not isinstance(file, str) or not file.strip():
            raise ReferenceError("reference is missing a file name")
        rotation = value.get("rotation", 0)
        if rotation not in (0, 90, 180, 270):
            raise ReferenceError("rotation must be 0, 90, 180, or 270")
        return cls(file.strip(), _crop(value["crop"]) if value.get("crop") is not None else None, rotation, bool(value.get("mirror", False)))

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"kind": "image", "file": self.file}
        if self.crop is not None: value["crop"] = list(self.crop)
        if self.rotation: value["rotation"] = self.rotation
        if self.mirror: value["mirror"] = True
        return value

@dataclass
class ReferenceSet:
    references: list[Reference] = field(default_factory=list)

    @classmethod
    def from_json(cls, value: str | None, max_images: int = MAX_IMAGES) -> "ReferenceSet":
        if not value: return cls()
        try: raw = json.loads(value)
        except json.JSONDecodeError as exc: raise ReferenceError("references_json is not valid JSON") from exc
        return cls.from_obj(raw, max_images=max_images)

    @classmethod
    def from_obj(cls, value: Any, max_images: int = MAX_IMAGES) -> "ReferenceSet":
        raw = value.get("references", []) if isinstance(value, dict) else value
        if not isinstance(raw, list) or len(raw) > max_images: raise ReferenceError(f"Image accepts at most {max_images} image references")
        refs = [Reference.from_dict(item) for item in raw]
        if any(item.get("kind", "image") != "image" for item in raw): raise ReferenceError("Image references must be images")
        return cls(refs)

    def to_json(self) -> str:
        return json.dumps({"version": 1, "references": [item.to_dict() for item in self.references]}, separators=(",", ":"))

    def missing_files(self, input_dir: str) -> list[str]:
        return [ref.file for ref in self.references if not reference_path(input_dir, ref.file).is_file()]

def output_names() -> tuple[str, ...]:
    return ("First image", "Last image")

def output_types() -> tuple[str, ...]:
    return ("IMAGE",) * MAX_IMAGES

def slot_index(name: str) -> int:
    return output_names().index(name)

def empty_outputs() -> list[Any]:
    return [None] * MAX_IMAGES
