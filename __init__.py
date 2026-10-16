try:
    from .image_refpack.nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    from .image_refpack import routes  # noqa: F401
except ImportError:  # pytest imports this hyphenated checkout without a package name
    from image_refpack.nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    from image_refpack import routes  # noqa: F401

WEB_DIRECTORY = "web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
