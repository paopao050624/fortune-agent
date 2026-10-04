"""Fetch Wikisource page transcriptions for local source inspection."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from urllib.parse import quote, urlencode

API = "https://en.wikisource.org/w/api.php"
OUTPUT = Path(__file__).resolve().parents[1] / "work/waite_pages.json"
PAGES = [*range(183, 295, 2), *range(296, 301)]


def curl_json(url: str) -> dict:
    response = subprocess.check_output([
        "curl", "-fsSL", "--retry", "2", "--retry-delay", "1", "--retry-all-errors",
        "--max-time", "20", url,
    ], stderr=subprocess.DEVNULL, timeout=70)
    return json.loads(response)


def fetch_batch(numbers: list[int]) -> dict[str, str]:
    titles = "|".join(f"Page:The_Pictorial_Key_to_the_Tarot.pdf/{n}" for n in numbers)
    query = urlencode({
        "action": "query", "prop": "revisions", "rvprop": "content",
        "titles": titles, "format": "json",
    })
    try:
        payload = curl_json(f"{API}?{query}")
    except (OSError, subprocess.SubprocessError):
        if len(numbers) != 1:
            raise
        title = quote(f"Page:The_Pictorial_Key_to_the_Tarot.pdf/{numbers[0]}", safe="")
        page = curl_json(f"https://api.wikimedia.org/core/v1/wikisource/en/page/{title}")
        return {str(numbers[0]): page["source"]}
    result = {}
    for page in payload["query"]["pages"].values():
        if "missing" in page:
            raise RuntimeError(f"Missing Wikisource page: {page['title']}")
        number = int(page["title"].rsplit("/", 1)[1])
        result[str(number)] = page["revisions"][0]["*"]
    if len(result) != len(numbers):
        raise RuntimeError(f"Expected {len(numbers)} pages, got {len(result)}")
    return result


def main() -> None:
    batches = [[number] for number in PAGES]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pages = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
    for batch in batches:
        remaining = [n for n in batch if str(n) not in pages]
        if not remaining:
            continue
        try:
            pages.update(fetch_batch(remaining))
            OUTPUT.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
            have = sum(str(number) in pages for number in PAGES)
            print(f"Fetched {have}/{len(PAGES)} pages", flush=True)
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            print(f"Skipped {remaining}: {type(exc).__name__}", flush=True)
        time.sleep(1)
    missing = [number for number in PAGES if str(number) not in pages]
    print(f"Saved {OUTPUT}; missing {len(missing)} pages: {missing}")


if __name__ == "__main__":
    main()
