from typing import Literal
from tavily import TavilyClient
from models.climate_model import climate_analysis
from langchain.tools import tool
from graph.agri_graph import run_agri_analysis

tavily_client = TavilyClient()


@tool
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    "Run a web search"
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )


@tool
def agri_decision_tool(county: str, crop: str):
    "Run agricultural decision analysis"
    return run_agri_analysis(county, crop)


def extract_features(lat, lon):
    coords = [(lon, lat)]
    features = [
        normalize_numeric(raster.sample(coords).__next__()[0])
        for _, raster in FEATURE_RASTERS
    ]
    return np.array(features).reshape(1, -1)


def predict_location(lat, lon, model, imputer):
    X_raw = extract_features(lat, lon)
    X = imputer.transform(X_raw)

    prob = model.predict_proba(X)[0, 1]

    suitable = prob > 0.3  # 你可以用 threshold

    return prob, suitable, X_raw


@tool
def apple_agent(county_name):
    """
    苹果种植适宜性分析工具，输入县名称，输出该县的经纬度、适宜性评分、是否适宜种植苹果，以及影响适宜性的主要因素分析。
    """
    lat, lon = get_location(county_name)

    prob, suitable, X_raw = predict_location(lat, lon, model, imputer)

    reasons = explain(X_raw)

    return {
        "location": county_name,
        "lat": lat,
        "lon": lon,
        "suitability_score": float(prob),
        "suitable": bool(suitable),
        "reasons": reasons,
    }
