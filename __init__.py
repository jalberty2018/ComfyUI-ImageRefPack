try:
    from .image_refpack.nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    from .image_refpack import routes  # noqa: F401
except ImportError:  # pytest imports this hyphenated checkout without a package name
    from image_refpack.nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    from image_refpack import routes  # noqa: F401

WEB_DIRECTORY = "web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]


try:
    from .image_refpack.save_image import LSSaveImage
except ImportError as exc:
    import logging
    logging.getLogger(__name__).warning("LS Save Image requires ComfyUI with Save Image (Advanced): %s", exc)
else:
    NODE_CLASS_MAPPINGS["LSSaveImage"] = LSSaveImage
    NODE_DISPLAY_NAME_MAPPINGS["LSSaveImage"] = "LS Save Image"
