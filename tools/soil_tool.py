from models.soil_model import soil_analysis
from langchain.tools import tool


@tool
def soil_analysis_tool(county, crop):
    """
    土壤分析工具，输入县和作物，输出土壤适宜性分析结果，包括土壤类型、pH值、有机质含量、海拔和坡度等。
    """
    return soil_analysis(county, crop)
