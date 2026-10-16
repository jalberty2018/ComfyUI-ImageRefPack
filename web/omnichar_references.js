import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { editImageReference } from "./image_refpack.js";

const ROWS = [
    { label: "Face", slots: ["face", "face_2", "face_3"] },
    { label: "Body", slots: ["body", "body_2", "body_3"] },
    { label: "Clothes", slots: ["cloths", "cloths_2", "cloths_3"] },
];
const SLOT_NAMES = ROWS.flatMap((row) => row.slots);

function readSlots(value) {
    try {
        const raw = JSON.parse(value || '{"slots":{}}').slots || {};
        return Object.fromEntries(SLOT_NAMES.filter((name) => raw[name]?.file)
            .map((name) => [name, raw[name]]));
    } catch {
        return {};
    }
}

function injectStyles() {
    if (document.getElementById("omnichar-reference-styles")) return;
    const link = document.createElement("link");
    link.id = "omnichar-reference-styles";
    link.rel = "stylesheet";
    link.href = new URL("./omnichar_references.css", import.meta.url).href;
    document.head.appendChild(link);
}

function imageUrl(file, reference = {}) {
    if (reference.crop || reference.rotation || reference.mirror) {
        const params = new URLSearchParams({ file });
        if (reference.crop) params.set("crop", reference.crop.join(","));
        if (reference.rotation) params.set("rotate", reference.rotation);
        if (reference.mirror) params.set("mirror", "1");
        return api.apiURL(`/image_refpack/thumb?${params}`);
    }
    const split = file.lastIndexOf("/");
    return api.apiURL(`/view?${new URLSearchParams({
        filename: file.slice(split + 1), subfolder: split < 0 ? "" : file.slice(0, split), type: "input",
    })}`);
}

