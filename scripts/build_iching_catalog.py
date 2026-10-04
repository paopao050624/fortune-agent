"""Extract the 64-combination lookup table from a saved Wikisource revision."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIGRAMS = (("乾", "111"), ("兌", "110"), ("離", "101"), ("震", "100"),
            ("巽", "011"), ("坎", "010"), ("艮", "001"), ("坤", "000"))


def main():
    payload = json.loads((ROOT / "work/zhouyi-index.json").read_text(encoding="utf-8"))
    page = next(iter(payload["query"]["pages"].values()))
    revision = page["revisions"][0]
    if page["title"] != "周易" or revision["revid"] != 7907208:
        raise ValueError("Expected 周易 fixed revision 7907208; review source changes before rebuilding")
    text = revision["*"]
    table = text.split("== 六十四卦速查表 ==", 1)[1].split("== 上下經卦名次序 ==", 1)[0]
    records = re.findall(r"([䷀-䷿])\s*\[\[/([^|\]]+)", table)
    if len(records) != 64 or len({symbol for symbol, _ in records}) != 64:
        raise ValueError("Expected a complete, unique 64-hexagram table")
    entries = []
    for index, (symbol, name) in enumerate(records):
        lower, lower_bits = TRIGRAMS[index // 8]
        upper, upper_bits = TRIGRAMS[index % 8]
        entries.append({"number": ord(symbol) - 0x4DC0 + 1, "name": name, "symbol": symbol,
                        "lower_trigram": lower, "upper_trigram": upper,
                        "bits_bottom_to_top": lower_bits + upper_bits,
                        "source_url": f"https://zh.wikisource.org/wiki/周易/{name}"})
    output = {"source": {"title": "周易 · 六十四卦速查表", "revision_id": revision["revid"],
                         "url": f"https://zh.wikisource.org/w/index.php?title=周易&oldid={revision['revid']}",
                         "scope": "仅卦名、上下卦及卦序，不含卦辞、爻辞或变爻解读规则。"},
              "hexagrams": entries}
    (ROOT / "src/fortune_agent/data/iching_hexagrams.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Built 64 hexagram combinations")


if __name__ == "__main__":
    main()
