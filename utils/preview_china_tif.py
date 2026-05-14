from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd

DEFAULT_TIF = Path(__file__).resolve().parents[1] / "output" / "china_suitability.tif"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
DEFAULT_BOUNDARY_SHP = (
    Path(__file__).resolve().parents[1] / "data" / "shapfile" / "china_county.shp"
)


def load_raster(tif_path: Path):
    with rasterio.open(tif_path) as src:
        array = src.read(1).astype("float32")
        bounds = src.bounds
        transform = src.transform
        crs = src.crs

    return array, bounds, transform, crs


def summarize_array(array: np.ndarray):
    valid = array[~np.isnan(array)]
    if valid.size == 0:
        return {
            "count": 0,
            "min": np.nan,
            "max": np.nan,
            "mean": np.nan,
            "std": np.nan,
        }

    return {
        "count": int(valid.size),
        "min": float(valid.min()),
        "max": float(valid.max()),
        "mean": float(valid.mean()),
        "std": float(valid.std()),
    }


def load_boundaries(boundary_path: Path, target_crs):
    boundaries = gpd.read_file(boundary_path)
    plot_crs = target_crs or "EPSG:4326"

    if boundaries.crs is not None and boundaries.crs != plot_crs:
        boundaries = boundaries.to_crs(plot_crs)

    return boundaries


def save_preview_png(
    array: np.ndarray,
    bounds,
    output_path: Path,
    threshold: float,
    boundaries: gpd.GeoDataFrame | None = None,
):
    fig, ax = plt.subplots(figsize=(8, 7))
    image = ax.imshow(
        array,
        extent=[bounds.left, bounds.right, bounds.bottom, bounds.top],
        origin="upper",
        cmap="YlOrRd",
    )
    plt.colorbar(image, ax=ax, label="Apple suitability probability")
    ax.set_title("China Apple Suitability")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    if boundaries is not None and not boundaries.empty:
        boundaries.boundary.plot(
            ax=ax,
            edgecolor="black",
            linewidth=0.6,
            alpha=0.8,
            zorder=3,
            autolim=False,
        )

    ax.set_xlim(bounds.left, bounds.right)
    ax.set_ylim(bounds.bottom, bounds.top)

    if np.nanmax(array) > threshold:
        ax.contour(
            array,
            levels=[threshold],
            extent=[bounds.left, bounds.right, bounds.bottom, bounds.top],
            origin="upper",
            colors="navy",
            linewidths=1.2,
        )

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def extract_suitable_points(
    array: np.ndarray,
    transform,
    threshold: float,
):
    rows, cols = np.where(array >= threshold)
    records = []

    for row, col in zip(rows, cols):
        lon, lat = rasterio.transform.xy(transform, row, col, offset="center")
        records.append(
            {
                "row": int(row),
                "col": int(col),
                "lon": float(lon),
                "lat": float(lat),
                "suitability": float(array[row, col]),
            }
        )

    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser(
        description="Preview apple suitability GeoTIFF, overlay province boundaries, and extract suitable cells."
    )
    parser.add_argument(
        "--tif",
        type=Path,
        default=DEFAULT_TIF,
        help="Path to the suitability GeoTIFF.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.199,
        help="Suitability threshold used to extract suitable cells.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save preview outputs.",
    )
    parser.add_argument(
        "--boundary-shp",
        type=Path,
        default=DEFAULT_BOUNDARY_SHP,
        help="Path to the province boundary shapefile to overlay on the preview image.",
    )
    args = parser.parse_args()

    tif_path = args.tif.resolve()
    output_dir = args.output_dir.resolve()
    boundary_path = args.boundary_shp.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    array, bounds, transform, crs = load_raster(tif_path)
    boundaries = load_boundaries(boundary_path, crs)
    stats = summarize_array(array)

    print(f"TIF: {tif_path}")
    print(f"CRS: {crs}")
    print(f"Bounds: {bounds}")
    print(f"Boundary shapefile: {boundary_path}")
    print(
        "Stats:"
        f" count={stats['count']}, min={stats['min']:.6f}, max={stats['max']:.6f},"
        f" mean={stats['mean']:.6f}, std={stats['std']:.6f}"
    )

    png_path = output_dir / "china_suitability_preview.png"
    save_preview_png(array, bounds, png_path, args.threshold, boundaries=boundaries)
    print(f"Preview image saved: {png_path}")

    suitable_df = extract_suitable_points(array, transform, args.threshold)
    suitable_csv_path = output_dir / "china_suitable_cells.csv"
    suitable_df.to_csv(suitable_csv_path, index=False)
    print(f"Suitable cells saved: {suitable_csv_path}")
    print(f"Suitable cell count (threshold={args.threshold}): {len(suitable_df)}")

    if len(suitable_df) > 0:
        print("Top 10 suitable cells:")
        print(suitable_df.sort_values("suitability", ascending=False).head(10))
    else:
        print("No cells exceeded the threshold. Try lowering --threshold.")


if __name__ == "__main__":
    main()
