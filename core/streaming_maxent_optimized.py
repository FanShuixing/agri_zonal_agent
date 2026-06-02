import numpy as np
import pandas as pd
import rasterio
import requests
import warnings
import json
import geopandas as gpd
from pygbif import occurrences
from pathlib import Path
from requests.adapters import HTTPAdapter
from rasterio.transform import from_origin
from urllib3.util.retry import Retry
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.neighbors import BallTree
from tqdm import tqdm
from core.feature_config import FEATURE_RASTERS
from core.feature_extractor import normalize_numeric
from core.model_registry import save_artifacts

warnings.filterwarnings(
    "ignore",
    message=r"Skipping features without any observed values: \[2\].*",
    category=UserWarning,
)

warnings.filterwarnings(
    "ignore",
    message=".*sklearn.utils.parallel.delayed.*",
    category=UserWarning,
)

# =========================
# 1️⃣ GBIF 分页获取
# =========================
GBIF_API_URL = "https://api.gbif.org/v1/occurrence/search"


def build_retry_session(
    total_retries=5,
    backoff_factor=1.0,
    status_forcelist=(429, 500, 502, 503, 504),
):
    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )

    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": "agri-zonal-agent/1.0 (GBIF occurrence fetcher)",
            "Accept": "application/json",
        }
    )
    return session


def _gbif_search_page(session, batch_size, offset, scientific_name):
    params = {
        "scientificName": scientific_name,
        "hasCoordinate": "true",
        "limit": batch_size,
        "offset": offset,
    }
    response = session.get(GBIF_API_URL, params=params, timeout=(10, 45))
    response.raise_for_status()
    return response.json()


def fetch_occurrence(
    total_limit=8000, batch_size=300, scientific_name="Malus domestica"
):
    all_records = []
    session = build_retry_session()

    offset = 0
    while len(all_records) < total_limit:
        try:
            # 优先沿用 pygbif，兼容当前代码习惯。
            res = occurrences.search(
                scientificName=scientific_name,
                hasCoordinate=True,
                limit=batch_size,
                offset=offset,
                timeout=45,
            )
        except requests.exceptions.SSLError:
            # 某些网络环境下 pygbif 的默认请求链路会出现 TLS EOF，
            # 这里切换到带重试的原生 requests 直连 GBIF API。
            print(f"GBIF SSL 握手异常，切换到直连重试模式，offset={offset}")
            res = _gbif_search_page(session, batch_size, offset, scientific_name)
        except requests.exceptions.RequestException as exc:
            print(f"GBIF 请求失败，切换到直连重试模式，offset={offset}: {exc}")
            res = _gbif_search_page(session, batch_size, offset, scientific_name)

        records = res.get("results", [])
        if not records:
            break

        for r in records:
            lat = r.get("decimalLatitude")
            lon = r.get("decimalLongitude")
            if lat is not None and lon is not None:
                all_records.append({"lat": lat, "lon": lon})
                if len(all_records) >= total_limit:
                    break

        offset += batch_size

    df = pd.DataFrame(all_records)
    return df.dropna()


# =========================
# 2️⃣ 空间稀疏化
# =========================
def spatial_thinning(df, distance_km=10):
    coords = np.radians(df[["lat", "lon"]].values)
    tree = BallTree(coords, metric="haversine")

    keep = np.ones(len(coords), dtype=bool)

    for i in range(len(coords)):
        if not keep[i]:
            continue
        idx = tree.query_radius([coords[i]], r=distance_km / 6371)[0]
        idx = idx[idx > i]
        keep[idx] = False

    return df[keep].reset_index(drop=True)


def haversine_distance_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))


# =========================
# 3️⃣ 环境变量（远程 raster）
# =========================
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "wc2.1_2.5m_bio"
OUTPUT_DIR = BASE_DIR / "output" / "train_output"

bio1 = rasterio.open(DATA_DIR / "wc2.1_2.5m_bio_1.tif")
bio12 = rasterio.open(DATA_DIR / "wc2.1_2.5m_bio_12.tif")
bio5 = rasterio.open(DATA_DIR / "wc2.1_2.5m_bio_5.tif")
bio6 = rasterio.open(DATA_DIR / "wc2.1_2.5m_bio_6.tif")
bio4 = rasterio.open(DATA_DIR / "wc2.1_2.5m_bio_4.tif")
bio15 = rasterio.open(DATA_DIR / "wc2.1_2.5m_bio_15.tif")

# elev = rasterio.open(DATA_DIR / "wc2.1_2.5m_elev.tif")

