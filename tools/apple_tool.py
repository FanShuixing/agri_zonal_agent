from langchain.tools import tool
from service.apple_service import (
    analyze_apple_suitability,
    analyze_predict_province_map,
    analyze_predict_region_map,
    normalize_mode,
    compute_region_zonal_stats_by_geometry,
    generate_html_report,
)
from typing import Literal


@tool
def apple_suitability_tool(region_name: str):
    """输入县名/基地/园区，返回苹果种植适宜性分析。"""
    return analyze_apple_suitability(region_name)


@tool
def apple_map_tool(region_name: str):
    """输入省，返回苹果种植适宜性地图。
    level 可以是 province  / county，默认是 province。
    region_name 可以是省、县的名称，比如中国、四川省、洛川县等。

    输出结果包含：
    - 适宜性地图的路径，包含四川省适宜性分布热力图
    - 适宜性统计数据
    """
    mode = normalize_mode(region_name)
    print(f"🔍 生成 {region_name} 的苹果种植适宜性地图，模式: {mode}")
    res = analyze_predict_region_map(region_name, mode)
    print(f"生成 {region_name} 的苹果种植适宜性地图完成，结果: {res}")
    return res


@tool
def city_suitability_analysis_tool(region_name: str):
    """
    当用户询问：
    - 哪些市区适合种植苹果
    - 哪些行政区更适合
    - 各地区适宜性排名
    - 市县级适宜性分析
    - 区域适宜性对比

    时，必须调用该工具。

    该工具会计算每个行政区的：
    - 平均适宜性
    - 最大适宜性
    - 最小适宜性

    用于分析不同地区的苹果种植适宜性差异。
    """
    stats = compute_region_zonal_stats_by_geometry(region_name)

    # print(f"stats: {stats}")
    return stats