app.registerExtension({
    name: "ImageRefPack.OmnicharReferences",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        const localInput = nodeData.name === "OmnicharLocalInputImagesReferencesManager";
        if (!localInput && nodeData.name !== "OmnicharImagesReferencesManager") return;
        const previousCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            previousCreated?.apply(this, arguments);
            injectStyles();
            const node = this;
            const stateWidget = node.widgets.find((widget) => widget.name === "references_json");
            // Keep JSON serialized while hiding its native editor on legacy and Vue frontends.
            for (const [key, value] of [["hidden", true], ["type", "hidden"]]) {
                try { Object.defineProperty(stateWidget, key, { get: () => value, set: () => {} }); }
                catch { /* Some frontend versions expose non-configurable accessors. */ }
            }
            stateWidget.computeSize = () => [0, 0];
            stateWidget.options = { ...stateWidget.options, hidden: true };
            const hideEditor = () => { if (stateWidget.element) stateWidget.element.style.display = "none"; };
            hideEditor();
            const hideTimer = setInterval(hideEditor, 50);
            const hideTimeout = setTimeout(() => clearInterval(hideTimer), 1000);

            let slots = readSlots(stateWidget.value);
            let disposed = false;
            let generation = 0;
            let picker = null;
            let editor = null;
            const busy = new Set();
            const root = document.createElement("div");
            root.className = "omnichar-refs";
            root.addEventListener("pointerdown", (event) => event.stopPropagation());
            const commit = () => {
                stateWidget.value = JSON.stringify({ version: 1, slots });
                stateWidget.callback?.(stateWidget.value);
                app.graph?.change?.();
                node.setDirtyCanvas?.(true, true);
                render();
            };
            const upload = async (name, file) => {
                if (!file || busy.has(name) || disposed) return;
                const started = generation;
                busy.add(name);
                render();
                try {
                    const form = new FormData();
                    form.append("image", file);
                    form.append("type", "input");
                    form.append("subfolder", "omnichar_references");
                    form.append("overwrite", "false");
                    const response = await api.fetchApi("/upload/image", { method: "POST", body: form });
                    if (!response.ok) throw new Error(`Upload failed (${response.status})`);
                    const info = await response.json();
                    if (disposed || generation !== started) return;
                    // Read current state after awaiting: concurrent uploads into other slots survive.
                    slots[name] = { kind: "image", file: info.subfolder ? `${info.subfolder}/${info.name}` : info.name };
                    commit();
                } catch (error) {
                    if (!disposed) alert(`${name}: ${error.message}`);
                } finally {
                    busy.delete(name);
                    if (!disposed) render();
                }
            };
            const choose = (name) => {
                if (localInput) return chooseLocal(name);
                const input = document.createElement("input");
                input.type = "file";
                input.accept = "image/*";
                input.onchange = () => upload(name, input.files?.[0]);
                input.click();
            };
            const edit = (name) => {
                if (!slots[name] || busy.has(name)) return;
                editor?.remove();
                const original = slots[name];
                const started = generation;
                editor = editImageReference(original, (updated) => {
                    if (disposed || generation !== started || slots[name] !== original) return;
                    slots[name] = updated;
                    commit();
                });
            };
            async function chooseLocal(name) {
                picker?.remove();
                const overlay = document.createElement("div");
                picker = overlay;
                overlay.className = "omnichar-refs-overlay";
                const close = () => { overlay.remove(); if (picker === overlay) picker = null; };
                overlay.onclick = (event) => { if (event.target === overlay) close(); };
                overlay.onkeydown = (event) => {
                    event.stopPropagation();
                    if (event.key === "Escape") close();
                };
                const modal = document.createElement("div");
                modal.className = "omnichar-refs-modal";
                modal.setAttribute("role", "dialog");
                modal.setAttribute("aria-label", `Choose ${name} from ComfyUI/input`);
                const title = document.createElement("h3");
                title.textContent = `Choose ${name} from ComfyUI/input`;
                const search = document.createElement("input");
                search.type = "search";
                search.value = "";
                search.placeholder = "Filter filenames...";
                search.setAttribute("aria-label", "Filter input images");
                const status = document.createElement("div");
                status.textContent = "Loading images...";
                const list = document.createElement("div");
                list.className = "omnichar-refs-files";
                const closeButton = document.createElement("button");
                closeButton.textContent = "Close";
                closeButton.onclick = close;
                for (const child of [title, search, status, list, closeButton]) modal.appendChild(child);
                overlay.appendChild(modal);
                document.body.appendChild(overlay);
                search.focus();
                const started = generation;
                try {
                    const response = await api.fetchApi("/image_refpack/files?kind=image");
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    const files = (await response.json()).files || [];
                    if (disposed || picker !== overlay || generation !== started) return;
                    const renderFiles = () => {
                        list.replaceChildren();
                        const matches = files.filter((file) => file.toLowerCase().includes(search.value.toLowerCase()));
                        status.textContent = matches.length ? `${matches.length} images` : "No images found.";
                        for (const file of matches) {
                            const button = document.createElement("button");
                            button.textContent = file;
                            button.onclick = () => {
                                if (disposed || generation !== started) return;
                                slots[name] = { kind: "image", file };
                                commit();
                                close();
                            };
                            list.appendChild(button);
                        }
                    };
                    search.oninput = renderFiles;
                    renderFiles();
                } catch (error) {
                    status.textContent = `Could not read ComfyUI/input: ${error.message}`;
                }
            }
            function render() {
                root.replaceChildren();
                for (const row of ROWS) {
                    const section = document.createElement("section");
                    const title = document.createElement("div");
                    title.className = "omnichar-refs-heading";
                    title.textContent = `${row.label} (${row.slots.filter((name) => slots[name]).length}/3)`;
                    section.appendChild(title);
                    const grid = document.createElement("div");
                    grid.className = "omnichar-refs-grid";
                    for (const name of row.slots) {
                        const tile = document.createElement("div");
                        tile.className = "omnichar-refs-tile";
                        const button = document.createElement("button");
                        button.className = "omnichar-refs-pick";
                        button.type = "button";
                        button.disabled = busy.has(name);
                        button.title = `${slots[name] ? "Replace" : localInput ? "Choose" : "Upload"} ${name}`;
                        button.onclick = () => choose(name);
                        if (slots[name] && !busy.has(name)) {
                            const image = document.createElement("img");
                            image.src = imageUrl(slots[name].file, slots[name]);
                            image.alt = name;
                            image.draggable = false;
                            button.appendChild(image);
                        } else {
                            button.textContent = busy.has(name) ? "Uploading…" : localInput ? "+ Choose image" : "+ Upload image";
                        }
                        tile.appendChild(button);
                        const label = document.createElement("div");
                        label.className = "omnichar-refs-label";
                        label.textContent = name;
                        tile.appendChild(label);
                        if (slots[name]) {
                            const remove = document.createElement("button");
                            remove.type = "button";
                            remove.className = "omnichar-refs-remove";
                            remove.textContent = "×";
                            remove.title = `Remove ${name}`;
                            remove.disabled = busy.has(name);
                            remove.onclick = () => { delete slots[name]; commit(); };
                            tile.appendChild(remove);
                            const editButton = document.createElement("button");
                            editButton.type = "button";
                            editButton.className = "omnichar-refs-edit";
                            editButton.textContent = "✂";
                            editButton.title = `Edit ${name}: crop, rotate or mirror`;
                            editButton.disabled = busy.has(name);
                            editButton.onclick = () => edit(name);
                            tile.appendChild(editButton);
                        }
                        tile.ondragover = (event) => { event.preventDefault(); event.stopPropagation(); };
                        tile.ondrop = (event) => {
                            event.preventDefault(); event.stopPropagation();
                            if (!localInput) upload(name, event.dataTransfer.files?.[0]);
                        };
                        grid.appendChild(tile);
                    }
                    section.appendChild(grid);
                    root.appendChild(section);
                }
            }
            const panel = node.addDOMWidget("omnichar_references", "custom", root, { serialize: false });
            panel.computeSize = () => [480, 570];
            node.setSize([Math.max(node.size?.[0] || 0, 520), 840]);
            render();
            const previousConfigure = node.onConfigure;
            node.onConfigure = function () {
                previousConfigure?.apply(this, arguments);
                generation += 1;
                editor?.remove();
                picker?.remove();
                picker = null;
                slots = readSlots(stateWidget.value);
                render();
            };
            const previousRemoved = node.onRemoved;
            node.onRemoved = function () {
                disposed = true;
                editor?.remove();
                picker?.remove();
                clearInterval(hideTimer);
                clearTimeout(hideTimeout);
                root.remove();
                previousRemoved?.apply(this, arguments);
            };
        };
    },
});
