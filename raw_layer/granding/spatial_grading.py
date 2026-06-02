import numpy as np


def build_spatial_grading_system(city_stats):
    """
    构建空间分级体系（Spatial Grading System）

    用于：
    ----------
    1. 空间热点识别
    2. 空间冷点识别
    3. 空间集聚分析
    4. 空间连续性分析
    5. 空间语义统一

    注意：
    ----------
    这是“相对空间分级体系”，
    不等于 suitability grading。

    Parameters
    ----------
    city_stats : list[dict]

    Returns
    ----------
    dict
    """

    # =========================================
    # 1️⃣ 提取 score
    # =========================================

    scores = np.array(
        [x["mean_score"] for x in city_stats if x["mean_score"] is not None]
    )

    # =========================================
    # 2️⃣ 计算空间阈值（Quantile）
    # =========================================

    hotspot_threshold = float(np.quantile(scores, 0.75))

    secondary_hotspot_threshold = float(np.quantile(scores, 0.60))

    coldspot_threshold = float(np.quantile(scores, 0.25))

    # =========================================
    # 3️⃣ 构建空间等级
    # =========================================

    spatial_levels = [
        {
            "name": "空间热点区",
            "min_score": hotspot_threshold,
            "max_score": float(np.max(scores)) + 1e-6,
        },
        {
            "name": "次热点区",
            "min_score": secondary_hotspot_threshold,
            "max_score": hotspot_threshold,
        },
        {
            "name": "中间过渡区",
            "min_score": coldspot_threshold,
            "max_score": secondary_hotspot_threshold,
        },
        {
            "name": "空间冷点区",
            "min_score": float(np.min(scores)) - 1e-6,
            "max_score": coldspot_threshold,
        },
    ]

    # =========================================
    # 4️⃣ 输出
    # =========================================

    return {
        "thresholds": {
            "hotspot_threshold": round(hotspot_threshold, 4),
            "secondary_hotspot_threshold": round(
                secondary_hotspot_threshold,
                4,
            ),
            "coldspot_threshold": round(coldspot_threshold, 4),
        },
        "levels": spatial_levels,
    }
