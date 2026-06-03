"""
纯数据驱动报告生成器 — 不依赖 LLM，直接从 context.json 生成 HTML。
换省份/换物种后自动适配，无需修改代码。

用法:
    python report_layer/generate_data_report.py                          # 标准模板
    python report_layer/generate_data_report.py --template dashboard    # 仪表盘模板
    python report_layer/generate_data_report.py --context path/to/context.json --out path/to/output.html
"""

import argparse
from apple_report_service import generate_data_report
from utils.json_handler import load_json


def main():
    parser = argparse.ArgumentParser(description="数据驱动 HTML 报告生成")
    parser.add_argument(
        "--context", default="output/cache/pipeline/context.json",
        help="context.json 路径 (默认: output/cache/pipeline/context.json)",
    )
    parser.add_argument(
        "--out", default=None,
        help="输出 HTML 路径 (默认: config.yaml 中的 final_stage_html)",
    )
    parser.add_argument(
        "--template", default=None,
        choices=["standard", "dashboard"],
        help="模板选择: standard (默认详细报告), dashboard (仪表盘风格)",
    )
    args = parser.parse_args()

    context = load_json(args.context)
    generate_data_report(context, output_path=args.out, template=args.template)


if __name__ == "__main__":
    main()
