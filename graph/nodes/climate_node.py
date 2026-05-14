from models.climate_model import climate_analysis


def climate_node(state):
    county = state["county"]
    crop = state["crop"]

    result = climate_analysis(county, crop)

    return {"climate": result}
