from pathlib import Path
from utils.config_loader import CONFIG
import geopandas as gpd
from raw_layer.geo.raster_service import clip_raster_by_region
from raw_layer.geo.region_service import (
    get_region_context,
    _match_region,
)

from report_layer.map_render_service import render_map

from raw_layer.stats.suitability_analysis import (
    compute_region_suitability_analysis,
)

RASTER_PATH = Path(CONFIG["paths"]["raster"]["china_suitability_tf"])
SHAPEFILE_PATHS = {
    "province": Path(CONFIG["paths"]["shapefile"]["province"]),
    "city": Path(CONFIG["paths"]["shapefile"]["city"]),
    "county": Path(CONFIG["paths"]["shapefile"]["county"]),
}


def prepare_region_map_data(region_name: str) -> dict:
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
    raster_result = clip_raster_by_region(RASTER_PATH, clip_region)
    array = raster_result["array"]
    left, right, bottom, top = raster_result["bounds"]
    crs = raster_result["crs"]

    # =========================
    # 3️⃣ 读取边界
    # =========================

    # 🔴 省边界（一定要画）
    province_boundary = None
    if region_name.endswith("省") or region_name in ["中国", "全国"]:
        province_gdf = gpd.read_file(SHAPEFILE_PATHS["province"])
        province_gdf = province_gdf.to_crs(crs)

        if clip_geom is not None:
            province_region = _match_region(province_gdf, region_name, "province")
            province_boundary = province_region
        else:
            province_boundary = province_gdf

    # 🟡 市/县边界（内部细分）
    display_gdf = gpd.read_file(SHAPEFILE_PATHS[display_level])
    display_gdf = display_gdf.to_crs(crs)

    if clip_geom is not None:
        clip_region = clip_region.to_crs(crs)
        display_gdf = gpd.overlay(display_gdf, clip_region, how="intersection")
    return {
        "array": array,
        "left": left,
        "right": right,
        "bottom": bottom,
        "top": top,
        "crs": crs,
        "display_gdf": display_gdf,
        "province_boundary": province_boundary,
    }


def analyze_region_suitability(region_name: str, city_stats: dict) -> dict:
    data = prepare_region_map_data(region_name)
    return compute_region_suitability_analysis(data["array"], city_stats)


def generate_region_map(region_name: str, output_path: str):
    data = prepare_region_map_data(region_name)
    render_map(
        array=data["array"],
        left=data["left"],
        right=data["right"],
        bottom=data["bottom"],
        top=data["top"],
        output_path=output_path,
        display_gdf=data["display_gdf"],
        province_boundary=data["province_boundary"],
    )
    # 生成地图
    return output_path


if __name__ == "__main__":
    # 测试函数
    region_name = "四川省"
    level = "province"
    map_path = generate_region_map(region_name)
    print(f"地图已保存到: {map_path}")
