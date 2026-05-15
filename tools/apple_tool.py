from langchain.tools import tool

from service.apple.apple_point_service import analyze_apple_suitability
from service.apple.apple_region_service import (
    analyze_region_suitability,
    analyze_predict_province_map,
    analyze_predict_region_map,
    analyze_province_suitability,
    compute_region_zonal_stats_by_geometry,
)
from service.apple.apple_report_service import build_region_analysis_report
from typing import Literal
from utils.config_loader import CONFIG

from service.semantic_metrics import build_semantic_metrics
from service.spatial_analysis_service import build_spatial_semantic_layer
from utils.write_json import save_json

save_path1 = "output/tmp/data_layer_1.json"
save_path2 = "output/tmp/data_layer_2.json"
save_path3 = "output/tmp/data_layer_3.json"


@tool
def apple_point_analysis_tool(region_name: str):
    """输入县名/基地/园区，返回苹果种植适宜性分析。"""
    return analyze_apple_suitability(region_name)


@tool
def apple_map_report_tool(region_name: str):
    """输入省，返回苹果种植适宜性地图。
    region_name 可以是省、县的名称，比如中国、四川省、洛川县等。

    输出结果包含：
    - 适宜性地图的路径，包含四川省适宜性分布热力图
    - 省级别的适宜性统计数据
    """
    apple_suitability_heatmap_path = analyze_predict_region_map(
        region_name, save_path=CONFIG["paths"]["output"]["region_map"]
    )
    overall_stats = analyze_province_suitability(region_name)
    semantic_suitability_stats = build_semantic_metrics(overall_stats)
    res = {
        "apple_suitability_heatmap_path": apple_suitability_heatmap_path,
        "overall_stats": overall_stats,
        "semantic_suitability_stats": semantic_suitability_stats,
    }
    save_json(res, save_path=save_path1)
    return


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
    stats = compute_region_zonal_stats_by_geometry(region_name)
    #
    semantic_insights = build_region_analysis_report(
        region_name, stats["region_gdf"], stats["city_stats"]
    )
    # 调用空间分布语义分析层
    spatial_semantic = build_spatial_semantic_layer(
        stats["region_gdf"], stats["city_stats"]
    )
    # 存储数据到本地
    semantic_insights["spatial_semantic"] = spatial_semantic
    save_path = save_json(semantic_insights, save_path=save_path2)

    return save_path
