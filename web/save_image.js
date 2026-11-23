import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "LS.SaveImage.Download",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "LSSaveImage") return;
        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            const result = onExecuted?.apply(this, arguments);
            // Use the executed input, not a widget that may have changed mid-render.
            if (message?.ls_download?.[0] === true) {
                for (const file of message.images ?? []) {
                    const params = new URLSearchParams({
                        filename: file.filename,
                        subfolder: file.subfolder ?? "",
                        type: file.type ?? "output",
                    });
                    const link = document.createElement("a");
                    link.href = api.apiURL(`/view?${params}`);
                    link.download = file.filename;
                    link.style.display = "none";
                    document.body.appendChild(link);
                    link.click();
                    link.remove();
                }
            }
            return result;
        };
    },
});
