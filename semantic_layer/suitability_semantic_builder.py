def _get_grade_ratio(grade_ratios, grade_name):
    for item in grade_ratios:
        if item.get("grade_name") == grade_name:
            return item.get("area_ratio", 0)
    return 0


def build_distribution_semantic(distribution_stats: dict) -> dict:
    mean_score = distribution_stats.get("mean_score", 0)
    std_score = distribution_stats.get("std_score", 0)
    p75_score = distribution_stats.get("p75_score", 0)
    p90_score = distribution_stats.get("p90_score", 0)
    p95_score = distribution_stats.get("p95_score", 0)

    if std_score >= 0.12:
        dispersion_level = "离散度高"
        distribution_pattern = "区域内部适宜性差异明显"
    elif std_score >= 0.06:
        dispersion_level = "离散度中等"
        distribution_pattern = "区域内部存在一定适宜性分化"
    else:
        dispersion_level = "离散度低"
        distribution_pattern = "区域内部适宜性分布相对集中"

    if p90_score - mean_score >= 0.15:
        high_value_tail = "高值尾部明显"
    elif p75_score - mean_score >= 0.08:
        high_value_tail = "存在局部高值区"
    else:
        high_value_tail = "高值突破不明显"

    return {
        "dispersion_level": dispersion_level,
        "distribution_pattern": distribution_pattern,
        "high_value_tail": high_value_tail,
        "key_percentiles": {
            "p75_score": p75_score,
            "p90_score": p90_score,
            "p95_score": p95_score,
        },
    }


def build_hotspot_semantic(hotspot_stats: dict) -> dict:
    hotspot_area_ratio = hotspot_stats.get("hotspot_area_ratio", 0)
    hotspot_count = hotspot_stats.get("hotspot_count", 0)
    largest_hotspot_ratio = hotspot_stats.get("largest_hotspot_ratio", 0)

    if hotspot_area_ratio >= 0.3:
        hotspot_scale = "热点面积占比较高"
    elif hotspot_area_ratio >= 0.1:
        hotspot_scale = "存在一定热点区域"
    else:
        hotspot_scale = "热点区域有限"

    if hotspot_count == 0:
        hotspot_pattern = "未形成明显热点"
    elif largest_hotspot_ratio >= 0.5:
        hotspot_pattern = "热点集中于主要核心区"
    elif hotspot_count >= 5:
        hotspot_pattern = "热点呈多点分布"
    else:
        hotspot_pattern = "热点呈局部分布"

    return {
        "hotspot_scale": hotspot_scale,
        "hotspot_pattern": hotspot_pattern,
        "hotspot_count": hotspot_count,
        "largest_hotspot_ratio": largest_hotspot_ratio,
    }


def build_patch_semantic(patch_stats: dict) -> dict:
    patch_count = patch_stats.get("patch_count", 0)
    total_core_pixels = patch_stats.get("total_core_pixels", 0)
    largest_patch_ratio = patch_stats.get("largest_patch_ratio", 0)
    mean_patch_pixels = patch_stats.get("mean_patch_pixels", 0)

    if patch_count == 0:
        connectivity_level = "无核心连续区"
        fragmentation_level = "无法判断"
    elif largest_patch_ratio >= 0.5:
        connectivity_level = "核心区连续性较强"
        fragmentation_level = "破碎化较低"
    elif patch_count >= 10 and largest_patch_ratio < 0.3:
        connectivity_level = "核心区连续性较弱"
        fragmentation_level = "破碎化明显"
    else:
        connectivity_level = "核心区存在局部连续"
        fragmentation_level = "存在一定破碎化"

    return {
        "connectivity_level": connectivity_level,
        "fragmentation_level": fragmentation_level,
        "patch_count": patch_count,
        "total_core_pixels": total_core_pixels,
        "largest_patch_ratio": largest_patch_ratio,
        "mean_patch_pixels": mean_patch_pixels,
    }


def build_grade_semantic(grade_stats: dict) -> dict:
    grade_ratios = grade_stats.get("grade_ratios", [])
    dominant_grade = grade_stats.get("dominant_grade")
    dominant_ratio = grade_stats.get("dominant_ratio", 0)

    core_ratio = _get_grade_ratio(grade_ratios, "核心优势区")
    suitable_ratio = core_ratio + _get_grade_ratio(grade_ratios, "较适宜区")
    unsuitable_ratio = _get_grade_ratio(grade_ratios, "不适宜区")

    if core_ratio >= 0.3:
        grade_structure = "核心优势区占比较高"
    elif suitable_ratio >= 0.4:
        grade_structure = "适宜等级结构较好"
    elif unsuitable_ratio >= 0.3:
        grade_structure = "不适宜区占比较高"
    else:
        grade_structure = "以一般适宜区为主"

    return {
        "dominant_grade": dominant_grade,
        "dominant_ratio": dominant_ratio,
        "core_ratio": round(core_ratio, 4),
        "suitable_ratio": round(suitable_ratio, 4),
        "unsuitable_ratio": round(unsuitable_ratio, 4),
        "grade_structure": grade_structure,
    }


def build_city_grade_semantic(city_grade_stats: list) -> dict:
    city_semantics = []

    for item in city_grade_stats:
        grade_semantic = build_grade_semantic(item)

        city_semantics.append(
            {
                "region": item.get("region"),
                **grade_semantic,
            }
        )

    # 核心优势城市
    core_dominant_regions = [
        item["region"]
        for item in city_semantics
        if item["dominant_grade"] == "核心优势区"
    ]

    # 核心占比最高城市
    high_core_regions = sorted(
        [
            {
                "region": item["region"],
                "core_ratio": item["core_ratio"],
            }
            for item in city_semantics
        ],
        key=lambda x: x["core_ratio"],
        reverse=True,
    )[:5]

    # 风险城市
    risk_regions = [
        item["region"]
        for item in city_semantics
        if item["grade_structure"] == "不适宜区占比较高"
    ]

    # 城市结构统计
    structure_summary = {
        "core_dominant_count": len(core_dominant_regions),
        "risk_region_count": len(risk_regions),
        "general_dominant_count": len(city_semantics) - len(core_dominant_regions),
    }

    return {
        "core_dominant_regions": core_dominant_regions,
        "high_core_regions": high_core_regions,
        "risk_regions": risk_regions,
        "structure_summary": structure_summary,
    }
