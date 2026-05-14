def risk_node(state):
    climate = state["climate"]
    soil = state["soil"]

    risk = {
        "drought_risk": climate["risk"],
        "soil_stability": "medium" if soil["soil_score"] > 70 else "low",
    }

    return {"risk": risk}
