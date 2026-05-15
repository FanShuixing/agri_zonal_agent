import os
from deepagents import create_deep_agent
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from utils.load_prompt import read_prompt
from tools.apple_tool import (
    apple_point_analysis_tool,
    apple_map_report_tool,
    apple_region_ranking_tool,
)
from service.report.build_context import build_report_context

from utils.config_loader import CONFIG
import json
from utils.write_json import save_json


# create a deep agent
def create_agri_agent():
    model = ChatOpenAI(name="gpt-3.5-turbo")
    research_prompt = read_prompt(CONFIG["prompts"]["data_layer"])
    agent = create_agent(
        model=model,
        tools=[
            apple_point_analysis_tool,
            apple_map_report_tool,
            apple_region_ranking_tool,
        ],
        system_prompt=research_prompt,
    )

    return agent


def create_report_agent():
    model = ChatOpenAI(name="gpt-3.5-turbo")
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
        # =========================
        # ✅ 1️⃣ 明显适合（核心产区）
        # =========================
        "陕西洛川县适合种苹果吗？",
        "山东栖霞市适合种苹果吗？",
        "甘肃静宁县适合种苹果吗？",
        "山西万荣县适合种苹果吗？",
        # =========================
    ]
    test_cases2 = [
        "输出山东省的苹果种植适宜性地图，并告诉我哪些市区比较适合种植苹果,生成报告。"
    ]
    for case in test_cases2[:1]:
        # 第一阶段，将输出内容写入json文件
        # result = agent.invoke({"messages": [{"role": "user", "content": case}]})
        # msg = result["messages"][-1].content

        # with open(
        #     CONFIG["paths"]["output"]["first_stage_json"], "w+", encoding="utf-8"
        # ) as f:
        #     f.write(f"{msg}\n\n")
        # print(f"第一阶段结果已保存: {CONFIG['paths']['output']['first_stage_json']}")

        # context阶段,基于第一阶段的内容生成context，作为第二阶段的输入
        # context_json = build_report_context(
        #     "./output/tmp/data_layer_1.json", "./output/tmp/data_layer_2.json"
        # )
        # context_json_path = save_json(context_json, "./output/tmp/context.json")

        # # 进入第二阶段，用于生成报告的agent
        report_agent = create_report_agent()
        with open("./output/tmp/context.json", "r", encoding="utf-8") as f:
            content = f.read()
        report_result = report_agent.invoke(
            {"messages": [{"role": "user", "content": content}]}
        )
        with open(
            CONFIG["paths"]["output"]["second_stage_json"], "w+", encoding="utf-8"
        ) as f:
            f.write(report_result["messages"][-1].content)
        print(f"第二阶段结果已保存: {CONFIG['paths']['output']['second_stage_json']}")

        # # 生成最终报告
        # with open(CONFIG["second_stage_json"], "r", encoding="utf-8") as f:
        #     report_data = json.loads(f.read())
        #     generate_html_report(report_data)
        #     print(f"最终报告已生成: {CONFIG['final_stage_html']}")
        # print(f"测试用例: {case}\n结果已保存并生成报告。\n{'='*50}\n")
