from jinja2 import Environment, FileSystemLoader
from utils.config_loader import CONFIG


def render_report(report_data):

    env = Environment(loader=FileSystemLoader("report_layer/templates"))

    template = env.get_template(CONFIG["paths"]["html_template"])

    html = template.render(**report_data)

    return html
