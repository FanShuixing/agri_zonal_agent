import geopandas as gpd
import rasterio
import numpy as np
from pathlib import Path
from rasterstats import zonal_stats
from apple.feature_config import DEFAULT_TIF, CLIP_SHP


def compute_region_zonal_stats(
    raster_path,
    region_gdf,
    region_name_field="name",
):
    """
    对每个行政区计算适宜性统计
    """

    stats = zonal_stats(
        region_gdf,
        raster_path,
        stats=["mean", "max", "min"],
        geojson_out=True,
        nodata=0,
    )

    results = []

    for item in stats:
        props = item["properties"]

        results.append(
            {
                "region": props[region_name_field],
                "mean_score": round(props["mean"] or 0, 4),
                "max_score": round(props["max"] or 0, 4),
                "min_score": round(props["min"] or 0, 4),
            }
        )

    return results


if __name__ == "__main__":
    stats = compute_region_zonal_stats_by_geometry()
    for stat in stats[:10]:
        print(stat)
