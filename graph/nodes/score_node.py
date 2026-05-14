def score_node(state):
    climate_score = state["climate"]["climate_score"]
    soil_score = state["soil"]["soil_score"]
    print("*" * 20, state)
    risk = state["risk"]

    risk_penalty = 0
    if risk.get("drought_risk") == "high":
        risk_penalty += 15

    if risk.get("soil_stability") == "low":
        risk_penalty += 10

    score = 0.6 * climate_score + 0.4 * soil_score - risk_penalty

    return {"score": round(max(0, min(100, score)), 1)}
