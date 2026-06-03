import numpy as np
from core.model_registry import load_model_threshold


def build_grading_system(
    city_stats,
    suitable_threshold=None,
):
    """
    构建统一适宜性等级体系（Unified Grading System）

    核心设计：
    - 等级边界完全由省内数据分布驱动（均值 + 标准差），做省内相对比较
    - 模型全局阈值仅作为参考标注，不参与等级划分
    - 换省换物种自动适配，无需修改阈值

    Returns
    ----------
    {
        "thresholds": {
            "model_threshold": 0.417,   # 全球生态适生阈值（参考线）
            "low_threshold": ...,       # 不适宜 / 一般适宜 分界
            "medium_threshold": ...,    # 一般 / 较适宜 分界
            "high_threshold": ...,      # 较适宜 / 核心优势 分界
            "mean_score": ...,
            "std_score": ...,
        },
        "grades": [...]
    }
    """
    model_threshold = suitable_threshold if suitable_threshold is not None else load_model_threshold()

    scores = np.array(
        [x["mean_score"] for x in city_stats if x.get("mean_score") is not None]
    )
    if len(scores) == 0:
        raise ValueError("city_stats 中不存在有效 mean_score")

    mean_score = float(np.mean(scores))
    std_score = float(np.std(scores))
    max_city_score = float(np.max(scores))

    # ═══════════════════════════════════════════
    # 最低门槛：省内最优城市必须达到模型阈值的 30%
    # 否则全省气候条件根本不适合，无需省内比较
    # ═══════════════════════════════════════════
    min_absolute_floor = model_threshold * 0.3
    province_viable = max_city_score >= min_absolute_floor

    if not province_viable:
        return {
            "thresholds": {
                "model_threshold": round(model_threshold, 4),
                "min_absolute_floor": round(min_absolute_floor, 4),
                "max_city_score": round(max_city_score, 4),
                "mean_score": mean_score,
                "std_score": std_score,
            },
            "grades": [
                {
                    "name": "不适宜种植区",
                    "min": -999,
                    "max": 999,
                    "description": (
                        f"全省最优城市（{max_city_score:.4f}）远低于"
                        f"全球生态适生阈值下限（{min_absolute_floor:.4f}），"
                        "该区域气候条件不适合苹果种植，不建议发展苹果产业。"
                    ),
                },
            ],
            "province_viable": False,
        }

    # ═══════════════════════════════════════════
    # 省内相对分级（仅当省份通过最低门槛时启用）
    # ═══════════════════════════════════════════
    low_threshold = round(mean_score * 0.8, 4)
    medium_threshold = round(mean_score, 4)
    high_threshold = round(mean_score + 0.5 * std_score, 4)

    grades = [
        {
            "name": "不适宜区",
            "min": -999,
            "max": low_threshold,
            "description": "低于全省均值 80%，在本省内相对弱势",
        },
        {
            "name": "一般适宜区",
            "min": low_threshold,
            "max": medium_threshold,
            "description": "处于全省平均水平附近，具备一定种植基础",
        },
        {
            "name": "较适宜区",
            "min": medium_threshold,
            "max": high_threshold,
            "description": "高于区域平均水平，具备产业发展潜力",
        },
        {
            "name": "核心优势区",
            "min": high_threshold,
            "max": 999,
            "description": "本省生态条件最优，适合规模化发展",
        },
    ]

    return {
        "thresholds": {
            "model_threshold": round(model_threshold, 4),
            "min_absolute_floor": round(min_absolute_floor, 4),
            "low_threshold": low_threshold,
            "medium_threshold": medium_threshold,
            "high_threshold": high_threshold,
            "mean_score": mean_score,
            "std_score": std_score,
        },
        "grades": grades,
        "province_viable": True,
    }


def classify_suitability(score, grading_system):
    grades = grading_system["grades"]
    for grade in grades:
        if grade["min"] <= score < grade["max"]:
            return grade["name"]
    return "未知"
