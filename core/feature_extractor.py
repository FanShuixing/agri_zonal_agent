import numpy as np
from core.feature_config import FEATURE_RASTERS


def normalize_numeric(value, nodata=None):
    if np.ma.is_masked(value):
        return np.nan

    try:
        v = float(value)

        # 🚨 关键：过滤异常极值
        if abs(v) > 1e10:
            return np.nan

        # 可选：用 raster 自带 nodata
        if nodata is not None and v == nodata:
            return np.nan

        return v

    except:
        return np.nan


def extract_features(lat, lon):
    """
    从经纬度坐标提取特征值，返回一个 1xN 的 numpy 数组，适用于模型输入。
    """
    coords = [(lon, lat)]
    features = [
        normalize_numeric(raster.sample(coords).__next__()[0])
        for _, raster in FEATURE_RASTERS
    ]
    return np.array(features).reshape(1, -1)
