from apple.predictor import predict_province_map
from service.map.map_service import generate_region_map, analyze_region_suitability
from service.geo.zonal_stats_service import compute_region_zonal_stats
from utils.config_loader import CONFIG
import geopandas as gpd

"""
存放区域地图和区域统计
"""


def analyze_predict_province_map(province_name: str):
    # 这里可以调用 predict_province_map 函数，生成省级适宜性地图
    res = predict_province_map(
        province_name=province_name,
        resolution=200,
        save_path="output/province_map.png",
    )
    return res


def analyze_predict_region_map(region_name: str, save_path: str):
    """
    生成区域的苹果种植适宜性地图
    """
    res = generate_region_map(
        region_name=region_name,
        # tif_path="output/china_suitability.tif",
        output_path=save_path,
    )
    return res


# 获取省级别的适宜性统计数据
def analyze_province_suitability(province_name: str):
    stats = analyze_region_suitability(province_name)
    return stats


def normalize_mode(region_name: str) -> str:
    if region_name in ["中国", "全国"]:
        return "province"

    if region_name.endswith("省"):
        return "city"

    if region_name.endswith("市"):
        return "county"
    return "county"  # fallback


def spatial_analysis(region_name: str):
    mode = normalize_mode(region_name)
    print(f"🔍 生成 {region_name} 的苹果种植适宜性地图，模式: {mode}")
    return analyze_predict_region_map(region_name, mode)


def compute_region_zonal_stats_by_geometry(
    region_name: str,
    raster_path=CONFIG["paths"]["raster"]["china_suitability_tf"],
    region_name_field="name",
):
    """
    对每个行政区计算适宜性统计
    """

    # 读取省级行政区划数据
    province_gdf = gpd.read_file(CONFIG["paths"]["shapefile"]["province"])

    target_province = province_gdf[province_gdf["name"] == region_name]

    province_gb = str(target_province.iloc[0]["gb"])[-6:]  # 获取省级GB代码的后6位
    province_prefix = province_gb[:2]

    DEFAULT_SHAPEFILE = CONFIG["paths"]["shapefile"]["city"]

    city_gdf = gpd.read_file(DEFAULT_SHAPEFILE, encoding="utf-8")
    city_gdf["gb"] = city_gdf["gb"].astype(str).str[-6:]  # 保留后6位GB代码
    province_city_gdf = city_gdf[city_gdf["gb"].str.startswith(province_prefix)]

    print(
        f"省份 {region_name} 包含的市区数量: {len(province_city_gdf)}, 市区列表: {province_city_gdf['name'].tolist()}"
    )

    city_stats = compute_region_zonal_stats(
        raster_path, province_city_gdf, region_name_field
    )

    return {
        "region_name": region_name,
        "city_stats": city_stats,
        "region_gdf": province_city_gdf,
    }
