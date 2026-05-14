from jinja2 import Environment, FileSystemLoader


def render_report(report_data):

    env = Environment(
        loader=FileSystemLoader("templates")
    )

    template = env.get_template("report.html")

    html = template.render(**report_data)

    return html