# FEATURE_RASTERS = [
#     ("bio1_temp", bio1),
#     ("bio12_rain", bio12),
#     ("bio5_max_temp_warmest_month", bio5),
#     ("bio6_min_temp_coldest_month", bio6),
#     ("bio4_temp_seasonality", bio4),
#     ("bio15_precip_seasonality", bio15),
#     # ("elevation", elev),  # ✅ 新增
# ]


# =========================
# 4️⃣ SoilGrids（缓存版🔥）
# =========================
# @lru_cache(maxsize=20000)
# def get_soil_cached(lat, lon):
#     try:
#         url = f"https://rest.soilgrids.org/soilgrids/v2.0/properties/query?lat={lat}&lon={lon}"
#         res = requests.get(url, timeout=5).json()

#         # 简化：取第一个属性（pH）
#         return res["properties"]["layers"][0]["depths"][0]["values"]["mean"]

#     except:
#         return np.nan


# =========================
# 5️⃣ 批量采样 raster（优化）
# =========================
def sample_raster_batch(raster, coords):
    return [v[0] for v in raster.sample(coords)]


# def normalize_numeric(value, nodata=None):
#     if np.ma.is_masked(value):
#         return np.nan

#     try:
#         v = float(value)

#         # 🚨 关键：过滤异常极值
#         if abs(v) > 1e10:
#             return np.nan

#         # 可选：用 raster 自带 nodata
#         if nodata is not None and v == nodata:
#             return np.nan

#         return v

#     except:
#         return np.nan


# =========================
# 6️⃣ 构建特征（优化版）
# =========================
def build_features(df):
    coords = list(zip(df["lon"], df["lat"]))

    sampled_feature_values = [
        sample_raster_batch(raster, coords) for _, raster in FEATURE_RASTERS
    ]

    features = []
    skipped_climate = 0
    # missing_soil = 0

    for i, (lat, lon) in enumerate(tqdm(df.values, desc="Feature Building")):
        feature_row = [
            normalize_numeric(values[i]) for values in sampled_feature_values
        ]

        if any(np.isnan(value) for value in feature_row):
            skipped_climate += 1
            continue

        # ph = normalize_numeric(get_soil_cached(lat, lon))
        # if np.isnan(ph):
        #     missing_soil += 1

        features.append(feature_row)

    print(
        f"有效特征数: {len(features)} / {len(df)} | "
        f"气候缺失跳过: {skipped_climate} | "
    )

    if not features:
        return np.empty((0, len(FEATURE_RASTERS)), dtype=float)

    return np.asarray(features, dtype=float)


def print_feature_summary(name, X):
    if X.size == 0:
        print(f"{name} 特征为空: shape={X.shape}")
        return

    feature_names = [name for name, _ in FEATURE_RASTERS]
    print(f"{name} shape: {X.shape}")
    for idx, feature_name in enumerate(feature_names[: X.shape[1]]):
        column = X[:, idx]
        valid = column[~np.isnan(column)]
        missing = int(np.isnan(column).sum())
        if valid.size == 0:
            print(f"  - {feature_name}: 全部缺失 | missing={missing}")
            continue

        print(
            f"  - {feature_name}: min={valid.min():.4f}, max={valid.max():.4f}, "
            f"mean={valid.mean():.4f}, missing={missing}"
        )


# =========================
# 7️⃣ 背景点（围绕presence🔥）
# =========================
def sample_background_near_presence(
    df,
    n=10000,
    buffer_km=250,
    min_distance_km=20,
    max_attempt_multiplier=20,
    random_state=42,
):
    """
    在 presence 点附近采样背景点，而不是在全球外接框里均匀撒点。

    这样得到的背景点更像“该物种可到达区域中的非出现点”，
    能显著提升 presence/background 的区分度。
    """

    if df.empty:
        raise ValueError("presence 数据为空，无法采样背景点。")

    rng = np.random.default_rng(random_state)
    presence = df[["lat", "lon"]].to_numpy(dtype=float)

    sampled = []
    attempts = 0
    max_attempts = max(n * max_attempt_multiplier, n)

    while len(sampled) < n and attempts < max_attempts:
        attempts += 1

        idx = rng.integers(0, len(presence))
        base_lat, base_lon = presence[idx]

        distance_km = rng.uniform(min_distance_km, buffer_km)
        bearing = rng.uniform(0, 2 * np.pi)

        lat_offset = (distance_km / 111.0) * np.cos(bearing)
        lon_scale = max(np.cos(np.radians(base_lat)), 1e-6)
        lon_offset = (distance_km / (111.0 * lon_scale)) * np.sin(bearing)

        lat = base_lat + lat_offset
        lon = base_lon + lon_offset

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue

        nearest_distance = np.min(
            haversine_distance_km(lat, lon, presence[:, 0], presence[:, 1])
        )
        if nearest_distance < min_distance_km:
            continue

        sampled.append({"lat": lat, "lon": lon})

    if len(sampled) < n:
        print(
            f"背景点采样未达到目标数量: {len(sampled)} / {n}。"
            " 可适当增大 buffer_km 或 max_attempt_multiplier。"
        )

    bg_df = pd.DataFrame(sampled)
    print(
        f"背景点采样完成: {len(bg_df)} 个 | "
        f"buffer_km={buffer_km} | min_distance_km={min_distance_km}"
    )
    return bg_df


