"""Extract only the 易經 block, preserving variants and fixed revisions."""
import hashlib
from html import unescape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BLUE = re.compile(r'<span\s+style=["\']color\s*:\s*blue["\']\s*>(.*?)(?:</span>|(?=\n\*)|$)', re.S)


def clean(raw, notes):
    def variant(match):
        fields = match.group(1).split("|")
        notes.append(f"电子转录异文：采用‘{fields[0]}’，另列‘{'、'.join(fields[1:])}’；未作底本校勘。")
        return fields[0]
    raw = re.sub(r"{{另\|([^{}]+)}}", variant, raw)
    def footnote(match):
        notes.append("转录注记：" + match.group(1))
        return ""
    raw = re.sub(r"{{\*\|([^{}]+)}}", footnote, raw)
    raw = re.sub(r"-\{([^{}]+)\}-", lambda m: m.group(1), raw)
    raw = re.sub(r"<[^>]+>", "", raw).replace("'''", "").replace("''", "")
    raw = unescape(raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if "{{" in raw or "[[" in raw or not raw:
        raise ValueError(f"Unparsed or empty source: {raw}")
    return raw


def extract(hexagram, revision):
    raw = revision["*"]
    # Stop at the first commentary block; never relabel 彖/象/文言 as 经文.
    end = re.search(r"^\*[^\n]*(?:彖曰|象曰)", raw, re.M)
    block = raw[:end.start()] if end else raw
    start = re.search(r"^\*#", block, re.M)
    if start is None:
        raise ValueError(f"No line text for {hexagram['name']}")
    judgment_raw = BLUE.findall(block[:start.start()])
    judgment_raw = [value for value in judgment_raw if "易經" not in value]
    notes = []
    judgment = " ".join(clean(value, notes) for value in judgment_raw)
    if not judgment:
        raise ValueError(f"Missing judgment for {hexagram['name']}")
    lines, special = [], {}
    for body in BLUE.findall(block[start.start():]):
        item_notes = []
        value = clean(body, item_notes)
        match = re.match(r"(初[九六]|[九六][二三四五]|上[九六]|用[九六])[:：，,](.+)", value)
        if not match:
            raise ValueError(f"Unexpected line: {hexagram['name']} {value}")
        label = match.group(1)
        item = {"label": label, "text": value, "notes": item_notes}
        if label.startswith("用"):
            special[label] = item
        else:
            position = 1 if label.startswith("初") else 6 if label.startswith("上") else "二三四五".index(label[1]) + 2
            item["position"] = position
            item["polarity"] = "阳" if "九" in label else "阴"
            lines.append(item)
    if sorted(item["position"] for item in lines) != list(range(1, 7)):
        raise ValueError(f"Incomplete six lines: {hexagram['name']}")
    lines.sort(key=lambda item: item["position"])
    for item, bit in zip(lines, hexagram["bits_bottom_to_top"], strict=True):
        if (item["polarity"] == "阳") != (bit == "1"):
            raise ValueError(f"Line polarity conflict: {hexagram['name']} {item['label']}")
    return {"number": hexagram["number"], "name": hexagram["name"],
            "judgment": {"text": judgment, "notes": notes}, "lines": lines, "special": special,
            "source": {"title": f"周易/{hexagram['name']}", "revision_id": revision["revid"],
                       "revision_timestamp": revision["timestamp"],
                       "url": f"https://zh.wikisource.org/w/index.php?title=周易/{hexagram['name']}&oldid={revision['revid']}",
                       "wikitext_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                       "format_notes": (["原页部分 HTML span 未闭合，按经文列表边界解析，保留原字。"]
                                        if block.count("<span") != block.count("</span>") else [])}}


def main():
    cache = json.loads((ROOT / "work/iching_raw_pages.json").read_text())
    hexagrams = json.loads((ROOT / "src/fortune_agent/data/iching_hexagrams.json").read_text())["hexagrams"]
    entries = [extract(h, cache[f"周易/{h['name']}"]) for h in sorted(hexagrams, key=lambda h: h["number"])]
    if len(entries) != 64 or sum(len(e["lines"]) for e in entries) != 384:
        raise ValueError("Corpus must contain 64 judgments and 384 line texts")
    if set(entries[0]["special"]) != {"用九"} or set(entries[1]["special"]) != {"用六"}:
        raise ValueError("Missing Qian/Kun special texts")
    if any(e["special"] for e in entries[2:]):
        raise ValueError("Unexpected special text")
    corpus = {"edition_note": "Wikisource 电子转录，各页固定修订；未与指定纸本或扫描底本逐字校勘，不提供纸本页码。保留转录主字与句读，异文和注记另列。",
              "scope": "64 卦卦辞、384 条爻辞、乾用九与坤用六；不含彖、象、文言或现代译注。",
              "hexagrams": entries}
    output = ROOT / "src/fortune_agent/data/iching_texts.json"
    output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Built complete corpus: 64 judgments, 384 lines, 2 special passages")


if __name__ == "__main__":
    main()
