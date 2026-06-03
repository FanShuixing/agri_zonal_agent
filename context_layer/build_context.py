"""
Context Layer — 将 semantic_layer 和 raw 数值数据组装成 LLM 可消费的完整上下文。

核心原则：LLM 擅长从数值中推理和叙事。只给标签 → 生成套话；给标签+数值 → 生成扎实分析。
"""

from pathlib import Path
from utils.json_handler import load_json
from core.model_registry import load_model_threshold

COMPOSITE_ALPHA = 0.5  # mean_score 在综合得分中的权重；(1-alpha) 给 max_score


def _compute_composite(mean_score: float, max_score: float) -> float:
    return round(COMPOSITE_ALPHA * mean_score + (1 - COMPOSITE_ALPHA) * max_score, 4)


def _classify_city_type(max_score: float, mean_score: float, model_threshold: float = 0.417) -> str:
    """
    城市类型分类（优先级依次）：
    1. 整体弱势型: max < 0.12
    2. 高峰值潜力型: max >= 0.30 且 max/mean >= 2.5
    3. 均匀适生型: max/mean < 1.4
    4. 一般分化型: 其余
    """
    _max = max_score or 0
    _mean = max(mean_score or 0, 0.001)
    weak_floor = max(0.12, model_threshold * 0.3)

    if _max < weak_floor:
        return "整体弱势型"
    if _max >= 0.30 and (_max / _mean) >= 2.5:
        return "高峰值潜力型"
    if (_max / _mean) < 1.4:
        return "均匀适生型"
    return "一般分化型"


