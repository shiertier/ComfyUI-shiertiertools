import { app } from "/scripts/app.js";

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

                // 从缓存获取检查点列表，如果没有则从服务器获取
                const fetchCheckpoints = async (modelType) => {
                    // 检查缓存
                    if (nodeType.checkpointsCache.has(modelType)) {
                        console.log(`使用缓存的检查点列表: ${modelType}`);
                        return nodeType.checkpointsCache.get(modelType);
                    }

                    try {
                        const url = new URL('/checkpoints/by_type', window.location.origin);
                        url.searchParams.append('type', modelType);

                        const response = await fetch(url, {
                            method: "GET",
                            headers: {
                                "Accept": "application/json"
                            }
                        });

                        if (response.ok) {
                            const result = await response.json();
                            if (result.success) {
                                const checkpoints = result.data.checkpoints.names;
                                // 存入缓存
                                nodeType.checkpointsCache.set(modelType, checkpoints);
                                console.log(`已缓存检查点列表: ${modelType}`);
                                return checkpoints;
                            } else {
                                console.error(`获取检查点失败: ${result.error}`);
                                return [];
                            }
                        } else {
                            console.error(`请求失败: ${response.status}`);
                            return [];
                        }
                    } catch (error) {
                        console.error(`请求出错`, error);
                        return [];
                    }
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
                        ckptNameWidget.value = prevValue; // 保持当前选择
                    } else if (checkpoints.length > 0) {
                        ckptNameWidget.value = checkpoints[0]; // 设置第一个为默认值
                    }
                };

                // 添加刷新缓存的方法
                this.refreshCache = async () => {
                    nodeType.checkpointsCache.clear();
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
