from utils.json_handler import load_json, save_json
from report_layer.apple_report_service import (
    build_region_analysis_report,
)
from semantic_layer.ranking_semantic_sevice import build_ranking_semantic
from semantic_layer.semantic_metrics import build_semantic_metrics
from semantic_layer.spatial_analysis_service import (
    build_spatial_semantic_layer,
)
from raw_layer.granding.suitability_grading import build_grading_system
import geopandas as gpd
from utils.config_loader import CONFIG
from semantic_layer.semantic_insights_service import build_semantic_insights
from semantic_layer.stability_semantic_service import build_stability_semantic

SAVE_PATH = CONFIG["paths"]["output"]["semantic_layer"]


def build_semantic_layer(overall_json_path, region_json_path, region_gdf_path):
    # 加载数据
    overall_data = load_json(overall_json_path)
    region_data = load_json(region_json_path)
    region_gdf = gpd.read_file(region_gdf_path)
    # 构建语义指标
    semantic_suitability_region_data = build_semantic_metrics(
        overall_data["overall_stats"]
    )

    # 调用空间分布语义分析层
    spatial_semantic = build_spatial_semantic_layer(
        region_gdf, region_data["city_stats"]
    )

    # 调用ranking语义分析层
    grade_system = build_grading_system(region_data["city_stats"])
    ranking_semantic = build_ranking_semantic(region_data["city_stats"], grade_system)

    # 调用区域适宜性波动分析层
    stability_semantic = build_stability_semantic(region_data["city_stats"])
    # 调用语义分析报告层
    regional_semantic_report = build_region_analysis_report(
        region_data["region_name"],
        region_gdf,
        region_data["city_stats"],
    )
    regional_semantic_report["apple_suitability_heatmap_path"] = overall_data[
        "apple_suitability_heatmap_path"
    ]
    # 调用语义分析报告层
    semantic_insights = build_semantic_insights(region_data["city_stats"])

    # 构建最终语义分析结果
    semantic_res = {
        "region_name": region_data["region_name"],
        "province_semantic": semantic_suitability_region_data,
        "spatial_semantic": spatial_semantic,
        "ranking_semantic": ranking_semantic,
        "stability_semantic": stability_semantic,
        "city_semantic": semantic_insights,
        "artifacts": regional_semantic_report,
    }

    # save semantic_res
    save_json(semantic_res, SAVE_PATH)
    return semantic_res
