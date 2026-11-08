import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "LS.ImageRefPack.ResolutionSelector",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "LSResolutionSelector") {
            const original = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function (...args) {
                const result = original?.apply(this, args);
                const toggle = this.widgets?.find(w => w.name === "use_original_image_resolution");
                if (!toggle) return result;
                toggle.label = "Use original image resolution";
                this.widgets.splice(this.widgets.indexOf(toggle), 1);
                this.widgets.unshift(toggle);
                const controls = this.widgets.filter(w => ["aspect_ratio", "megapixels"].includes(w.name))
                    .map(widget => ({ widget, type: widget.type, computeSize: widget.computeSize }));
                this.lsSyncResolution = () => {
                    for (const { widget, type, computeSize } of controls) {
                        widget.type = toggle.value ? "ls_hidden" : type;
                        widget.computeSize = toggle.value ? () => [0, -4] : computeSize;
                        widget.hidden = !!toggle.value;
                    }
                    this.setSize(this.computeSize());
                    this.setDirtyCanvas(true, true);
                };
                const callback = toggle.callback;
                toggle.callback = (...values) => {
                    callback?.apply(toggle, values);
                    this.lsSyncResolution();
                };
                this.addCustomWidget({
                    name: "resolution_info", type: "ls_resolution_info",
                    options: { serialize: false },
                    computeSize: () => [0, 44],
                    draw: (ctx, node, width, y) => {
                        ctx.fillStyle = "#bbb";
                        ctx.font = "12px sans-serif";
                        ctx.textAlign = "left";
                        ctx.fillText(`width: ${this.lsResolution?.width ?? "—"}`, 12, y + 16);
                        ctx.fillText(`height: ${this.lsResolution?.height ?? "—"}`, 12, y + 34);
                    },
                });
                this.lsSyncResolution();
                return result;
            };
            const configure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (info) {
                const result = configure?.apply(this, arguments);
                // Older workflows serialized the toggle after the three settings.
                if (typeof info?.widgets_values?.[0] === "string") {
                    ["aspect_ratio", "megapixels", "multiple", "use_original_image_resolution"].forEach((name, i) => {
                        const widget = this.widgets?.find(w => w.name === name);
                        if (widget) widget.value = info.widgets_values[i];
                    });
                }
                this.lsSyncResolution?.();
                return result;
            };
            const executed = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                const result = executed?.apply(this, arguments);
                this.lsResolution = { width: message.width?.[0], height: message.height?.[0] };
                this.setDirtyCanvas(true, true);
                return result;
            };
            return;
        }
    },
});