def build_report_context(
    semantic_json_path: str | Path = "output/cache/semantic_layer.json",
    raw_data_json_path: str | Path = "output/cache/pipeline/data_layer_2.json",
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
    numerical_basis = _build_numerical_basis(stats, raw.get("city_stats", []))

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
        "better_ratio": grade_semantic["better_ratio"],
        "general_ratio": grade_semantic["general_ratio"],
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

    # ── 11. 峰值潜力分析 ──────────────────────────────────────────
    peak_analysis = _build_peak_analysis(city_scorecards, ranking_semantic, numerical_basis)

    # ── 12. 最终组装 ───────────────────────────────────────────────
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
        "peak_analysis": peak_analysis,
        "artifacts": {
            "heatmap": "output/predictions/region_map.png",
            "suitability_map": "output/static/suitability_map.png",
            "ranking_chart": "output/static/ranking_table.png",
            "range_chart": "output/static/range_chart.png",
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════

def _build_numerical_basis(stats: dict, city_stats: list | None = None) -> dict:
    """构建数值基础数据块——LLM 据此做出量化分析。"""
    overall = stats["overall_stats"]
    dist = stats["distribution_stats"]

    model_t = load_model_threshold()
    mean_s = overall.get("mean_score", 0)
    std_s = dist.get("std_score", 0)

    # 城市间极差（与 KPI 面板中其他数据口径一致）
    if city_stats:
        city_means = [c["mean_score"] for c in city_stats if c.get("mean_score") is not None]
        city_range = round(max(city_means) - min(city_means), 4) if city_means else 0
    else:
        city_range = round(overall.get("max_score", 0) - overall.get("min_score", 0), 4)

    # 省内数据驱动的等级边界（与 suitability_grading.py 一致）
    local_floor = round(mean_s * 0.8, 4)
    local_high = round(mean_s + 0.5 * std_s, 4)

    return {
        "province_level": {
            "mean_score": overall["mean_score"],
            "max_city_score": round(max(city_means), 4) if city_stats else overall["max_score"],
            "min_city_score": round(min(city_means), 4) if city_stats else overall["min_score"],
            "score_range": city_range,
            "std_score": std_s,
            "model_threshold": round(model_t, 4),
        },
        "distribution_percentiles": {
            "median_p50": dist.get("median_score", 0),
            "p75": dist.get("p75_score", 0),
            "p90": dist.get("p90_score", 0),
            "p95": dist.get("p95_score", 0),
        },
        "grade_thresholds": [
            {"grade": "不适宜区", "score_range": f"0 — {local_floor}", "meaning": f"低于全省均值80%，省内相对弱势"},
            {"grade": "一般适宜区", "score_range": f"{local_floor} — {mean_s:.4f}", "meaning": "处于全省平均水平附近"},
            {"grade": "较适宜区", "score_range": f"{mean_s:.4f} — {local_high}", "meaning": "高于全省平均，有发展潜力"},
            {"grade": "核心优势区", "score_range": f"{local_high} — 1.0", "meaning": "本省生态条件最优区域"},
        ],
        "note": (
            f"参考：全球苹果生态适生阈值 = {model_t:.3f}（GBDT 物种分布模型）。"
            "省内等级划分基于数据分布，用于相对比较。"
            "适宜性得分来自 WorldClim 6 个气候变量，值域 0-1。"
        ),
    }



def _build_city_scorecards(raw: dict, semantic: dict) -> list[dict]:
    """为每个城市生成一份数值卡片，包含得分 + 等级占比。"""
    city_stats = raw.get("city_stats", [])
    city_grades = raw.get("stats", {}).get("city_grade_ratios", [])

    # 建 grade 索引
    grade_map = {}
    for cg in city_grades:
        grade_map[cg["region"]] = cg

    # 建排名索引（按综合得分排序）
    all_regions = [s["region"] for s in city_stats]
    sorted_by_composite = sorted(
        city_stats,
        key=lambda x: _compute_composite(x.get("mean_score", 0), x.get("max_score", 0)),
        reverse=True,
    )

    cards = []
    for rank_idx, city in enumerate(sorted_by_composite, 1):
        region = city["region"]
        ginfo = grade_map.get(region, {})
        grade_ratios = ginfo.get("grade_ratios", [])

        # 提取各等级占比
        grade_pct = {}
        for g in grade_ratios:
            grade_pct[g["grade_name"]] = round(g["area_ratio"] * 100, 1)

        _mean = city.get("mean_score", 0)
        _max = city.get("max_score", 0)
        composite = _compute_composite(_mean, _max)

        card = {
            "rank": rank_idx,
            "region": region,
            "composite_score": composite,
            "mean_score": _mean,
            "max_score": _max,
            "min_score": city.get("min_score", 0),
            "city_type": _classify_city_type(_max, _mean),
            "max_mean_ratio": round(_max / max(_mean, 0.001), 2),
            "core_ratio_pct": grade_pct.get("核心优势区", 0),
            "suitable_ratio_pct": grade_pct.get("较适宜区", 0),
            "general_ratio_pct": grade_pct.get("一般适宜区", 0),
            "unsuitable_ratio_pct": grade_pct.get("不适宜区", 0),
            "dominant_grade": ginfo.get("dominant_grade", ""),
            "total_cities": len(sorted_by_composite),
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

    # 按均分、按峰值分别找最优城市
    by_mean = max(city_scorecards, key=lambda c: c["mean_score"])
    by_max = max(city_scorecards, key=lambda c: c["max_score"])

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
        "best_city_score": top5[0]["composite_score"] if top5 else 0,
        "best_city_by_mean": by_mean["region"],
        "best_city_by_mean_score": by_mean["mean_score"],
        "best_city_by_max": by_max["region"],
        "best_city_by_max_score": by_max["max_score"],
        "worst_city": bottom5[-1]["region"] if bottom5 else "",
        "worst_city_score": bottom5[-1]["composite_score"] if bottom5 else 0,
        "leading_group_description": ranking_semantic.get("leading_group", {}).get("description", ""),
        "peak_cities": [c for c in city_scorecards if c["city_type"] == "高峰值潜力型"],
    }


def _build_peak_analysis(city_scorecards: list[dict], ranking_semantic: dict, numerical_basis: dict) -> dict:
    """峰值潜力分析：识别均分不高但拥有顶级地块的城市。"""
    peak_cities = [c for c in city_scorecards if c["city_type"] == "高峰值潜力型"]
    model_threshold = numerical_basis.get("province_level", {}).get("model_threshold", 0.417)

    # 数据驱动 insight
    insight_parts = []
    for pc in peak_cities[:3]:
        insight_parts.append(
            f"{pc['region']}虽均分（{pc['mean_score']:.3f}）非最高，"
            f"但境内部分区域达到 {pc['max_score']:.3f} 的高适宜性水平"
            f"（峰值/均值比 = {pc['max_mean_ratio']:.1f}），"
            f"存在优质种植潜力区。"
        )

    # 排名分歧：按 composite 排 vs 按 mean 排，差异 ≥ 2 的城市
    by_mean_rank = sorted(city_scorecards, key=lambda c: c["mean_score"], reverse=True)
    ranking_mismatch = []
    for c in city_scorecards:
        mean_rank = by_mean_rank.index(c) + 1
        comp_rank = c["rank"]
        diff = mean_rank - comp_rank
        if abs(diff) >= 2:
            ranking_mismatch.append({
                "region": c["region"],
                "mean_rank": mean_rank,
                "composite_rank": comp_rank,
                "rank_change": diff,
                "max_score": c["max_score"],
                "mean_score": c["mean_score"],
            })

    return {
        "exists": len(peak_cities) > 0,
        "peak_cities": peak_cities,
        "peak_city_count": len(peak_cities),
        "ranking_mismatch": ranking_mismatch[:5],
        "insight": "；".join(insight_parts) if insight_parts else "无显著峰值潜力城市。",
        "model_threshold": round(model_threshold, 4),
        "note": (
            "峰值潜力分析识别那些虽平均适宜性不高，"
            "但拥有局部顶级适宜区的城市（max/mean ≥ 2.5 且 max ≥ 0.30）。"
            "对农业生产而言，局部优质地块的价值远超均值指标所反映的水平。"
        ),
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
            "better_ratio": grade_structure["better_ratio"],
            "general_ratio": grade_structure["general_ratio"],
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
