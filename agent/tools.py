"""
Agent 工具集 — 被 Claude 通过 tool use 调用的纯 Python 函数。

每个工具返回 JSON-serializable dict，供 Claude 组织自然语言回答。
所有数值计算由确定性管道完成，工具只是薄封装。
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from core.model_registry import model_exists, load_metadata, load_model_threshold
from core.predictor import init_predictor_from_disk

BASE_DIR = Path(__file__).resolve().parents[1]


# ═══════════════════════════════════════════════════════════════════
# 工具 1: 查询作物模型
# ═══════════════════════════════════════════════════════════════════
def check_crop_model(crop: str) -> dict:
    """查询指定作物是否有已训练的 SDM 模型。

    Returns
    -------
    {"exists": bool, "crop": str, "threshold": float | None, "eval_metrics": dict | None}
    """
    if not model_exists(crop):
        return {
            "exists": False,
            "crop": crop,
            "message": f"作物「{crop}」尚未训练模型。需要先调用 train_crop_model 训练。",
        }

    meta = load_metadata(crop)
    return {
        "exists": True,
        "crop": crop,
        "threshold": meta.get("threshold"),
        "eval_metrics": meta.get("eval_metrics"),
        "message": f"作物「{crop}」已有预训练模型，可直接分析。",
    }


# ═══════════════════════════════════════════════════════════════════
# 工具 2: 训练作物模型
# ═══════════════════════════════════════════════════════════════════
def train_crop_model(crop: str, scientific_name: str | None = None) -> dict:
    """训练新作物的 SDM 模型（全球 GBIF 数据 + GBDT）。

    训练耗时 3-5 分钟。此函数同步执行。

    Parameters
    ----------
    crop : 作物标识符（如 "peach", "rice"）
    scientific_name : GBIF 学名，不提供则用 crop 作为搜索词
    """
    from core.apple_sdm_trainer import train_crop_model as _train

    sci_name = scientific_name or crop

    try:
        result = _train(crop_name=crop, scientific_name=sci_name)
        return {
            "success": True,
            "crop": crop,
            "scientific_name": sci_name,
            "threshold": round(result["threshold"], 4),
            "roc_auc": result["eval_metrics"]["roc_auc"],
            "message": (
                f"模型训练完成。ROC AUC = {result['eval_metrics']['roc_auc']:.4f}，"
                f"阈值 = {result['threshold']:.4f}。现在可以对任意省份进行适宜性分析。"
            ),
        }
    except Exception as e:
        return {
            "success": False,
            "crop": crop,
            "error": str(e),
            "message": f"训练失败: {e}",
        }


# ═══════════════════════════════════════════════════════════════════
# 工具 3: 分析适宜性（核心工具）
# ═══════════════════════════════════════════════════════════════════
def analyze_suitability(crop: str, region: str) -> dict:
    """对指定区域进行完整的作物适宜性分析。

    内部调用完整管道：
    predict → zonal_stats → grading → semantic → context → summary

    返回精简摘要（非完整 context），避免 token 爆炸。
    """
    # 1. 检查模型
    if not model_exists(crop):
        return {
            "error": True,
            "message": f"作物「{crop}」尚未训练模型。请先调用 train_crop_model 训练，或使用 check_crop_model 查看可用作物。",
        }

    try:
        # 2. 加载模型
        init_predictor_from_disk(crop)

        # 3. 生成区域热力图 + 区域统计
        from raw_layer.map.map_service import generate_region_map, analyze_region_suitability
        from raw_layer.stats.zonal_stats import compute_region_zonal_stats
        from raw_layer.geo.region_locator import get_cities_within_province
        from utils.config_loader import CONFIG

        heatmap_path = generate_region_map(
            region, output_path=CONFIG["paths"]["output"]["region_map"]
        )
        province_city_gdf = get_cities_within_province(region)
        city_stats = compute_region_zonal_stats(province_city_gdf)
        overall_stats = analyze_region_suitability(region, city_stats)

        # 4. 等级体系
        from raw_layer.granding.suitability_grading import build_grading_system
        grading = build_grading_system(city_stats)

        # 5. 语义层
        from semantic_layer.ranking_semantic_sevice import build_ranking_semantic
        from semantic_layer.suitability_semantic_builder import (
            build_distribution_semantic,
            build_grade_semantic,
            build_city_grade_semantic,
        )
        from semantic_layer.semantic_metrics import build_semantic_metrics

        # 先计算等级分布和峰值信息，供 province_semantic 使用
        grade_sem = build_grade_semantic(overall_stats["grade_ratios"])
        unsuitable_ratio = grade_sem.get("unsuitable_ratio", 0)

        model_t = load_model_threshold(crop)
        has_peak = any(
            c.get("max_score", 0) >= model_t
            and c.get("max_score", 0) / max(c.get("mean_score", 0.001), 0.001) >= 2.0
            for c in city_stats
        )

        province_semantic = build_semantic_metrics(
            overall_stats["overall_stats"],
            unsuitable_ratio=unsuitable_ratio,
            has_peak_potential=has_peak,
        )
        ranking = build_ranking_semantic(city_stats, grading)
        dist_sem = build_distribution_semantic(overall_stats["distribution_stats"])

        # 6. 摘要
        city_cards = _build_city_summary(city_stats, overall_stats, ranking, grading)

        # 峰值分析
        peak_cities = []
        for c in city_cards[:5]:
            if c.get("max_score", 0) >= 0.30 and c.get("max_score", 0) / max(c.get("mean_score", 0.001), 0.001) >= 2.5:
                peak_cities.append({
                    "region": c["region"],
                    "max_score": c["max_score"],
                    "mean_score": c["mean_score"],
                    "ratio": round(c["max_score"] / max(c["mean_score"], 0.001), 1),
                })

        summary = {
            "region": region,
            "crop": crop,
            "province_viable": grading.get("province_viable", True),
            "province_assessment": {
                "suitability_level": province_semantic.get("suitability_level", ""),
                "risk_level": province_semantic.get("risk_level", ""),
                "development_advice": province_semantic.get("development_advice", ""),
            },
            "key_stats": {
                "province_mean_score": round(overall_stats["overall_stats"]["mean_score"], 4),
                "city_score_range": round(
                    max(c["mean_score"] for c in city_stats) - min(c["mean_score"] for c in city_stats), 4
                ),
                "model_threshold": round(model_t, 4),
            },
            "grade_distribution": {
                "core_ratio": round(grade_sem["core_ratio"] * 100, 1),
                "better_ratio": round(grade_sem["better_ratio"] * 100, 1),
                "general_ratio": round(grade_sem["general_ratio"] * 100, 1),
                "unsuitable_ratio": round(grade_sem["unsuitable_ratio"] * 100, 1),
                "dominant_grade": grade_sem["dominant_grade"],
            },
            "top_cities": city_cards[:5],
            "bottom_cities": city_cards[-3:],
            "peak_analysis": {
                "exists": len(peak_cities) > 0,
                "peak_cities": peak_cities,
            },
            "ranking_type": ranking.get("ranking_structure", {}).get("type", ""),
            "heatmap_path": heatmap_path,
        }

        # 7. 缓存完整 context 供后续 export_report / get_risk_detail 使用
        _cache_context(crop, region, city_stats, overall_stats, grading, ranking)

        return summary

    except Exception as e:
        return {"error": True, "message": f"分析失败: {e}"}


# ═══════════════════════════════════════════════════════════════════
# 工具 4: 多区域对比
# ═══════════════════════════════════════════════════════════════════
def compare_regions(crop: str, regions: list[str]) -> dict:
    """对比多个区域的适宜性。"""
    results = {}
    for r in regions:
        result = analyze_suitability(crop, r)
        if "error" not in result:
            results[r] = {
                "mean_score": result["key_stats"]["province_mean_score"],
                "dominant_grade": result["grade_distribution"]["dominant_grade"],
                "top_city": result["top_cities"][0]["region"] if result["top_cities"] else "",
                "top_city_score": result["top_cities"][0]["composite_score"] if result["top_cities"] else 0,
                "province_viable": result["province_viable"],
            }
        else:
            results[r] = {"error": result["message"]}

    # Ranking
    ranked = sorted(
        [(r, d["top_city_score"]) for r, d in results.items() if "error" not in d],
        key=lambda x: x[1],
        reverse=True,
    )

    return {
        "crop": crop,
        "regions_compared": len(results),
        "ranking": [{"region": r, "score": s} for r, s in ranked],
        "details": results,
    }


# ═══════════════════════════════════════════════════════════════════
# 工具 5: 城市风险详情
# ═══════════════════════════════════════════════════════════════════
def get_risk_detail(crop: str, region: str, city: str) -> dict:
    """获取指定城市的详细适宜性拆解。"""
    context = _load_cached_context(crop, region)

    if not context:
        return {"error": True, "message": f"请先运行 analyze_suitability('{crop}', '{region}')"}

    city_data = None
    for c in context.get("city_stats", []):
        if city in c.get("region", ""):
            city_data = c
            break

    if not city_data:
        return {"error": True, "message": f"未找到城市「{city}」的数据"}

    # 等级占比
    grade_map = {}
    for cg in context.get("grade_ratios", []):
        if cg.get("region") == city_data["region"]:
            for g in cg.get("grade_ratios", []):
                grade_map[g["grade_name"]] = round(g["area_ratio"] * 100, 1)
            break

    model_t = load_model_threshold(crop)
    _max = city_data.get("max_score", 0)
    _mean = city_data.get("mean_score", 0)

    return {
        "city": city,
        "region": region,
        "crop": crop,
        "scores": {
            "mean": round(_mean, 4),
            "max": round(_max, 4),
            "min": round(city_data.get("min_score", 0), 4),
        },
        "grade_ratios": grade_map,
        "assessment": {
            "above_global_threshold": _max >= model_t,
            "global_threshold": round(model_t, 4),
            "peak_ratio": round(_max / max(_mean, 0.001), 1),
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 工具 6: 导出报告
# ═══════════════════════════════════════════════════════════════════
def export_report(crop: str, region: str, template: str = "standard") -> dict:
    """导出 HTML 分析报告。

    Parameters
    ----------
    template : "standard" (详细报告) 或 "dashboard" (仪表盘)
    """
    # 尝试从缓存加载原始数据
    cached = _load_cached_context(crop, region)

    if not cached:
        # 没有缓存 → 重新分析
        result = analyze_suitability(crop, region)
        if "error" in result:
            return {"error": True, "message": result["message"]}
        cached = _load_cached_context(crop, region)

    if not cached:
        return {"error": True, "message": "无法生成报告上下文"}

    try:
        from semantic_layer.semantic_layer import build_semantic_layer
        from context_layer.build_context import build_report_context
        from report_layer.apple_report_service import generate_data_report
        from utils.json_handler import save_json, load_json
        from utils.gdf_handler import sanitize_gdf_for_save
        from raw_layer.geo.region_locator import get_cities_within_province
        from report_layer.static_map_service import (
            plot_ranking_table,
            plot_score_range_chart,
        )
        from utils.config_loader import CONFIG

        # 重建 region_gdf
        province_city_gdf = get_cities_within_province(region)
        clean_gdf = sanitize_gdf_for_save(province_city_gdf)

        # 保存临时文件供 semantic_layer 使用
        tmp_raw = BASE_DIR / "output" / "cache" / "pipeline" / f"{crop}_{region}_raw.json"
        tmp_gdf = BASE_DIR / "output" / "cache" / "pipeline" / f"{crop}_{region}_gdf.geojson"

        raw_data = {
            "region_name": region,
            "apple_suitability_heatmap_path": str(
                BASE_DIR / "output" / "predictions" / "region_map.png"
            ),
            "stats": cached["stats"],
            "city_stats": cached["city_stats"],
        }
        save_json(raw_data, str(tmp_raw))
        clean_gdf.to_file(tmp_gdf, driver="GeoJSON")

        # 生成静态图（语义层构建时也会生成，这里预先生成确保存在）
        plot_ranking_table(cached["city_stats"])
        plot_score_range_chart(cached["city_stats"])

        # 构建语义层 → context → 渲染
        semantic_data = build_semantic_layer(str(tmp_raw), str(tmp_gdf))
        tmp_semantic = BASE_DIR / "output" / "cache" / "pipeline" / f"{crop}_{region}_semantic.json"
        save_json(semantic_data, str(tmp_semantic))

        ctx = build_report_context(str(tmp_semantic), str(tmp_raw))

        # 每个作物+区域输出独立报告，避免相互覆盖
        report_path = (
            BASE_DIR / "output" / "reports" / f"{crop}_{region}_{template}.html"
        )
        generate_data_report(ctx, template=template, output_path=str(report_path))
        html_path = str(report_path)

        return {
            "success": True,
            "html_path": str(html_path),
            "template": template,
            "message": f"报告已生成: {html_path}",
        }
    except Exception as e:
        import traceback
        return {"error": True, "message": f"报告生成失败: {e}", "traceback": traceback.format_exc()}


# ═══════════════════════════════════════════════════════════════════
# 内部辅助
# ═══════════════════════════════════════════════════════════════════

def _build_city_summary(city_stats, overall_stats, ranking, grading) -> list[dict]:
    """构建城市摘要列表（按综合得分排序）。"""
    from context_layer.build_context import _compute_composite

    cards = []
    for city in city_stats:
        _mean = city.get("mean_score", 0)
        _max = city.get("max_score", 0)
        composite = _compute_composite(_mean, _max)
        cards.append({
            "region": city["region"],
            "mean_score": round(_mean, 4),
            "max_score": round(_max, 4),
            "composite_score": composite,
        })

    cards.sort(key=lambda c: c["composite_score"], reverse=True)
    for i, c in enumerate(cards):
        c["rank"] = i + 1

    return cards


_CONTEXT_CACHE: dict[str, dict] = {}


def _cache_key(crop: str, region: str) -> str:
    return f"{crop}::{region}"


def _cache_context(crop: str, region: str, city_stats, overall_stats, grading, ranking):
    """缓存分析上下文，供后续工具使用。"""
    _CONTEXT_CACHE[_cache_key(crop, region)] = {
        "crop": crop,
        "region_name": region,
        "city_stats": city_stats,
        "stats": overall_stats,
        "grading": grading,
        "ranking": ranking,
    }


def _load_cached_context(crop: str, region: str) -> dict | None:
    return _CONTEXT_CACHE.get(_cache_key(crop, region))
