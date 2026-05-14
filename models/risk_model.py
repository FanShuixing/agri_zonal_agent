def compute_risk(climate: dict, soil: dict, crop: dict):
    """
    跨模态风险模型（唯一允许融合 climate + soil）
    """

    risk = {"drought_risk": "low", "flood_risk": "low", "soil_risk": "low"}

    # 气候风险
    if climate["risk"] == "high":
        risk["drought_risk"] = "high"

    # 土壤风险
    if soil["soil_score"] < 60:
        risk["soil_risk"] = "medium"

    if soil["soil_score"] < 50:
        risk["soil_risk"] = "high"

    # 简单融合逻辑（后面可以升级 ML）
    if risk["drought_risk"] == "high" and risk["soil_risk"] == "high":
        overall = "high"
    elif "high" in risk.values():
        overall = "medium"
    else:
        overall = "low"

    return {"risk_level": overall, "details": risk}
