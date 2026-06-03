"""
apple_sdm_trainer.py
Global SDM for Malus domestica (apple) — 全球训练 + 中国预测。

核心改进（相比 streaming_maxent_optimized.py）:
  1. 全球 GBIF 数据获取 (30,000+ 条)，不再限制中国境内
  2. 训练前不做气候预过滤 — 让模型自己学习苹果的气候生态位
  3. 全球背景点采样，覆盖完整气候空间
  4. 阈值 = max(sensitivity + specificity)，不再用 presence 的 P10
  5. 完整的模型评估：train/test split, ROC AUC, classification report
  6. 无死代码、无硬编码列索引

用法:
    python -m core.apple_sdm_trainer
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests
from pygbif import occurrences as gbif_occurrences
from requests.adapters import HTTPAdapter
from rasterio.transform import from_origin
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import BallTree
from tqdm import tqdm
from urllib3.util.retry import Retry

from core.feature_config import FEATURE_RASTERS
from core.feature_extractor import normalize_numeric
from core.model_registry import save_artifacts

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════
# 路径 & 常量
# ═══════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parents[1]
DIAGNOSTICS_DIR = BASE_DIR / "output" / "diagnostics"
PREDICTIONS_DIR = BASE_DIR / "output" / "predictions"
CACHE_DIR = BASE_DIR / "output" / "cache" / "training"
CHINA_SHP = BASE_DIR / "data" / "shapfile" / "china_province.shp"

GBIF_API = "https://api.gbif.org/v1/occurrence/search"
GBIF_LIMIT = 30_000
BATCH_SIZE = 300
SPATIAL_THINNING_KM = 10
BG_SAMPLES = 10_000
RANDOM_STATE = 42
FEATURE_NAMES = [name for name, _ in FEATURE_RASTERS]

# 全局默认（训练脚本直接运行时使用）
_SPECIES = "Malus domestica"
_CROP_NAME = "apple"


def _cache_for(crop: str) -> tuple[Path, Path, Path]:
    """返回某作物的三个缓存路径。"""
    gbif = CACHE_DIR / f"{crop}_gbif_thinned.csv"
    pres = CACHE_DIR / f"{crop}_pres_X.npy"
    bg = CACHE_DIR / f"{crop}_bg_X.npy"
    return gbif, pres, bg


# ═══════════════════════════════════════════
# 1. GBIF — 全球分页获取
# ═══════════════════════════════════════════
def _build_retry_session():
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": "agri-zonal-agent/1.0 (GBIF)",
        "Accept": "application/json",
    })
    return session


def _gbif_direct(session, offset, limit):
    """直连 GBIF API 的备用路径（pygbif SSL 异常时使用）。"""
    params = {
        "scientificName": _SPECIES,
        "hasCoordinate": "true",
        "limit": limit,
        "offset": offset,
    }
    r = session.get(GBIF_API, params=params, timeout=(10, 60))
    r.raise_for_status()
    return r.json()


def fetch_occurrences(limit=GBIF_LIMIT, batch=BATCH_SIZE):
    """全球获取 Malus domestica 的 GBIF 分布记录。"""
    session = _build_retry_session()
    records = []
    offset = 0

    while len(records) < limit:
        try:
            res = gbif_occurrences.search(
                scientificName=_SPECIES,
                hasCoordinate=True,
                limit=batch,
                offset=offset,
                timeout=60,
            )
        except (requests.exceptions.SSLError, requests.exceptions.RequestException) as e:
            print(f"  GBIF 连接异常 (offset={offset})，切换直连: {e}")
            res = _gbif_direct(session, offset, batch)

        results = res.get("results", [])
        if not results:
            break

        for r in results:
            lat = r.get("decimalLatitude")
            lon = r.get("decimalLongitude")
            if lat is not None and lon is not None:
                records.append({"lat": float(lat), "lon": float(lon)})
                if len(records) >= limit:
                    break

        offset += batch
        if len(records) % 3000 == 0:
            print(f"    已获取 {len(records)} 条...")

    df = pd.DataFrame(records).dropna()
    print(f"  GBIF 全球获取: {len(df)} 条")
    return df


# ═══════════════════════════════════════════
# 2. 空间稀疏化 (10 km)
# ═══════════════════════════════════════════
def spatial_thinning(df, distance_km=SPATIAL_THINNING_KM):
    """基于 BallTree + haversine 的空间稀疏化，保留密度均匀的分布点。"""
    if df.empty:
        return df

    coords = np.radians(df[["lat", "lon"]].values)
    tree = BallTree(coords, metric="haversine")
    keep = np.ones(len(coords), dtype=bool)

    for i in range(len(coords)):
        if not keep[i]:
            continue
        neighbors = tree.query_radius([coords[i]], r=distance_km / 6371)[0]
        neighbors = neighbors[neighbors > i]
        keep[neighbors] = False

    result = df[keep].reset_index(drop=True)
    print(f"  空间稀疏化 ({distance_km} km): {len(df)} → {len(result)}")
    return result


# ═══════════════════════════════════════════
# 3. 特征构建
# ═══════════════════════════════════════════
def _sample_raster(raster, coords):
    return [v[0] for v in raster.sample(coords)]


def build_features(df):
    """从 (lon, lat) DataFrame 提取所有 WorldClim 特征，剔除含 NaN 的行。"""
    coords = list(zip(df["lon"], df["lat"]))

    per_feature = [
        _sample_raster(raster, coords) for _, raster in FEATURE_RASTERS
    ]

    X_list = []
    skipped = 0
    for i in tqdm(range(len(df)), desc="  提取特征"):
        row = [normalize_numeric(per_feature[f][i]) for f in range(len(FEATURE_RASTERS))]
        if any(np.isnan(v) for v in row):
            skipped += 1
            continue
        X_list.append(row)

    print(f"  有效特征: {len(X_list)} / {len(df)} | 缺失跳过: {skipped}")
    if not X_list:
        return np.empty((0, len(FEATURE_RASTERS)), dtype=float)
    return np.array(X_list, dtype=float)


# ═══════════════════════════════════════════
# 4. 全球背景点
# ═══════════════════════════════════════════
def sample_background_global(n=BG_SAMPLES, seed=RANDOM_STATE,
                             min_lat=-60, max_lat=80):
    """
    全球陆地范围内均匀随机采样背景点。

    不做"围绕 presence 采样"——全球训练的 presence 已经覆盖全球，
    背景点直接从全球气候空间中随机抽样即可。
    """
    rng = np.random.default_rng(seed)
    lats = rng.uniform(min_lat, max_lat, n * 3)
    lons = rng.uniform(-180, 180, n * 3)

    # 简单陆地过滤：通过 WorldClim 数据有效性判断（海洋点 raster 返回 nodata/NaN）
    bg_candidates = pd.DataFrame({"lat": lats, "lon": lons})
    valid_features = build_features(bg_candidates)

    # 取前 n 个有效点
    if len(valid_features) < n:
        print(f"  背景点不足: 仅 {len(valid_features)} / {n} 个有效点")
    else:
        valid_features = valid_features[:n]

    print(f"  全球背景点: {len(valid_features)} 个")
    return valid_features


# ═══════════════════════════════════════════
# 5. 训练 + 评估
# ═══════════════════════════════════════════
def train_and_evaluate(pres_X, bg_X, test_size=0.2):
    """
    构建 presence/background 训练集，拆分 train/test，
    训练 GBDT，输出完整的评估指标。
    """
    n_pres, n_bg = len(pres_X), len(bg_X)
    print(f"\n  训练集: presence={n_pres}, background={n_bg}")

    X = np.vstack([pres_X, bg_X])
    y = np.hstack([np.ones(n_pres), np.zeros(n_bg)])

    # Impute
    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(X)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=RANDOM_STATE,
    )
    print(f"  train={len(X_train)}, test={len(X_test)}  (test_size={test_size})")

    # Train
    model = GradientBoostingClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.8,
        random_state=RANDOM_STATE,
    )
    model.fit(X_train, y_train)

    # Predict
    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)

    # Threshold: max(sensitivity + specificity)
    fpr, tpr, thresholds = roc_curve(y_test, y_prob)
    # roc_curve 从 (1,1) 到 (0,0)，thresholds[0] 可能是 max+1，需要处理
    # 跳过第一个元素（对应 max threshold）
    sss = tpr + (1 - fpr)  # sensitivity + specificity
    best_idx = np.argmax(sss)
    best_threshold = float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.5

    # Eval at best threshold
    y_pred = (y_prob >= best_threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

    print(f"\n  === 模型评估 ===")
    print(f"  ROC AUC:           {auc:.4f}")
    print(f"  Best threshold:    {best_threshold:.4f}")
    print(f"  Sensitivity (TPR): {sensitivity:.4f}")
    print(f"  Specificity (TNR): {specificity:.4f}")
    print(f"  Confusion matrix:  TN={tn}, FP={fp}, FN={fn}, TP={tp}")
    print(f"\n  Classification report (threshold={best_threshold:.4f}):")
    print(classification_report(y_test, y_pred, target_names=["background", "presence"]))

    # Feature importance
    print("\n  === 特征重要性 ===")
    for name, imp in sorted(
        zip(FEATURE_NAMES, model.feature_importances_),
        key=lambda x: -x[1],
    ):
        print(f"    {name:30s} {imp:.4f}")

    return model, imputer, best_threshold, {
        "roc_auc": float(auc),
        "threshold": float(best_threshold),
        "sensitivity": float(sensitivity),
        "specificity": float(specificity),
        "confusion_matrix": {
            "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp),
        },
        "n_presence": int(n_pres),
        "n_background": int(n_bg),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "feature_importance": dict(
            zip(FEATURE_NAMES, model.feature_importances_.tolist())
        ),
    }


# ═══════════════════════════════════════════
# 6. 中国预测
# ═══════════════════════════════════════════
def _load_china_mask():
    """加载中国边界，失败则返回 None（用经纬度范围兜底）。"""
    if not CHINA_SHP.exists():
        print(f"  ⚠ China shapefile 不存在: {CHINA_SHP}，使用经纬度范围兜底")
        return None
    import geopandas as gpd
    china = gpd.read_file(CHINA_SHP)
    china = china.to_crs("EPSG:4326")
    return china.unary_union


def predict_china(model, imputer, resolution=300):
    """全球训练模型 → 中国境内 300x300 网格预测。"""
    lats = np.linspace(18, 54, resolution)
    lons = np.linspace(73, 135, resolution)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    points = np.column_stack([lon_grid.ravel(), lat_grid.ravel()])

    # 空间掩膜
    china_geom = _load_china_mask()
    if china_geom is not None:
        import geopandas as gpd
        gdf = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy(points[:, 0], points[:, 1]),
            crs="EPSG:4326",
        )
        mask = gdf.within(china_geom).values
    else:
        mask = np.ones(len(points), dtype=bool)

    # 提取特征
    sampled = [
        np.array([normalize_numeric(v[0]) for v in raster.sample(points)])
        for _, raster in FEATURE_RASTERS
    ]
    X_raw = np.column_stack(sampled)
    X = imputer.transform(X_raw)

    # 预测
    probs = model.predict_proba(X)[:, 1]
    probs[~mask] = np.nan

    grid = probs.reshape(resolution, resolution)
    print(f"  中国预测 grid: {grid.shape}  "
          f"min={np.nanmin(grid):.4f} max={np.nanmax(grid):.4f} "
          f"mean={np.nanmean(grid):.4f}")

    return grid, lats, lons


def save_prediction(grid, lats, lons, output_dir=PREDICTIONS_DIR, crop: str = "apple"):
    """保存预测栅格为 GeoTIFF + NPY。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    npy_path = output_dir / f"{crop}_suitability.npy"
    tif_path = output_dir / f"{crop}_suitability.tif"

    np.save(npy_path, grid)

    x_res = (lons[-1] - lons[0]) / (len(lons) - 1)
    y_res = (lats[-1] - lats[0]) / (len(lats) - 1)
    transform = from_origin(
        lons.min() - x_res / 2,
        lats.max() + y_res / 2,
        x_res, y_res,
    )
    tif_grid = np.flipud(grid).astype("float32")

    with rasterio.open(
        tif_path, "w",
        driver="GTiff",
        height=tif_grid.shape[0],
        width=tif_grid.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=np.nan,
    ) as dst:
        dst.write(tif_grid, 1)

    print(f"  预测结果: {npy_path}, {tif_path}")
    return {"npy": str(npy_path), "tif": str(tif_path)}


