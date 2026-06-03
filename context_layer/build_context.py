"""
Context Layer — 将 semantic_layer 和 raw 数值数据组装成 LLM 可消费的完整上下文。

核心原则：LLM 擅长从数值中推理和叙事。只给标签 → 生成套话；给标签+数值 → 生成扎实分析。
"""

from pathlib import Path
from utils.json_handler import load_json


def build_report_context(
    semantic_json_path: str | Path = "output/cache/semantic_layer.json",
    raw_data_json_path: str | Path = "output/tmp/data_layer_2.json",
):
    semantic = load_json(semantic_json_path)
    raw = load_json(raw_data_json_path)

    province_semantic = semantic["province_semantic"]
    distribution_semantic = semantic["distribution_semantic"]
    hotspot_semantic = semantic["hotspot_semantic"]
    patch_semantic = semantic["patch_semantic"]
    grade_semantic = semantic["grade_semantic"]
    ranking_semantic = semantic["ranking_semantic"]
    city_semantic = semantic["city_semantic"]
    spatial_semantic = semantic["spatial_semantic"]
    stats = raw["stats"]

    # ── 1. 数值基础：LLM 需要知道数字才有东西可写 ──────────────────
    numerical_basis = _build_numerical_basis(stats)

    # ── 2. 各城市数据卡片 ──────────────────────────────────────────
    city_scorecards = _build_city_scorecards(raw, semantic)

    # ── 3. 对比分析：Top vs Bottom 差距量化 ───────────────────────
    comparative_analysis = _build_comparative(city_scorecards, ranking_semantic)

    # ── 4. 省级定性摘要（保留原有字段） ─────────────────────────────
    province_summary = {
        "suitability_level": province_semantic["suitability_level"],
        "industrialization_level": province_semantic["industrialization_level"],
        "risk_level": province_semantic["risk_level"],
        "stability_level": province_semantic["stability_level"],
        "development_advice": province_semantic["development_advice"],
    }

    # ── 5. 空间格局（保留原有 + 补充数值） ──────────────────────────
    spatial_structure = {
        "global_pattern": spatial_semantic["spatial_pattern"]["global_pattern"],
        "gradient_direction": spatial_semantic["spatial_pattern"]["gradient_direction"],
        "core_area": spatial_semantic["core_area"],
        "high_value_regions": spatial_semantic["high_value_regions"],
        "low_value_regions": spatial_semantic["low_value_regions"],
        "adjacency_pairs": spatial_semantic.get("adjacency_pairs", []),
    }

    # ── 6. 排名结构 ────────────────────────────────────────────────
    ranking_structure = {
        "top_regions": ranking_semantic["top_regions"],
        "bottom_regions": ranking_semantic["bottom_regions"],
        "leading_group": ranking_semantic["leading_group"],
        "ranking_type": ranking_semantic["ranking_structure"]["type"],
        "regional_gap": ranking_semantic["regional_gap"],
    }

    # ── 7. 城市结构 ────────────────────────────────────────────────
    city_structure = {
        "core_dominant_regions": city_semantic["core_dominant_regions"],
        "high_core_regions": city_semantic["high_core_regions"],
        "risk_regions": city_semantic["risk_regions"],
        "structure_summary": city_semantic["structure_summary"],
    }

    # ── 8. 等级结构 ────────────────────────────────────────────────
    grade_structure = {
        "dominant_grade": grade_semantic["dominant_grade"],
        "dominant_ratio": grade_semantic.get("dominant_ratio", 0.5),
        "grade_structure": grade_semantic["grade_structure"],
        "core_ratio": grade_semantic["core_ratio"],
        "suitable_ratio": grade_semantic["suitable_ratio"],
        "unsuitable_ratio": grade_semantic["unsuitable_ratio"],
    }

    # ── 9. 空间质量 ────────────────────────────────────────────────
    spatial_quality = {
        "hotspot_pattern": hotspot_semantic["hotspot_pattern"],
        "hotspot_scale": hotspot_semantic["hotspot_scale"],
        "hotspot_count": hotspot_semantic["hotspot_count"],
        "fragmentation_level": patch_semantic["fragmentation_level"],
        "connectivity_level": patch_semantic["connectivity_level"],
        "patch_count": patch_semantic["patch_count"],
    }

    # ── 10. 产业背景（中文自然语言描述，替换旧的英文 tag） ──────────
    industrial_context = _build_industrial_context(
        spatial_structure, ranking_structure, city_structure,
        grade_structure, spatial_quality, numerical_basis,
    )

    # ── 11. 最终组装 ───────────────────────────────────────────────
    return {
        "province": semantic["region_name"],
        "province_summary": province_summary,
        "numerical_basis": numerical_basis,
        "city_scorecards": city_scorecards,
        "comparative_analysis": comparative_analysis,
        "spatial_structure": spatial_structure,
        "ranking_structure": ranking_structure,
        "city_structure": city_structure,
        "grade_structure": grade_structure,
        "spatial_quality": spatial_quality,
        "industrial_context": industrial_context,
        "artifacts": {
            "heatmap": "output/train_output/region_map.png",
            "suitability_map": "output/static/suitability_map.png",
            "ranking_chart": "output/static/ranking_table.png",
            "range_chart": "output/static/range_chart.png",
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════

def _build_numerical_basis(stats: dict) -> dict:
    """构建数值基础数据块——LLM 据此做出量化分析。"""
    overall = stats["overall_stats"]
    dist = stats["distribution_stats"]

    return {
        "province_level": {
            "mean_score": overall["mean_score"],
            "max_score": overall["max_score"],
            "min_score": overall["min_score"],
            "score_range": round(overall["max_score"] - overall["min_score"], 4),
            "std_score": dist.get("std_score", 0),
        },
        "distribution_percentiles": {
            "median_p50": dist.get("median_score", 0),
            "p75": dist.get("p75_score", 0),
            "p90": dist.get("p90_score", 0),
            "p95": dist.get("p95_score", 0),
        },
        "grade_thresholds": [
            {"grade": "不适宜区", "score_range": "0 — 0.148", "meaning": "低于生态适生阈值，苹果种植风险很高"},
            {"grade": "一般适宜区", "score_range": "0.148 — 全省均值", "meaning": "可种植但优势不突出"},
            {"grade": "较适宜区", "score_range": "全省均值 — 均值+0.5σ", "meaning": "高于全省平均水平，有发展潜力"},
            {"grade": "核心优势区", "score_range": "均值+0.5σ — 1.0", "meaning": "生态条件最优，适合规模化种植"},
        ],
        "note": "适宜性得分来自 GradientBoosting 物种分布模型（WorldClim 6个气候变量），值域 0-1，越高越适宜苹果种植。全省均值约 0.21，最高 0.35，说明山东省整体得分不高，需要在省内做相对比较。",
    }


def _build_city_scorecards(raw: dict, semantic: dict) -> list[dict]:
    """为每个城市生成一份数值卡片，包含得分 + 等级占比。"""
    city_stats = raw.get("city_stats", [])
    city_grades = raw.get("stats", {}).get("city_grade_ratios", [])

    # 建 grade 索引
    grade_map = {}
    for cg in city_grades:
        grade_map[cg["region"]] = cg

    # 建排名索引（从 semantic 中获取城市顺序）
    all_regions = [s["region"] for s in city_stats]
    sorted_by_mean = sorted(city_stats, key=lambda x: x.get("mean_score", 0), reverse=True)

    cards = []
    for rank_idx, city in enumerate(sorted_by_mean, 1):
        region = city["region"]
        ginfo = grade_map.get(region, {})
        grade_ratios = ginfo.get("grade_ratios", [])

        # 提取各等级占比
        grade_pct = {}
        for g in grade_ratios:
            grade_pct[g["grade_name"]] = round(g["area_ratio"] * 100, 1)

        card = {
            "rank": rank_idx,
            "region": region,
            "mean_score": city.get("mean_score", 0),
            "max_score": city.get("max_score", 0),
            "min_score": city.get("min_score", 0),
            "core_ratio_pct": grade_pct.get("核心优势区", 0),
            "suitable_ratio_pct": grade_pct.get("较适宜区", 0),
            "general_ratio_pct": grade_pct.get("一般适宜区", 0),
            "unsuitable_ratio_pct": grade_pct.get("不适宜区", 0),
            "dominant_grade": ginfo.get("dominant_grade", ""),
            "total_cities": len(sorted_by_mean),
        }
        cards.append(card)

    return cards


def _build_comparative(city_scorecards: list[dict], ranking_semantic: dict) -> dict:
    """生成对比数据：头部 vs 尾部、领先集团、区域差异。"""
    if not city_scorecards:
        return {}

    top5 = city_scorecards[:5]
    bottom5 = city_scorecards[-5:]

    top5_mean = round(sum(c["mean_score"] for c in top5) / len(top5), 4)
    bottom5_mean = round(sum(c["mean_score"] for c in bottom5) / len(bottom5), 4)

    return {
        "top5_cities": [
            {"region": c["region"], "mean_score": c["mean_score"], "core_ratio_pct": c["core_ratio_pct"]}
            for c in top5
        ],
        "bottom5_cities": [
            {"region": c["region"], "mean_score": c["mean_score"], "core_ratio_pct": c["core_ratio_pct"]}
            for c in bottom5
        ],
        "top5_average_score": top5_mean,
        "bottom5_average_score": bottom5_mean,
        "top_vs_bottom_gap": round(top5_mean - bottom5_mean, 4),
        "best_city": top5[0]["region"] if top5 else "",
        "best_city_score": top5[0]["mean_score"] if top5 else 0,
        "worst_city": bottom5[-1]["region"] if bottom5 else "",
        "worst_city_score": bottom5[-1]["mean_score"] if bottom5 else 0,
        "leading_group_description": ranking_semantic.get("leading_group", {}).get("description", ""),
    }


def _build_industrial_context(
    spatial_structure, ranking_structure, city_structure,
    grade_structure, spatial_quality, numerical_basis,
) -> dict:
    """
    产业背景——纯数据驱动，不硬编码城市名或结论。

    每条描述都从传入数据中取值，换省份/换作物后自动适配。
    结论性判断留给 LLM，context 只提供事实。
    """
    high_regions = spatial_structure["high_value_regions"]
    low_regions = spatial_structure["low_value_regions"]
    core_area = spatial_structure["core_area"]
    neighbors = spatial_structure.get("adjacency_pairs", [])
    rankings = ranking_structure
    city_summary = city_structure["structure_summary"]

    return {
        "spatial_overview": {
            "global_pattern": spatial_structure["global_pattern"],
            "gradient_direction": spatial_structure["gradient_direction"],
            "core_area": core_area,
            "high_value_regions": high_regions,
            "high_value_count": len(high_regions),
            "low_value_regions": low_regions,
            "low_value_count": len(low_regions),
            "adjacent_high_value_pairs": [
                list(pair) for pair in neighbors
                if pair[0] in high_regions and pair[1] in high_regions
            ],
        },
        "industrial_structure_overview": {
            "ranking_type": rankings["ranking_type"],
            "head_tail_score_gap": rankings["regional_gap"]["score_range"],
            "head_tail_gap_type": rankings["regional_gap"]["type"],
            "core_dominant_city_count": city_summary["core_dominant_count"],
            "risk_city_count": city_summary["risk_region_count"],
            "general_dominant_city_count": city_summary.get("general_dominant_count", 0),
        },
        "grade_overview": {
            "dominant_grade": grade_structure["dominant_grade"],
            "dominant_ratio": grade_structure["dominant_ratio"],
            "core_ratio": grade_structure["core_ratio"],
            "suitable_ratio": grade_structure["suitable_ratio"],
            "unsuitable_ratio": grade_structure["unsuitable_ratio"],
        },
        "spatial_quality_overview": {
            "hotspot_pattern": spatial_quality["hotspot_pattern"],
            "hotspot_scale": spatial_quality["hotspot_scale"],
            "hotspot_count": spatial_quality["hotspot_count"],
            "connectivity_level": spatial_quality["connectivity_level"],
            "fragmentation_level": spatial_quality["fragmentation_level"],
            "patch_count": spatial_quality["patch_count"],
        },
        "data_driven_signals": {
            "province_mean_score": numerical_basis["province_level"]["mean_score"],
            "province_score_range": numerical_basis["province_level"]["score_range"],
            "note": (
                "以下信号全部从数据派生，未硬编码任何城市名或结论。"
                "province_mean_score 低于 0.3 说明该作物在本省普遍适宜性不高；"
                "score_range 很小说明省内差异有限，排名靠前不代表绝对优势。"
            ),
        },
    }
