"""Fetch the fixed Wikisource revision used by the stem excerpt catalog."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ("ditiansui-tiangan.json", 11117658),
    ("ditiansui-17.json", 844366),
    ("ditiansui-12.json", 844360),
)


def main() -> None:
    for filename, revision in SOURCES:
        output = ROOT / "work" / filename
        query = urlencode({
            "action": "query", "prop": "revisions", "rvprop": "ids|timestamp|content",
            "revids": revision, "format": "json",
        })
        response = subprocess.check_output([
            "curl", "-fsSL", "--connect-timeout", "8", "--max-time", "20",
            f"https://zh.wikisource.org/w/api.php?{query}",
        ], timeout=25)
        payload = json.loads(response)
        pages = list(payload["query"]["pages"].values())
        if len(pages) != 1 or pages[0]["revisions"][0]["revid"] != revision:
            raise ValueError("Unexpected source revision")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Saved revision {revision} to {output}")


if __name__ == "__main__":
    main()
