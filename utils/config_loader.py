from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parents[1]

CONFIG_PATH = BASE_DIR / "config" / "apple_config.yaml"


def load_config():

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:

        config = yaml.safe_load(f)
        config["suitability_map_path"] = BASE_DIR / config["suitability_map_path"]
        config["ranking_table_path"] = BASE_DIR / config["ranking_table_path"]
        config["score_range_chart_path"] = BASE_DIR / config["score_range_chart_path"]

    return config


# 全局配置
CONFIG = load_config()
