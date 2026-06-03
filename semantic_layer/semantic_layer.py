from utils.json_handler import load_json, save_json

from semantic_layer.ranking_semantic_sevice import build_ranking_semantic
from semantic_layer.semantic_metrics import build_semantic_metrics
from semantic_layer.spatial_analysis_service import (
    build_spatial_semantic_layer,
)
from report_layer.apple_report_service import build_region_analysis_report
from raw_layer.granding.suitability_grading import build_grading_system
import geopandas as gpd
from utils.config_loader import CONFIG
from semantic_layer.semantic_insights_service import build_semantic_insights
from semantic_layer.stability_semantic_service import build_stability_semantic
from semantic_layer.suitability_semantic_builder import (
    build_distribution_semantic,
    build_hotspot_semantic,
    build_patch_semantic,
    build_grade_semantic,
    build_city_grade_semantic,
)
from semantic_layer.ranking_semantic_sevice import build_ranking_semantic

SAVE_PATH = CONFIG["paths"]["output"]["semantic_layer"]


def build_semantic_layer(
    raw_result_json,
    region_gdf_path,
):
    overall_data = load_json(raw_result_json)

    region_gdf = gpd.read_file(region_gdf_path)

    stats = overall_data["stats"]
    grading_system = build_grading_system(overall_data["city_stats"])

    # ==========================
    # 省级整体适宜性
    # ==========================
    province_semantic = build_semantic_metrics(stats["overall_stats"])

    # ==========================
    # 分布特征
    # ==========================
    distribution_semantic = build_distribution_semantic(stats["distribution_stats"])

    # ==========================
    # 核心优势区
    # ==========================
    hotspot_semantic = build_hotspot_semantic(stats["hotspot_stats"])

    # ==========================
    # 连续优势片区
    # ==========================
    patch_semantic = build_patch_semantic(stats["connected_patch_stats"])

    # ==========================
    # 全省等级结构
    # ==========================
    grade_semantic = build_grade_semantic(stats["grade_ratios"])

    # ==========================
    # 城市排名
    # ==========================
    ranking_semantic = build_ranking_semantic(
        overall_data["city_stats"], grading_system
    )

    # ==========================
    # 城市等级结构
    # ==========================
    city_semantic = build_city_grade_semantic(stats["city_grade_ratios"])

    # ==========================
    # 空间分布
    # ==========================
    spatial_semantic = build_spatial_semantic_layer(
        region_gdf,
        overall_data["city_stats"],
    )

    # ==========================
    # 报告层
    # ==========================
    regional_semantic_report = build_region_analysis_report(
        overall_data["region_name"],
        region_gdf,
        overall_data["city_stats"],
    )

    regional_semantic_report["apple_suitability_heatmap_path"] = overall_data[
        "apple_suitability_heatmap_path"
    ]

    semantic_res = {
        "region_name": overall_data["region_name"],
        "province_semantic": province_semantic,
        "distribution_semantic": distribution_semantic,
        "hotspot_semantic": hotspot_semantic,
        "patch_semantic": patch_semantic,
        "grade_semantic": grade_semantic,
        "ranking_semantic": ranking_semantic,
        "city_semantic": city_semantic,
        "spatial_semantic": spatial_semantic,
        "artifacts": regional_semantic_report,
    }

    save_json(semantic_res, SAVE_PATH)

    return semantic_res
