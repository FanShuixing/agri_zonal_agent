from models.soil_model import soil_analysis


def soil_node(state):
    county = state["county"]
    crop = state["crop"]

    result = soil_analysis(county, crop)

    return {"soil": result}
