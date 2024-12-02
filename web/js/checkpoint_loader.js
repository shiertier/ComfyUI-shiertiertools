import { app } from "/scripts/app.js";

// 初始化全局命名空间
if (!window.shiertier) {
    window.shiertier = {
        value: {}
    };
}

app.registerExtension({
    name: "Comfy.CheckpointLoader",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "LoadCheckpoint12") {
            // 添加静态缓存
            if (!nodeType.checkpointsCache) {
                nodeType.checkpointsCache = new Map();
            }

            const originalNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = async function() {
                if (originalNodeCreated) {
                    originalNodeCreated.apply(this, arguments);
                }

                const modelTypeWidget = this.widgets.find((w) => w.name === "model_type");
                const ckptNameWidget = this.widgets.find((w) => w.name === "ckpt_name");

                // 从缓存获取检查点列表
                const fetchCheckpoints = async (modelType) => {
                    // 如果全局缓存中没有数据，则从服务器获取
                    if (!window.shiertier.value.checkpoints) {
                        try {
                            const response = await fetch('/shiertier/checkpoints/all', {
                                method: "GET",
                                headers: {
                                    "Accept": "application/json"
                                }
                            });

                            if (response.ok) {
                                const result = await response.json();
                                if (result.success) {
                                    window.shiertier.value.checkpoints = result.data.checkpoints;
                                }
                            }
                        } catch (error) {
                            console.error('获取检查点数据失败:', error);
                        }
                    }

                    // 从全局缓存中获取指定类型的检查点
                    const checkpoints = window.shiertier.value.checkpoints?.[modelType] || {};
                    return Object.keys(checkpoints);
                };

                // 更新ckpt_name的选项
                const updateCheckpoints = async () => {
                    const modelType = modelTypeWidget.value;
                    const prevValue = ckptNameWidget.value;
                    ckptNameWidget.value = '';
                    ckptNameWidget.options.values = [];

                    const checkpoints = await fetchCheckpoints(modelType);

                    // 更新ckptNameWidget的选项和值
                    ckptNameWidget.options.values = checkpoints;
                    
                    if (checkpoints.includes(prevValue)) {
                        ckptNameWidget.value = prevValue;
                    } else if (checkpoints.length > 0) {
                        ckptNameWidget.value = checkpoints[0];
                    }
                };

                // 添加刷新缓存的方法
                this.refreshCache = async () => {
                    window.shiertier.value.checkpoints = null;
                    await updateCheckpoints();
                };

                // 设置model_type变化时的回调
                modelTypeWidget.callback = updateCheckpoints;

                // 初始化时更新一次
                await updateCheckpoints();
            };
        }
    },
});
