import folder_paths
import comfy.sd
import os
import json
from typing import Dict, List, Optional, Tuple
from aiohttp import web
from server import PromptServer

def load_model_types() -> Dict[str, List[str]]:
    '''加载模型类型配置'''
    try:
        type_path = os.path.join(os.path.dirname(__file__), "models_type.json")
        with open(type_path, 'r', encoding='utf-8') as f:
            model_types = json.load(f)
            if not isinstance(model_types, dict):
                raise ValueError("模型类型配置文件格式错误")
            return model_types
    except (json.JSONDecodeError, FileNotFoundError) as e:
        raise ValueError(f"加载模型类型配置文件失败: {str(e)}")

def get_all_checkpoints() -> List[Tuple[str, str]]:
    """获取所有检查点文件的路径和名称"""
    checkpoints = []
    
    for filename in folder_paths.get_filename_list("checkpoints"):
        full_path = folder_paths.get_full_path("checkpoints", filename)
        if full_path:
            try:
                # 获取相对于 checkpoints 目录的路径
                path_parts = full_path.split(os.sep)
                checkpoint_index = path_parts.index('checkpoints')
                rel_parts = path_parts[checkpoint_index + 1:]
                rel_path = os.path.join(*rel_parts) if rel_parts else filename
                checkpoints.append((rel_path, filename))
            except ValueError:
                checkpoints.append((filename, filename))
                
    return checkpoints

def remove_suffix(text: str | list[str]) -> str | list[str]:
    '''移除文件扩展名'''
    if isinstance(text, str):
        return text.rsplit('.', 1)[0]
    elif isinstance(text, list):
        return [i.rsplit('.', 1)[0] for i in text]
    else:
        raise ValueError(f"Unsupported type: {type(text)}")

def classify_models(model_types: Dict[str, List[str]]) -> Dict[str, Dict[str, str]]:
    """根据路径对模型进行分类"""
    classified_models = {model_type: {} for model_type in model_types}
    classified_models["other"] = {}
    other_models = []

    checkpoints = get_all_checkpoints()
    for rel_path, filename in checkpoints:
        full_path = folder_paths.get_full_path("checkpoints", filename)
        name_without_ext = remove_suffix(filename)
        
        path_parts = [p for p in rel_path.split(os.sep) if p]
        if path_parts:
            folder_name = path_parts[0].lower()
            # 从名称中移除文件夹名
            if folder_name in name_without_ext.lower():
                name_without_ext = name_without_ext[len(folder_name):].lstrip('_-/ ')
            
            # 查找匹配的模型类型
            matched = False
            for model_type, patterns in model_types.items():
                if any(pattern.lower() == folder_name for pattern in patterns):
                    classified_models[model_type][name_without_ext] = full_path
                    matched = True
                    break
            
            if not matched:
                other_models.append((name_without_ext, full_path))
        else:
            other_models.append((name_without_ext, full_path))

    # 对 other 类型的文件进行二次检查
    for name_without_ext, full_path in other_models:
        name_lower = name_without_ext.lower()
        matched = False
        
        # 特殊处理 flux 和 sdxl
        for special_type in ['flux', 'sdxl']:
            if special_type in model_types and any(pattern.lower() in name_lower 
                  for pattern in model_types[special_type]):
                classified_models[special_type][name_without_ext] = full_path
                matched = True
                break
        
        if not matched:
            classified_models["other"][name_without_ext] = full_path

    # 按模型名称排序
    return {
        model_type: dict(sorted(models.items(), key=lambda x: x[0].lower()))
        for model_type, models in classified_models.items()
    }

class LoadCheckpoint12:
    """模型检查点加载器"""
    _model_types_cache: Optional[Dict[str, List[str]]] = None
    _models_by_type_cache: Optional[Dict[str, Dict[str, str]]] = None

    @classmethod
    def get_model_types(cls) -> Dict[str, List[str]]:
        '''获取模型类型配置（带缓存）'''
        if cls._model_types_cache is None:
            cls._model_types_cache = load_model_types()
        return cls._model_types_cache

    @classmethod
    def get_classified_models(cls) -> Dict[str, Dict[str, str]]:
        '''获取分类后的模型（带缓存）'''
        if cls._models_by_type_cache is None:
            model_types = cls.get_model_types()
            cls._models_by_type_cache = classify_models(model_types)
        return cls._models_by_type_cache

    @classmethod
    def clear_cache(cls):
        '''清除缓存'''
        cls._model_types_cache = None
        cls._models_by_type_cache = None

    @classmethod
    def INPUT_TYPES(s):
        try:
            model_types = s.get_model_types()
            classified_models = s.get_classified_models()
            model_type_list = list(model_types.keys())
            if "other" not in model_type_list:
                model_type_list.append("other")
            
            return {
                "required": { 
                    "model_type": (model_type_list,),
                    "ckpt_name": (list(classified_models.get(model_type_list[0], {}).keys()), 
                                {"tooltip": "选择要加载的模型文件"}),
                }
            }
        except Exception as e:
            # 如果加载失败，提供默认值
            return {
                "required": {
                    "model_type": (["other"],),
                    "ckpt_name": ([], {"tooltip": "选择要加载的模型文件"}),
                }
            }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    OUTPUT_TOOLTIPS = ("用于去噪的模型", 
                      "用于编码文本提示的CLIP模型", 
                      "用于编码和解码图像的VAE模型")
    FUNCTION = "load_checkpoint"
    CATEGORY = "loaders"
    DESCRIPTION = "加载扩散模型检查点，用于对潜空间进行去噪。"

    def load_checkpoint(self, model_type: str, ckpt_name: str):
        try:
            classified_models = self.get_classified_models()
            model_path = classified_models[model_type][ckpt_name]
            
            out = comfy.sd.load_checkpoint_guess_config(
                model_path, 
                output_vae=True, 
                output_clip=True,
                embedding_directory=folder_paths.get_folder_paths("embeddings")
            )
            return out[:3]
        except Exception as e:
            raise ValueError(f"加载模型失败: {str(e)}")


@PromptServer.instance.routes.get("/checkpoints/by_type")
@PromptServer.instance.routes.post("/checkpoints/by_type")
async def get_checkpoints_by_type(request):
    """获取指定类型的模型列表"""
    try:
        # 根据请求方法获取数据
        if request.method == "GET":
            # 从查询参数中获取type
            model_type = request.query.get("type")
        else:  # POST
            data = await request.json()
            model_type = data.get("type")
            
        if not model_type:
            return web.json_response({
                "success": False,
                "error": "缺少模型类型参数"
            }, status=400)
            
        try:
            classified_models = LoadCheckpoint12.get_classified_models()
            models = classified_models.get(model_type, {})
            
            return web.json_response({
                "success": True,
                "data": {
                    "checkpoints": {
                        "names": list(models.keys()),
                        "paths": models
                    },
                    "total": len(models)
                }
            })
            
        except ValueError as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
            
    except Exception as e:
        return web.json_response({
            "success": False,
            "error": f"服务器内部错误: {str(e)}"
        }, status=500)


# 注册节点
NODE_CLASS_MAPPINGS = {
    "LoadCheckpoint12": LoadCheckpoint12
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadCheckpoint12": "加载Checkpoint(简易)"
}