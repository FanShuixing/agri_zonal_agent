"""
对话式农业适宜性 Agent — 基于 OpenAI function calling。

用法:
    python -m agent.conversation

原则: AI = 编导（意图理解 + 工具编排 + 叙事）
      管道 = 演员（数值 100% 确定性）
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from agent.tools import (
    check_crop_model,
    analyze_suitability,
    compare_regions,
    get_risk_detail,
    export_report,
    train_crop_model,
)
from core.model_registry import list_models

load_dotenv()

# ═══════════════════════════════════════════════════════════════════
# System Prompt
# ═══════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """你是一位农业种植适宜性分析专家。你的任务是通过对话帮助用户评估某种作物在中国任意省份/城市的种植适宜性。

## 核心原则
- 所有数值必须来自工具返回的数据，绝不编造或猜测数字
- 先查模型是否存在；不存在则告知用户并询问是否训练
- 报告仅在用户明确要求时导出
- 回答风格：结论先行 → 关键数据支撑 → 简要解释 → 实用建议

## 回答结构
1. **结论**（一句话）
2. **关键数据**（全省均分、最佳城市、等级分布等）
3. **亮点与风险**（峰值潜力城市、不适宜区域）
4. **建议**（是否适合、优先发展区域、需谨慎区域）

## 工具使用指南
- 用户询问"XX适合种YY吗" → check_crop_model(YY) → 如存在则 analyze_suitability(YY, XX)
- 用户问"哪些城市适合" → analyze_suitability 的 top_cities 字段已包含排名
- 用户问"XX市具体怎么样" → get_risk_detail
- 用户问"江苏和山东哪个更好" → compare_regions
- 用户说"导出报告"/"生成报告" → export_report
- 可用作物列表: {available_models}
- 如果用户问的作物不在列表中且未训练，必须说明并等待用户确认再训练

## 约束
- 严禁编造模型阈值、AUC、城市得分等任何数字
- 严禁在未调用工具的情况下声称某城市"适合"或"不适合"
- 如果工具返回 error，如实告知用户
- 训练模型需要 3-5 分钟，必须提前告知用户
"""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_crop_model",
            "description": "查询某作物是否有已训练的 SDM 模型。在分析前必须先调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {
                        "type": "string",
                        "description": "作物名称，如 苹果、水蜜桃、水稻、小麦",
                    },
                },
                "required": ["crop"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_suitability",
            "description": "对指定区域进行完整的作物种植适宜性分析。返回综合评分、城市排名、等级分布、峰值潜力等。这是核心分析工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "作物名称"},
                    "region": {"type": "string", "description": "省/市名称，如 山东省、江苏省、成都市"},
                },
                "required": ["crop", "region"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_regions",
            "description": "对比多个区域对同一作物的适宜性。",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "作物名称"},
                    "regions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要对比的区域列表，如 ['山东省', '江苏省']",
                    },
                },
                "required": ["crop", "regions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_detail",
            "description": "获取单个城市的详细适宜性拆解，包括各等级占比、与全球阈值对比。",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "作物名称"},
                    "region": {"type": "string", "description": "所在省份"},
                    "city": {"type": "string", "description": "城市名称，如 烟台市、无锡市"},
                },
                "required": ["crop", "region", "city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_report",
            "description": "导出 HTML 分析报告。仅在用户明确要求时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "作物名称"},
                    "region": {"type": "string", "description": "区域名称"},
                    "template": {
                        "type": "string",
                        "enum": ["standard", "dashboard"],
                        "description": "standard=详细报告, dashboard=仪表盘",
                    },
                },
                "required": ["crop", "region"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "train_crop_model",
            "description": "训练新作物的 SDM 模型。耗时 3-5 分钟，必须先告知用户并获确认。",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "作物标识符"},
                    "scientific_name": {
                        "type": "string",
                        "description": "GBIF 学名，如 Malus domestica。不提供则用 crop 作为搜索词",
                    },
                },
                "required": ["crop"],
            },
        },
    },
]

# 工具调度表
TOOL_MAP = {
    "check_crop_model": check_crop_model,
    "analyze_suitability": analyze_suitability,
    "compare_regions": compare_regions,
    "get_risk_detail": get_risk_detail,
    "export_report": export_report,
    "train_crop_model": train_crop_model,
}

# ═══════════════════════════════════════════════════════════════════
# Agent
# ═══════════════════════════════════════════════════════════════════
class AgriAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI()
        self.model = model
        self.messages: list[dict] = []
        self._init_system_prompt()

    def _init_system_prompt(self):
        models = list_models()
        available = "、".join(models) if models else "暂无预训练模型，需按需训练"
        prompt = SYSTEM_PROMPT.format(available_models=available)
        self.messages = [{"role": "system", "content": prompt}]

    def chat(self, user_message: str) -> str:
        """一轮对话。返回自然语言回复。"""
        self.messages.append({"role": "user", "content": user_message})

        # 调用 API（可能多次，因为有 tool calls）
        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=TOOL_DEFINITIONS,
                temperature=0.3,
            )

            msg = response.choices[0].message

            # 无 tool call → 直接返回文本
            if not msg.tool_calls:
                self.messages.append({"role": "assistant", "content": msg.content})
                return msg.content

            # 有 tool call → 执行并反馈结果
            self.messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                tool_args = json.loads(tc.function.arguments)

                print(f"\n  🔧 {tool_name}({tool_args})")

                func = TOOL_MAP.get(tool_name)
                if func:
                    try:
                        result = func(**tool_args)
                    except Exception as e:
                        result = {"error": True, "message": str(e)}
                else:
                    result = {"error": True, "message": f"未知工具: {tool_name}"}

                result_str = json.dumps(result, ensure_ascii=False, indent=2)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })

    def run_loop(self):
        """交互式对话循环。"""
        print("\n" + "=" * 56)
        print("  🌾  农业种植适宜性 Agent")
        print("  可用模型:", "、".join(list_models()) or "无（按需训练）")
        print("  输入 'quit' 退出, 'report' 导出报告")
        print("=" * 56 + "\n")

        while True:
            try:
                user_input = input("👤 你: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 再见！")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 再见！")
                break

            print("\n🤖 Agent: ", end="", flush=True)
            reply = self.chat(user_input)
            print(reply)
            print()


# ═══════════════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    agent = AgriAgent()
    agent.run_loop()
