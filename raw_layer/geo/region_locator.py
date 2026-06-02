import geopandas as gpd
from utils.config_loader import CONFIG


def get_cities_within_province(region_name: str):
    # 读取省级行政区划数据
    province_gdf = gpd.read_file(CONFIG["paths"]["shapefile"]["province"])

    target_province = province_gdf[province_gdf["name"] == region_name]

    province_gb = str(target_province.iloc[0]["gb"])[-6:]  # 获取省级GB代码的后6位
    province_prefix = province_gb[:2]

    city_shapefile = CONFIG["paths"]["shapefile"]["city"]
    city_gdf = gpd.read_file(city_shapefile, encoding="utf-8")

    city_gdf["gb"] = city_gdf["gb"].astype(str).str[-6:]  # 保留后6位GB代码
    province_city_gdf = city_gdf[city_gdf["gb"].str.startswith(province_prefix)]
    return province_city_gdf
