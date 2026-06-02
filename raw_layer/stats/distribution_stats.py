import numpy as np


def compute_distribution_stats(array):
    """
    适宜性分布统计

    Parameters
    ----------
    array : np.ndarray
        suitability raster

    Returns
    -------
    dict
    """

    valid = array[~np.isnan(array)]

    if len(valid) == 0:
        return {
            "mean_score": 0,
            "std_score": 0,
            "median_score": 0,
            "p75_score": 0,
            "p90_score": 0,
            "p95_score": 0,
        }

    return {
        "mean_score": round(float(np.mean(valid)), 4),
        "std_score": round(float(np.std(valid)), 4),
        "median_score": round(float(np.percentile(valid, 50)), 4),
        "p75_score": round(float(np.percentile(valid, 75)), 4),
        "p90_score": round(float(np.percentile(valid, 90)), 4),
        "p95_score": round(float(np.percentile(valid, 95)), 4),
    }
