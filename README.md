# Qwen Image References Manager

Image-only reference nodes with crop, rotation, horizontal mirroring and optional
downscaling, bundled image and mask outputs, and the native ComfyUI Mask Editor.

## Nodes

| Display name | Node ID | Outputs | Source |
| --- | --- | --- | --- |
| Image reference manager (Local) | `ImageReferenceManager` | `references`, `masks` | Local input |
| Image reference manager (Upload) | `ImageReferenceManagerUpload` | `references`, `masks` | Upload |
| Reference spitter | `ReferenceSpitter` | `image_1` through `image_10` | `references` input |
| Mask splitter | `MaskSplitter` | `mask_1` through `mask_10` | `masks` input |
| Image References Manager (Upload, First/Last) | `QwenImageUploadFirstLastReferencePack` | `First image`, `Last image`, `first_width`, `first_height`, `last_width`, `last_height` | Upload |
| Image References Manager (Local Input, First/Last) | `QwenImageLocalInputFirstLastReferencePack` | `First image`, `Last image`, `first_width`, `first_height`, `last_width`, `last_height` | Local input |
| Omnichar Images References Manager | `OmnicharImagesReferencesManager` | `face`, `face_2`, `face_3`, `body`, `body_2`, `body_3`, `cloths`, `cloths_2`, `cloths_3` | Upload |
| Omnichar Images References Manager (Local Input) | `OmnicharLocalInputImagesReferencesManager` | Same nine named outputs | Local input |

The old ten-output managers (`QwenImageReferencePack` and
`QwenImageLocalInput10ReferencePack`) have been removed. In existing workflows,
replace them with **Image reference manager (Upload)** or **Image reference
manager (Local)** and connect **Reference spitter** for the ten image outputs.

## Install

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/jalberty2018/ComfyUI-QwenImageRefPack.git
```

Restart ComfyUI and refresh the browser after installing or updating.

## Use

Find the nodes under **Qwen Image**. Click the add tile to upload images, or to
browse the ComfyUI server's local `input` directory (including subfolders) in a
Local Input node. Local selection supports filename filtering and needs no upload.
Images fill the grid in output order: 5 x 2 for ten images, 2 x 1 for first/last.
Empty outputs return `None`.

Connect **Image reference manager (Local)** → `references` → **Reference spitter** to
carry all ten image slots over one connection. The manager uses the local input
picker and the same editing and downscaling controls as the ten-image manager.
The splitter preserves image order, individual dimensions and empty slots.
The bundle uses the custom `QWEN_IMAGE_REFERENCES` type for these two nodes.
Use **Image reference manager (Upload)** to upload images instead of selecting
local input files. It has the same bundled `references` output and connects to
the same **Reference spitter**, with editing and downscaling preserved.

### Masks

Both bundled managers have a **brush icon next to the scissors** on each image
thumbnail. Click it to open that image in the standard **ComfyUI Mask Editor**.
Save writes the editor's new image file back to that reference; Cancel leaves it
unchanged. The original source file is not overwritten. The editor opens the
source image; the manager applies its crop, rotation, mirror and size cap to both
the saved image and its mask afterwards.

Connect `masks` to **Mask splitter** to obtain `mask_1` through `mask_10`, matched
to the image outputs. Masks use ComfyUI's inverted alpha convention: white is
masked, black is unmasked. Images without transparency produce an all-black mask
with the image's dimensions; empty reference slots return `None`. Saved masks
survive workflow reloads through their image files in ComfyUI/input.
The masks bundle has type `QWEN_IMAGE_MASKS`.

On the Qwen managers, double-click a tile or use its edit control to crop, rotate or mirror it.
Those managers share the Crop presets: **Free**, **1:1 (Square)**,
**2:3 (Portrait Photo)**, **3:2 (Photo)**, **3:4 (Portrait Standard)**,
**4:3 (Standard)**, **9:16 (Portrait Widescreen)**, **16:9 (Widescreen)**,
and **21:9 (Ultrawide)**. Free releases the aspect lock for manual cropping.
The ten-image nodes retain `max_reference_edge` (0 disables downscaling).

### First/Last scaling

Both First/Last variants use the calculations from
[Scale Image to Total Pixels Adv](https://github.com/BigStationW/ComfyUi-Scale-Image-to-Total-Pixels-Advanced).
The scaler is integrated; installing that separate custom node is unnecessary.

- `megapixels`: target pixel count per image (default 1.05); 0 keeps the source size before multiple alignment.
- `multiple_of`: round each target dimension down to this multiple (default 16; the selected multiple is also the minimum output dimension).
- `resize_mode`: `stretch`, centered `crop` (default), or black `pad`.
- `upscale_method`: `nearest-exact`, `bilinear`, `area`, `bicubic`, or `lanczos` (default).
- `width` and `height`: optional fixed target dimensions. Set both above 0 to override megapixels; these dimensions are also aligned to `multiple_of`. Zero means automatic. Fields can be converted to connected inputs in ComfyUI.

The same settings apply independently to both images, after orientation and the
editor crop. Without a fixed width/height pair, each image keeps its own aspect
ratio before alignment. Outputs 0 and 1 remain First image and Last image;
four appended INT outputs report the actual scaled dimensions:
`first_width`, `first_height`, `last_width`, `last_height`.
An absent image returns `None` with width/height 0.

These nodes do not generate prompts and have no video or audio support.

### Omnichar character references

Add **Omnichar Images References Manager** from **Qwen Image**. Its three rows
are **Face**, **Body**, and **Clothes**, each with three fixed image slots.
Click a slot to upload or replace one image, or drop an image onto that slot.
Use its × button to clear it. Empty slots return `None`; other images never
shift when a slot is cleared. The workflow preserves every slot assignment.

Connect the nine outputs to the identically named inputs on Omnichar's
**Encode Character** node. The Clothes outputs use `cloths`, `cloths_2`,
and `cloths_3` to match Omnichar's input spelling. `max_reference_edge`
limits the longest image edge (default 2048; 0 disables downscaling).
Both Omnichar managers include the same editor as the Qwen managers. Click the
**scissors** button at the top left of a loaded image to crop (including aspect-ratio
presets), rotate or mirror it. **Save** applies the edits to that slot and its preview;
**Cancel** leaves it unchanged. Edits are preserved in the workflow and applied to
the corresponding image output. Clear crop and Reset remove the respective edits.

**Omnichar Images References Manager (Local Input)** has the same three rows and
nine outputs. Click a slot to browse images already in the ComfyUI server's
`input` folder, including subfolders. Filter by filename and click an image to
assign it to that exact slot. No upload is needed. Selecting an occupied slot
replaces only that reference; the × button clears it without moving other images.

## Development

```bash
pytest -q --confcutdir=tests
node --check web/qwen_image_refpack.js
```
