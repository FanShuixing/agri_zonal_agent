from langchain.tools import tool
from utils.config_loader import CONFIG
from utils.json_handler import save_json
from utils.gdf_handler import sanitize_gdf_for_save
from raw_layer.map.map_service import analyze_region_suitability
from raw_layer.map.map_service import generate_region_map
from raw_layer.stats.zonal_stats import compute_region_zonal_stats
from raw_layer.geo.region_locator import get_cities_within_province

save_path1 = "output/tmp/data_layer_1.json"
save_path2 = "output/tmp/data_layer_2.json"
save_path3 = "output/tmp/data_layer_3.json"
region_gdf = "output/tmp/apple_region_gdf.geojson"


# @tool
# def apple_map_report_tool(region_name: str):
#     """输入省，返回种植适宜性地图。
#     region_name 可以是省、县的名称，比如中国、四川省、洛川县等。

#     输出结果包含：
#     - 适宜性地图的路径，包含四川省适宜性分布热力图
#     - 省级别的适宜性统计数据
#     """

#     save_json(res, save_path=save_path1)
#     return


@tool
def apple_region_ranking_tool(region_name: str):
    """
    当用户询问：
    - 哪些市区适合种植苹果
    - 哪些行政区更适合
    - 各地区适宜性排名
    - 市县级适宜性分析
    - 区域适宜性对比

    时，必须调用该工具。

    该工具会计算每个行政区的：
    - 平均适宜性
    - 最大适宜性
    - 最小适宜性

    用于分析不同地区的苹果种植适宜性差异。
    """
    apple_suitability_heatmap_path = generate_region_map(
        region_name, output_path=CONFIG["paths"]["output"]["region_map"]
    )

    province_city_gdf = get_cities_within_province(region_name)
    city_stats = compute_region_zonal_stats(province_city_gdf)
    # 保存json
    res = {"region_name": region_name, "city_stats": city_stats}

    overall_stats = analyze_region_suitability(region_name, city_stats)
    res = {
        "apple_suitability_heatmap_path": apple_suitability_heatmap_path,
        "stats": overall_stats,
        "city_stats": city_stats,
        "apple_suitability_heatmap_path": apple_suitability_heatmap_path,
    }
    save_json(res, save_path=save_path2)
    # 保存gdf
    clean_gdf = sanitize_gdf_for_save(province_city_gdf)
    clean_gdf.to_file(region_gdf, driver="GeoJSON")
    return
