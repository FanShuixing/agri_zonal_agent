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
