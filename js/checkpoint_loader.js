import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Comfy.CheckpointLoaderSimple",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "CheckpointLoaderSimple") {
            const originalNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = async function() {
                if (originalNodeCreated) {
                    originalNodeCreated.apply(this, arguments);
                }

                const typeWidget = this.widgets.find(w => w.name === "model_type");
                const ckptWidget = this.widgets.find(w => w.name === "ckpt_name");

                if (!typeWidget || !ckptWidget) {
                    console.error("找不到必要的部件");
                    return;
                }

                const updateCheckpoints = async () => {
                    try {
                        const response = await fetch("/checkpoints/by_type", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                            },
                            body: JSON.stringify({
                                type: typeWidget.value
                            })
                        });

                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }

                        const result = await response.json();
                        
                        if (!result.success) {
                            throw new Error(result.error || "未知错误");
                        }

                        const checkpoints = result.data.checkpoints.names;
                        
                        // 更新选项
                        ckptWidget.options.values = checkpoints;
                        
                        // 保持当前值如果它仍然有效
                        if (!checkpoints.includes(ckptWidget.value)) {
                            ckptWidget.value = checkpoints[0] || "";
                        }
                        
                        // 触发更新
                        if (ckptWidget.callback) {
                            ckptWidget.callback(ckptWidget.value);
                        }
                        
                    } catch (error) {
                        console.error("获取检查点列表失败:", error);
                        // 清空选项并显示错误
                        ckptWidget.options.values = [];
                        ckptWidget.value = "";
                        app.ui.dialog.show("错误", `加载模型列表失败: ${error.message}`);
                    }
                };

                // 添加防抖
                let updateTimeout;
                typeWidget.callback = () => {
                    clearTimeout(updateTimeout);
                    updateTimeout = setTimeout(updateCheckpoints, 100);
                };

                // 初始化加载
                await updateCheckpoints();
            };
        }
    }
});