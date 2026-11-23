"""Native advanced image saving with an opt-in browser download."""
from comfy_api.latest import IO
from comfy_extras.nodes_images import SaveImageAdvanced


class LSSaveImage(SaveImageAdvanced):
    @classmethod
    def define_schema(cls):
        schema = super().define_schema()
        schema.node_id = "LSSaveImage"
        schema.display_name = "LS Save Image"
        schema.category = "Image"
        schema.inputs.append(IO.Boolean.Input(
            "download", default=False,
            tooltip="Download saved files in the browser after rendering. Files are also saved in ComfyUI's output directory.",
        ))
        return schema

    @classmethod
    def execute(cls, images, filename_prefix, format, download=False):
        result = super().execute(images, filename_prefix, format)
        result.ui["ls_download"] = [bool(download)]
        return result