# =========================
# 8️⃣ 训练模型
# =========================
from sklearn.ensemble import GradientBoostingClassifier


def train_model(pres_X, bg_X):
    X = np.vstack([pres_X, bg_X])
    y = np.array([1] * len(pres_X) + [0] * len(bg_X))

    imputer = SimpleImputer(strategy="median")
    X_imputed = imputer.fit_transform(X)

    print_feature_summary("presence", pres_X)
    print_feature_summary("background", bg_X)

    # ❌ 不要再做 StandardScaler（树模型不需要）
    model = GradientBoostingClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.8,
        random_state=42,
    )

    model.fit(X_imputed, y)

    print("特征重要性:", model.feature_importances_)

    return model, None, imputer


def save_training_diagnostics(
    model,
    scaler,
    imputer,
    pres_X,
    bg_X,
    threshold,
    output_dir=OUTPUT_DIR,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    diagnostics = {
        "feature_importance": model.feature_importances_.tolist(),
        "n_features_after_impute": int(len(imputer.statistics_)),
        "presence_shape": list(pres_X.shape),
        "background_shape": list(bg_X.shape),
        "threshold": float(threshold),
        "feature_names": [name for name, _ in FEATURE_RASTERS],
    }

    # 保存 JSON（核心）
    json_path = output_dir / "model_diagnostics.json"
    with open(json_path, "w") as f:
        json.dump(diagnostics, f, indent=2)

    # 保存原始特征（用于复盘🔥）
    np.save(output_dir / "pres_X.npy", pres_X)
    np.save(output_dir / "bg_X.npy", bg_X)

    print(f"诊断信息已保存: {json_path}")


def persist_prediction_artifacts(model, imputer, threshold):
    artifact_paths = save_artifacts(model, imputer, threshold=threshold)
    print(f"模型已保存: {artifact_paths['model_path']}")
    print(f"插补器已保存: {artifact_paths['imputer_path']}")
    print(f"元数据已保存: {artifact_paths['metadata_path']}")
    return artifact_paths


# =========================
# 9️⃣ 阈值计算
# =========================
def compute_threshold(model, scaler, imputer, pres_X):
    pres_X_imputed = imputer.transform(pres_X)
    probs = model.predict_proba(pres_X_imputed)[:, 1]
    return np.percentile(probs, 10)


# =========================
# 🔟 全国预测（轻量版）
# =========================
def predict_china(model, scaler, imputer):
    # 中国范围（建议）
    lats = np.linspace(18, 54, 300)
    lons = np.linspace(73, 135, 300)

    # 1️⃣ meshgrid
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    points = np.column_stack([lon_grid.ravel(), lat_grid.ravel()])

    # 2️⃣ 读取中国边界
    china = gpd.read_file("./data/shapfile/china_province.shp")
    china = china.to_crs("EPSG:4326")
    china_geom = china.unary_union

    # 3️⃣ 批量空间判断
    gdf_points = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(points[:, 0], points[:, 1]), crs="EPSG:4326"
    )

    mask = gdf_points.within(china_geom).values

    # 4️⃣ 批量采样 raster
    sampled_feature_values = [
        np.array([normalize_numeric(v[0]) for v in raster.sample(points)])
        for _, raster in FEATURE_RASTERS
    ]

    # 5️⃣ 构建特征
    X_raw = np.column_stack(sampled_feature_values)
    X = imputer.transform(X_raw)

    # 6️⃣ 批量预测
    probs = model.predict_proba(X)[:, 1]
    climate_mask = climate_filter_batch(X_raw)
    # 不满足条件的降权或剔除
    probs[~climate_mask] *= 0  # 或者直接 = 0
    # 7️⃣ 应用 mask
    probs[~mask] = np.nan

    # 8️⃣ reshape
    grid = probs.reshape(len(lats), len(lons))

    print(
        "中国预测输出范围: "
        f"min={np.nanmin(grid):.6f}, max={np.nanmax(grid):.6f}, std={np.nanstd(grid):.6f}"
    )

    return grid


