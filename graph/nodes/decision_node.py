def decision_node(state):
    score = state["score"]

    if score >= 80:
        decision = "RECOMMENDED"
    elif score >= 65:
        decision = "CONDITIONAL"
    else:
        decision = "NOT_RECOMMENDED"

    return {"decision": decision, "explanation": f"final score = {score}"}
