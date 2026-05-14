import numpy as np


def compute_suitability_stats(array):
    """
    计算适宜性统计信息
    """

    # 去除 nan
    valid = array[~np.isnan(array)]

    if len(valid) == 0:
        return {
            "mean_score": None,
            "max_score": None,
            "min_score": None,
            "high_ratio": 0,
            "medium_ratio": 0,
            "low_ratio": 0,
        }

    # 基础统计
    mean_score = float(np.mean(valid))
    max_score = float(np.max(valid))
    min_score = float(np.min(valid))

    # 分类统计
    high_ratio = float(np.sum(valid >= 0.7) / len(valid))
    medium_ratio = float(np.sum((valid >= 0.4) & (valid < 0.7)) / len(valid))
    low_ratio = float(np.sum(valid < 0.4) / len(valid))

    return {
        "mean_score": round(mean_score, 4),
        "max_score": round(max_score, 4),
        "min_score": round(min_score, 4),
        "high_ratio": round(high_ratio, 4),
        "medium_ratio": round(medium_ratio, 4),
        "low_ratio": round(low_ratio, 4),
    }
