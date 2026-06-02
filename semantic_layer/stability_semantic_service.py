from typing import Dict, List


def build_stability_semantic(city_stats: List[Dict]) -> Dict:
    """
    构建“稳定性语义层”

    目标：
    - 不做自然语言大段报告
    - 只生成结构化稳定性认知
    - 为 LLM 提供“波动性 / 稳定性”推理依据

    输入:
        city_stats:
        [
            {
                "region": "德州市",
                "mean_score": 0.46,
                "max_score": 0.70,
                "min_score": 0.26
            }
        ]

    输出:
        {
            "stability_overview": {},
            "high_fluctuation_regions": [],
            "stable_regions": [],
            "stability_structure": {}
        }
    """

    stability_records = []

    # =========================
    # 1. 计算波动指标
    # =========================

    for city in city_stats:

        region = city["region"]

        mean_score = city["mean_score"]
        max_score = city["max_score"]
        min_score = city["min_score"]

        score_range = round(max_score - min_score, 4)

        # 避免除零
        fluctuation_ratio = round(score_range / mean_score, 4) if mean_score > 0 else 0

        # =========================
        # 稳定性等级
        # =========================

        if fluctuation_ratio >= 1.5:
            stability_level = "波动极高"
            stability_risk = "区域内部适宜性差异显著"

        elif fluctuation_ratio >= 1.0:
            stability_level = "波动较高"
            stability_risk = "存在一定空间不稳定性"

        elif fluctuation_ratio >= 0.6:
            stability_level = "相对稳定"
            stability_risk = "整体适宜性较均衡"

        else:
            stability_level = "稳定"
            stability_risk = "区域内部适宜性稳定"

        stability_records.append(
            {
                "region": region,
                "score_range": score_range,
                "fluctuation_ratio": fluctuation_ratio,
                "stability_level": stability_level,
                "stability_risk": stability_risk,
            }
        )

    # =========================
    # 2. 高波动区域
    # =========================

    high_fluctuation_regions = sorted(
        [x for x in stability_records if x["fluctuation_ratio"] >= 1.0],
        key=lambda x: x["fluctuation_ratio"],
        reverse=True,
    )

    # =========================
    # 3. 稳定区域
    # =========================

    stable_regions = sorted(
        [x for x in stability_records if x["fluctuation_ratio"] < 0.8],
        key=lambda x: x["fluctuation_ratio"],
    )

    # =========================
    # 4. 全省稳定性结构
    # =========================

    avg_fluctuation = round(
        sum(x["fluctuation_ratio"] for x in stability_records) / len(stability_records),
        4,
    )

    if avg_fluctuation >= 1.2:
        province_stability = "整体波动较大"

    elif avg_fluctuation >= 0.8:
        province_stability = "存在一定空间差异"

    else:
        province_stability = "整体稳定性较好"

    # =========================
    # 5. 返回结构化语义
    # =========================

    return {
        "overall_stability": {
            "avg_fluctuation_ratio": avg_fluctuation,
            "province_stability": province_stability,
        },
        "unstable_regions": [
            {
                "region": x["region"],
                "fluctuation_ratio": x["fluctuation_ratio"],
                "stability_level": x["stability_level"],
            }
            for x in high_fluctuation_regions[:5]
        ],
        "high_stability_regions": [
            {
                "region": x["region"],
                "fluctuation_ratio": x["fluctuation_ratio"],
                "stability_level": x["stability_level"],
            }
            for x in stable_regions[:5]
        ],
        "stability_structure": stability_records,
    }
