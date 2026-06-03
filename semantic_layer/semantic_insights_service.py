from core.model_registry import load_model_threshold


def build_semantic_insights(
    city_stats: list,
    threshold: float = None,
):
    if threshold is None:
        threshold = load_model_threshold()
    """
    构建市级农业适宜性语义解释层（单区域层）

    核心回答：
    - 是否适宜
    - 为什么适宜/不适宜
    - 风险在哪里
    - 如何发展

    注意：
    - 不负责空间格局
    - 不负责区域排名
    - 不负责空间集聚
    - 不负责产业带分析

    这些内容由：
    - spatial_semantic
    - ranking_semantic

    单独负责。

    Parameters
    ----------
    city_stats : list[dict]

    threshold : float
        生态适生阈值

    Returns
    -------
    list[dict]
    """

    insights = []

    for item in city_stats:

        region = item["region"]

        mean_score = item["mean_score"]
        max_score = item["max_score"]
        min_score = item["min_score"]

        # ---------------------------------------------------
        # 1️⃣ 阈值倍率
        # ---------------------------------------------------

        ratio = round(mean_score / threshold, 2)

        # ---------------------------------------------------
        # 2️⃣ 产业等级
        # ---------------------------------------------------

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

        # ---------------------------------------------------
        # 3️⃣ 气候生态解释
        # ---------------------------------------------------

        if mean_score >= 0.4:

            climate_comment = (
                "区域整体水热条件协调，生态适宜性较高，" "具备较好的苹果产业发展基础"
            )

        elif mean_score >= 0.25:

            climate_comment = (
                "区域具备一定苹果种植条件，" "但局部生态条件仍存在一定限制"
            )

        else:

            climate_comment = "区域整体生态适宜性偏弱，" "苹果种植稳定性可能不足"

        # ---------------------------------------------------
        # 4️⃣ 风险分析
        # ---------------------------------------------------

        risks = []

        # 局部低适宜风险
        if min_score < threshold:

            risks.append("部分区域低于生态适生阈值，存在种植不稳定风险")

        # 区域内部差异
        if (max_score - min_score) > 0.4:

            risks.append("区域内部适宜性差异较大，需进行分区布局")

        # 整体生态风险
        if mean_score < 0.25:

            risks.append("整体生态适宜性偏低，不建议大规模扩张")

        # 默认风险
        if not risks:

            risks.append("整体种植风险相对可控")

        # ---------------------------------------------------
        # 5️⃣ 发展建议
        # ---------------------------------------------------

        if industry_level == "核心优势区":

            development_advice = [
                "优先建设标准化苹果种植基地",
                "推进规模化与现代化果园建设",
                "加强冷链物流与区域品牌建设",
                "重点发展优质苹果产业",
            ]

        elif industry_level == "重点发展区":

            development_advice = [
                "适度扩大苹果种植规模",
                "加强水肥管理与品种优化",
                "提升产业组织化水平",
            ]

        elif industry_level == "一般适宜区":

            development_advice = [
                "建议开展适度规模试种",
                "加强农业基础设施建设",
                "重点提升灌溉与防灾能力",
            ]

        else:

            development_advice = [
                "谨慎布局苹果产业",
                "避免盲目扩大种植面积",
                "建议优先发展替代作物",
            ]

        # ---------------------------------------------------
        # 6️⃣ 输出
        # ---------------------------------------------------

        insights.append(
            {
                "region": region,
                # 核心结论
                "industry_level": industry_level,
                "development_potential": development_potential,
                "risk_level": risk_level,
                # 定量指标
                # "threshold_ratio": ratio,
                # "mean_score": round(mean_score, 4),
                # "max_score": round(max_score, 4),
                # "min_score": round(min_score, 4),
                # 解释层
                "climate_comment": climate_comment,
                "risks": risks,
                "development_advice": development_advice,
            }
        )

    return insights
