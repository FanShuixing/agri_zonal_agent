"""
将json内容加载到本地
"""

import json
from pathlib import Path


def save_json(data: dict, save_path: str):
    """
    将 JSON 数据保存到本地文件

    Args:
        data (dict): 要保存的数据
        save_path (str): 保存路径
    """

    save_path = Path(save_path)

    # 自动创建目录
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入 JSON
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"JSON 已保存: {save_path}")
    return save_path


def load_json(json_path: str | Path):
    """读取 JSON 文件"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


# 合并json，加载图片路径
def merge_json(report_path: str | Path, context_path: str | Path):
    """合并json，加载图片路径"""
    data = load_json(report_path)
    context_data = load_json(context_path)
    # 将context_data中的图片路径添加到report_data中
    data["images"] = context_data["artifacts"]
    return data
