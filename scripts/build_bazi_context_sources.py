"""Extract the short main verses, excluding mixed commentary."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "src/fortune_agent/data/bazi_context_sources.json"
CHAPTERS = (("17", "月令论", "month-principle"), ("12", "衰旺论", "strength-principle"))


def main() -> None:
    entries = []
    for number, chapter, entry_id in CHAPTERS:
        payload = json.loads((ROOT / f"work/ditiansui-{number}.json").read_text(encoding="utf-8"))
        pages = list(payload["query"]["pages"].values())
        if len(pages) != 1 or pages[0]["title"] != f"滴天髓/{number}":
            raise ValueError(f"Unexpected source chapter {number}")
        revision = pages[0]["revisions"][0]
        raw = revision["*"]
        verses = re.findall(r"{{color\|red\|{{\+\|([^{}]+)}}}}", raw)
        if len(verses) != 1:
            raise ValueError(f"Expected one main verse in {chapter}")
        entries.append({
            "id": f"ditiansui-{entry_id}",
            "work": "滴天髓辑要", "chapter": chapter, "heading": chapter,
            "locator": chapter + " · 原文短段", "source_text": verses[0].strip(),
            "source_url": f"https://zh.wikisource.org/w/index.php?title=滴天髓/{number}&oldid={revision['revid']}",
            "revision_id": revision["revid"], "revision_timestamp": revision["timestamp"],
            "wikitext_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "edition_note": "电子转录，尚未与指定纸本或扫描底本校勘；仅提取原文，不收录混排注解。",
            "notes": [],
            "retrieval_basis": "所有四柱解读共用的方法性参考，不能据此自动判定用神或旺衰",
        })
    OUTPUT.write_text(json.dumps({"entries": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(entries)} contextual excerpts at {OUTPUT}")


if __name__ == "__main__":
    main()
