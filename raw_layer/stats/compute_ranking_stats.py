import numpy as np


def compute_city_ranking_stats(
    city_stats,
    top_n=5,
):
    """
    市区适宜性排名统计

    Parameters
    ----------
    city_stats : list[dict]

        [
            {
                "region": "德州市",
                "mean_score": 0.2446,
                "max_score": 0.2903,
                "min_score": 0.1699
            }
        ]

    top_n : int

        返回前N名和后N名

    Returns
    -------
    {
        "best_region": ...,
        "worst_region": ...,
        "top_regions": [...],
        "bottom_regions": [...],
        "ranking_gap": ...
    }
    """

    valid_stats = [x for x in city_stats if x.get("mean_score") is not None]

    if not valid_stats:
        return {}

    ranked = sorted(
        valid_stats,
        key=lambda x: x["mean_score"],
        reverse=True,
    )

    top_regions = []
    for idx, item in enumerate(ranked[:top_n], start=1):
        top_regions.append(
            {
                "rank": idx,
                "region": item["region"],
                "mean_score": round(item["mean_score"], 4),
            }
        )

    bottom_regions = []
    bottom_ranked = ranked[-top_n:]

    for idx, item in enumerate(bottom_ranked, start=1):
        bottom_regions.append(
            {
                "rank": len(ranked) - len(bottom_ranked) + idx,
                "region": item["region"],
                "mean_score": round(item["mean_score"], 4),
            }
        )

    best_region = ranked[0]
    worst_region = ranked[-1]

    return {
        "best_region": {
            "region": best_region["region"],
            "mean_score": round(best_region["mean_score"], 4),
        },
        "worst_region": {
            "region": worst_region["region"],
            "mean_score": round(worst_region["mean_score"], 4),
        },
        "ranking_gap": round(
            best_region["mean_score"] - worst_region["mean_score"],
            4,
        ),
        "top_regions": top_regions,
        "bottom_regions": bottom_regions,
    }
