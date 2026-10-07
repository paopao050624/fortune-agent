#!/usr/bin/env python3
"""Install the repository's Codex Skill and bind it to this checkout."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Fortune Agent's Codex Skill")
    parser.add_argument("--destination", type=Path, help="Skill root (default: CODEX_HOME/skills/fortune-agent)")
    parser.add_argument("--force", action="store_true", help="Replace an existing installation")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    source = repo / "skills" / "fortune-agent"
    if not (source / "SKILL.md").is_file():
        parser.error(f"missing skill source: {source}")
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    destination = (args.destination or codex_home / "skills" / "fortune-agent").expanduser().resolve()
    if destination.exists():
        if not args.force:
            parser.error(f"destination already exists: {destination}; pass --force to replace it")
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "runtime.json"))
    runtime = destination / "runtime.json"
    runtime.write_text(json.dumps({"project": str(repo)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    runtime.chmod(0o600)
    print(f"Installed {destination}")
    print(f"Bound project {repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
