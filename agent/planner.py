from pathlib import Path

from agent.writer import generate_report
from report_layer.apple_report_service import generate_html_report
from context_layer.build_context import build_report_context
from semantic_layer.semantic_layer import build_semantic_layer
from utils.config_loader import CONFIG
from utils.json_handler import load_json, merge_json, save_json

RAW_LAYER_1_PATH = "output/tmp/data_layer_1.json"
RAW_LAYER_2_PATH = "output/tmp/data_layer_2.json"
REGION_GDF_PATH = "output/tmp/apple_region_gdf.geojson"
SEMANTIC_SAVE_PATH = CONFIG["paths"]["output"]["semantic_layer"]
CONTEXT_JSON_PATH = "output/tmp/context.json"
REPORT_JSON_PATH = "output/tmp/report.json"


def run_raw_data_stage(
    agent, user_query: str, save_path: str | Path | None = None
) -> Path:
    """运行工具层并保存第一阶段原始输出。"""
    result = agent.invoke({"messages": [{"role": "user", "content": user_query}]})
    message = result["messages"][-1].content
    output_path = Path(save_path or CONFIG["paths"]["output"]["first_stage_json"])

    return output_path


def run_semantic_stage(
    raw_result_json: str | Path = RAW_LAYER_2_PATH,
    region_gdf_path: str | Path = REGION_GDF_PATH,
):
    """根据 raw layer 数据构建 semantic layer。"""
    semantic_data = build_semantic_layer(
        raw_result_json=raw_result_json,
        region_gdf_path=region_gdf_path,
    )
    print(f"语义层结果已生成: {SEMANTIC_SAVE_PATH}")
    return semantic_data


def run_context_stage(
    semantic_json_path: str | Path = SEMANTIC_SAVE_PATH,
    save_path: str | Path = CONTEXT_JSON_PATH,
):
    """根据 semantic layer 构建 LLM context。"""
    context_json = build_report_context(semantic_json_path)
    saved_path = save_json(context_json, str(save_path))
    print(f"Context 已生成: {saved_path}")
    return context_json, saved_path


def run_report_stage(
    context_json_path: str | Path = CONTEXT_JSON_PATH,
    save_path: str | Path = REPORT_JSON_PATH,
):
    """根据 context 生成分章节报告 JSON。"""
    context = load_json(context_json_path)
    report_json = generate_report(context)
    saved_path = save_json(report_json, str(save_path))
    print(f"报告 JSON 已生成: {saved_path}")
    return report_json, saved_path


def run_render_stage(
    report_json_path: str | Path = REPORT_JSON_PATH,
    context_json_path: str | Path = CONTEXT_JSON_PATH,
):
    """合并上下文与报告数据，并渲染最终 HTML。"""
    report_data = merge_json(report_json_path, context_json_path)
    generate_html_report(report_data)
    final_html_path = CONFIG["paths"]["output"]["final_stage_html"]
    print(f"最终报告已生成: {final_html_path}")
    return report_data, final_html_path


def run_full_report_pipeline(
    agent,
    user_query: str,
    overall_json_path: str | Path = RAW_LAYER_1_PATH,
    region_json_path: str | Path = RAW_LAYER_2_PATH,
    region_gdf_path: str | Path = REGION_GDF_PATH,
    semantic_json_path: str | Path = SEMANTIC_SAVE_PATH,
    context_json_path: str | Path = CONTEXT_JSON_PATH,
    report_json_path: str | Path = REPORT_JSON_PATH,
):
    """串联执行完整的报告生成流程。"""
    # run_raw_data_stage(agent, user_query)
    # semantic_data = run_semantic_stage(
    #     raw_result_json=region_json_path,
    #     region_gdf_path=region_gdf_path,
    # )
    context_json, _ = run_context_stage(
        semantic_json_path=semantic_json_path,
        save_path=context_json_path,
    )
    # report_json, _ = run_report_stage(
    #     context_json_path=context_json_path,
    #     save_path=report_json_path,
    # )
    # report_data, final_html_path = run_render_stage(
    #     report_json_path=report_json_path,
    #     context_json_path=context_json_path,
    # )

    # return {
    #     "semantic_data": semantic_data,
    #     "context_json": context_json,
    #     "report_json": report_json,
    #     "report_data": report_data,
    #     "final_html_path": final_html_path,
    # }
