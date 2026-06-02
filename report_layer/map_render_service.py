from __future__ import annotations
import matplotlib.pyplot as plt


def render_map(
    array,
    left,
    right,
    bottom,
    top,
    output_path,
    display_gdf=None,
    province_boundary=None,
    colorbar_label="Suitability",
):
    fig, ax = plt.subplots(figsize=(8, 7))

    # 🔥 raster
    interpolation = "bilinear"  # 或 'bilinear'，根据需要选择
    im = ax.imshow(
        array,
        extent=[left, right, bottom, top],
        cmap="YlOrRd",
        origin="upper",
        interpolation=interpolation,
    )

    # 🟡 内部边界（细线）
    if not display_gdf.empty:
        display_gdf.boundary.plot(
            ax=ax,
            color="gray",
            linewidth=0.4,
            alpha=0.6,
        )

    # 🔴 外轮廓（粗线！关键）
    if province_boundary is not None and not province_boundary.empty:
        province_boundary.boundary.plot(
            ax=ax,
            color="black",
            linewidth=1.5,
        )

    plt.colorbar(im, ax=ax)

    ax.set_xlim(left, right)
    ax.set_ylim(bottom, top)

    plt.savefig(output_path, dpi=300)
    plt.close()

    return str(output_path)
