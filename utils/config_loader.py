from pathlib import Path
import yaml
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]

CONFIG_PATH = BASE_DIR / "config" / "apple_config.yaml"


def resolve_path(relative_path: str) -> Path:
    return BASE_DIR / relative_path


def convert_paths(obj):
    """
    递归转换所有 path 字段为 Path 对象
    """

    if isinstance(obj, dict):

        new_dict = {}

        for key, value in obj.items():

            # 如果 key 包含 path
            if isinstance(value, str) and (
                "path" in key
                or "dir" in key
                or key.endswith("_shp")
                or key.endswith("_tif")
            ):
                new_dict[key] = resolve_path(value)

            else:
                new_dict[key] = convert_paths(value)

        return new_dict

    elif isinstance(obj, list):

        return [convert_paths(i) for i in obj]

    return obj


def load_config():

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:

        config = yaml.safe_load(f)

    config = convert_paths(config)

    return config


CONFIG: dict[str, Any] = load_config()
