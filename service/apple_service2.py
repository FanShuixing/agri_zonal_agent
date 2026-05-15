from service.geocode_service import get_location
from apple.predictor import predict_location
from apple.explainer import explain_prediction, plot_radar, plot_map
from apple.predictor import predict_province_map
from service.map_service import generate_region_map, analyze_region_suitability
from service.zonal_stats_service import compute_region_zonal_stats
from apple.feature_config import DEFAULT_TIF, CLIP_SHP
import geopandas as gpd
from service.static_map_service import (
    plot_ranking_table,
    plot_score_range_chart,
    plot_suitability_map,
)
from service.sematic_service import build_semantic_insights
from service.renderer import render_report
from utils.config_loader import CONFIG
from service.spatial_analysis_service import compute_suitability_stats
from service.raster_service import clip_raster_by_region


def analyze_apple_suitability(county_name: str):
    lat, lon = get_location(county_name)
    prob, suitable, X_raw = predict_location(lat, lon)
    # print(f"/n预测结果 - 适宜性得分: {prob:.4f}, 是否适宜: {suitable}/n")

    reasons = explain_prediction(X_raw)
    # 画雷达图
    plot_radar(X_raw)
    # 画地图
    plot_map(lat, lon)

    return {
        "location": county_name,
        "lat": lat,
        "lon": lon,
        "suitability_score": float(prob),
        "suitable": suitable,
        "reasons": reasons,
    }


def analyze_predict_province_map(province_name: str):
    # 这里可以调用 predict_province_map 函数，生成省级适宜性地图
    res = predict_province_map(
        province_name=province_name,
        resolution=200,
        save_path="output/province_map.png",
    )
    return res


def analyze_predict_region_map(region_name: str, save_path: str):
    """
    生成区域的苹果种植适宜性地图
    """
    res = generate_region_map(
        region_name=region_name,
        # tif_path="output/china_suitability.tif",
        output_path=save_path,
    )
    return res


# 获取省级别的适宜性统计数据
def analyze_province_suitability(province_name: str):
    stats = analyze_region_suitability(province_name)
    return stats


def normalize_mode(region_name: str) -> str:
    if region_name in ["中国", "全国"]:
        return "province"

    if region_name.endswith("省"):
        return "city"

    if region_name.endswith("市"):
        return "county"

    return "county"  # fallback


def spatial_analysis(region_name: str):
    mode = normalize_mode(region_name)
    print(f"🔍 生成 {region_name} 的苹果种植适宜性地图，模式: {mode}")
    return analyze_predict_region_map(region_name, mode)


import geopandas as gpd


def compute_region_zonal_stats_by_geometry(
    region_name: str,
    raster_path=DEFAULT_TIF,
    region_name_field="name",
):
    """
    对每个行政区计算适宜性统计
    """

    # 读取省级行政区划数据
    province_gdf = gpd.read_file(CLIP_SHP["province"])

    target_province = province_gdf[province_gdf["name"] == region_name]

    province_gb = str(target_province.iloc[0]["gb"])[-6:]  # 获取省级GB代码的后6位
    province_prefix = province_gb[:2]

    DEFAULT_SHAPEFILE = CLIP_SHP["city"]

    city_gdf = gpd.read_file(DEFAULT_SHAPEFILE, encoding="utf-8")
    city_gdf["gb"] = city_gdf["gb"].astype(str).str[-6:]  # 保留后6位GB代码
    province_city_gdf = city_gdf[city_gdf["gb"].str.startswith(province_prefix)]

    print(
        f"省份 {region_name} 包含的市区数量: {len(province_city_gdf)}, 市区列表: {province_city_gdf['name'].tolist()}"
    )

    city_stats = compute_region_zonal_stats(
        raster_path, province_city_gdf, region_name_field
    )
    stats = sorted(city_stats, key=lambda x: x["mean_score"], reverse=True)[
        :10
    ]  # 取前10个适宜性最高的市区

    # 生成可视化报告
    suitability_map_path = plot_suitability_map(province_city_gdf, city_stats)
    ranking_table_path = plot_ranking_table(city_stats)
    score_range_chart_path = plot_score_range_chart(city_stats)

    # 生成语义洞察
    insights = build_semantic_insights(city_stats)

    return {
        "region_name": region_name,
        "city_stats": stats,
        "suitability_map_path": suitability_map_path,
        "ranking_table_path": ranking_table_path,
        "score_range_chart_path": score_range_chart_path,
        "semantic_insights": insights,
    }


# 生成html报告
def generate_html_report(report_json):
    """
    生成HTML报告
    """
    html_content = render_report(report_data=report_json)
    with open(CONFIG["final_stage_html"], "w", encoding="utf-8") as f:
        f.write(html_content)
        print(f"HTML报告已生成: {CONFIG['final_stage_html']}")


if __name__ == "__main__":

    # 测试省级地图生成
    province_map_res = compute_region_zonal_stats_by_geometry("山东省")
    print(province_map_res)
