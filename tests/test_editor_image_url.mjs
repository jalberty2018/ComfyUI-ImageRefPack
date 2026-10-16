import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../web/image_refpack.js", import.meta.url), "utf8");
const shared = source.match(/export function referenceImageUrl\(file\) \{[\s\S]*?\n\}/)[0].replace("export ", "");
const editor = source.match(/function fileUrl\(file\) \{[\s\S]*?\n\}/)[0];
const context = vm.createContext({ URLSearchParams, api: { apiURL: (path) => `/proxy${path}` } });
vm.runInContext(`${shared}\n${editor}`, context);

for (const [file, folder, filename] of [
    ["face.png", "", "face.png"],
    ["omnichar_references/girl_front.png", "omnichar_references", "girl_front.png"],
    ["omnichar_references/face_2.png", "omnichar_references", "face_2.png"],
    ["people/body/full length #2.png", "people/body", "full length #2.png"],
]) {
    test(`editor view URL separates filename and subfolder: ${file}`, () => {
        const url = new URL(context.fileUrl(file), "https://comfy.example");
        assert.equal(url.pathname, "/proxy/view");
        assert.equal(url.searchParams.get("filename"), filename);
        assert.equal(url.searchParams.get("subfolder"), folder);
        assert.equal(url.searchParams.get("type"), "input");
    });
}
