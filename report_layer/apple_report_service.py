from report_layer.renderer import render_report
from utils.config_loader import CONFIG
from report_layer.static_map_service import (
    plot_ranking_table,
    plot_score_range_chart,
    plot_suitability_map,
)

import markdown


def generate_html_report(report_json):
    """
    生成HTML报告（带 Markdown 自动化解析，彻底修复排版糊在一起的 Bug）
    """
    # 1. 深度拷贝一份数据，避免污染原始的 report_json 字典
    formatted_json = report_json.copy()

    # 2. 遍历大模型生成的各个章节，将 Markdown 纯文本升级为 HTML 标签文本
    for section_name, text in formatted_json.items():
        if isinstance(text, str):
            # 【防御性清洗】：强制把大模型可能漏掉的换行补齐，确保必定换行
            cleaned_text = text.replace(" **", "\n\n**").replace("  **", "\n\n**")

            # 【核心转换】：通过 markdown 库将 ** 转化为 <strong>，将 \n 转化为 <br>
            # 必须启用 'nl2br'（换行转br）和 'extra' 插件
            html_snippet = markdown.markdown(
                cleaned_text, extensions=["nl2br", "extra"]
            )

            # 将处理后的 HTML 片段存回字典
            formatted_json[section_name] = html_snippet

    # 3. 此时再将带有 <strong> 和 <br> 标签的完美数据喂给模板渲染
    html_content = render_report(report_data=formatted_json)

    # 4. 标准文件写入
    final_stage_html = CONFIG["paths"]["output"]["final_stage_html"]
    with open(final_stage_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        print(f"HTML报告已生成并成功排版: {final_stage_html}")


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
