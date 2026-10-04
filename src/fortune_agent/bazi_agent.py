"""Interpret a calculated chart without allowing the model to invent pillars."""

from __future__ import annotations

import json
import hashlib
from dataclasses import asdict
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from .bazi import BaziChart
from .bazi_sources import evidence_for
from .bazi_facts import chart_facts
from .bazi_rules import wealth_checklist
from .bazi_structure import analyze_structure

BAZI_INSTRUCTIONS = (
    "你是八字学习辅助工具。四柱可能来自历法程序或用户提供，必须逐字使用输入数据，"
    "不得重新排盘或更改日主。根据 calculator 和 birth_time 判断来源。"
    "birth_time 为 null 时是用户提供四柱，仅校验单柱干支，未核对同一出生时刻的四柱组合。"
    "此时出生日期、时区、节气与时间规则未知，必须说明未知，不得虚构或声称已经排盘验证。"
    "有出生时间时说明输入给出的法定时间、真太阳时校正状态和子时换日规则。"
    "source_evidence 包含《滴天髓辑要》短段与《子平真诠》论用神、财格条件及月令通根的扫描核对短段；"
    "只可引用其中的 source_text，标明条目和 source_url。"
    "只有《子平真诠》条目提供了 printed_pages 与 scan_pages，必须分别标明书内页码与 PDF 扫描页。"
    "其他资料没有纸本页码，不得为它们编造页码。不得把 26 个扫描页称为书内第 26 页。"
    "不得补写未提供的原文、注解或其他章节；《渊海子平》《三命通会》"
    "《穷通宝鉴》尚未接入。《子平真诠》仅接入所列短段，不是整章或整本。"
    "引用使用给定 source_text；notes 中的疑字须说明尚未校勘，不得静默更正。"
    "子平真诠原字保留，标点按 punctuation_policy 整理；‘以干日’不得静默改成‘以日干’。"
    "短引原文后，分别写明传统含义解释与行动建议；建议是现代反思，不能说成古书的结论。"
    "滴天髓电子转录尚未与底本校勘；子平真诠所列短段已看图核对，但版本间未完整校勘。"
    "仅凭日主不能判断整盘强弱、格局、用神或大运。"
    "子平真诠的月令起点、四柱配合和例外提示须结合说明，不得简化为缺某五行就补某五行。"
    "derived_facts 中的十神、五行、阴阳和藏干由程序算出，不得改写或另列不同的藏干。"
    "月令对应程序给出的月支；藏干顺序不是旺衰权重，不能套用未提供的人元司令天数。"
    "未建立完整的旺衰、格局、用神规则，询问这些结论时必须说明当前不能确定。"
    "structural_analysis 已由程序计算季节标签、逐柱根气观察、月支藏干透出位置和格局研究候选。"
    "使用它回答结构问题，不再说完全没有分析；但不改变其结论为确定旺衰、定格或用神。"
    "same_stem 是同干藏根出现，same_element 是同五行的其他藏干出现，两者都未判断根力。"
    "未见藏干根气不等于全盘身弱，季节同类不等于身强；季末月不直接判土旺或得令。"
    "pattern_candidates 仅研究候选；列表不排名，不能仅凭透出就说成格，也不能把比劫直接当普通八格。"
    "method_checklist 只展示天干可见信息和未核实条件，不代表已成财格。"
    "每条财格路径的 unverified_conditions 都须保留不确定性；见印星透干不等于位置妥适或两不相克。"
    "不存在透干观察不等于藏干中没有该星；不能把日柱日主计为另一个透出比肩。"
    "只引用与问题相关的资料；医疗、法律、投资问题不需要用古籍合理化建议。"
    "不要从单个天干断言用户性格、能力、婚姻、寿命或疾病。"
    "不要把命理推断当成事实或必然预言，也不要替代医疗、法律、财务判断。"
    "今天、明年等相对日期必须以输入中的 reference_date 为准；它与出生日期不同。"
    "结合用户问题给出具体的反思方向。用中文回答。"
)
PROMPT_SHA256 = hashlib.sha256(BAZI_INSTRUCTIONS.encode("utf-8")).hexdigest()


def current_reference_date() -> date:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def interpret_bazi(
    chart: BaziChart, question: str, client: Any, model: str,
    reference_date: date | None = None,
    style: str = "gentle",
    daily_context: dict | None = None,
) -> str:
    if not question.strip():
        raise ValueError("问题不能为空")
    if style not in ("direct","gentle"):
        raise ValueError("无效回答风格")
    response = client.responses.create(
        model=model,
        instructions=BAZI_INSTRUCTIONS + ("\n措辞直接简洁，保留不确定性。" if style=="direct" else "\n措辞温和，给出可选择的建议。") + (
            "\n这是每日八字提示。daily_context 的日期和参考时刻由程序确定，不能把当日柱说成本命柱。"
            "只使用其中计算的十神关系。偏财、正官等是分类，不意味着今天有进账或升职，"
            "七杀、伤官等不能变成灾祸、疾病或失败预言。没有大运或旺衰、喜用神，不能评分或判断吉凶。"
            "把当日关系转化为可选的反思问题，并结合用户实际问题给行动建议；这种现代类比不冒充古籍结论。"
            "说明每日参考为中国标准时间12:00，节气切换日其他时段可能不同。" if daily_context else ""),
        input=[{
            "role": "user",
            "content": json.dumps({
                "question": question.strip(),
                "chart": asdict(chart),
                "reference_date": (reference_date or current_reference_date()).isoformat(),
                "reference_timezone": "Asia/Shanghai",
                "style": style,
                "daily_context":daily_context,
                "source_evidence": evidence_for(chart),
                "derived_facts": chart_facts(chart),
                "method_checklist": wealth_checklist(chart),
                "structural_analysis":analyze_structure(chart),
            }, ensure_ascii=False),
        }],
        store=False,
    )
    if not response.output_text.strip():
        raise RuntimeError("模型返回了空的八字解读")
    return response.output_text.strip()
