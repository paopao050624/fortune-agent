"""Verify or fetch the exact scan underlying the checked-in short excerpts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "src/fortune_agent/data/ziping_sources.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", type=Path, default=ROOT / "work/ziping-nlc-world-library.pdf")
    parser.add_argument("--fetch", action="store_true", help="下载不存在的扫描本，已有文件只做校验")
    args = parser.parse_args()
    source = json.loads(CATALOG.read_text(encoding="utf-8"))["source"]
    if args.fetch and not args.scan.exists():
        args.scan.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.scan.with_suffix(".download")
        subprocess.run([
            "curl", "-fsSL", "--connect-timeout", "8", "--max-time", "90",
            source["file_url"], "-o", str(temporary),
        ], check=True, timeout=95)
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        if digest != source["file_sha256"]:
            raise ValueError("下载文件哈希与工作底本不一致；临时文件保留，未替换底本")
        temporary.rename(args.scan)
    digest = hashlib.sha256(args.scan.read_bytes()).hexdigest()
    if digest != source["file_sha256"]:
        raise ValueError("扫描文件已变化，不能沿用现有摘录的页码与校勘状态")
    print(f"Verified {source['catalogue_identifier']}: {digest}")


if __name__ == "__main__":
    main()
