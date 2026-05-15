import json
from pathlib import Path


def load_json(json_path: str | Path):
    """读取 JSON 文件"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_report_context(
    overall_json_path: str | Path,
    region_json_path: str | Path,
):
    """
    构建给 LLM 使用的“第二层报告上下文”

    输入：
    - overall_json_path:
        全省总体统计 JSON

    - region_json_path:
        市级统计与语义分析 JSON

    输出：
    - report_context（给 LLM 的精简上下文）
    """

    overall_data = load_json(overall_json_path)
    region_data = load_json(region_json_path)

    overall_stats = overall_data["overall_stats"]
    semantic_stats = overall_data["semantic_suitability_stats"]

    semantic_insights = region_data["semantic_insights"]

    # =========================
    # 1. 计算优势区域
    # =========================

    sorted_regions = sorted(
        semantic_insights,
        key=lambda x: x["mean_score"],
        reverse=True,
    )

    advantage_regions = []
    risk_regions = []

    for region in sorted_regions:

        region_item = {
            "region": region["region"],
            "industry_level": region["industry_level"],
            "development_potential": region["development_potential"],
            "risk_level": region["risk_level"],
            "reason": region["climate_comment"],
            "strategy": (
                region["development_advice"][0] if region["development_advice"] else ""
            ),
        }

        # 优势区域
        if region["industry_level"] in ["核心优势区", "重点发展区"]:
            advantage_regions.append(region_item)

        # 风险区域
        if region["risk_level"] in ["高", "较高", "中等"]:
            risk_regions.append(
                {
                    "region": region["region"],
                    "risk_level": region["risk_level"],
                    "reason": (
                        region["risks"][0] if region["risks"] else "存在一定种植风险"
                    ),
                    "advice": (
                        region["development_advice"][0]
                        if region["development_advice"]
                        else ""
                    ),
                }
            )

    # 只保留前几个
    advantage_regions = advantage_regions[:5]
    risk_regions = risk_regions[:5]

    # =========================
    # 2. 空间格局
    # =========================
    spatial_semantic = region_data["spatial_semantic"]

    regional_pattern = {
        "global_pattern": spatial_semantic["spatial_pattern"]["global_pattern"],
        "gradient_direction": spatial_semantic["spatial_pattern"]["gradient_direction"],
        "aggregation_type": spatial_semantic["spatial_pattern"]["aggregation_type"],
        "continuity": spatial_semantic["spatial_pattern"]["continuity"],
        "industrial_belt": spatial_semantic["spatial_pattern"]["industrial_belt"],
        "core_area": spatial_semantic["core_area"],
        "high_value_regions": spatial_semantic["high_value_regions"],
        "low_value_regions": spatial_semantic["low_value_regions"],
    }

    # 产业发现
    implication = ""
    if regional_pattern["industrial_belt"]:
        implication = "区域高适宜区呈连续集聚分布，具备形成规模化苹果产业带潜力。"

    elif regional_pattern["aggregation_type"] == "高值区局部集聚明显":
        implication = "高适宜区域存在局部集聚特征，适合开展区域化产业布局。"

    else:
        implication = "高适宜区较为离散，建议采取分散化布局策略。"

    # =========================
    # 3. 关键发现
    # =========================

    key_findings = []

    if advantage_regions:
        key_findings.append(f"{advantage_regions[0]['region']}适宜性表现最佳")

    if overall_stats["low_ratio"] > 0.5:
        key_findings.append("低适宜区域占比较高")

    if overall_stats["medium_ratio"] > 0:
        key_findings.append("部分区域具备一定产业发展潜力")

    key_findings.append("区域内部适宜性差异明显")

    # =========================
    # 4. 最终报告上下文
    # =========================

    report_context = {
        "province": region_data["region_name"],
        "overall_summary": {
            "mean_score": overall_stats["mean_score"],
            "suitability_level": semantic_stats["suitability_level"],
            "development_potential": semantic_stats["industrialization_level"],
            "risk_level": semantic_stats["risk_level"],
            "main_conclusion": semantic_stats["development_advice"],
        },
        "regional_pattern": regional_pattern,
        "advantage_regions": advantage_regions,
        "risk_regions": risk_regions,
        "industry_strategy": {
            "core_strategy": semantic_stats["development_advice"],
            "risk_control_strategy": semantic_stats["risk_hint"],
        },
        "implication": implication,
        "key_findings": key_findings,
        "images": {
            "heatmap": overall_data.get("apple_suitability_heatmap_path"),
            "suitability_map": region_data.get("suitability_map_path"),
            "ranking_chart": region_data.get("ranking_table_path"),
            "range_chart": region_data.get("score_range_chart_path"),
        },
    }

    return report_context


if __name__ == "__main__":

    report_context = build_report_context(
        overall_json_path="output/overall_analysis.json",
        region_json_path="output/region_analysis.json",
    )

    print(json.dumps(report_context, ensure_ascii=False, indent=2))
