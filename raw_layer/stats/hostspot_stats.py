import numpy as np
from scipy.ndimage import label


def compute_hotspot_stats(
    array,
    grading_system,
):
    """
    hotspot统计

    Parameters
    ----------
    array : np.ndarray

    hotspot_threshold : float
        hotspot阈值

    Returns
    -------
    dict
    hotspot_pixel_count:核心适宜区共有多少个hotspot像素
    hotspot_area_ratio:核心适宜区hotspot占比
    hotspot_count:核心适宜区共有多少个独立spot
    largest_hotspot_ratio:最大spot占全部核心区比例
    """
    hotspot_threshold = grading_system["thresholds"]["high_threshold"]
    valid = ~np.isnan(array)

    if np.sum(valid) == 0:
        return {
            "hotspot_pixel_count": 0,
            "hotspot_area_ratio": 0,
            "hotspot_count": 0,
            "largest_hotspot_ratio": 0,
        }

    hotspot_mask = (array >= hotspot_threshold) & valid

    hotspot_pixels = int(np.sum(hotspot_mask))

    if hotspot_pixels == 0:
        return {
            "hotspot_pixel_count": 0,
            "hotspot_area_ratio": 0,
            "hotspot_count": 0,
            "largest_hotspot_ratio": 0,
        }

    structure = np.ones((3, 3))

    labeled, hotspot_count = label(
        hotspot_mask,
        structure=structure,
    )

    hotspot_sizes = []

    for idx in range(1, hotspot_count + 1):
        hotspot_sizes.append(np.sum(labeled == idx))

    largest_hotspot = int(np.max(hotspot_sizes))

    return {
        "hotspot_pixel_count": hotspot_pixels,
        "hotspot_area_ratio": round(
            hotspot_pixels / np.sum(valid),
            4,
        ),
        "hotspot_count": int(hotspot_count),
        "largest_hotspot_pixels": largest_hotspot,
        "largest_hotspot_ratio": round(
            largest_hotspot / hotspot_pixels,
            4,
        ),
    }
