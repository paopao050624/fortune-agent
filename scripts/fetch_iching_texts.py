"""Fetch source revisions for all 64 hexagrams, preserving per-page provenance."""
import json
from pathlib import Path
import subprocess
import time
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "work/iching_raw_pages.json"


def main():
    catalog = json.loads((ROOT / "src/fortune_agent/data/iching_hexagrams.json").read_text())
    corpus_path = ROOT / "src/fortune_agent/data/iching_texts.json"
    pinned = ({entry["source"]["title"]:entry["source"]["revision_id"]
               for entry in json.loads(corpus_path.read_text())["hexagrams"]} if corpus_path.exists() else {})
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    missing = [f"周易/{entry['name']}" for entry in catalog["hexagrams"]
               if f"周易/{entry['name']}" not in cache
               or (pinned and cache[f"周易/{entry['name']}"]["revid"]!=pinned[f"周易/{entry['name']}"])]
    for i in range(0, len(missing), 4):
        batch = missing[i:i + 4]
        parameters = {"action":"query","prop":"revisions","rvprop":"ids|timestamp|content","format":"json"}
        parameters["revids" if pinned else "titles"] = "|".join(str(pinned[title]) if pinned else title for title in batch)
        query = urlencode(parameters)
        try:
            raw = subprocess.check_output(["curl", "-fsSL", "--retry", "2", "--retry-all-errors",
                "--connect-timeout", "8", "--max-time", "20", f"https://zh.wikisource.org/w/api.php?{query}"], timeout=80)
            payload = json.loads(raw)
            for page in payload["query"]["pages"].values():
                if "revisions" not in page:
                    raise ValueError(f"Missing source page {page['title']}")
                if pinned and page["revisions"][0]["revid"] != pinned.get(page["title"]):
                    raise ValueError(f"Unexpected revision for {page['title']}")
                cache[page["title"]] = page["revisions"][0]
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n")
            print(f"Cached {len(cache)}/64 pages", flush=True)
        except (subprocess.SubprocessError, ValueError, KeyError) as exc:
            print(f"Batch failed {batch}: {type(exc).__name__}", flush=True)
        time.sleep(1)
    if len(cache) != 64:
        raise SystemExit(f"Incomplete corpus: {len(cache)}/64; rerun to fetch missing pages")
    if pinned and any(cache[title]["revid"] != revision for title,revision in pinned.items()):
        raise SystemExit("Pinned revisions are not all present; rerun to complete the corpus")


if __name__ == "__main__":
    main()
