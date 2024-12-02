import random
from typing import List

class RandomChoiceList:
    """从列表中随机选择一个元素的节点"""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_list": ("SIMPLE_PROMPT_LIST",),  # 使用多行字符串输入作为列表
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "The random seed used for creating the noise."}),  # 添加随机种子输入
            }
        }
    
    RETURN_TYPES = ("STRING",)
    FUNCTION = "random_choice"
    CATEGORY = "utils"
    
    def random_choice(self, input_list: List[str], seed: int) -> tuple[str]:
        """从输入列表中随机选择一个元素"""
        if not input_list:
            raise ValueError("输入列表不能为空")
        print(seed)
        # 随机选择一个元素并返回
        # ComfyUI要求返回tuple，所以用(result,)的形式
        return (random.choice(input_list),)

# 注册节点
NODE_CLASS_MAPPINGS = {
    "RandomChoiceList": RandomChoiceList
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomChoiceList": "随机选择(列表)"
} 