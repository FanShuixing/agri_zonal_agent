from __future__ import annotations

from core.feature_extractor import extract_features
from core.model_registry import load_artifacts, load_metadata
from core.feature_config import FEATURE_RASTERS
from core.feature_extractor import normalize_numeric

MODEL = None
IMPUTER = None
DEFAULT_THRESHOLD = float(load_metadata("apple").get("threshold", 0.3))
_CURRENT_CROP = "apple"


def init_predictor_from_disk(crop: str = "apple"):
    """加载指定作物的模型到全局单例。"""
    model, imputer, threshold = load_artifacts(crop)

    global MODEL, IMPUTER, DEFAULT_THRESHOLD, _CURRENT_CROP
    MODEL = model
    IMPUTER = imputer
    DEFAULT_THRESHOLD = float(threshold)
    _CURRENT_CROP = crop
    return MODEL, IMPUTER, DEFAULT_THRESHOLD


def _get_prediction_artifacts(model=None, imputer=None):
    active_model = MODEL if model is None else model
    active_imputer = IMPUTER if imputer is None else imputer

    if active_model is None or active_imputer is None:
        raise RuntimeError(
            "predict_by_latlon 尚未配置模型。"
            " 请先调用 init_predictor_from_disk() / configure_predictor(...)，"
            " 或在调用时显式传入 model 和 imputer。"
        )

    return active_model, active_imputer


def classify(score, threshold):
    if score > threshold + 0.1:
        return "高度适宜"
    elif score > threshold + 0.03:
        return "适宜"
    elif score > threshold:
        return "临界适宜"
    else:
        return "不适宜"


def predict_location(
    lat: float,
    lon: float,
    model=None,
    imputer=None,
    threshold: float | None = None,
):
    """
    预测给定经纬度位置的适宜性得分和是否适宜种植苹果。
    steps:
        1. 调用 _get_prediction_artifacts 获取模型和 imputer
        2. 使用 imputer 对特征进行预处理
        3. 调用模型进行预测

    通过调用 _get_prediction_artifacts 获取模型和 imputer，可以使用默认的全局配置，也可以在调用时覆盖。

    """
    active_model, active_imputer = _get_prediction_artifacts(model, imputer)
    active_threshold = DEFAULT_THRESHOLD if threshold is None else float(threshold)

    X_raw = extract_features(lat, lon)
    X = active_imputer.transform(X_raw)
    prob = float(active_model.predict_proba(X)[0, 1])
    # suitable = bool(prob > active_threshold)
    suitable = classify(prob, active_threshold)

    return prob, suitable, X_raw


try:
    init_predictor_from_disk("apple")
except FileNotFoundError:
    pass


def predict_province_map2(
    province_name="四川省",
    resolution=200,
    save_path="output/province_map.png",
):
    import matplotlib

    matplotlib.use("Agg")  # 🔥 防止线程报错

    import matplotlib.pyplot as plt
    import geopandas as gpd
    import numpy as np

    print(f"📍 生成 {province_name} 精细化适宜性地图...")
    model, imputer = _get_prediction_artifacts()

    # =========================
    # 1️⃣ 读取省边界
    # =========================
    china = gpd.read_file("./data/shapfile/china_province.shp")
    china = china.to_crs("EPSG:4326")
    print(china.keys(), china["name"])
    province_name = "四川省"
    province = china[china["name"] == province_name]

    if province.empty:
        raise ValueError(f"❌ 未找到省份: {province_name}")

    geom = province.unary_union
    minx, miny, maxx, maxy = geom.bounds

    # =========================
    # 2️⃣ 构建局部 grid
    # =========================
    lons = np.linspace(minx, maxx, resolution)
    lats = np.linspace(miny, maxy, resolution)

    lon_grid, lat_grid = np.meshgrid(lons, lats)
    points = np.column_stack([lon_grid.ravel(), lat_grid.ravel()])

    # =========================
    # 3️⃣ 点 → GeoDataFrame
    # =========================
    gdf_points = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(points[:, 0], points[:, 1]), crs="EPSG:4326"
    )

    # =========================
    # 4️⃣ 只保留省内点（🔥关键）
    # =========================
    mask = gdf_points.within(geom).values

    valid_points = points[mask]

    if len(valid_points) == 0:
        raise ValueError("❌ 该省没有有效点")

    # =========================
    # 5️⃣ 采样气候特征
    # =========================
    sampled_feature_values = [
        np.array([normalize_numeric(v[0]) for v in raster.sample(valid_points)])
        for _, raster in FEATURE_RASTERS
    ]

    X_raw = np.column_stack(sampled_feature_values)
    X = imputer.transform(X_raw)

    # =========================
    # 6️⃣ 预测
    # =========================
    probs = model.predict_proba(X)[:, 1]

    # 👉 气候过滤（你已有）
    climate_mask = climate_filter_batch(X_raw)
    probs[~climate_mask] *= 0.1

    # =========================
    # 7️⃣ 画图（🔥核心）
    # =========================
    fig, ax = plt.subplots(figsize=(6, 6))

    sc = ax.scatter(
        valid_points[:, 0],
        valid_points[:, 1],
        c=probs,
        cmap="YlOrRd",
        s=5,
    )

    # 👇 关键：指定 ax
    province.boundary.plot(ax=ax, color="black", linewidth=1)

    plt.colorbar(sc, ax=ax, label="Suitability")

    ax.set_title(f"{province_name} 苹果种植适宜性分布")

    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    plt.savefig(save_path, dpi=300)
    plt.close()

    print(f"✅ 地图已保存: {save_path}")
    print("valid_points:", len(valid_points))
    print("probs nan:", np.isnan(probs).sum())
    print("probs min/max:", np.nanmin(probs), np.nanmax(probs))
    print("高值点数量:", (probs > 0.05).sum())
    print(valid_points)

    # =========================
    # 8️⃣ 返回统计信息（给Agent用）
    # =========================
    return {
        "province": province_name,
        "mean_score": float(np.nanmean(probs)),
        "max_score": float(np.nanmax(probs)),
        "min_score": float(np.nanmin(probs)),
        "map_path": save_path,
    }


