from __future__ import annotations

import json
from pathlib import Path

import joblib

BASE_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = BASE_DIR / "output" / "models"

# ── 向后兼容：无 crop 参数时的默认值 ──────────────────────────
DEFAULT_CROP = "apple"


def model_dir(crop: str = DEFAULT_CROP) -> Path:
    """返回指定作物的模型目录。"""
    return MODELS_DIR / crop


def list_models() -> list[str]:
    """列出所有已训练的作物。"""
    if not MODELS_DIR.exists():
        return []
    return sorted(
        d.name for d in MODELS_DIR.iterdir()
        if d.is_dir() and (d / "metadata.json").exists()
    )


def model_exists(crop: str) -> bool:
    """检查作物是否有已训练的模型。"""
    return (model_dir(crop) / "metadata.json").exists()


def _metadata_path(crop: str) -> Path:
    return model_dir(crop) / "metadata.json"


def _model_path(crop: str) -> Path:
    return model_dir(crop) / "model.pkl"


def _imputer_path(crop: str) -> Path:
    return model_dir(crop) / "imputer.pkl"


def load_metadata(crop: str = DEFAULT_CROP):
    """读取训练产出的元数据。"""
    path = _metadata_path(crop)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_model_threshold(crop: str = DEFAULT_CROP, default: float = 0.3) -> float:
    """读取模型阈值，metadata.json 不存在时返回 default。"""
    meta = load_metadata(crop)
    return float(meta.get("threshold", default))


def save_artifacts(
    model,
    imputer,
    threshold: float | None = None,
    eval_metrics: dict | None = None,
    crop: str = DEFAULT_CROP,
) -> dict:
    """保存模型、插补器和元数据到 output/models/{crop}/。"""
    mdir = model_dir(crop)
    mdir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, _model_path(crop))
    joblib.dump(imputer, _imputer_path(crop))

    metadata = {}
    if threshold is not None:
        metadata["threshold"] = float(threshold)
    if eval_metrics is not None:
        metadata["eval_metrics"] = eval_metrics

    with open(_metadata_path(crop), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return {
        "model_path": str(_model_path(crop)),
        "imputer_path": str(_imputer_path(crop)),
        "metadata_path": str(_metadata_path(crop)),
    }


def load_artifacts(crop: str = DEFAULT_CROP):
    """加载模型、插补器和阈值。"""
    mp = _model_path(crop)
    ip = _imputer_path(crop)

    if not mp.exists():
        raise FileNotFoundError(f"未找到模型文件: {mp}")
    if not ip.exists():
        raise FileNotFoundError(f"未找到插补器文件: {ip}")

    model = joblib.load(mp)
    imputer = joblib.load(ip)

    metadata = load_metadata(crop)
    threshold = metadata.get("threshold")

    return model, imputer, threshold
