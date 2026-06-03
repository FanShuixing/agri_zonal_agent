import numpy as np
import pandas as pd


def build_ranking_semantic(
    city_stats,
    grading_system,
):
    """
    构建 Ranking Semantic Layer

    功能：
    ----------
    1. 排名结构分析
    2. 头部区域识别
    3. 尾部区域识别
    4. 区域差异分析
    5. 均衡性分析
    6. 生成 ranking summary

    Parameters
    ----------
    city_stats : list[dict]

    grading_system : dict
        build_grading_system 返回结果

    Returns
    ----------
    dict
    """

    # 全省不适宜 → 跳过正常分级逻辑
    if not grading_system.get("province_viable", True):
        return {
            "top_regions": [],
            "bottom_regions": [],
            "leading_group": {"exists": False, "regions": [], "description": "全省气候条件不适合苹果种植"},
            "ranking_structure": {"type": "全省不适宜", "description": "无城市达到最低生态适生门槛，不建议发展苹果产业"},
            "regional_gap": {"type": "不适用", "score_range": 0},
            "ranking_type": "全省不适宜",
            "summary": "该区域气候条件不适合苹果种植。",
        }

    # =========================================
    # 1️⃣ 转 DataFrame
    # =========================================

    df = pd.DataFrame(city_stats)

    df = df.sort_values(
        by="mean_score",
        ascending=False,
    ).reset_index(drop=True)

    # =========================================
    # 2️⃣ 提取阈值
    # =========================================

    thresholds = grading_system["thresholds"]

    high_threshold = thresholds["high_threshold"]

    medium_threshold = thresholds["medium_threshold"]

    low_threshold = thresholds["low_threshold"]

    # =========================================
    # 3️⃣ 基础统计
    # =========================================

    scores = df["mean_score"].values

    max_score = float(np.max(scores))

    min_score = float(np.min(scores))

    mean_score = float(np.mean(scores))

    std_score = float(np.std(scores))

    score_gap = max_score - min_score

    cv = std_score / mean_score if mean_score > 0 else 0

    # =========================================
    # 4️⃣ Top / Bottom Regions
    # =========================================

    top_regions = df.head(5)["region"].tolist()

    bottom_regions = df.tail(5)["region"].tolist()

    # =========================================
    # 5️⃣ Head Group（头部梯队）
    # =========================================

    leading_df = df[df["mean_score"] >= high_threshold]

    leading_regions = leading_df["region"].tolist()

    if len(leading_regions) >= 1:

        leading_group = {
            "exists": True,
            "regions": leading_regions,
            "description": (
                f"{'、'.join(leading_regions)}" "适宜性明显高于区域平均水平"
            ),
        }

    else:

        leading_group = {
            "exists": False,
            "regions": [],
            "description": "未形成明显头部优势区域",
        }

    # =========================================
    # 6️⃣ 排名结构分析
    # =========================================

    high_count = len(df[df["mean_score"] >= high_threshold])

    low_count = len(df[df["mean_score"] <= low_threshold])

    if high_count <= max(1, len(df) * 0.2):

        ranking_structure = {
            "type": "头部集中型",
            "description": ("少数区域适宜性明显领先，" "多数区域处于中低水平"),
        }

    elif low_count >= len(df) * 0.4:

        ranking_structure = {
            "type": "低值广泛型",
            "description": ("低适宜区域占比较高，" "整体适宜性偏弱"),
        }

    else:

        ranking_structure = {
            "type": "相对均衡型",
            "description": ("区域间适宜性差异相对有限"),
        }

    # =========================================
    # 7️⃣ 区域差异分析
    # =========================================

    if score_gap >= 0.35:

        gap_level = "头尾差异极大"

    elif score_gap >= 0.25:

        gap_level = "头尾差异较大"

    elif score_gap >= 0.15:

        gap_level = "头尾差异中等"

    else:

        gap_level = "头尾差异较小"

    regional_gap = {
        "type": gap_level,
        "score_range": round(score_gap, 4),
    }

    # =========================================
    # 9️⃣ Top Tier / Mid Tier / Low Tier
    # =========================================

    top_tier = df[df["mean_score"] >= high_threshold]["region"].tolist()

    mid_tier = df[
        (df["mean_score"] >= medium_threshold) & (df["mean_score"] < high_threshold)
    ]["region"].tolist()

    low_tier = df[df["mean_score"] < medium_threshold]["region"].tolist()

    # =========================================
    # 🔟 Ranking Summary
    # =========================================

    summary_parts = []

    if leading_regions:

        summary_parts.append(f"{'、'.join(leading_regions)}" "形成明显头部优势")

    if len(mid_tier) > 0:

        summary_parts.append("部分区域处于中等适宜梯队")

    if low_count >= len(df) * 0.3:

        summary_parts.append("低适宜区域占比相对较高")

    summary_parts.append(gap_level)

    ranking_summary = "；".join(summary_parts) + "。"

    # =========================================
    # 1️⃣1️⃣ 输出
    # =========================================

    return {
        "top_regions": top_regions,
        "bottom_regions": bottom_regions,
        "leading_group": leading_group,
        "ranking_structure": ranking_structure,
        "regional_gap": regional_gap,
        # "tier_structure": {
        #     "top_tier": top_tier,
        #     "mid_tier": mid_tier,
        #     "low_tier": low_tier,
        # },
        # "ranking_summary": ranking_summary,
    }
