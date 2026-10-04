"""Extract ten historical stem verses from a saved Wikisource revision."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/ditiansui-tiangan.json"
OUTPUT = ROOT / "src/fortune_agent/data/bazi_sources.json"
STEMS = "甲乙丙丁戊己庚辛壬癸"


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    pages = list(payload["query"]["pages"].values())
    if len(pages) != 1 or pages[0]["title"] != "滴天髓/02":
        raise ValueError("Expected Wikisource 滴天髓/02")
    revision = pages[0]["revisions"][0]
    raw = revision["*"]
    parts = re.findall(
        r"===([甲乙丙丁戊己庚辛壬癸][木火土金水])===\s*"
        r"{{color\|red\|{{\+\|([^{}]+)}}}}", raw,
    )
    if len(parts) != 10 or {title[0] for title, _ in parts} != set(STEMS):
        raise ValueError("Expected exactly ten unique heavenly-stem verses")
    permalink = f"https://zh.wikisource.org/w/index.php?title=滴天髓/02&oldid={revision['revid']}"
    entries = []
    for title, verse in parts:
        notes = []
        if title == "丁火":
            notes.append("转录作‘抱乙而考’，未据扫描底本校勘；请勿静默改成其他字。")
        if title == "戊土":
            notes.append("转录作‘火燥囍潤’，原样保留；未据扫描底本校勘。")
        entries.append({
            "id": f"ditiansui-tiangan-{title[0]}",
            "stem": title[0],
            "heading": title,
            "work": "滴天髓辑要",
            "chapter": "天干论",
            "source_text": verse.strip(),
            "source_url": permalink,
            "locator": f"天干论 · {title}",
            "notes": notes,
        })
    catalog = {
        "source": {
            "provider": "Wikisource",
            "title": "滴天髓/02",
            "revision_id": revision["revid"],
            "revision_timestamp": revision["timestamp"],
            "url": permalink,
            "wikitext_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "edition_note": "电子转录，尚未与扫描底本或指定纸本校勘；作者归属及底本版本不在此批数据中确证。",
            "scope": "仅十天干原文，不收录页面的解释段落。",
        },
        "entries": entries,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(entries)} stem excerpts at {OUTPUT}")


if __name__ == "__main__":
    main()
