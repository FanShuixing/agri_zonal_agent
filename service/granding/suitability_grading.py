from dataclasses import dataclass
import numpy as np


@dataclass
class SuitabilityGrade:

    name: str
    min_score: float
    max_score: float
    description: str


def compute_high_threshold(scores):

    mean_score = np.mean(scores)

    std_score = np.std(scores)

    return mean_score + 0.5 * std_score


def compute_spatial_thresholds(
    city_stats,
    suitable_threshold=0.148,
):
    scores = np.array(
        [x["mean_score"] for x in city_stats if x["mean_score"] is not None]
    )

    mean_score = float(np.mean(scores))

    low_threshold = max(
        suitable_threshold,
        mean_score * 0.8,
    )

    high_threshold = float(np.percentile(scores, 75))

    return (
        round(low_threshold, 4),
        round(high_threshold, 4),
    )


import numpy as np


def build_grading_system(
    city_stats,
    suitable_threshold=0.148,
):
    """
    构建统一适宜性等级体系（Unified Grading System）

    功能：
    ----------
    1. 自动计算空间分析阈值
    2. 自动生成适宜性等级体系
    3. 为 ranking / semantic / spatial / context 提供统一标准

    Parameters
    ----------
    city_stats : list[dict]

        示例：
        [
            {
                "region": "德州市",
                "mean_score": 0.46,
            }
        ]

    suitable_threshold : float

        模型生态适生阈值

    Returns
    ----------
    {
        "thresholds": {...},
        "grades": [...]
    }
    """

    # =========================================
    # 1️⃣ 提取 score
    # =========================================

    scores = np.array(
        [x["mean_score"] for x in city_stats if x.get("mean_score") is not None]
    )

    if len(scores) == 0:
        raise ValueError("city_stats 中不存在有效 mean_score")

    # =========================================
    # 2️⃣ 基础统计
    # =========================================

    mean_score = float(np.mean(scores))

    std_score = float(np.std(scores))

    # =========================================
    # 3️⃣ 动态阈值
    # =========================================

    # 低值区：
    # 接近适生阈值
    low_threshold = max(
        suitable_threshold,
        mean_score * 0.8,
    )

    # 中值区：
    # 全省平均水平
    medium_threshold = mean_score

    # 高值区：
    # 高于平均 + 0.5 std
    high_threshold = mean_score + 0.5 * std_score

    # =========================================
    # 4️⃣ 统一等级体系
    # =========================================

    grades = [
        {
            "name": "不适宜区",
            "min": -999,
            "max": suitable_threshold,
            "description": "低于生态适生阈值，产业发展风险较高",
        },
        {
            "name": "一般适宜区",
            "min": suitable_threshold,
            "max": medium_threshold,
            "description": "具备一定苹果种植基础，但整体适宜性有限",
        },
        {
            "name": "较适宜区",
            "min": medium_threshold,
            "max": high_threshold,
            "description": "适宜性高于区域平均水平，具备一定产业发展潜力",
        },
        {
            "name": "核心优势区",
            "min": high_threshold,
            "max": 999,
            "description": "区域生态条件较优，具备规模化产业发展潜力",
        },
    ]

    # =========================================
    # 5️⃣ 输出
    # =========================================

    grading_system = {
        "thresholds": {
            "suitable_threshold": round(suitable_threshold, 4),
            "low_threshold": round(low_threshold, 4),
            "medium_threshold": round(medium_threshold, 4),
            "high_threshold": round(high_threshold, 4),
            "mean_score": round(mean_score, 4),
            "std_score": round(std_score, 4),
        },
        "grades": grades,
    }

    return grading_system


def classify_suitability(score, grading_system):

    grades = grading_system["grades"]

    for grade in grades:

        if grade["min"] <= score < grade["max"]:
            return grade["name"]

    return "未知"
