"""OpenAI Responses API orchestration for a grounded tarot reading."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Callable, Literal

from .meanings import evidence_for
from .tarot import Reading, draw_reading
from .question_focus import question_guidance

Style = Literal["direct", "gentle"]

DRAW_TOOL: dict[str, Any] = {
    "type": "function",
    "name": "draw_tarot",
    "description": "Reveal the tarot card or cards selected by the application.",
    "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    "strict": True,
}

SYSTEM_INSTRUCTIONS = """你是塔罗解读助手。抽牌结果只能来自 draw_tarot 工具。
解读时按牌位、牌名和正逆位说明推理依据，并给出可执行的反思或行动建议。
不编造牌、经典引文、出生信息或其他占卜系统的计算结果。
占卜是反思与娱乐，不把未来事件表述为事实或必然结果。
如用户询问医疗、法律、财务或其他重大决定，避免给出确定性结论，建议参考相关专业人士。
回答使用中文。"""
SOURCE_INSTRUCTIONS = """工具的 source_meanings 是 Waite《The Pictorial Key to the Tarot》原书转录的历史牌义。
仅对 status=sourced 的牌和正逆位说明该书依据；status=unavailable 表示该方向尚无核对资料，不得冒充书中原文。
原书包含旧时代的性别、疾病、灾祸及宿命论表述，请作为历史语境解释，不把它们套用成用户的事实或预言。
每张有资料的牌可简要说明牌义并给出出处链接；解读应结合用户实际问题，不机械照搬原文。"""


@dataclass(frozen=True)
class AgentResult:
    reading: Reading
    interpretation: str
    evidence: tuple[dict[str, object], ...] = ()


class TarotAgent:
    def __init__(
        self,
        client: Any,
        model: str,
        draw: Callable[..., Reading] = draw_reading,
        use_sources: bool = True,
    ):
        if not model.strip():
            raise ValueError("Model name cannot be empty")
        self.client = client
        self.model = model
        self.draw = draw
        self.use_sources = use_sources

    def read(
        self,
        question: str,
        spread: str = "single",
        selected_positions: tuple[int, ...] | None = None,
        style: Style = "gentle",
    ) -> AgentResult:
        if style not in ("direct", "gentle"):
            raise ValueError("Style must be direct or gentle")
        if not question.strip():
            raise ValueError("Question cannot be empty")

        style_instruction = (
            "表达直接、简洁，明确说出牌面提示和建议，但不要断言未来必然发生。"
            if style == "direct"
            else "表达温和，标明不确定性，给出可选择的建议。"
        )
        instructions = f"{SYSTEM_INSTRUCTIONS}\n{style_instruction}\n{question_guidance(question)}"
        if self.use_sources:
            instructions += f"\n{SOURCE_INSTRUCTIONS}"
        user_input = [{"role": "user", "content": question.strip()}]
        first = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=user_input,
            tools=[DRAW_TOOL],
            tool_choice={"type": "function", "name": "draw_tarot"},
            parallel_tool_calls=False,
            store=False,
        )
        calls = [item for item in first.output if item.type == "function_call"]
        if len(calls) != 1 or calls[0].name != "draw_tarot":
            raise RuntimeError("Expected exactly one draw_tarot tool call")
        if json.loads(calls[0].arguments) != {}:
            raise RuntimeError("Unexpected draw_tarot arguments")

        reading = self.draw(question, spread, selected_positions)
        evidence = evidence_for(reading) if self.use_sources else ()
        tool_result = asdict(reading)
        if self.use_sources:
            tool_result["source_meanings"] = evidence
        tool_output = {
            "type": "function_call_output",
            "call_id": calls[0].call_id,
            "output": json.dumps(tool_result, ensure_ascii=False),
        }
        second = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=[*user_input, *first.output, tool_output],
            tools=[DRAW_TOOL],
            tool_choice="none",
            store=False,
        )
        if not second.output_text.strip():
            raise RuntimeError("Model returned an empty interpretation")
        return AgentResult(reading, second.output_text.strip(), evidence)
