import { app, ComfyApp } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// The native editor writes an `image` widget on its source node. Give it an
// isolated target so its previews/widget writes never replace the manager UI.
// A value setter also handles older clipspace editors that omit callbacks.
export function createMaskEditorTarget(node, file, image, onSave) {
    const slash = file.lastIndexOf("/");
    let value = file;
    const widget = { name: "image", type: "combo", options: {}, serialize: false };
    Object.defineProperty(widget, "value", {
        enumerable: true,
        get: () => value,
        set(next) {
            let saved;
            if (typeof next === "string") {
                if (/ \[(output|temp)\]$/.test(next)) throw new Error("Mask must be saved in ComfyUI/input");
                saved = next.replace(/ \[input\]$/, "");
            } else if (next?.filename) {
                if (next.type && next.type !== "input") throw new Error("Mask must be saved in ComfyUI/input");
                saved = (next.subfolder ? `${next.subfolder}/` : "") + next.filename;
            }
            if (!saved || saved === value) return;
            onSave(saved);
            value = saved;
        },
    });
    const target = Object.create(node);
    // Own fields are essential: never mutate properties or widgets on the source.
    const fields = {
        id: `image-refpack-mask-${crypto.randomUUID()}`,
        widgets: [widget], properties: {}, imgs: [image], imageIndex: 0,
        images: [{ filename: file.slice(slash + 1), subfolder: slash < 0 ? "" : file.slice(0, slash), type: "input" }],
        previewMediaType: "image",
        onWidgetChanged: undefined,
    };
    for (const [key, field] of Object.entries(fields)) {
        Object.defineProperty(target, key, { value: field, writable: true, configurable: true });
    }
    return target;
}

export async function openReferenceMaskEditor(node, file, onSave) {
    if (ComfyApp.maskeditor_is_opended?.()) {
        throw new Error("Close the current Mask Editor before editing another reference.");
    }
    const slash = file.lastIndexOf("/");
    const image = new Image();
    image.src = api.apiURL(`/view?${new URLSearchParams({
        filename: file.slice(slash + 1), subfolder: slash < 0 ? "" : file.slice(0, slash), type: "input",
    })}`);
    await image.decode();
    const target = createMaskEditorTarget(node, file, image, onSave);
    // Prefer the native context-menu entry. Recent frontends no longer use
    // clipspace for their editor, but keep the older API for plugin compatibility.
    const options = [];
    target.getExtraMenuOptions?.(app.canvas, options);
    const nativeEditor = options.find((option) => /mask\s*editor/i.test(option?.content || "") && typeof option.callback === "function");
    if (nativeEditor) {
        await nativeEditor.callback.call(target);
        return;
    }
    if (typeof ComfyApp.open_maskeditor !== "function") {
        throw new Error("The standard ComfyUI Mask Editor is unavailable. Update the ComfyUI frontend and refresh.");
    }
    ComfyApp.copyToClipspace(target);
    // Legacy editors read this; modern editors read the target's image widget.
    if (ComfyApp.clipspace) ComfyApp.clipspace.images = target.images;
    ComfyApp.clipspace_return_node = target;
    try {
        await ComfyApp.open_maskeditor();
    } catch (error) {
        if (ComfyApp.clipspace_return_node === target) ComfyApp.clipspace_return_node = null;
        throw error;
    }
}
