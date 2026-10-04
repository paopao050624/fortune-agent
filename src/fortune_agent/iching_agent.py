"""Interpret only deterministically selected passages, validating citation IDs."""
from dataclasses import asdict
import json

from .iching_reading import select_passages, passage

INSTRUCTIONS = """你是周易学习与反思助手。主卦、变卦、动爻及取辞由程序确定，不得重新起卦或修改。
只解释 selection.passages 给出的经文，不补写其他爻辞、彖传、象传、纸本页码或流派出处。
输出必须是指定 JSON；passage_id 只能引用所给 ID。meaning 是传统语义解释，application 是结合问题的现代反思，两者不得混淆。
不要在模型字段重写原文引文，原文与链接由程序呈现。primary 表示项目取辞主次，不代表事实必然性。
选文策略是本项目明确公开的约定，并非唯一流派；电子转录未与指定底本完整校勘，notes 内异文不得静默改成定本。
原文吉、凶、利、无咎等是历史占辞，不是实际风险概率。不给确定性未来预测，不断言他人想法，不把疾病、死亡等意象当作诊断。
医疗、法律、投资或其他重大决定须明确命理不能代替专业判断，提供可执行的核实或求助方向。
直接风格要清楚简洁，温和风格给可选择的建议，两者都不得保证结果。中文回答。"""


def interpret_cast(cast, question, client, model, policy="moving-count-v1", style="gentle",include_hexagram_context=False):
    if not isinstance(question, str) or not question.strip():
        raise ValueError("解读需要一个具体问题")
    if style not in ("direct", "gentle"):
        raise ValueError("无效回答风格")
    selection = select_passages(cast, policy)
    if include_hexagram_context:
        ids={p["id"] for p in selection["passages"]}
        added=[]
        for number in (cast.main_hexagram["number"],cast.changed_hexagram["number"]):
            original=passage(number,"judgment")
            if original["id"] not in ids:
                original.update({"primary":False,"supplementary":True,
                                 "heading":original["heading"]+"（追问补充背景）"})
                selection["passages"].append(original);ids.add(original["id"]);added.append(original["id"])
        if added:
            selection["rule_explanation"].append("应追问追加主变卦卦辞作背景查阅，不改变原取辞的主次。")
            selection["supplementary_ids"]=added
    ids = [item["id"] for item in selection["passages"]]
    schema = {"type": "object", "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "explanations": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                "properties": {"passage_id": {"type": "string", "enum": ids},
                               "meaning": {"type": "string"}, "application": {"type": "string"}},
                "required": ["passage_id", "meaning", "application"]}},
            "advice": {"type": "array", "items": {"type": "string"}},
            "limitations": {"type": "array", "items": {"type": "string"}}},
        "required": ["summary", "explanations", "advice", "limitations"]}
    response = client.responses.create(
        model=model, instructions=INSTRUCTIONS+"\nsupplementary=true 的条目只是用户追问补充背景，不得将其说成原规则的主辞。",
        input=[{"role": "user", "content": json.dumps({"question": question.strip(), "style": style,
                        "cast": asdict(cast), "selection": selection}, ensure_ascii=False)}],
        text={"format": {"type": "json_schema", "name": "iching_interpretation", "strict": True, "schema": schema}},
        store=False,
    )
    try:
        result = json.loads(response.output_text)
        validate_interpretation(result, ids)
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        raise RuntimeError("模型未返回有效解读或引用了未提供的条目；本次结果未采用") from exc
    rendered = [result["summary"]]
    by_id = {item["passage_id"]: item for item in result["explanations"]}
    for original in selection["passages"]:
        explanation = by_id[original["id"]]
        rendered.extend([f"\n{original['heading']}{'（主辞）' if original['primary'] else ''}",
                         f"原文：{original['source_text']}", f"传统语义：{explanation['meaning']}",
                         f"现代反思：{explanation['application']}", f"出处：{original['source_url']}"])
    rendered.append("\n行动建议：\n" + "\n".join(f"• {item}" for item in result["advice"]))
    rendered.append("\n限制：\n" + "\n".join(f"• {item}" for item in result["limitations"]))
    return {"interpretation": "\n".join(rendered), "analysis": result, "selection": selection}


def validate_interpretation(result, ids):
    if not isinstance(result, dict) or set(result) != {"summary", "explanations", "advice", "limitations"}:
        raise ValueError("Wrong interpretation schema")
    if not isinstance(result["summary"], str) or not result["summary"].strip():
        raise ValueError("Empty summary")
    explanations = result["explanations"]
    if not isinstance(explanations, list) or len(explanations) != len(ids):
        raise ValueError("Missing passage explanations")
    seen = []
    for item in explanations:
        if not isinstance(item, dict) or set(item) != {"passage_id", "meaning", "application"}:
            raise ValueError("Wrong explanation schema")
        if any(not isinstance(item[key], str) or not item[key].strip() for key in item):
            raise ValueError("Empty explanation")
        seen.append(item["passage_id"])
    if len(set(seen)) != len(ids) or set(seen) != set(ids):
        raise ValueError("Invented or duplicate passage IDs")
    for key in ("advice", "limitations"):
        if not isinstance(result[key], list) or not result[key] or any(not isinstance(item, str) or not item.strip() for item in result[key]):
            raise ValueError("Missing advice or limitations")
