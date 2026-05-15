from pathlib import Path
import geopandas as gpd
from utils.config_loader import CONFIG


def extract_region(query):
    import re

    pattern = r"(?:北京|天津|上海|重庆|[\u4e00-\u9fa5]{2,20}?(?:省|市|县|区))"
    matches = re.findall(pattern, query)
    return matches[0] if matches else None


def _normalize_region_name(name: str) -> str:
    return str(name).strip()


def _match_region(gdf: gpd.GeoDataFrame, region_name: str, level: str):
    normalized_name = _normalize_region_name(region_name)
    region_names = gdf["name"].astype(str).str.strip()
    # print(f"line43区域名列表: {region_names}, 匹配: {normalized_name}")

    exact_match = gdf[region_names == normalized_name]
    if not exact_match.empty:
        return exact_match

    if level == "province" and not normalized_name.endswith("省"):
        province_match = gdf[region_names == f"{normalized_name}省"]
        if not province_match.empty:
            return province_match

    fuzzy_match = gdf[region_names.str.contains(normalized_name, regex=False)]
    if len(fuzzy_match) == 1:
        return fuzzy_match

    if len(fuzzy_match) > 1:
        candidates = "、".join(fuzzy_match["name"].astype(str).head(10).tolist())
        raise ValueError(
            f"❌ 区域名 {region_name} 匹配到多个{level}记录，请提供更完整名称。候选: {candidates}"
        )

    raise ValueError(f"❌ 未找到区域: {region_name}")


def get_region_context(region_name):
    """
    获取区域的上下文信息，包括行政级别、所属省份等。
    """
    clip_region = None
    if region_name in ["中国", "全国"]:
        clip_geom = None
        display_level = "province"

    elif region_name.endswith("省"):
        clip_gdf = gpd.read_file(CONFIG["paths"]["shapefile"]["province"])
        clip_region = _match_region(clip_gdf, region_name, "province")
        clip_geom = clip_region.geometry
        display_level = "city"

    else:
        # 默认市级
        clip_gdf = gpd.read_file(CONFIG["paths"]["shapefile"]["city"], encoding="utf-8")
        clip_region = _match_region(clip_gdf, region_name, "city")
        clip_geom = clip_region.geometry
        display_level = "county"
    return {
        "clip_region": clip_region,
        "clip_geom": clip_geom,
        "display_level": display_level,
        # "region_level": region_level,
    }
