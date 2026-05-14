import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd
import matplotlib

matplotlib.use("Agg")


def explain_prediction(features):
    bio1, bio12, bio5, bio6, bio4, bio15 = features[0]

    result = {
        "temperature": {},
        "winter_chill": {},
        "rainfall": {},
        "extreme_heat": {},
        "seasonality": [],
    }

    # =========================
    # 🌡️ 年均温
    # =========================
    if bio1 < 5:
        result["temperature"] = {
            "level": "过低",
            "desc": "年均气温明显偏低，生长季较短",
            "impact": "不利于苹果正常生长和成熟",
        }
    elif 5 <= bio1 < 8:
        result["temperature"] = {
            "level": "偏低",
            "desc": "年均气温略低",
            "impact": "可能影响产量和成熟度",
        }
    elif 8 <= bio1 <= 15:
        result["temperature"] = {
            "level": "适宜",
            "desc": "年均气温处于理想范围",
            "impact": "有利于苹果生长和品质形成",
        }
    elif 15 < bio1 <= 20:
        result["temperature"] = {
            "level": "偏高",
            "desc": "年均气温略高",
            "impact": "可能导致品质下降",
        }
    else:
        result["temperature"] = {
            "level": "过高",
            "desc": "年均气温过高",
            "impact": "不利于苹果种植",
        }

    # =========================
    # ❄️ 冬季低温
    # =========================
    if bio6 > 7:
        result["winter_chill"] = {
            "level": "不足",
            "desc": "冬季气温偏高",
            "impact": "无法满足休眠需求，影响开花结果",
        }
    elif 0 < bio6 <= 7:
        result["winter_chill"] = {
            "level": "一般",
            "desc": "冬季低温条件一般",
            "impact": "基本可满足休眠，但稳定性不足",
        }
    elif -15 <= bio6 <= 0:
        result["winter_chill"] = {
            "level": "充足",
            "desc": "冬季低温条件良好",
            "impact": "有利于休眠，提高产量",
        }
    else:
        result["winter_chill"] = {
            "level": "过强",
            "desc": "冬季气温过低",
            "impact": "存在冻害风险",
        }

    # =========================
    # 🌧️ 降水
    # =========================
    if bio12 < 400:
        result["rainfall"] = {
            "level": "过少",
            "desc": "降水明显不足",
            "impact": "需要依赖灌溉",
        }
    elif 400 <= bio12 < 600:
        result["rainfall"] = {
            "level": "偏少",
            "desc": "降水略少",
            "impact": "干旱年份需补水",
        }
    elif 600 <= bio12 <= 1200:
        result["rainfall"] = {
            "level": "适宜",
            "desc": "降水适中",
            "impact": "有利于稳定生长",
        }
    elif 1200 < bio12 <= 1800:
        result["rainfall"] = {
            "level": "偏多",
            "desc": "降水偏多",
            "impact": "病害风险增加",
        }
    else:
        result["rainfall"] = {
            "level": "过多",
            "desc": "降水过多",
            "impact": "湿度大，不利于优质苹果生产",
        }

    # =========================
    # 🌡️ 极端高温
    # =========================
    if bio5 > 35:
        result["extreme_heat"] = {
            "exists": True,
            "impact": "可能出现日灼，影响果实品质",
        }
    else:
        result["extreme_heat"] = {"exists": False}

    # =========================
    # 🌡️ 温度季节性
    # =========================
    if bio4 < 300:
        result["seasonality"].append("温度季节变化较小，不利于苹果生长节律形成")
    elif bio4 > 900:
        result["seasonality"].append("温度季节变化较大，气候波动风险较高")

    # =========================
    # 🌧️ 降水季节性
    # =========================
    if bio15 > 80:
        result["seasonality"].append("降水季节分布不均，可能出现旱涝交替")

    return result


def plot_radar(features, save_path="radar.png"):
    labels = ["bio1", "bio12", "bio5", "bio6", "bio4", "bio15"]
    values = features[0]

    # 归一化（简单版）
    values = np.array(values)
    values = (values - values.min()) / (values.max() - values.min() + 1e-6)

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    values = np.concatenate([values, [values[0]]])
    angles = np.concatenate([angles, [angles[0]]])

    plt.figure()
    ax = plt.subplot(111, polar=True)
    ax.plot(angles, values)
    ax.fill(angles, values, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)

    plt.title("Climate Profile Radar")
    plt.savefig(save_path)
    plt.close()


def plot_map(lat, lon, save_path="map.png"):
    china = gpd.read_file("./data/shapfile/china_province.shp")
    china = china.to_crs("EPSG:4326")

    fig, ax = plt.subplots(figsize=(6, 6))
    china.plot(ax=ax, color="lightgray", edgecolor="black")

    ax.scatter(lon, lat, color="red", s=50)
    ax.set_title("Location")

    plt.savefig(save_path)
    plt.close()


from reportlab.platypus import SimpleDocTemplate, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet


def generate_pdf(report_text, radar_path, map_path, output="report.pdf"):
    doc = SimpleDocTemplate(output)
    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph("Apple Suitability Report", styles["Title"]))
    elements.append(Paragraph(report_text, styles["BodyText"]))

    elements.append(Image(radar_path, width=400, height=300))
    elements.append(Image(map_path, width=400, height=300))

    doc.build(elements)
