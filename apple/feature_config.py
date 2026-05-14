from pathlib import Path
import rasterio

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "wc2.1_2.5m_bio"

FEATURE_RASTERS = [
    ("bio1_temp", rasterio.open(DATA_DIR / "wc2.1_2.5m_bio_1.tif")),
    ("bio12_rain", rasterio.open(DATA_DIR / "wc2.1_2.5m_bio_12.tif")),
    ("bio5_max_temp_warmest_month", rasterio.open(DATA_DIR / "wc2.1_2.5m_bio_5.tif")),
    ("bio6_min_temp_coldest_month", rasterio.open(DATA_DIR / "wc2.1_2.5m_bio_6.tif")),
    ("bio4_temp_seasonality", rasterio.open(DATA_DIR / "wc2.1_2.5m_bio_4.tif")),
    ("bio15_precip_seasonality", rasterio.open(DATA_DIR / "wc2.1_2.5m_bio_15.tif")),
]


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TIF = BASE_DIR / "output" / "china_suitability.tif"
DEFAULT_OUTPUT = BASE_DIR / "output" / "region_map.png"


CLIP_SHP = {
    "province": BASE_DIR / "data" / "shapfile" / "china_province.shp",
    "city": BASE_DIR / "data" / "shapfile" / "china_city.shp",
}

DISPLAY_SHP = {
    "province": BASE_DIR / "data" / "shapfile" / "china_province.shp",
    "city": BASE_DIR / "data" / "shapfile" / "china_city.shp",
    "county": BASE_DIR / "data" / "shapfile" / "china_county.shp",
}
