from service.report.renderer import render_report
from utils.config_loader import CONFIG

from service.static_map_service import (
    plot_ranking_table,
    plot_score_range_chart,
    plot_suitability_map,
)
from service.report.semantic_service import build_semantic_insights


# 生成html报告
def generate_html_report(report_json):
    """
    生成HTML报告
    """
    html_content = render_report(report_data=report_json)
    with open(CONFIG["final_stage_html"], "w", encoding="utf-8") as f:
        f.write(html_content)
        print(f"HTML报告已生成: {CONFIG['final_stage_html']}")


def build_region_analysis_report(
    region_name: str, region_gdf, city_stats: list
) -> dict:
    suitability_map_path = plot_suitability_map(region_gdf, city_stats)
    ranking_table_path = plot_ranking_table(city_stats)
    score_range_chart_path = plot_score_range_chart(city_stats)
    insights = build_semantic_insights(city_stats)

    return {
        "region_name": region_name,
        "city_stats": city_stats,
        "suitability_map_path": suitability_map_path,
        "ranking_table_path": ranking_table_path,
        "score_range_chart_path": score_range_chart_path,
        "semantic_insights": insights,
    }