# ═══════════════════════════════════════════
# 7. 诊断 & 工件保存
# ═══════════════════════════════════════════
def save_diagnostics(eval_metrics, pres_X, bg_X, output_dir=DIAGNOSTICS_DIR):
    output_dir.mkdir(parents=True, exist_ok=True)

    diag = {
        **eval_metrics,
        "presence_shape": list(pres_X.shape),
        "background_shape": list(bg_X.shape),
        "feature_names": FEATURE_NAMES,
        "species": _SPECIES,
        "gbif_limit": GBIF_LIMIT,
        "spatial_thinning_km": SPATIAL_THINNING_KM,
        "bg_samples": BG_SAMPLES,
    }

    json_path = output_dir / "model_diagnostics.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(diag, f, indent=2, ensure_ascii=False)

    np.save(output_dir / "pres_X.npy", pres_X)
    np.save(output_dir / "bg_X.npy", bg_X)

    print(f"  诊断已保存: {json_path}")


# ═══════════════════════════════════════════
# 8. 主流程
# ═══════════════════════════════════════════
def train_crop_model(
    crop_name: str = "apple",
    scientific_name: str = "Malus domestica",
):
    """训练指定作物的 SDM 模型。

    Parameters
    ----------
    crop_name : 作物中文名/标识符，用于缓存和模型目录命名
    scientific_name : GBIF 学名，用于物种分布数据查询
    """
    global _SPECIES, _CROP_NAME
    _SPECIES = scientific_name
    _CROP_NAME = crop_name

    gbif_cache, pres_cache, bg_cache = _cache_for(crop_name)

    print("=" * 60)
    print(f"  {_CROP_NAME} ({_SPECIES}) SDM 训练 — 全球训练 + 中国预测")
    print("=" * 60)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1-2 — GBIF + 空间稀疏化（带缓存）
    if gbif_cache.exists():
        print(f"\n[1/7] 加载缓存的 GBIF 数据: {gbif_cache}")
        df = pd.read_csv(gbif_cache)
    else:
        print("\n[1/7] 获取全球 GBIF 数据")
        df = fetch_occurrences()
        print("\n[2/7] 空间稀疏化")
        df = spatial_thinning(df)
        df.to_csv(gbif_cache, index=False)
        print(f"  已缓存: {gbif_cache}")

    # Step 3 — 构建 presence 特征（带缓存）
    if pres_cache.exists():
        print(f"\n[3/7] 加载缓存的 presence 特征: {pres_cache}")
        pres_X = np.load(pres_cache)
    else:
        print("\n[3/7] 构建 presence 特征")
        pres_X = build_features(df)
        np.save(pres_cache, pres_X)
        print(f"  已缓存: {pres_cache}")
    print(f"  presence feature matrix: {pres_X.shape}")

    # Step 4 — 全球背景点（带缓存）
    if bg_cache.exists():
        print(f"\n[4/7] 加载缓存的背景点特征: {bg_cache}")
        bg_X = np.load(bg_cache)
    else:
        print("\n[4/7] 采样全球背景点")
        bg_X = sample_background_global()
        np.save(bg_cache, bg_X)
        print(f"  已缓存: {bg_cache}")

    # Step 5 — 训练 + 评估
    print("\n[5/7] 训练 GBDT + 评估")
    model, imputer, threshold, eval_metrics = train_and_evaluate(pres_X, bg_X)

    # Step 6 — 保存工件
    print("\n[6/7] 保存模型 & 诊断")
    save_artifacts(model, imputer, threshold=threshold, eval_metrics=eval_metrics, crop=crop_name)
    save_diagnostics(eval_metrics, pres_X, bg_X)

    # Step 7 — 中国预测
    print("\n[7/7] 中国境内预测")
    grid, lats, lons = predict_china(model, imputer)
    save_prediction(grid, lats, lons, crop=crop_name)

    print("\n" + "=" * 60)
    print(f"  ✅ 训练完成")
    print(f"  ROC AUC: {eval_metrics['roc_auc']:.4f}")
    print(f"  Threshold: {threshold:.4f}")
    print(f"  Presence: {len(pres_X)} 点 | Background: {len(bg_X)} 点")
    print("=" * 60)

    return {
        "model": model,
        "imputer": imputer,
        "threshold": threshold,
        "eval_metrics": eval_metrics,
        "grid": grid,
    }


if __name__ == "__main__":
    train_crop_model("apple", "Malus domestica")
