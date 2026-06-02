from __future__ import annotations

import json
from pathlib import Path

import joblib

BASE_DIR = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = BASE_DIR / "artifacts" / "apple"
MODEL_PATH = ARTIFACT_DIR / "model.pkl"
IMPUTER_PATH = ARTIFACT_DIR / "imputer.pkl"
METADATA_PATH = ARTIFACT_DIR / "metadata.json"


def load_metadata():
    if not METADATA_PATH.exists():
        return {}

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_artifacts(model, imputer, threshold: float | None = None):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(imputer, IMPUTER_PATH)

    metadata = {}
    if threshold is not None:
        metadata["threshold"] = float(threshold)

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return {
        "model_path": MODEL_PATH,
        "imputer_path": IMPUTER_PATH,
        "metadata_path": METADATA_PATH,
    }


def load_artifacts():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"未找到模型文件: {MODEL_PATH}")
    if not IMPUTER_PATH.exists():
        raise FileNotFoundError(f"未找到插补器文件: {IMPUTER_PATH}")

    model = joblib.load(MODEL_PATH)
    imputer = joblib.load(IMPUTER_PATH)

    metadata = load_metadata()
    threshold = metadata.get("threshold")

    return model, imputer, threshold
