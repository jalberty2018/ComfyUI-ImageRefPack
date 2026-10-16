import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const url = new URL("../web/omnichar_references.js", import.meta.url);
const source = readFileSync(url, "utf8").replace(/^import .*;\r?\n/gm, "")
    .replaceAll("import.meta.url", JSON.stringify(url.href));

class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.style = {}; }
    appendChild(child) { this.children.push(child); }
    replaceChildren() { this.children = []; }
    addEventListener() {}
    remove() {}
    click() {}
    focus() {}
    setAttribute() {}
}

async function setup(localInput = false) {
    let extension;
    let root;
    const state = { name: "references_json", value: "", options: {} };
    const pending = [];
    const edits = [];
    const body = new Element("body");
    vm.runInNewContext(source, {
        editImageReference: (reference, onSave) => {
            edits.push({ reference, onSave });
            return new Element("editor");
        },
        app: { registerExtension: (value) => { extension = value; }, graph: { change() {} } },
        api: {
            apiURL: (path) => `/proxy${path}`,
            fetchApi: (path, options) => new Promise((resolve) => {
                if (localInput) {
                    assert.equal(path, "/image_refpack/files?kind=image");
                    resolve({ ok: true, json: async () => ({ files: ["face.png", "nested/body.png", "clothes.png"] }) });
                    return;
                }
                assert.equal(path, "/upload/image");
                assert.equal(options.body.get("overwrite"), "false");
                pending.push({ resolve, options });
            }),
        },
        document: { getElementById: () => true, createElement: (tag) => new Element(tag), head: new Element("head"), body },
        URL, URLSearchParams, FormData,
        setInterval: () => 1, clearInterval() {}, setTimeout: () => 2, clearTimeout() {},
        alert: (message) => { throw new Error(message); },
    });
    class Node {
        constructor() { this.widgets = [state]; this.size = [300, 300]; }
        addDOMWidget(name, type, element) { root = element; return {}; }
        setSize(value) { this.size = value; }
        setDirtyCanvas() {}
    }
    await extension.beforeRegisterNodeDef(Node, { name: localInput ? "LSOmnicharLocalInputImagesReferencesManager" : "LSOmnicharImagesReferencesManager" });
    const node = new Node();
    node.onNodeCreated();
    return { root, node, state, pending, body, edits };
}

function tiles(root) { return root.children.flatMap((section) => section.children[1].children); }

for (const local of [false, true]) {
    test(`edit saves transforms to the exact slot and restores preview (local=${local})`, async () => {
        const { root, node, state, edits } = await setup(local);
        state.value = JSON.stringify({ slots: { body_2: { file: "body.png" }, cloths: { file: "clothes.png" } } });
        node.onConfigure();
        tiles(root)[4].children[3].onclick();
        assert.equal(edits[0].reference.file, "body.png");
        const updated = { file: "body.png", crop: [0, 0, 0.5, 1], rotation: 90, mirror: true };
        edits[0].onSave(updated);
        assert.deepEqual(JSON.parse(state.value).slots.body_2, updated);
        assert.deepEqual(JSON.parse(state.value).slots.cloths, { file: "clothes.png" });
        node.onConfigure();
        const preview = tiles(root)[4].children[0].children[0].src;
        assert.match(preview, /image_refpack\/thumb/);
        assert.match(preview, /rotate=90/);
        assert.match(preview, /mirror=1/);
        tiles(root)[4].children[3].onclick();
        edits[1].onSave({ file: "body.png" });
        assert.match(tiles(root)[4].children[0].children[0].src, /\/view\?/);
        node.onRemoved();
    });
}

test("local picker filters subfolders and assigns only the selected slot", async () => {
    const { root, node, state, body } = await setup(true);
    assert.equal(tiles(root)[4].children[0].textContent, "+ Choose image");
    await tiles(root)[4].children[0].onclick();
    const modal = body.children.at(-1).children[0];
    const search = modal.children[1];
    const list = modal.children[3];
    assert.equal(list.children.length, 3);
    search.value = "NESTED";
    search.oninput();
    assert.equal(list.children.length, 1);
    list.children[0].onclick();
    assert.deepEqual(JSON.parse(state.value).slots, { body_2: { kind: "image", file: "nested/body.png" } });
    await tiles(root)[7].children[0].onclick();
    body.children.at(-1).children[0].children[3].children[2].onclick();
    assert.deepEqual(Object.keys(JSON.parse(state.value).slots), ["body_2", "cloths_2"]);
    await tiles(root)[4].children[0].onclick();
    body.children.at(-1).children[0].children[3].children[0].onclick();
    assert.equal(JSON.parse(state.value).slots.body_2.file, "face.png");
    assert.equal(JSON.parse(state.value).slots.cloths_2.file, "clothes.png");
    node.onRemoved();
});

test("renders three named rows of three fixed slots", async () => {
    const { root, node } = await setup();
    assert.deepEqual(root.children.map((section) => section.children[0].textContent), ["Face (0/3)", "Body (0/3)", "Clothes (0/3)"]);
    assert.deepEqual(tiles(root).map((tile) => tile.children[1].textContent),
        ["face", "face_2", "face_3", "body", "body_2", "body_3", "cloths", "cloths_2", "cloths_3"]);
    node.onRemoved();
});

test("parallel uploads preserve their roles, removal leaves gaps, workflow restores", async () => {
    const { root, node, state, pending } = await setup();
    for (const index of [1, 7]) {
        tiles(root)[index].ondrop({ preventDefault() {}, stopPropagation() {},
            dataTransfer: { files: [new File(["image"], "same.png")] } });
    }
    pending[1].resolve({ ok: true, json: async () => ({ name: "same_1.png", subfolder: "omnichar_references" }) });
    pending[0].resolve({ ok: true, json: async () => ({ name: "same.png", subfolder: "omnichar_references" }) });
    await new Promise((resolve) => setImmediate(resolve));
    const slots = JSON.parse(state.value).slots;
    assert.deepEqual(Object.keys(slots).sort(), ["cloths_2", "face_2"]);
    assert.equal(slots.cloths_2.file, "omnichar_references/same_1.png");
    assert.equal(slots.face_2.file, "omnichar_references/same.png");
    const saved = state.value;
    tiles(root)[1].children[2].onclick();
    assert.deepEqual(Object.keys(JSON.parse(state.value).slots), ["cloths_2"]);
    assert.equal(tiles(root)[7].children[0].children[0].alt, "cloths_2");
    state.value = saved;
    node.onConfigure();
    assert.equal(tiles(root)[1].children[0].children[0].alt, "face_2");
    assert.equal(tiles(root)[7].children[0].children[0].alt, "cloths_2");
    node.onRemoved();
});
