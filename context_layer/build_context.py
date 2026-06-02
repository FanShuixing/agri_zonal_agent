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
    stability_structure,
    province_summary,
    advantage_regions,
    risk_regions,
):
    # =========================
    # 7. 产业认知标签
    # =========================

    industrial_tags = {
        "spatial_tags": [],
        "industrial_structure_tags": [],
        "risk_tags": [],
        "development_tags": [],
    }

    pattern = spatial_structure["global_pattern"]

    ranking_type = ranking_structure["ranking_type"]

    regional_gap = ranking_structure["regional_gap"]

    core_area = spatial_structure["core_area"]

    risk_patterns = stability_structure.get("risk_patterns", {})

    # =========================
    # 空间标签
    # =========================

    if "北高南低" in pattern:
        industrial_tags["spatial_tags"].append("north_high_south_low")

    if "西高东低" in pattern:
        industrial_tags["spatial_tags"].append("west_high_east_low")

    if "集聚" in pattern:
        industrial_tags["spatial_tags"].append("localized_cluster")

    if core_area:
        industrial_tags["spatial_tags"].append("core_production_area")

    # =========================
    # 产业结构标签
    # =========================

    if ranking_type == "头部集中型":
        industrial_tags["industrial_structure_tags"].append("head_concentration")

    if regional_gap == "头尾差异较大":
        industrial_tags["industrial_structure_tags"].append("regional_gap_large")

    if len(ranking_structure["top_regions"]) >= 3:
        industrial_tags["industrial_structure_tags"].append("multi_tier_structure")

    if core_area:
        industrial_tags["industrial_structure_tags"].append("core_area_dominance")

    # =========================
    # 风险标签
    # =========================

    if stability_structure["unstable_regions"]:
        industrial_tags["risk_tags"].append("regional_instability")

    if risk_patterns.get("high_score_high_fluctuation"):
        industrial_tags["risk_tags"].append("high_value_fluctuation")

    if risk_patterns.get("low_score_low_stability"):
        industrial_tags["risk_tags"].append("low_stability_risk")

    if province_summary["risk_level"] in ["高风险", "较高风险"]:
        industrial_tags["risk_tags"].append("overall_risk_exposure")

    # =========================
    # 发展标签
    # =========================

    if "localized_cluster" in industrial_tags["spatial_tags"]:
        industrial_tags["development_tags"].append("cluster_development_potential")

    if core_area:
        industrial_tags["development_tags"].append("core_area_expansion")

    if regional_gap == "头尾差异较大":
        industrial_tags["development_tags"].append("regional_collaboration_needed")

    if len(advantage_regions) >= 3:
        industrial_tags["development_tags"].append("advantage_region_synergy")

    if len(risk_regions) >= 3:
        industrial_tags["development_tags"].append("risk_control_required")
        return industrial_tags


def build_report_context(
    semantic_json_path: str | Path,
):
    """
    构建给 LLM 使用的轻量级认知上下文

    目标：
    - 不重复 semantic 推理
    - 不重复 ranking 分析
    - 不携带 raw stats
    - 尽量减少 token
    - 保留“产业认知”
    """

    # overall_data = load_json(overall_json_path)
    semantic_data = load_json(semantic_json_path)

    # =========================
    # 1. 顶层 semantic
    # =========================

    province_semantic = semantic_data["province_semantic"]

    spatial_semantic = semantic_data["spatial_semantic"]

    ranking_semantic = semantic_data["ranking_semantic"]

    city_semantic = semantic_data["city_semantic"]

    artifacts = semantic_data["artifacts"]

    stability_semantic = semantic_data["stability_semantic"]

    # =========================
    # 2. 重点区域
    # =========================

    advantage_regions = []

    for city in city_semantic:

        if city["industry_level"] not in ["核心优势区", "重点发展区"]:
            continue

        advantage_regions.append(
            {
                "region": city["region"],
                "industry_level": city["industry_level"],
                "development_potential": city["development_potential"],
                "main_risk": (city["risks"][0] if city.get("risks") else None),
            }
        )

    # =========================
    # 3. 高风险区域
    # =========================

    risk_regions = []

    for city in city_semantic:

        if city["risk_level"] not in ["中等", "较高", "高"]:
            continue

        risk_regions.append(
            {
                "region": city["region"],
                "risk_level": city["risk_level"],
                "main_risk": (city["risks"][0] if city.get("risks") else None),
            }
        )

    # =========================
    # 4. 省级认知摘要
    # =========================

    province_summary = {
        "suitability_level": province_semantic["suitability_level"],
        "industrialization_level": province_semantic["industrialization_level"],
        "risk_level": province_semantic["risk_level"],
        "stability_level": province_semantic["stability_level"],
    }

    # =========================
    # 5. 空间格局
    # =========================

    spatial_structure = {
        "global_pattern": spatial_semantic["spatial_pattern"]["global_pattern"],
        "core_area": spatial_semantic["core_area"],
        "high_value_regions": spatial_semantic["high_value_regions"][:5],
        "low_value_regions": spatial_semantic["low_value_regions"][:5],
    }

    # =========================
    # 6. 排序结构
    # =========================

    ranking_structure = {
        "top_regions": ranking_semantic["top_regions"][:5],
        "bottom_regions": ranking_semantic["bottom_regions"][:5],
        "ranking_type": ranking_semantic["ranking_structure"]["type"],
        "regional_gap": ranking_semantic["regional_gap"]["type"],
    }

    # industrial_tags = []

    # pattern = spatial_structure["global_pattern"]

    # ranking_type = ranking_structure["ranking_type"]

    # if "北高南低" in pattern:
    #     industrial_tags.append("north_high_south_low")

    # if "西高东低" in pattern:
    #     industrial_tags.append("west_high_east_low")

    # if "集聚" in pattern:
    #     industrial_tags.append("localized_cluster")

    # if ranking_type == "头部集中型":
    #     industrial_tags.append("head_concentration")

    # if spatial_structure["core_area"]:
    #     industrial_tags.append("core_production_area")

    # 稳定性结构
    stability_structure = {
        "overall_stability": stability_semantic["overall_stability"],
        "high_stability_regions": stability_semantic["high_stability_regions"][:5],
        "unstable_regions": stability_semantic["unstable_regions"][:5],
        # "risk_patterns": stability_semantic["risk_patterns"],
    }
    # =========================
    # 7. 产业结构标签（供LLM快速理解）
    # =========================
    industrial_tags = build_industrial_tags(
        spatial_structure,
        ranking_structure,
        stability_structure,
        province_summary,
        advantage_regions,
        risk_regions,
    )
    # =========================
    # 8. 最终 context
    # =========================

    report_context = {
        "province": semantic_data["region_name"],
        "province_summary": province_summary,
        "spatial_structure": spatial_structure,
        "ranking_structure": ranking_structure,
        "advantage_regions": advantage_regions[:5],
        "risk_regions": risk_regions[:5],
        "industrial_tags": industrial_tags,
        "artifacts": {
            "heatmap": artifacts.get("apple_suitability_heatmap_path"),
            "suitability_map": artifacts.get("suitability_map_path"),
            "ranking_chart": artifacts.get("ranking_table_path"),
            "range_chart": artifacts.get("score_range_chart_path"),
        },
        "stability_structure": stability_structure,
    }

    return report_context
