from service.geo.geocode_service import get_location
from apple.predictor import predict_location
from apple.explainer import explain_prediction, plot_radar, plot_map


def analyze_apple_suitability(county_name: str):
    "处理单点预测相关"
    lat, lon = get_location(county_name)
    prob, suitable, X_raw = predict_location(lat, lon)
    # print(f"/n预测结果 - 适宜性得分: {prob:.4f}, 是否适宜: {suitable}/n")

    reasons = explain_prediction(X_raw)
    # 画雷达图
    plot_radar(X_raw)
    # 画地图
    plot_map(lat, lon)

    return {
        "location": county_name,
        "lat": lat,
        "lon": lon,
        "suitability_score": float(prob),
        "suitable": suitable,
        "reasons": reasons,
    }
