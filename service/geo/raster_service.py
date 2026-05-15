import rasterio
from pathlib import Path
from rasterio.mask import mask
import geopandas as gpd

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TIF = BASE_DIR / "output" / "china_suitability.tif"


import rasterio
import numpy as np
from rasterio.mask import mask


def clip_raster_by_region(
    tif_path,
    clip_region,
):
    """裁剪 raster 数据到指定区域，返回裁剪后的数组、变换矩阵、边界和 CRS 信息。"""
    with rasterio.open(tif_path) as src:

        clip_region = clip_region.to_crs(src.crs)

        out_image, out_transform = mask(
            src,
            clip_region.geometry,
            crop=True,
        )

        array = out_image[0].astype("float32")

        if src.nodata is not None:
            array[array == src.nodata] = np.nan

        left = out_transform.c
        top = out_transform.f
        right = left + out_transform.a * array.shape[1]
        bottom = top + out_transform.e * array.shape[0]

        return {
            "array": array,
            "transform": out_transform,
            "bounds": (left, right, bottom, top),
            "crs": src.crs,
            "nodata": src.nodata,
        }
