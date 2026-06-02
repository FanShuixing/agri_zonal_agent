import json
from pathlib import Path


def load_json(json_path: str | Path):
    """读取 JSON 文件"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


from pathlib import Path
from utils.json_handler import load_json


def build_industrial_tags(
    spatial_structure,
    ranking_structure,
    city_structure,
    grade_structure,
    spatial_quality,
):
    """
    基于 Context 信息构建产业认知标签

    输入：
    - spatial_structure
    - ranking_structure
    - city_structure
    - grade_structure
    - spatial_quality

    输出：
    - industrial_tags
    """

    industrial_tags = {
        "spatial_tags": [],
        "industrial_structure_tags": [],
        "risk_tags": [],
        "development_tags": [],
    }

    # =========================
    # 空间标签
    # =========================

    pattern = spatial_structure["global_pattern"]

    if "北高南低" in pattern:
        industrial_tags["spatial_tags"].append("north_high_south_low")

    if "南高北低" in pattern:
        industrial_tags["spatial_tags"].append("south_high_north_low")

    if "东高西低" in pattern:
        industrial_tags["spatial_tags"].append("east_high_west_low")

    if "西高东低" in pattern:
        industrial_tags["spatial_tags"].append("west_high_east_low")

    if "集聚" in pattern:
        industrial_tags["spatial_tags"].append("localized_cluster")

    if spatial_structure["core_area"]:
        industrial_tags["spatial_tags"].append("core_production_area")

    # =========================
    # 产业结构标签
    # =========================

    ranking_type = ranking_structure["ranking_type"]

    if ranking_type == "头部集中型":
        industrial_tags["industrial_structure_tags"].append("head_concentration")

    if ranking_type == "相对均衡型":
        industrial_tags["industrial_structure_tags"].append("balanced_structure")

    if ranking_structure["leading_group"]["exists"]:
        industrial_tags["industrial_structure_tags"].append("leading_group_present")

    if city_structure["structure_summary"]["core_dominant_count"] >= 3:
        industrial_tags["industrial_structure_tags"].append("multiple_core_regions")

    # =========================
    # 风险标签
    # =========================

    if city_structure["structure_summary"]["risk_region_count"] > 0:
        industrial_tags["risk_tags"].append("regional_risk_exists")

    if grade_structure["unsuitable_ratio"] > 0.2:
        industrial_tags["risk_tags"].append("high_unsuitable_ratio")

    if spatial_quality["fragmentation_level"] == "存在明显破碎化":
        industrial_tags["risk_tags"].append("fragmentation_risk")

    # =========================
    # 发展标签
    # =========================

    if "localized_cluster" in industrial_tags["spatial_tags"]:
        industrial_tags["development_tags"].append("cluster_development_potential")

    if spatial_structure["core_area"]:
        industrial_tags["development_tags"].append("core_area_expansion")

    if city_structure["structure_summary"]["core_dominant_count"] >= 3:
        industrial_tags["development_tags"].append("advantage_region_synergy")

    if city_structure["structure_summary"]["risk_region_count"] > 0:
        industrial_tags["development_tags"].append("risk_control_required")

    return industrial_tags


def build_report_context(
    semantic_json_path: str | Path,
):

    semantic_data = load_json(semantic_json_path)

    province_semantic = semantic_data["province_semantic"]
    distribution_semantic = semantic_data["distribution_semantic"]
    hotspot_semantic = semantic_data["hotspot_semantic"]
    patch_semantic = semantic_data["patch_semantic"]
    grade_semantic = semantic_data["grade_semantic"]
    ranking_semantic = semantic_data["ranking_semantic"]
    city_semantic = semantic_data["city_semantic"]
    spatial_semantic = semantic_data["spatial_semantic"]
    artifacts = semantic_data["artifacts"]

    # =========================
    # 1. 省级总体认知
    # =========================

    province_summary = {
        "suitability_level": province_semantic["suitability_level"],
        "industrialization_level": province_semantic["industrialization_level"],
        "risk_level": province_semantic["risk_level"],
        "stability_level": province_semantic["stability_level"],
        "development_advice": province_semantic["development_advice"],
    }

    # =========================
    # 2. 空间格局
    # =========================

    spatial_structure = {
        "global_pattern": spatial_semantic["spatial_pattern"]["global_pattern"],
        "gradient_direction": spatial_semantic["spatial_pattern"]["gradient_direction"],
        "core_area": spatial_semantic["core_area"],
        "high_value_regions": spatial_semantic["high_value_regions"],
        "low_value_regions": spatial_semantic["low_value_regions"],
    }

    # =========================
    # 3. 区域竞争格局
    # =========================

    ranking_structure = {
        "top_regions": ranking_semantic["top_regions"],
        "bottom_regions": ranking_semantic["bottom_regions"],
        "leading_group": ranking_semantic["leading_group"],
        "ranking_type": ranking_semantic["ranking_structure"]["type"],
        "regional_gap": ranking_semantic["regional_gap"],
    }

    # =========================
    # 4. 城市发展结构
    # =========================

    city_structure = {
        "core_dominant_regions": city_semantic["core_dominant_regions"],
        "high_core_regions": city_semantic["high_core_regions"],
        "risk_regions": city_semantic["risk_regions"],
        "structure_summary": city_semantic["structure_summary"],
    }

    # =========================
    # 5. 适宜等级结构
    # =========================

    grade_structure = {
        "dominant_grade": grade_semantic["dominant_grade"],
        "grade_structure": grade_semantic["grade_structure"],
        "core_ratio": grade_semantic["core_ratio"],
        "suitable_ratio": grade_semantic["suitable_ratio"],
        "unsuitable_ratio": grade_semantic["unsuitable_ratio"],
    }

    # =========================
    # 6. 空间连续性
    # =========================

    spatial_quality = {
        "hotspot_pattern": hotspot_semantic["hotspot_pattern"],
        "hotspot_scale": hotspot_semantic["hotspot_scale"],
        "fragmentation_level": patch_semantic["fragmentation_level"],
        "connectivity_level": patch_semantic["connectivity_level"],
    }

    # =========================
    # 7. 工业标签
    # =========================

    industrial_tags = build_industrial_tags(
        spatial_structure=spatial_structure,
        ranking_structure=ranking_structure,
        city_structure=city_structure,
        grade_structure=grade_structure,
        spatial_quality=spatial_quality,
    )

    # =========================
    # 8. 最终Context
    # =========================

    report_context = {
        "province": semantic_data["region_name"],
        "province_summary": province_summary,
        "spatial_structure": spatial_structure,
        "ranking_structure": ranking_structure,
        "city_structure": city_structure,
        "grade_structure": grade_structure,
        "spatial_quality": spatial_quality,
        "industrial_tags": industrial_tags,
        "artifacts": {
            "heatmap": artifacts.get("apple_suitability_heatmap_path"),
            "suitability_map": artifacts.get("suitability_map_path"),
            "ranking_chart": artifacts.get("ranking_table_path"),
            "range_chart": artifacts.get("score_range_chart_path"),
        },
    }

    return report_context
