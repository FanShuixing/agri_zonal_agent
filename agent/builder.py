from dotenv import load_dotenv
load_dotenv()

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from utils.load_prompt import read_prompt
from agent.planner import run_full_report_pipeline
from tools.apple_tool import (
    apple_region_ranking_tool,
)
from utils.config_loader import CONFIG


# create a deep agent
def create_agri_agent():
    model = ChatOpenAI(name="gpt-4o-mini")
    research_prompt = read_prompt(CONFIG["prompts"]["data_layer"])
    agent = create_agent(
        model=model,
        tools=[
            apple_region_ranking_tool,
        ],
        system_prompt=research_prompt,
    )

    return agent


def create_report_agent():
    model = ChatOpenAI(name="gpt-4o-mini")
    planner_prompt = read_prompt(CONFIG["prompts"]["analysis_layer"])
    agent = create_agent(
        model=model,
        tools=[],
        system_prompt=planner_prompt,
    )

    return agent


if __name__ == "__main__":
    agent = create_agri_agent()
    test_cases = [
        "输出山东省的苹果种植适宜性地图，并告诉我哪些市区比较适合种植苹果,生成报告。"
    ]

    for case in test_cases[:1]:
        run_full_report_pipeline(agent=agent, user_query=case)
        print(f"测试用例: {case}\n结果已保存并生成报告。\n{'='*50}\n")
