import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../web/resolution_selector.js", import.meta.url), "utf8")
    .replace('import { app } from "../../scripts/app.js";', "");

function fixture(nodeName = "LSResolutionSelector") {
    let extension;
    vm.runInNewContext(source, { app: { registerExtension(value) { extension = value; } } });
    class Node {
        addCustomWidget(widget) { this.widgets.push(widget); }
        computeSize() { return [320, 220]; }
        setSize(size) { this.size = size; }
        setDirtyCanvas() {}
    }
    extension.beforeRegisterNodeDef(Node, { name: nodeName });
    return { node: new Node() };
}

test("resolution selector reorders, toggles, restores old settings and displays results", () => {
    const { node } = fixture("LSResolutionSelector");
    node.widgets = [
        { name: "aspect_ratio", type: "combo", value: "1:1 (Square)" },
        { name: "megapixels", type: "number", value: 1 },
        { name: "multiple", type: "number", value: 8 },
        { name: "use_original_image_resolution", type: "toggle", value: false },
    ];
    node.onNodeCreated();
    const toggle = node.widgets[0];
    assert.equal(toggle.name, "use_original_image_resolution");
    node.onConfigure({ widgets_values: ["3:4 (Portrait Standard)", 4, 32, true] });
    assert.equal(toggle.value, true);
    const aspect = node.widgets.find(w => w.name === "aspect_ratio");
    assert.equal(aspect.value, "3:4 (Portrait Standard)");
    assert.equal(aspect.hidden, true);
    assert.equal(aspect.computeSize()[1], -4);
    assert.equal(node.widgets.find(w => w.name === "multiple").value, 32);
    toggle.value = false;
    toggle.callback(false);
    assert.equal(aspect.type, "combo");
    assert.equal(aspect.hidden, false);
    node.onExecuted({ width: [1248], height: [704] });
    const lines = [];
    node.widgets.at(-1).draw({ fillText: text => lines.push(text) }, node, 300, 0);
    assert.deepEqual(lines, ["width: 1248", "height: 704"]);
    assert.equal(node.widgets.at(-1).options.serialize, false);
});
