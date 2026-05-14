import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from pathlib import Path
from rasterio.mask import mask
from service.raster_service import clip_raster_by_region
from service.region_service import _match_region, get_region_context
from service.map_render_service import render_map
from service.spatial_analysis_service import compute_suitability_stats

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TIF = BASE_DIR / "output" / "china_suitability.tif"
DEFAULT_OUTPUT = BASE_DIR / "output" / "region_map.png"
SHP_MAP = {
    "province": BASE_DIR / "data" / "shapfile" / "china_province.shp",
    "county": BASE_DIR / "data" / "shapfile" / "china_county.shp",
}

CLIP_SHP = {
    "province": BASE_DIR / "data" / "shapfile" / "china_province.shp",
    "city": BASE_DIR / "data" / "shapfile" / "china_city.shp",
}

DISPLAY_SHP = {
    "province": BASE_DIR / "data" / "shapfile" / "china_province.shp",
    "city": BASE_DIR / "data" / "shapfile" / "china_city.shp",  # ✅ 加这个
    "county": BASE_DIR / "data" / "shapfile" / "china_county.shp",
}


def generate_region_map(region_name, mode="province"):
    """
    mode:
    - province
    - city
    - county
    """

    # =========================
    # 1️⃣ 判断模式
    # =========================
    clip_map = get_region_context(region_name)
    clip_region = clip_map["clip_region"]
    clip_geom = clip_map["clip_geom"]
    display_level = clip_map["display_level"]
    # =========================
    # 2️⃣ 裁剪 raster
    # =========================
    raster_result = clip_raster_by_region(DEFAULT_TIF, clip_region)
    array = raster_result["array"]
    left, right, bottom, top = raster_result["bounds"]
    crs = raster_result["crs"]

    # =========================
    # 3️⃣ 读取边界
    # =========================

    # 🔴 省边界（一定要画）
    province_boundary = None
    if region_name.endswith("省") or region_name in ["中国", "全国"]:
        province_gdf = gpd.read_file(CLIP_SHP["province"])
        province_gdf = province_gdf.to_crs(crs)

        if clip_geom is not None:
            province_region = _match_region(province_gdf, region_name, "province")
            province_boundary = province_region
        else:
            province_boundary = province_gdf

    # 🟡 市/县边界（内部细分）
    display_gdf = gpd.read_file(DISPLAY_SHP[display_level])
    display_gdf = display_gdf.to_crs(crs)
    clip_region = clip_region.to_crs(crs)

    if clip_geom is not None:
        display_gdf = gpd.overlay(display_gdf, clip_region, how="intersection")
    # print("display_gdf len:", len(display_gdf))
    # print(display_gdf.total_bounds)
    # print(f"left: {left}, right: {right}, bottom: {bottom}, top: {top}")

    # =========================
    # 4️⃣ 画图（分层绘制）
    # =========================
    render_map(
        array=array,
        left=left,
        right=right,
        bottom=bottom,
        top=top,
        output_path=DEFAULT_OUTPUT,
        display_gdf=display_gdf,
        province_boundary=province_boundary,
    )
    stats = compute_suitability_stats(array)
    return {"stats": stats, "apple_suitability_map_path": str(DEFAULT_OUTPUT)}


if __name__ == "__main__":
    # 测试函数
    region_name = "四川省"
    level = "province"
    map_path = generate_region_map(region_name, level)
    print(f"地图已保存到: {map_path}")