from scipy.ndimage import binary_opening, binary_closing


def predict_province_map(
    province_name="四川省",
    resolution=300,
    save_path="output/province_map_pro.png",
):
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt
    import geopandas as gpd
    import numpy as np
    from scipy.ndimage import gaussian_filter

    print(f"📍 生成【论文级】{province_name} 适宜性地图...")

    model, imputer = _get_prediction_artifacts()

    # =========================
    # 1️⃣ 省边界
    # =========================
    china = gpd.read_file("./data/shapfile/china_province.shp")
    china = china.to_crs("EPSG:4326")
    province_name = "四川省"
    province = china[china["name"] == province_name]
    if province.empty:
        raise ValueError(f"❌ 未找到省份: {province_name}")

    geom = province.unary_union
    minx, miny, maxx, maxy = geom.bounds

    # =========================
    # 2️⃣ grid
    # =========================
    lons = np.linspace(minx, maxx, resolution)
    lats = np.linspace(miny, maxy, resolution)

    lon_grid, lat_grid = np.meshgrid(lons, lats)
    points = np.column_stack([lon_grid.ravel(), lat_grid.ravel()])

    # =========================
    # 3️⃣ mask（省内点）
    # =========================
    gdf_points = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(points[:, 0], points[:, 1]), crs="EPSG:4326"
    )

    mask = gdf_points.within(geom).values

    # =========================
    # 4️⃣ 采样气候
    # =========================
    sampled_feature_values = [
        np.array([normalize_numeric(v[0]) for v in raster.sample(points)])
        for _, raster in FEATURE_RASTERS
    ]

    X_raw = np.column_stack(sampled_feature_values)
    X = imputer.transform(X_raw)

    probs = model.predict_proba(X)[:, 1]

    # 👉 气候过滤
    climate_mask = climate_filter_batch(X_raw)
    probs[~climate_mask] *= 0.1

    # =========================
    # 5️⃣ reshape成grid（🔥关键）
    # =========================
    grid = probs.reshape(resolution, resolution)

    # 省外设为 nan
    grid_flat = grid.ravel()
    grid_flat[~mask] = np.nan
    grid = grid_flat.reshape(resolution, resolution)

    # =========================
    # 6️⃣ 平滑（🔥论文级关键）
    # =========================
    grid_smooth = gaussian_filter(grid, sigma=1.2)

    # =========================
    # 7️⃣ 阈值区域
    # =========================
    from core.model_registry import load_model_threshold
    threshold = load_model_threshold()
    suitable_mask = grid_smooth >= threshold
    suitable_mask = binary_opening(suitable_mask, structure=np.ones((3, 3)))
    suitable_mask = binary_closing(suitable_mask, structure=np.ones((5, 5)))

    # =========================
    # 8️⃣ 画图（🔥最终版）
    # =========================
    fig, ax = plt.subplots(figsize=(8, 6))

    # 🌈 连续热力图
    im = ax.imshow(
        grid_smooth,
        extent=[minx, maxx, miny, maxy],
        origin="lower",
        cmap="YlOrRd",
        vmin=0,
        vmax=np.nanpercentile(grid_smooth, 98),
    )

    # 🔴 阈值等值线（核心）
    ax.contour(
        lon_grid,
        lat_grid,
        suitable_mask,
        levels=[0.5],
        colors="red",
        linewidths=1.5,
    )
    ax.text(102, 28, "高适宜区", fontsize=10, color="darkred")
    # ⚫ 边界
    province.boundary.plot(ax=ax, color="black", linewidth=1)

    # 色条
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Apple Suitability Probability")

    ax.set_title(f"{province_name} 苹果种植适宜性分布（模型预测）")

    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"✅ 地图已保存: {save_path}")

    # =========================
    # 9️⃣ 统计（给Agent🔥）
    # =========================
    valid = ~np.isnan(grid_smooth)

    return {
        "province": province_name,
        "mean_score": float(np.nanmean(grid_smooth)),
        "max_score": float(np.nanmax(grid_smooth)),
        "suitable_ratio": float(np.mean(grid_smooth[valid] >= threshold)),
        "map_path": save_path,
    }
