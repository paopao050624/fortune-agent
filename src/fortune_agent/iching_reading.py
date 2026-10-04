"""Full reference corpus and deterministic, versioned passage selection."""
from dataclasses import asdict
from functools import lru_cache
from importlib.resources import files
import hashlib
import json

from .iching import CoinCast, load_catalog


@lru_cache(maxsize=1)
def load_texts():
    corpus = json.loads(files("fortune_agent").joinpath("data/iching_texts.json").read_text(encoding="utf-8"))
    entries = corpus["hexagrams"]
    if len(entries) != 64 or {e["number"] for e in entries} != set(range(1, 65)):
        raise ValueError("周易参考库必须包含 64 个唯一卦辞")
    index = {e["number"]: e for e in load_catalog()["hexagrams"]}
    for entry in entries:
        if entry["name"] != index[entry["number"]]["name"] or not entry["judgment"]["text"]:
            raise ValueError("参考库卦名或卦辞与卦序不一致")
        if len(entry["lines"]) != 6 or [line["position"] for line in entry["lines"]] != list(range(1, 7)):
            raise ValueError("周易参考库必须包含每卦六条有序爻辞")
        for line, bit in zip(entry["lines"], index[entry["number"]]["bits_bottom_to_top"], strict=True):
            if not line["text"] or (line["polarity"] == "阳") != (bit == "1"):
                raise ValueError("爻辞阴阳或内容无效")
        expected_special = {"用九"} if entry["number"] == 1 else {"用六"} if entry["number"] == 2 else set()
        if set(entry["special"]) != expected_special or any(not item["text"] for item in entry["special"].values()):
            raise ValueError("乾坤特殊辞不完整或出现额外特殊辞")
    return corpus


@lru_cache(maxsize=1)
def load_rules():
    return json.loads(files("fortune_agent").joinpath("data/iching_rules.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def reference_sha256():
    raw = json.dumps({"texts": load_texts(), "rules": load_rules()}, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def passage(number, kind, position=None):
    corpus = load_texts()
    entry = next(e for e in corpus["hexagrams"] if e["number"] == number)
    if kind == "judgment":
        body = entry["judgment"]
        label = "卦辞"
    elif kind == "line":
        body = entry["lines"][position - 1]
        label = body["label"]
    else:
        body = entry["special"][kind]
        label = kind
    return {"id": f"iching-{number}-{kind}" + (f"-{position}" if position else ""),
            "number": number, "name": entry["name"], "kind": kind, "position": position,
            "heading": f"{entry['name']} · {label}", "locator": f"周易/{entry['name']} · {label}",
            "source_text": body["text"], "source_url": entry["source"]["url"],
            "notes": body["notes"] + entry["source"]["format_notes"],
            "edition_note": corpus["edition_note"]}


def select_passages(cast: CoinCast, policy="moving-count-v1"):
    rules = load_rules()
    if policy not in rules["policies"]:
        raise ValueError("未知周易取辞规则")
    main, changed = cast.main_hexagram["number"], cast.changed_hexagram["number"]
    moving = list(cast.moving_positions)
    count = len(moving)
    selected = []
    def add(number, kind, position=None, primary=False):
        selected.append({**passage(number, kind, position), "primary": primary})
    if policy == "all-moving-v1":
        add(main, "judgment")
        for position in moving:
            add(main, "line", position)
        if moving:
            add(changed, "judgment")
        if count == 6 and main in (1, 2):
            add(main, "用九" if main == 1 else "用六")
        explanation = rules["policies"][policy]["rules"]
    else:
        explanation = [rules["policies"][policy]["rules"][count]]
        if count == 0:
            add(main, "judgment", primary=True)
        elif count == 1:
            add(main, "line", moving[0], True)
        elif count == 2:
            for position in moving:
                add(main, "line", position, position == max(moving))
        elif count == 3:
            add(main, "judgment")
            add(changed, "judgment")
        elif count in (4, 5):
            static = [position for position in range(1, 7) if position not in moving]
            for position in static:
                add(changed, "line", position, position == min(static))
        elif main in (1, 2):
            add(main, "用九" if main == 1 else "用六", primary=True)
        else:
            add(changed, "judgment", primary=True)
    return {"policy": policy, "title": rules["policies"][policy]["title"],
            "attribution": rules["policies"][policy]["attribution"],
            "moving_count": count, "rule_explanation": explanation,
            "passages": selected, "reference_sha256": reference_sha256()}


def reference_hexagram(number):
    if type(number) is not int or not 1 <= number <= 64:
        raise ValueError("卦序须为 1–64")
    entry = next(e for e in load_texts()["hexagrams"] if e["number"] == number)
    return {**entry, "edition_note": load_texts()["edition_note"]}
