from raw_layer.granding.suitability_grading import build_grading_system
from raw_layer.stats.zonal_stats import compute_suitability_stats
from raw_layer.stats.distribution_stats import compute_distribution_stats
from raw_layer.stats.hostspot_stats import compute_hotspot_stats
from raw_layer.stats.connected_patch_stats import compute_connected_patch_stats
from raw_layer.stats.grade_ratio_stats import (
    compute_grade_ratios,
    compute_city_grade_ratios,
)
from raw_layer.stats.compute_ranking_stats import compute_city_ranking_stats


def compute_region_suitability_analysis(array, city_stats):
    grading_system = build_grading_system(city_stats)

    overall_stats = compute_suitability_stats(array, grading_system)
    distribution_stats = compute_distribution_stats(array)
    hotspot_stats = compute_hotspot_stats(array, grading_system)
    connected_patch_stats = compute_connected_patch_stats(array, grading_system)
    grade_ratios = compute_grade_ratios(array, grading_system)
    city_grade_ratios = compute_city_grade_ratios(city_stats, grading_system)
    ranking_stats = compute_city_ranking_stats(city_stats, top_n=5)

    return {
        "overall_stats": overall_stats,
        "distribution_stats": distribution_stats,
        "hotspot_stats": hotspot_stats,
        "connected_patch_stats": connected_patch_stats,
        "grade_ratios": grade_ratios,
        "city_grade_ratios": city_grade_ratios,
        "ranking_stats": ranking_stats,
    }
