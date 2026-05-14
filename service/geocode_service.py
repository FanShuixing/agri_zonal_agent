def get_location(county_name):
    from geopy.geocoders import Nominatim

    geolocator = Nominatim(user_agent="apple-agent")
    location = geolocator.geocode(county_name)
    if location is None:
        raise ValueError(f"无法找到县名 '{county_name}' 的地理位置。")
    return location.latitude, location.longitude
