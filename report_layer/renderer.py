from jinja2 import Environment, FileSystemLoader
from utils.config_loader import CONFIG

_AVAILABLE_TEMPLATES = {
    "standard": "report.html",
    "dashboard": "report_dashboard.html",
}


def render_report(report_data, template_name: str | None = None):

    env = Environment(loader=FileSystemLoader("report_layer/templates"))

    if template_name is None:
        template_name = CONFIG["paths"].get("html_template", "report.html")
    elif template_name in _AVAILABLE_TEMPLATES:
        template_name = _AVAILABLE_TEMPLATES[template_name]

    template = env.get_template(template_name)

    html = template.render(**report_data)

    return html
