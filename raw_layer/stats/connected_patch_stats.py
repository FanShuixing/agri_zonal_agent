import numpy as np
from scipy.ndimage import label


def compute_connected_patch_stats(
    array,
    grading_system,
):
    """
    连续适宜区统计

    Parameters
    ----------
    array : np.ndarray
        suitability raster

    threshold : float
        核心适宜区阈值

    Returns
    -------
    dict
    patch_count:核心适宜区共有多少个独立斑块
    total_core_pixels:核心适宜区总面积
    largest_patch_pixels:最大连续适宜区面积
    largest_patch_ratio:最大斑块占全部核心区比例
    mean_patch_pixels:平均斑块面积
    """

    valid = ~np.isnan(array)

    if np.sum(valid) == 0:
        return {
            "patch_count": 0,
            "largest_patch_pixels": 0,
            "largest_patch_ratio": 0,
            "mean_patch_pixels": 0,
        }

    # 核心适宜区
    threshold = grading_system["thresholds"]["high_threshold"]
    core_mask = (array >= threshold) & valid

    if np.sum(core_mask) == 0:
        return {
            "patch_count": 0,
            "largest_patch_pixels": 0,
            "largest_patch_ratio": 0,
            "mean_patch_pixels": 0,
        }

    # 8邻域连通
    structure = np.ones((3, 3))

    labeled, num_patches = label(core_mask, structure=structure)

    patch_sizes = []

    for patch_id in range(1, num_patches + 1):
        size = np.sum(labeled == patch_id)
        patch_sizes.append(size)

    patch_sizes = np.array(patch_sizes)

    largest_patch = int(np.max(patch_sizes))

    total_core_pixels = int(np.sum(core_mask))

    return {
        "patch_count": int(num_patches),
        "total_core_pixels": total_core_pixels,
        "largest_patch_pixels": largest_patch,
        "largest_patch_ratio": round(
            largest_patch / total_core_pixels,
            4,
        ),
        "mean_patch_pixels": round(
            float(np.mean(patch_sizes)),
            2,
        ),
    }
