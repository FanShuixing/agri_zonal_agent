import geopandas as gpd
from rasterstats import zonal_stats
from utils.config_loader import CONFIG
import numpy as np


def compute_region_zonal_stats(
    region_gdf,
    raster_path=CONFIG["paths"]["raster"]["china_suitability_tf"],
    region_name_field="name",
):
    """
    对每个行政区计算适宜性统计
    """

    stats = zonal_stats(
        region_gdf,
        raster_path,
        stats=["mean", "max", "min"],
        geojson_out=True,
        nodata=0,
        raster_out=True,
    )

    results = []

    for item in stats:
        props = item["properties"]

        city_array = np.array(props["mini_raster_array"]).astype(
            float
        )  # 转为 numpy 数组，方便后续计算

        results.append(
            {
                "region": props[region_name_field],
                "mean_score": round(props["mean"] or 0, 4),
                "max_score": round(props["max"] or 0, 4),
                "min_score": round(props["min"] or 0, 4),
                "city_array": city_array,
            }
        )

    return results


def compute_suitability_stats(array, grading_system):
    """
    计算适宜性统计信息
    """

    # 去除 nan
    valid = array[~np.isnan(array)]

    if len(valid) == 0:
        return {
            "mean_score": None,
            "max_score": None,
            "min_score": None,
            "high_ratio": 0,
            "medium_ratio": 0,
            "low_ratio": 0,
        }

    # 基础统计
    mean_score = float(np.mean(valid))
    max_score = float(np.max(valid))
    min_score = float(np.min(valid))

    return {
        "mean_score": round(mean_score, 4),
        "max_score": round(max_score, 4),
        "min_score": round(min_score, 4),
    }
