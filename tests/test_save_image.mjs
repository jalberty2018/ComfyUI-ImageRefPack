import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../web/save_image.js", import.meta.url), "utf8")
    .replace(/^import .*;$/gm, "");

function fixture(name = "LSSaveImage") {
    let extension;
    const downloads = [];
    let previews = 0;
    class Node { onExecuted() { previews++; return "preview"; } }
    vm.runInNewContext(source, {
        app: { registerExtension(value) { extension = value; } },
        api: { apiURL: path => `/comfy${path}` },
        URLSearchParams,
        document: {
            body: { appendChild() {} },
            createElement() {
                return { style: {}, click() { downloads.push({ url: this.href, name: this.download }); }, remove() {} };
            },
        },
    });
    extension.beforeRegisterNodeDef(Node, { name });
    return { node: new Node(), downloads, previews: () => previews };
}

test("download is opt-in and preserves native execution/preview", () => {
    const f = fixture();
    for (const message of [{}, { images: [{ filename: "a.png" }] }, { ls_download: [false] }]) {
        assert.equal(f.node.onExecuted(message), "preview");
    }
    assert.equal(f.previews(), 3);
    assert.equal(f.downloads.length, 0);
});

test("downloads all original batch files using encoded paths and API base", () => {
    const f = fixture();
    f.node.onExecuted({ ls_download: [true], images: [
        { filename: "a #1.png", subfolder: "folder & more", type: "output" },
        { filename: "b.exr" },
    ] });
    assert.equal(f.downloads.length, 2);
    const url = new URL(f.downloads[0].url, "http://localhost");
    assert.equal(url.pathname, "/comfy/view");
    assert.equal(url.searchParams.get("filename"), "a #1.png");
    assert.equal(url.searchParams.get("subfolder"), "folder & more");
    assert.equal(f.downloads[1].name, "b.exr");
    assert.equal(f.previews(), 1);
});

test("other nodes never trigger downloads", () => {
    const f = fixture("SaveImageAdvanced");
    f.node.onExecuted({ ls_download: [true], images: [{ filename: "a.png" }] });
    assert.equal(f.downloads.length, 0);
});
