def compute_suitability(climate: dict, soil: dict, risk: dict):
    """
    最终适宜性模型（统一输出层）
    """

    climate_score = climate["climate_score"]
    soil_score = soil["soil_score"]

    # 风险惩罚
    penalty = {"low": 0, "medium": 10, "high": 25}

    base = climate_score * 0.6 + soil_score * 0.4

    final = base - penalty[risk["risk_level"]]

    return {
        "suitability_score": round(max(0, min(100, final)), 1),
        "grade": (
            "RECOMMENDED"
            if final >= 80
            else "CONDITIONAL" if final >= 65 else "NOT_RECOMMENDED"
        ),
    }
