import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../web/reference_mask_editor.js", import.meta.url), "utf8")
    .replace(/^import .*;\r?\n/gm, "").replace(/export /g, "");

function harness() {
    const calls = [];
    const app = { canvas: {} };
    const ComfyApp = {
        copyToClipspace(target) { this.clipspace = {}; calls.push(target); },
        open_maskeditor() { calls.push("open"); },
    };
    const context = vm.createContext({
        app, ComfyApp, URLSearchParams, crypto: { randomUUID: () => "unique" },
        api: { apiURL: (path) => `/proxy${path}` },
        Image: class { async decode() {} },
    });
    vm.runInContext(source, context);
    return { context, ComfyApp, calls };
}

test("native editor saves only to isolated image widget; other thumbnails untouched", () => {
    const { context } = harness();
    const node = { id: 12, widgets: [{ name: "references_json", value: "original" }], properties: { user: true }, graph: {} };
    const saved = [];
    const target = context.createMaskEditorTarget(node, "nested/a.png", {}, (file) => saved.push(file));
    assert.notEqual(target.id, node.id);
    assert.equal(target.graph, node.graph);
    target.widgets[0].value = "clipspace-painted-masked-123.png [input]";
    target.widgets[0].value = "clipspace-painted-masked-123.png [input]";
    assert.deepEqual(saved, ["clipspace-painted-masked-123.png"]);
    assert.equal(node.widgets[0].value, "original");
    target.properties.image = "new";
    assert.equal(node.properties.image, undefined);
    assert.equal(target.images[0].filename, "a.png");
    assert.equal(target.images[0].subfolder, "nested");
});

test("legacy clipspace object writes preserve subfolder and reject temp files", () => {
    const { context } = harness();
    const saved = [];
    const target = context.createMaskEditorTarget({}, "a.png", {}, (file) => saved.push(file));
    target.widgets[0].value = { filename: "mask.png", subfolder: "clipspace", type: "input" };
    assert.deepEqual(saved, ["clipspace/mask.png"]);
    assert.throws(() => { target.widgets[0].value = "bad.png [temp]"; }, /input/);
    assert.deepEqual(saved, ["clipspace/mask.png"]);
});

test("native menu opens standard editor with isolated selected image; cancel does not save", async () => {
    const { context, calls } = harness();
    let edited;
    const node = { getExtraMenuOptions(canvas, options) {
        options.push({ content: "Open in MaskEditor | Image Canvas", callback: () => { edited = this; } });
    } };
    const saved = [];
    await context.openReferenceMaskEditor(node, "nested/face #2.png", (file) => saved.push(file));
    assert.ok(edited);
    assert.notEqual(edited, node);
    assert.equal(edited.widgets[0].value, "nested/face #2.png");
    assert.deepEqual(saved, []);
    assert.deepEqual(calls, []); // No global clipboard changes on modern frontends.
});

test("legacy fallback initializes clipspace and routes saves to selected reference", async () => {
    const { context, calls, ComfyApp } = harness();
    const saved = [];
    await context.openReferenceMaskEditor({}, "nested/a.png", (file) => saved.push(file));
    const target = calls[0];
    assert.equal(calls[1], "open");
    assert.equal(ComfyApp.clipspace_return_node, target);
    assert.equal(ComfyApp.clipspace.images[0].subfolder, "nested");
    target.widgets[0].value = "clipspace/new.png [input]";
    assert.deepEqual(saved, ["clipspace/new.png"]);
});

test("missing editor and failed opens are reported without leaving a return node", async () => {
    const { context, ComfyApp } = harness();
    ComfyApp.open_maskeditor = undefined;
    await assert.rejects(context.openReferenceMaskEditor({}, "a.png", () => {}), /unavailable/);
    ComfyApp.open_maskeditor = () => { throw new Error("failed"); };
    await assert.rejects(context.openReferenceMaskEditor({}, "a.png", () => {}), /failed/);
    assert.equal(ComfyApp.clipspace_return_node, null);
});

test("thumbnail save follows its reference after reorder and ignores deleted references", async () => {
    const managerSource = readFileSync(new URL("../web/qwen_image_refpack.js", import.meta.url), "utf8");
    const handler = managerSource.match(/async function editReferenceMask\(node, index\) \{[\s\S]*?\n\}/)[0];
    let save;
    let synced = 0;
    const context = vm.createContext({
        openReferenceMaskEditor: async (node, file, callback) => { save = callback; },
        dropThumb() {}, renderNodeBody() {},
        syncReferencesWidget() { synced++; }, console,
        alert(message) { throw new Error(message); },
    });
    vm.runInContext(handler, context);
    const first = { file: "a.png" };
    const second = { file: "b.png" };
    const node = { _mmrpRefs: { images: [first, second] }, graph: { change() {}, setDirtyCanvas() {} } };
    await context.editReferenceMask(node, 1);
    node._mmrpRefs.images.reverse();
    save("saved.png");
    assert.equal(first.file, "a.png");
    assert.equal(second.file, "saved.png");
    assert.equal(synced, 1);
    node._mmrpRefs.images = [first];
    save("deleted-reference.png");
    assert.equal(synced, 1);
    assert.equal(second.file, "saved.png");
});
