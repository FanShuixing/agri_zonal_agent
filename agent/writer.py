from utils.load_prompt import read_prompt
from utils.config_loader import CONFIG

SUMMARY_PROMPT = read_prompt(CONFIG["prompts"]["summary_prompt"])
OVERALL_PROMPT = read_prompt(CONFIG["prompts"]["overall_analysis_prompt"])
SPATIAL_PROMPT = read_prompt(CONFIG["prompts"]["spatial_analysis_prompt"])
RISK_PROMPT = read_prompt(CONFIG["prompts"]["risk_analysis_prompt"])
STABILITY_PROMPT = read_prompt(CONFIG["prompts"]["stability_analysis_prompt"])
ADVICE_PROMPT = read_prompt(CONFIG["prompts"]["industry_advice_prompt"])
TOP_REGIONS_PROMPT = read_prompt(CONFIG["prompts"]["top_regions_analysis_prompt"])

# CONCLUSION_PROMPT = read_prompt(CONFIG["prompts"]["conclusion_prompt"])

SECTION_PROMPTS = {
    "summary": SUMMARY_PROMPT,
    "overall_analysis": OVERALL_PROMPT,
    "spatial_analysis": SPATIAL_PROMPT,
    "risk_analysis": RISK_PROMPT,
    "stability_analysis": STABILITY_PROMPT,
    "industry_advice": ADVICE_PROMPT,
    # "conclusion": CONCLUSION_PROMPT,
    "top_regions_analysis": TOP_REGIONS_PROMPT,
}

import json
from langchain_openai import ChatOpenAI
from utils.json_handler import save_json

# 初始化大语言模型（建议生成专家报告时，将 temperature 调低以确保公文严谨性，防止幻觉）
llm = ChatOpenAI(name="gpt-3.5-turbo", temperature=0.2)


def generate_section(section_name: str, section_inputs: dict) -> str:
    """
    负责调用单个 Prompt 节点，为其灌入独享的、裁剪后的上下文数据
    """
    # 1. 获取对应的解耦 Prompt
    prompt_template = SECTION_PROMPTS[section_name]

    # 2. 将特定输入参数转化为可读的 JSON 字符串或格式化字典
    # 注意：确保你的 Prompt 模板内部有类似于 {formatted_data} 的占位符
    print(section_name, section_inputs)
    formatted_data = json.dumps(section_inputs, ensure_ascii=False, indent=2)

    # 3. 渲染并组装 Prompt
    final_prompt = prompt_template.format(formatted_data)

    # 4. 驱动大模型生成高信息密度的纯文本
    response = llm.invoke(final_prompt)

    return response.content.strip()


def generate_report(global_context: dict) -> dict:
    """
    主控流程：负责从原始的全局 context 中精准抽离、组装不同章节所需的独特参数
    """
    # 🗺️ 核心设计：定义每一章的【专属输入参数路由表】
    # 这样可以防止 LLM 注意力被无关数据稀释，彻底阻断跨行业幻觉
    section_inputs_mapping = {
        "summary": {
            "province_summary": global_context.get("province_summary"),
            "spatial_structure": global_context.get("spatial_structure"),
            "ranking_structure": global_context.get("ranking_structure"),
            "advantage_regions": global_context.get("advantage_regions"),
            "risk_regions": global_context.get("risk_regions"),
            "model_threshold": global_context.get("model_threshold"),
        },
        "overall_analysis": {
            "province_summary": global_context.get("province_summary"),
            "advantage_regions": global_context.get("advantage_regions"),
            "risk_regions": global_context.get("risk_regions"),
            "model_threshold": global_context.get("model_threshold"),
        },
        "spatial_analysis": {
            "spatial_structure": global_context.get("spatial_structure"),
            "industrial_tags": global_context.get("industrial_tags"),
        },
        "top_regions_analysis": {
            "ranking_structure": global_context.get("ranking_structure"),
            "advantage_regions": global_context.get("advantage_regions"),
            "risk_regions": global_context.get("risk_regions"),
        },
        "risk_analysis": {
            "risk_regions": global_context.get("risk_regions"),
            "province_summary": global_context.get("province_summary"),
            "spatial_structure": global_context.get("spatial_structure"),
        },
        "stability_analysis": {
            "stability_structure": global_context.get("stability_structure"),
            "risk_regions": global_context.get("risk_regions"),
            # 从原始稳定性数据中提取核心定量数据，强行作为参数下发给 Prompt 强制绑定
            "average_fluctuation_ratio": global_context.get(
                "stability_structure", {}
            ).get("average_fluctuation_ratio", 1.0961),
        },
        # industry_advice 和 conclusion 依赖前面几章生成的深度文本作为推导依据
        "industry_advice": {},
        "conclusion": {},
    }

    report = {}

    # ────────────────────────────────────────────────────────
    # 阶段 1：并行或串行生成基础分析章节（依赖原始切片数据）
    # ────────────────────────────────────────────────────────
    base_sections = [
        "summary",
        "overall_analysis",
        "spatial_analysis",
        "top_regions_analysis",
        "risk_analysis",
        "stability_analysis",
    ]

    for section in base_sections:
        # 获取当前 Section 专属的裁剪后参数
        inputs_for_this_section = section_inputs_mapping[section]

        # 执行独立节点的文本生成
        report[section] = generate_section(section, inputs_for_this_section)

    # ────────────────────────────────────────────────────────
    # 阶段 2：前瞻建议与战略结论生成（依赖阶段 1 的文本作为综合输入）
    # ────────────────────────────────────────────────────────
    # 这样可以保证决策和前文的推导逻辑是绝对闭环、因果连贯的
    advanced_context = {
        "overall_analysis_result": report["overall_analysis"],
        "spatial_analysis_result": report["spatial_analysis"],
        "top_regions_analysis_result": report["top_regions_analysis"],
        "stability_analysis_result": report["stability_analysis"],
    }

    report["industry_advice"] = generate_section("industry_advice", advanced_context)
    # report["conclusion"] = generate_section("conclusion", advanced_context)

    # ────────────────────────────────────────────────────────
    # 阶段 3：直接返回拼装好的 Python 字典（即符合你需要的 JSON 结构的完整对象）
    # ────────────────────────────────────────────────────────
    return report


if __name__ == "__main__":
    from utils.json_handler import load_json

    context = load_json("./output/tmp/context.json")
    report = generate_report(context)
    print(report)
    # 保存报告到 JSON 文件
    save_json(report, "./output/tmp/report.json")
