import numpy as np


def compute_grade_ratios(array, grading_system):
    """
    suitability分级面积统计,输入一个数值数组和一个分级系统，输出每个分级的面积占比和主导分级。
    """

    valid = array[~np.isnan(array)]

    total = len(valid)

    grade_results = []

    dominant_grade = None
    dominant_ratio = 0

    for grade in grading_system["grades"]:

        mask = (valid >= grade["min"]) & (valid < grade["max"])

        count = np.sum(mask)

        ratio = float(count / total)

        result = {
            "grade_name": grade["name"],
            "pixel_count": int(count),
            "area_ratio": round(ratio, 4),
        }

        grade_results.append(result)

        if ratio > dominant_ratio:
            dominant_ratio = ratio
            dominant_grade = grade["name"]

    return {
        "grade_ratios": grade_results,
        "dominant_grade": dominant_grade,
        "dominant_ratio": round(dominant_ratio, 4),
    }


def compute_city_grade_ratios(
    city_stats,
    grading_system,
):
    results = []

    for city in city_stats:

        if "city_array" not in city:
            continue

        grade_stats = compute_grade_ratios(
            city["city_array"],
            grading_system,
        )

        results.append(
            {
                "region": city["region"],
                **grade_stats,
            }
        )

    return results
