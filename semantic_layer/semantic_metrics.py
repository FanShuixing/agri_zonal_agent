from core.model_registry import load_model_threshold


def build_semantic_metrics(stats: dict, threshold: float = None) -> dict:
    if threshold is None:
        threshold = load_model_threshold()
    """
    基于适宜性统计数据，生成农业语义分析结果

    输入:
    {
        "mean_score": 0.4619,
        "max_score": 0.6999,
        "min_score": 0.2613,
        "high_ratio": 0.12,
        "medium_ratio": 0.35,
        "low_ratio": 0.53
    }

    输出:
    {
        "threshold_ratio": 3.12,
        "suitability_level": "重点适宜区",
        "industrialization_level": "适合规模化发展",
        "stability_level": "稳定性较高",
        "risk_level": "低风险",
        "risk_hint": "...",
        "development_advice": "...",
    }
    """
    mean_score = stats.get("mean_score")
    max_score = stats.get("max_score")
    min_score = stats.get("min_score")

    high_ratio = stats.get("high_ratio", 0)
    medium_ratio = stats.get("medium_ratio", 0)
    low_ratio = stats.get("low_ratio", 0)

    # 空数据保护
    if mean_score is None:
        return {
            "threshold_ratio": None,
            "suitability_level": "无数据",
            "industrialization_level": "无法判断",
            "stability_level": "无法判断",
            "risk_level": "未知",
            "risk_hint": "区域缺少有效栅格数据",
            "development_advice": "建议补充数据后重新分析",
        }

    # =========================
    # 阈值倍数
    # =========================
    threshold_ratio = round(mean_score / threshold, 2)

    # =========================
    # 适宜性等级
    # =========================
    if threshold_ratio >= 2.5:
        suitability_level = "重点适宜区"

    elif threshold_ratio >= 1.8:
        suitability_level = "较适宜区"

    elif threshold_ratio >= 1.2:
        suitability_level = "一般适宜区"

    else:
        suitability_level = "边缘适宜区"

    # =========================
    # 空间稳定性
    # =========================
    spread = max_score - min_score

    if spread <= 0.2:
        stability_level = "稳定性较高"

    elif spread <= 0.4:
        stability_level = "稳定性中等"

    else:
        stability_level = "空间差异较大"

    # =========================
    # 风险等级
    # =========================
    if min_score < threshold * 0.8:
        risk_level = "高风险"

    elif min_score < threshold:
        risk_level = "中等风险"

    else:
        risk_level = "低风险"

    # =========================
    # 产业化潜力
    # =========================
    if (
        threshold_ratio >= 2.5
        and high_ratio >= 0.1
        and stability_level != "空间差异较大"
    ):
        industrialization_level = "适合规模化发展"

    elif threshold_ratio >= 1.8:
        industrialization_level = "具备一定产业发展潜力"

    elif threshold_ratio >= 1.2:
        industrialization_level = "适合小规模试种"

    else:
        industrialization_level = "不建议大规模发展"

    # =========================
    # 风险提示
    # =========================
    risk_hints = []

    if min_score < threshold:
        risk_hints.append("局部区域低于适生阈值")

    if spread > 0.4:
        risk_hints.append("区域内部适宜性差异明显")

    if low_ratio > 0.7:
        risk_hints.append("低适宜区域占比较高")

    if high_ratio < 0.05:
        risk_hints.append("高适宜区域分布有限")

    if len(risk_hints) == 0:
        risk_hints.append("整体种植风险相对可控")

    # =========================
    # 发展建议
    # =========================
    if suitability_level == "重点适宜区":
        development_advice = (
            "建议作为苹果产业重点发展区域，"
            "可适度扩大种植规模，并加强标准化与产业化建设。"
        )

    elif suitability_level == "较适宜区":
        development_advice = (
            "建议稳步推进苹果产业发展，" "重点优化品种结构与农业基础设施。"
        )

    elif suitability_level == "一般适宜区":
        development_advice = "建议开展小规模试种，" "重点关注灌溉、防灾及生态适应性。"

    else:
        development_advice = "区域整体适宜性偏低，" "不建议进行大规模苹果产业扩张。"

    return {
        "threshold_ratio": threshold_ratio,
        "suitability_level": suitability_level,
        "industrialization_level": industrialization_level,
        "stability_level": stability_level,
        "risk_level": risk_level,
        "risk_hint": "；".join(risk_hints),
        "development_advice": development_advice,
    }
