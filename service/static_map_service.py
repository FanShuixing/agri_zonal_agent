import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection

import geopandas as gpd
import pandas as pd

from utils.config_loader import CONFIG
from utils.ensure_file import ensure_save_path

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = [
    "PingFang SC",
    "Microsoft YaHei",
    "SimHei",
]
plt.rcParams["axes.unicode_minus"] = False


def plot_suitability_map(
    gdf,
    city_stats,
    score_col="mean_score",
    save_path=CONFIG["suitability_map_path"],
):
    """
    手工 Polygon 绘制苹果种植适宜性地图
    避免 geopandas.plot() 黑图 / 空白图问题
    """

    # ======================
    # 合并数据
    # ======================

    stats_df = pd.DataFrame(city_stats)

    gdf = gdf.merge(
        stats_df,
        left_on="name",
        right_on="region",
        how="left",
    )

    # 重新声明 GeoDataFrame
    gdf = gpd.GeoDataFrame(
        gdf,
        geometry="geometry",
        crs=gdf.crs,
    )

    # 去除空 geometry
    gdf = gdf[~gdf.geometry.is_empty]

    # 修复 geometry
    gdf["geometry"] = gdf.buffer(0)

    # ======================
    # 颜色分级
    # ======================

    bins = [0, 0.2, 0.25, 0.3, 0.35, 1.0]

    colors = [
        "#f46d43",
        "#f9c74f",
        "#d9e176",
        "#a7c957",
        "#3a7d44",
    ]

    cmap = mcolors.ListedColormap(colors)

    norm = mcolors.BoundaryNorm(
        bins,
        cmap.N,
        clip=True,
    )

    # ======================
    # 创建画布
    # ======================

    fig, ax = plt.subplots(
        figsize=(10, 8),
        facecolor="white",
    )

    ax.set_facecolor("white")

    patches = []
    patch_colors = []

    # ======================
    # 手工绘制 Polygon
    # ======================

    for _, row in gdf.iterrows():

        geom = row.geometry

        if geom is None:
            continue

        if geom.is_empty:
            continue

        score = row.get(score_col)

        if pd.isna(score):
            continue

        color = cmap(norm(score))

        # ------------------
        # Polygon
        # ------------------

        if geom.geom_type == "Polygon":

            try:

                polygon = Polygon(
                    list(geom.exterior.coords),
                    closed=True,
                )

                patches.append(polygon)
                patch_colors.append(color)

            except Exception as e:
                print("Polygon 绘制失败:", e)

        # ------------------
        # MultiPolygon
        # ------------------

        elif geom.geom_type == "MultiPolygon":

            for poly in geom.geoms:

                try:

                    polygon = Polygon(
                        list(poly.exterior.coords),
                        closed=True,
                    )

                    patches.append(polygon)
                    patch_colors.append(color)

                except Exception as e:
                    print("MultiPolygon 绘制失败:", e)

    # ======================
    # PatchCollection
    # ======================

    pc = PatchCollection(
        patches,
        facecolor=patch_colors,
        edgecolor="gray",
        linewidth=0.6,
    )

    ax.add_collection(pc)

    # 自动缩放
    ax.autoscale()

    # ======================
    # 添加文字标签
    # ======================

    for _, row in gdf.iterrows():

        geom = row.geometry

        if geom is None or geom.is_empty:
            continue

        score = row.get(score_col)

        if pd.isna(score):
            continue

        point = geom.representative_point()

        ax.text(
            point.x,
            point.y,
            f"{row['region']}\n{score:.3f}",
            fontsize=8,
            ha="center",
            va="center",
            color="black",
        )

    # ======================
    # 标题
    # ======================

    ax.set_title(
        "各市苹果种植适宜性空间分布图",
        fontsize=18,
        fontweight="bold",
    )

    ax.axis("off")

    # ======================
    # 保存
    # ======================

    plt.tight_layout()

    ensure_save_path(save_path)

    plt.savefig(
        save_path,
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(fig)

    print(f"空间分布图已保存: {save_path}")

    return save_path


import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


def plot_ranking_table(
    city_stats,
    save_path=CONFIG["ranking_table_path"],
):
    """
    绘制适宜性排名表（优化版）
    """

    df = pd.DataFrame(city_stats)

    df = df.sort_values(by="mean_score", ascending=False).reset_index(drop=True)

    df["排名"] = df.index + 1

    # 适宜性等级
    def level(score):

        if score >= 0.35:
            return "高适宜"

        elif score >= 0.30:
            return "较适宜"

        elif score >= 0.25:
            return "中等适宜"

        else:
            return "低适宜"

    df["适宜性等级"] = df["mean_score"].apply(level)

    # 保留展示字段
    show_df = df[
        [
            "排名",
            "region",
            "mean_score",
            "适宜性等级",
        ]
    ].copy()

    show_df.columns = [
        "排名",
        "城市",
        "平均适宜性",
        "适宜性等级",
    ]

    # 保留4位小数
    show_df["平均适宜性"] = show_df["平均适宜性"].map(lambda x: f"{x:.4f}")

    # 高度动态调整
    fig_height = max(4, len(show_df) * 0.5)

    fig, ax = plt.subplots(figsize=(8, fig_height))

    ax.axis("off")

    # 创建表格
    table = ax.table(
        cellText=show_df.values,
        colLabels=show_df.columns,
        loc="center",
        cellLoc="center",
    )

    # 字体
    table.auto_set_font_size(False)
    table.set_fontsize(12)

    # 行高
    table.scale(1, 1.8)

    # 表头样式
    for (row, col), cell in table.get_celld().items():

        if row == 0:
            cell.set_text_props(weight="bold")
            cell.set_height(0.08)

    # 标题
    plt.title(
        "适宜性排名（从高到低）",
        fontsize=18,
        weight="bold",
        pad=20,
    )

    plt.tight_layout()
    ensure_save_path(save_path)
    plt.savefig(
        save_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close()

    print(f"排名表已保存: {save_path}")
    return save_path


def plot_score_range_chart(
    city_stats,
    save_path=CONFIG["score_range_chart_path"],
):
    """
    绘制 min-mean-max 区间图
    """

    df = pd.DataFrame(city_stats)

    df = df.sort_values(by="mean_score", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))

    y_pos = range(len(df))

    # 区间线
    for i, row in enumerate(df.iterrows()):

        row = row[1]

        ax.plot(
            [row["min_score"], row["max_score"]],
            [i, i],
            linewidth=2,
        )

        # min
        ax.scatter(
            row["min_score"],
            i,
            s=80,
            label="min" if i == 0 else "",
        )

        # mean
        ax.scatter(
            row["mean_score"],
            i,
            s=80,
            label="mean" if i == 0 else "",
        )

        # max
        ax.scatter(
            row["max_score"],
            i,
            s=80,
            label="max" if i == 0 else "",
        )

        # 数值标注
        ax.text(
            row["min_score"] - 0.02,
            i,
            f"{row['min_score']:.2f}",
            va="center",
        )

        ax.text(
            row["mean_score"] + 0.01,
            i,
            f"{row['mean_score']:.2f}",
            va="center",
        )

        ax.text(
            row["max_score"] + 0.01,
            i,
            f"{row['max_score']:.2f}",
            va="center",
        )

    ax.set_yticks(list(y_pos))

    ax.set_yticklabels(df["region"])

    ax.set_xlabel("适宜性得分")

    ax.set_title(
        "适宜性得分范围（min ~ max）",
        fontsize=16,
        fontweight="bold",
    )

    ax.legend()

    plt.tight_layout()
    ensure_save_path(save_path)
    plt.savefig(save_path, dpi=300)
    plt.close()

    print(f"区间图已保存: {save_path}")
    return save_path
