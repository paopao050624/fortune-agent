"""Build a complete, page-cited tarot meaning catalog from fetched transcriptions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/waite_pages.json"
OUTPUT = ROOT / "src/fortune_agent/data/waite_meanings.json"
MINOR_PAGES = range(183, 295, 2)
MAJOR_PAGES = range(296, 301)
SUIT_IDS = {"WANDS": 1, "CUPS": 2, "SWORDS": 3, "PENTACLES": 4}
RANK_IDS = {
    "ACE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5,
    "SIX": 6, "SEVEN": 7, "EIGHT": 8, "NINE": 9, "TEN": 10,
    "PAGE": 11, "KNIGHT": 12, "QUEEN": 13, "KING": 14,
}
MAJOR_NAMES = {
    0: "Zero. The Fool", 1: "The Magician", 2: "The High Priestess",
    3: "The Empress", 4: "The Emperor", 5: "The Hierophant",
    6: "The Lovers", 7: "The Chariot", 8: "Fortitude",
    9: "The Hermit", 10: "Wheel of Fortune", 11: "Justice",
    12: "The Hanged Man", 13: "Death", 14: "Temperance",
    15: "The Devil", 16: "The Tower", 17: "The Star",
    18: "The Moon", 19: "The Sun", 20: "The Last Judgment",
    21: "The World",
}
MINOR_HEADING = re.compile(
    r"'''(?:THE SUIT OF )?(WANDS|CUPS|SWORDS|PENTACLES)<br>"
    r"(ACE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|PAGE|KNIGHT|QUEEN|KING)'''",
    re.IGNORECASE,
)
MAJOR_HEADING = re.compile(r"(?:(\d+)\.\s*)?{{sc\|([^{}]+)}}\.\s*—")


def clean(value: str) -> str:
    value = re.sub(r"<noinclude>.*?</noinclude>", " ", value, flags=re.DOTALL)
    value = re.sub(r"{{hws\|([^|}]+)\|[^}]+}}", r"\1", value)
    value = re.sub(r"{{hwe\|([^|}]+)\|[^}]+}}", r"\1", value)
    value = re.sub(r"{{[^{}]*}}", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("''", "").replace("@@PAGE_", " @@PAGE_")
    value = re.sub(r"@@PAGE_\d+@@", " ", value)
    value = re.sub(r"([A-Za-z])-\s+([a-z])", r"\1\2", value)
    value = value.replace("bewray ment", "bewrayment")
    return re.sub(r"\s+", " ", value).strip(" .\n")


def record(upright: str, reversed_text: str | None, page: int) -> dict[str, object]:
    clean_upright = clean(upright)
    clean_reversed = clean(reversed_text) if reversed_text is not None else None
    if not clean_upright or (reversed_text is not None and not clean_reversed):
        raise ValueError(f"Empty meaning on page {page}")
    return {
        "upright": clean_upright,
        "reversed": clean_reversed,
        "source_page": page,
        "source_url": f"https://en.wikisource.org/wiki/Page:The_Pictorial_Key_to_the_Tarot.pdf/{page}",
    }


def parse_minor(pages: dict[str, str], allow_partial: bool) -> dict[str, dict[str, object]]:
    meanings = {}
    for page in MINOR_PAGES:
        if str(page) not in pages and allow_partial:
            continue
        raw = pages[str(page)]
        heading = MINOR_HEADING.search(raw)
        if heading is None:
            raise ValueError(f"Missing minor card heading on page {page}")
        suit, rank = (part.upper() for part in heading.groups())
        card_id = f"{SUIT_IDS[suit]}-{RANK_IDS[rank]:02d}"
        match = re.search(
            r"''Divinatory Meanings:''\s*(.*?)(?:\s*''Reversed[:;]''\s*(.*?))?(?:{{nop}}|<noinclude>|$)",
            raw, re.DOTALL,
        )
        if match is None:
            raise ValueError(f"Missing upright meaning for {card_id} on page {page}")
        if card_id in meanings:
            raise ValueError(f"Duplicate card: {card_id}")
        meanings[card_id] = record(match.group(1), match.group(2), page)
    return meanings


def parse_major(pages: dict[str, str]) -> dict[str, dict[str, object]]:
    text = "\n".join(f"@@PAGE_{page}@@\n{pages[str(page)]}" for page in MAJOR_PAGES)
    headings = list(MAJOR_HEADING.finditer(text))
    meanings = {}
    for index, heading in enumerate(headings):
        name = heading.group(2).strip()
        number = 0 if name == "Zero. The Fool" else int(heading.group(1))
        if MAJOR_NAMES.get(number) != name:
            raise ValueError(f"Unexpected major card {number}: {name}")
        end = headings[index + 1].start() if index + 1 < len(headings) else text.index("It will be seen", heading.end())
        body = text[heading.end():end]
        if "''Reversed:''" not in body:
            raise ValueError(f"Missing reversed meaning for major-{number:02d}")
        upright, reversed_text = body.split("''Reversed:''", 1)
        page = int(re.findall(r"@@PAGE_(\d+)@@", text[:heading.start()])[-1])
        card_id = f"major-{number:02d}"
        meanings[card_id] = record(upright, reversed_text, page)
    return meanings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    pages = json.loads(SOURCE.read_text(encoding="utf-8"))
    missing = [page for page in [*MINOR_PAGES, *MAJOR_PAGES] if str(page) not in pages]
    if missing and not args.allow_partial:
        raise ValueError(f"Missing source pages: {missing}")
    if any(str(page) not in pages for page in MAJOR_PAGES):
        raise ValueError("Major Arcana source pages 296-300 are required")
    meanings = {**parse_minor(pages, args.allow_partial), **parse_major(pages)}
    if len(meanings) != 78 and not args.allow_partial:
        raise ValueError(f"Expected 78 cards, got {len(meanings)}")
    output = {
        "source": {
            "id": "waite-pictorial-key-wikisource",
            "title": "The Pictorial Key to the Tarot, Part III",
            "author": "A. E. Waite",
            "url": "https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot/Part_3",
        },
        "coverage": {"card_count": len(meanings), "complete": len(meanings) == 78, "missing_source_pages": missing},
        "cards": dict(sorted(meanings.items())),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(meanings)} cited card meanings at {OUTPUT}")


if __name__ == "__main__":
    main()
