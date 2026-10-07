"""Offline smoke test for the checked-in Codex Skill adapter."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "skills/fortune-agent/scripts/run_fortune.py"


def run(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        [sys.executable, str(RUNNER), "--project", str(ROOT), *args],
        cwd=cwd, capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError(f"{' '.join(args)} failed:\n{result.stderr}")
    return result.stdout


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="fortune-skill-smoke-") as temp:
        work = Path(temp)
        assert json.loads(run("tarot", "论文安排", "--spread", "three", "--json", cwd=work))["cards"]
        bazi = work / "bazi.json"
        bazi.write_text(run("bazi", "--pillars", "己卯 丙子 戊午 戊午", "--complete", "--json", cwd=work), encoding="utf-8")
        assert json.loads(run("library", "财格", "--module", "bazi", "--limit", "2", cwd=work))["selected_count"]
        output = work / "report.html"
        run("export", str(bazi), str(output), "--mode", "bazi", cwd=work)
        assert output.read_text(encoding="utf-8").startswith("<!doctype html>")
    print("Codex Skill smoke test passed")


if __name__ == "__main__":
    main()
