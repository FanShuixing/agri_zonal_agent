def sanitize_gdf_for_save(gdf):

    gdf = gdf.copy()

    for col in gdf.columns:

        if col == "geometry":
            continue

        # 统一全部转 object
        gdf[col] = gdf[col].astype(object)

    return gdf
