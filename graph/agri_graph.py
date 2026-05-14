from typing import TypedDict, Dict, Any

from langgraph.graph import StateGraph, END

# =========================
# 1. 引入 nodes（核心变化）
# =========================
from graph.nodes.climate_node import climate_node
from graph.nodes.soil_node import soil_node
from graph.nodes.score_node import score_node
from graph.nodes.decision_node import decision_node
from graph.nodes.risk_node import risk_node


# =========================
# 2. State 定义
# =========================
class AgriState(TypedDict, total=False):
    county: str
    crop: str

    climate: Dict[str, Any]
    soil: Dict[str, Any]
    risk: Dict[str, Any]

    score: float
    decision: str


# =========================
# 3. 构建 Graph（只做编排）
# =========================
def build_agri_graph():
    workflow = StateGraph(AgriState)

    # 注册 nodes（注意：这里只注册，不写逻辑）
    workflow.add_node("climate", climate_node)
    workflow.add_node("soil", soil_node)
    workflow.add_node("risk", risk_node)
    workflow.add_node("score", score_node)
    workflow.add_node("decision", decision_node)

    # 设置入口
    workflow.set_entry_point("climate")

    # 执行流（顺序执行版）
    workflow.add_edge("climate", "soil")
    workflow.add_edge("soil", "risk")
    workflow.add_edge("risk", "score")
    workflow.add_edge("score", "decision")
    workflow.add_edge("decision", END)

    return workflow.compile()


# =========================
# 4. 对外接口
# =========================
agri_graph = build_agri_graph()


def run_agri_analysis(county: str, crop: str):
    return agri_graph.invoke({"county": county, "crop": crop})


# =========================
# 5. 测试入口
# =========================
if __name__ == "__main__":
    result = run_agri_analysis("南江县", "rice")
    print("=== 农业决策结果 ===")
    print(result)
