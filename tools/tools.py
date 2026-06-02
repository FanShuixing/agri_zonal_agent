from typing import Literal
from tavily import TavilyClient
from langchain.tools import tool

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


# @tool
# def agri_decision_tool(county: str, crop: str):
#     "Run agricultural decision analysis"
#     return run_agri_analysis(county, crop)


# def extract_features(lat, lon):
#     coords = [(lon, lat)]
#     features = [
#         normalize_numeric(raster.sample(coords).__next__()[0])
#         for _, raster in FEATURE_RASTERS
#     ]
#     return np.array(features).reshape(1, -1)
