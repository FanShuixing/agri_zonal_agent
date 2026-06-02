import numpy as np
from raw_layer.granding.spatial_grading import build_spatial_grading_system


def build_spatial_semantic_layer(
    province_city_gdf,
    city_stats,
):
    """
    构建空间语义层（V2）

    功能：
    - 高值区识别
    - 低值区识别
    - 北高南低 / 东高西低分析
    - 空间连续性分析
    - 空间集聚分析
    - 核心优势区识别

    Parameters
    ----------
    province_city_gdf : GeoDataFrame
        市级行政区 geometry

    city_stats : list[dict]
        每个市的适宜性统计

    Returns
    -------
    dict
    """
    spatial_grading = build_spatial_grading_system(city_stats)

    thresholds = spatial_grading["thresholds"]

    hotspot_threshold = thresholds["hotspot_threshold"]

    coldspot_threshold = thresholds["coldspot_threshold"]
    # ---------------------------------------------------
    # 1️⃣ 合并统计数据
    # ---------------------------------------------------

    stats_map = {x["region"]: x for x in city_stats}

    gdf = province_city_gdf.copy()

    gdf["mean_score"] = gdf["name"].map(
        lambda x: stats_map.get(x, {}).get("mean_score", np.nan)
    )

    gdf = gdf.dropna(subset=["mean_score"])

    # ---------------------------------------------------
    # 2️⃣ 计算中心点
    # ---------------------------------------------------

    gdf["centroid"] = gdf.geometry.centroid
    gdf["cx"] = gdf.centroid.x
    gdf["cy"] = gdf.centroid.y

    # ---------------------------------------------------
    # 3️⃣ 高低值区识别
    # ---------------------------------------------------

    high_gdf = gdf[gdf["mean_score"] >= hotspot_threshold]
    low_gdf = gdf[gdf["mean_score"] <= coldspot_threshold]

    high_regions = high_gdf["name"].tolist()
    low_regions = low_gdf["name"].tolist()

    # ---------------------------------------------------
    # 4️⃣ 南北梯度分析
    # ---------------------------------------------------

    corr_ns = gdf["cy"].corr(gdf["mean_score"])

    if corr_ns > 0.3:
        gradient_direction = "北高南低"
    elif corr_ns < -0.3:
        gradient_direction = "南高北低"
    else:
        gradient_direction = "南北差异不显著"

    # ---------------------------------------------------
    # 5️⃣ 东西梯度分析
    # ---------------------------------------------------

    corr_ew = gdf["cx"].corr(gdf["mean_score"])

    if corr_ew > 0.3:
        ew_pattern = "东高西低"
    elif corr_ew < -0.3:
        ew_pattern = "西高东低"
    else:
        ew_pattern = "东西差异不显著"

    # ---------------------------------------------------
    # 6️⃣ 高值区空间连续性分析
    # ---------------------------------------------------

    adjacency_pairs = []

    high_indices = high_gdf.index.tolist()

    for i in range(len(high_indices)):
        for j in range(i + 1, len(high_indices)):

            idx1 = high_indices[i]
            idx2 = high_indices[j]

            geom1 = high_gdf.loc[idx1].geometry
            geom2 = high_gdf.loc[idx2].geometry

            if geom1.touches(geom2) or geom1.intersects(geom2):
                adjacency_pairs.append(
                    (
                        high_gdf.loc[idx1]["name"],
                        high_gdf.loc[idx2]["name"],
                    )
                )

    # ---------------------------------------------------
    # 7️⃣ 连续性判断
    # TODO:建 adjacency_map,然后做DFS/BFS，计算connected components
    # ---------------------------------------------------

    # if len(adjacency_pairs) >= max(1, len(high_regions) // 2):
    #     continuity = "高值区呈连续集聚分布"
    # elif len(adjacency_pairs) > 0:
    #     continuity = "高值区存在局部连续分布"
    # else:
    #     continuity = "高值区呈离散分布"

    # ---------------------------------------------------
    # 8️⃣ 集聚程度判断
    # ---------------------------------------------------

    if len(high_regions) >= 3 and len(adjacency_pairs) >= 2:
        aggregation_type = "高值区局部集聚明显"
    elif len(high_regions) >= 2:
        aggregation_type = "高值区存在一定集聚"
    else:
        aggregation_type = "空间集聚特征不明显"

    # ---------------------------------------------------
    # 9️⃣ 核心优势区识别
    # ---------------------------------------------------

    core_area = None

    if len(high_regions) > 0:

        # 按纬度排序
        sorted_high = high_gdf.sort_values("mean_score", ascending=False)

        core_area = sorted_high.iloc[0]["name"]

    # ---------------------------------------------------
    # 🔟 空间断裂分析
    # ---------------------------------------------------

    # if continuity == "高值区呈连续集聚分布":
    #     fragmentation = "空间破碎化程度较低"

    # elif continuity == "高值区存在局部连续分布":
    #     fragmentation = "存在一定空间断裂"

    # else:
    #     fragmentation = "空间破碎化明显"

    # ---------------------------------------------------
    # 1️⃣1️⃣ 空间模式总结
    # ---------------------------------------------------

    spatial_patterns = []

    if gradient_direction != "南北差异不显著":
        spatial_patterns.append(gradient_direction)

    if ew_pattern != "东西差异不显著":
        spatial_patterns.append(ew_pattern)

    spatial_patterns.append(aggregation_type)

    # ---------------------------------------------------
    # 1️⃣2️⃣ 产业带识别（轻量版）
    # TODO：判断过于机械
    # ---------------------------------------------------

    # industrial_belt = None

    # if (
    #     "北高南低" in spatial_patterns
    #     and len(high_regions) >= 3
    #     and len(adjacency_pairs) >= 2
    # ):
    #     industrial_belt = "具备形成区域性苹果产业带潜力"

    # ---------------------------------------------------
    # 1️⃣3️⃣ 输出
    # ---------------------------------------------------

    return {
        "spatial_pattern": {
            "global_pattern": "、".join(spatial_patterns),
            "gradient_direction": gradient_direction,
            "east_west_pattern": ew_pattern,
            "aggregation_type": aggregation_type,
            # "continuity": continuity,
            # "fragmentation": fragmentation,
            # "industrial_belt": industrial_belt,
        },
        "high_value_regions": high_regions,
        "low_value_regions": low_regions,
        "core_area": core_area,
        "high_value_count": len(high_regions),
        "low_value_count": len(low_regions),
        "adjacency_pairs": adjacency_pairs,
        # "spatial_grading": spatial_grading,
    }
