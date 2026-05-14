def build_semantic_insights(
    city_stats: list,
    threshold: float = 0.148,
):
    """
    基于市级适宜性统计结果，
    构建农业产业语义信息（Semantic Insights）

    输入:
    [
        {
            "region": "德州市",
            "mean_score": 0.4619,
            "max_score": 0.6999,
            "min_score": 0.2613
        }
    ]

    输出:
    [
        {
            "region": "德州市",
            "industry_level": "核心优势区",
            "threshold_ratio": 3.12,
            "development_potential": "高",
            "risk_level": "低",
            "spatial_position": "高适宜性集聚区",
            "climate_comment": "...",
            "development_advice": [...],
            "risks": [...]
        }
    ]
    """

    insights = []

    # =========================
    # 全局统计
    # =========================
    all_scores = [x["mean_score"] for x in city_stats]

    overall_mean = sum(all_scores) / len(all_scores)

    high_count = len([x for x in all_scores if x >= threshold * 2])
    low_count = len([x for x in all_scores if x < threshold])

    # =========================
    # 空间格局
    # =========================
    if high_count / len(all_scores) > 0.4:
        spatial_pattern = "适宜性高值区域分布较广，具备规模化产业发展基础"
    elif high_count > 0:
        spatial_pattern = "适宜性高值区域呈局部集聚分布"
    else:
        spatial_pattern = "整体适宜性偏低，高适宜区较少"

    # =========================
    # 单区域分析
    # =========================
    for item in city_stats:

        region = item["region"]

        mean_score = item["mean_score"]
        max_score = item["max_score"]
        min_score = item["min_score"]

        ratio = round(mean_score / threshold, 2)

        # =========================
        # 产业等级
        # =========================
        if ratio >= 3:
            industry_level = "核心优势区"
            development_potential = "高"
            risk_level = "低"

        elif ratio >= 2:
            industry_level = "重点发展区"
            development_potential = "较高"
            risk_level = "较低"

        elif ratio >= 1:
            industry_level = "一般适宜区"
            development_potential = "中等"
            risk_level = "中等"

        else:
            industry_level = "风险区"
            development_potential = "低"
            risk_level = "高"

        # =========================
        # 气候解释
        # =========================
        if mean_score >= 0.4:
            climate_comment = "区域整体热量与水热条件较为协调，具备较好的苹果适生基础"

        elif mean_score >= 0.25:
            climate_comment = "区域具备一定苹果种植基础，但局部生态条件存在一定限制"

        else:
            climate_comment = "区域生态适宜性偏低，苹果种植稳定性可能不足"

        # =========================
        # 空间特征
        # =========================
        if mean_score > overall_mean:
            spatial_position = "区域适宜性高于全省平均水平"
        else:
            spatial_position = "区域适宜性低于全省平均水平"

        # =========================
        # 风险分析
        # =========================
        risks = []

        if min_score < threshold:
            risks.append("部分区域低于适生阈值，存在种植不稳定风险")

        if (max_score - min_score) > 0.4:
            risks.append("区域内部适宜性差异较大，需分区布局")

        if mean_score < 0.25:
            risks.append("整体生态适宜性偏低，不建议大规模扩张")

        if not risks:
            risks.append("整体种植风险相对可控")

        # =========================
        # 产业建议
        # =========================
        if industry_level == "核心优势区":

            development_advice = [
                "优先建设标准化苹果种植基地",
                "推进规模化与现代化果园建设",
                "加强冷链物流与区域品牌建设",
                "重点发展优质苹果产业带",
            ]

        elif industry_level == "重点发展区":

            development_advice = [
                "适度扩大苹果种植规模",
                "加强水肥管理与品种优化",
                "提升产业组织化水平",
            ]

        elif industry_level == "一般适宜区":

            development_advice = [
                "建议开展小规模试种",
                "加强农业基础设施建设",
                "重点关注灌溉与防灾能力",
            ]

        else:

            development_advice = [
                "谨慎布局苹果产业",
                "避免盲目扩大种植面积",
                "建议优先发展替代作物",
            ]

        # =========================
        # 汇总
        # =========================
        insights.append(
            {
                "region": region,
                "industry_level": industry_level,
                "threshold_ratio": ratio,
                "development_potential": development_potential,
                "risk_level": risk_level,
                "spatial_position": spatial_position,
                "climate_comment": climate_comment,
                "development_advice": development_advice,
                "risks": risks,
                "spatial_pattern": spatial_pattern,
                "mean_score": mean_score,
                "max_score": max_score,
                "min_score": min_score,
            }
        )

    return insights
