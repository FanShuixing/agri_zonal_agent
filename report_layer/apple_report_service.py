from datetime import datetime
from report_layer.renderer import render_report
from report_layer.static_map_service import plot_ranking_table, plot_score_range_chart, plot_suitability_map

def generate_data_report(
    context: dict,
    output_path: str | None = None,
    template: str | None = None,
) -> str:
    """
    纯数据驱动报告生成。
    context 直接喂给 Jinja2 模板，不走 LLM。

    template 可选:
      - None: 使用 config.yaml 中的 html_template 设置
      - "standard": report.html（默认详细报告）
      - "dashboard": report_dashboard.html（仪表盘风格）
      - 或直接传模板文件名，如 "report.html"

    context 格式：build_context() 的输出（context.json）
    """
    data = context.copy()

    # 补充分辨率无关但模板需要的字段
    data.setdefault("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    data.setdefault("images", data.get("artifacts", {}))

    # LLM 叙事字段（可选，目前为空，后续可 merge 进来）
    data.setdefault("llm_summary", "")
    data.setdefault("llm_spatial", "")
    data.setdefault("llm_ranking", "")
    data.setdefault("llm_risk", "")

    html = render_report(report_data=data, template_name=template)

    if output_path is None:
        from utils.config_loader import CONFIG
        output_path = CONFIG["paths"]["output"]["final_stage_html"]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML report saved: {output_path}")
    return html

def build_region_analysis_report(
    region_name: str, region_gdf, city_stats: list
) -> dict:
    suitability_map_path = plot_suitability_map(region_gdf, city_stats)
    ranking_table_path = plot_ranking_table(city_stats)
    score_range_chart_path = plot_score_range_chart(city_stats)

    return {
        "region_name": region_name,
        "suitability_map_path": suitability_map_path,
        "ranking_table_path": ranking_table_path,
        "score_range_chart_path": score_range_chart_path,
    }