def save_prediction_outputs(grid, output_dir=OUTPUT_DIR):
    output_dir.mkdir(parents=True, exist_ok=True)

    npy_path = output_dir / "china_suitability.npy"
    csv_path = output_dir / "china_suitability.csv"
    tif_path = output_dir / "china_suitability.tif"

    np.save(npy_path, grid)
    pd.DataFrame(grid).to_csv(csv_path, index=False)

    # Keep the GeoTIFF georeferencing aligned with the national prediction grid.
    lats = np.linspace(18, 54, grid.shape[0])
    lons = np.linspace(73, 135, grid.shape[1])
    x_res = (lons[-1] - lons[0]) / (len(lons) - 1)
    y_res = (lats[-1] - lats[0]) / (len(lats) - 1)

    west = lons.min() - x_res / 2
    north = lats.max() + y_res / 2
    transform = from_origin(west, north, x_res, y_res)

    # GeoTIFF 默认按自北向南存储，因此需要把纬度升序网格翻转。
    tif_grid = np.flipud(grid).astype("float32")

    with rasterio.open(
        tif_path,
        "w",
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

    print(f"预测结果已保存: {npy_path}")
    print(f"预测结果已保存: {csv_path}")
    print(f"预测结果已保存: {tif_path}")

    return {"npy": npy_path, "csv": csv_path, "tif": tif_path}


def climate_filter_batch(X):
    bio1 = X[:, 0]
    bio6 = X[:, 3]
    bio12 = X[:, 1]
    # elev = X[:, 6]  # 新增

    return (
        (bio1 > 5)
        & (bio1 < 20)
        & (bio6 < 0)
        & (bio12 < 1500)
        # & (elev > 200)  # ✅ 海拔约束
    )


def filter_presence(df):
    coords = list(zip(df["lon"], df["lat"]))

    bio1_vals = [v[0] for v in bio1.sample(coords)]
    bio6_vals = [v[0] for v in bio6.sample(coords)]

    mask = []
    for b1, b6 in zip(bio1_vals, bio6_vals):
        if np.isnan(b1) or np.isnan(b6):
            mask.append(False)
        elif (5 < b1 < 20) and (b6 < 0):
            mask.append(True)
        else:
            mask.append(False)

    return df[mask]


def filter_presence_by_climate(df):
    coords = list(zip(df["lon"], df["lat"]))

    bio1_vals = [v[0] for v in bio1.sample(coords)]
    bio6_vals = [v[0] for v in bio6.sample(coords)]
    bio12_vals = [v[0] for v in bio12.sample(coords)]

    keep = []
    for b1, b6, b12 in zip(bio1_vals, bio6_vals, bio12_vals):
        if np.isnan(b1) or np.isnan(b6) or np.isnan(b12):
            keep.append(False)
            continue

        # 🌡️ 年均温
        if not (5 < b1 < 20):
            keep.append(False)
            continue

        # ❄️ 冷量（关键）
        if b6 > 0:
            keep.append(False)
            continue

        # 🌧️ 降水
        if b12 > 1500:
            keep.append(False)
            continue

        keep.append(True)

    return df[keep].reset_index(drop=True)


# =========================
# 主流程
# =========================
def run():
    print("1️⃣ 获取GBIF数据")
    df = fetch_occurrence(8000)

    print("🌍 原始点数:", len(df))

    df = filter_presence_by_climate(df)

    print("🌱 气候过滤后:", len(df))

    print("2️⃣ 空间稀疏化")
    df = spatial_thinning(df)

    print(f"保留点数: {len(df)}")

    print("3️⃣ 构建presence特征")
    pres_X = build_features(df)
    pres_X = pres_X[climate_filter_batch(pres_X)]

    print("4️⃣ 背景点")
    bg_df = sample_background_near_presence(df, 10000)
    bg_X = build_features(bg_df)

    print("5️⃣ 训练模型")
    model, scaler, imputer = train_model(pres_X, bg_X)

    print("6️⃣ 计算阈值")
    threshold = compute_threshold(model, scaler, imputer, pres_X)
    print("threshold:", threshold)
    save_training_diagnostics(model, scaler, imputer, pres_X, bg_X, threshold)
    persist_prediction_artifacts(model, imputer, threshold)

    print("7️⃣ 全国预测")
    grid = predict_china(model, scaler, imputer)

    print("8️⃣ 保存结果")
    save_prediction_outputs(grid)

    print("✅ 完成")
    return grid


if __name__ == "__main__":
    run()
