import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";
const source = readFileSync(new URL("../web/image_refpack.js", import.meta.url), "utf8");
const code = source.slice(source.indexOf("function replaceReference("), source.indexOf("function toggleSoundtrack("));
function setup() {
    const listeners = {};
    const canvas = { style: {}, addEventListener: (name, fn) => listeners[name] = fn, setPointerCapture() {}, hasPointerCapture: () => false };
    const node = { graph: {}, _mmrpBody: { canvas }, _mmrpRefs: { images: [{ file: "a", rotation: 90 }, { file: "b" }, { file: "c" }] } };
    const context = vm.createContext({
        cloneRefs: structuredClone,
        applyRefs: (node, refs) => { node._mmrpRefs = refs; },
        getMousePos: (_, e) => ({ x: e.clientX, y: e.clientY }),
        hitTest: (_, x) => x < 0 ? null : ({ type: "tile", kind: "image", index: Math.floor(x / 100) }),
    });
    vm.runInContext(code, context);
    context.installCanvasReordering(node, canvas);
    const event = (x, type = "pointerup") => ({ type, button: 0, clientX: x, clientY: 0, pointerId: 1, stopPropagation() {} });
    return { context, node, listeners, event };
}
test("canvas drag inserts at destination and preserves edits", () => {
    const { node, listeners, event } = setup();
    listeners.pointerdown(event(10));
    listeners.pointermove(event(210));
    listeners.pointerup(event(210));
    assert.deepEqual(node._mmrpRefs.images, [{ file: "b" }, { file: "c" }, { file: "a", rotation: 90 }]);
    assert.equal(node._mmrpSelected.index, 2);
});
for (const cancel of [true, false]) test(`canvas ignores ${cancel ? "cancelled drag" : "single click"}`, () => {
    const { node, listeners, event } = setup();
    listeners.pointerdown(event(10));
    if (cancel) { listeners.pointermove(event(210)); listeners.pointercancel(event(210, "pointercancel")); }
    else listeners.pointerup(event(10));
    assert.equal(node._mmrpRefs.images[0].file, "a");
});
test("replacement clears previous edits and ignores removed references", () => {
    const { context, node } = setup();
    const original = node._mmrpRefs.images[0];
    context.replaceReference(node, original, "new");
    assert.equal(JSON.stringify(node._mmrpRefs.images[0]), '{"file":"new"}');
    context.replaceReference(node, original, "stale");
    assert.equal(node._mmrpRefs.images[0].file, "new");
});
