"""Portable adapter for Fortune Agent; no bundled credentials or shell commands."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import runpy
import sys


MODULES = {
    "doctor": "doctor", "tarot": "cli", "daily": "daily_cli",
    "bazi": "bazi_cli", "iching": "iching_cli", "chart": "chart_cli",
    "profile": "fortune_cli",
}


def locate_project(explicit=None):
    configured = explicit or os.environ.get("FORTUNE_AGENT_HOME")
    if not configured:
        settings = Path(__file__).resolve().parents[1] / "runtime.json"
        if settings.exists():
            configured = json.loads(settings.read_text(encoding="utf-8")).get("project")
    if configured:
        root = Path(configured).expanduser().resolve()
        if not (root / "src/fortune_agent").is_dir():
            raise ValueError("项目目录不存在或缺少 src/fortune_agent")
        return root
    for start in (Path.cwd(), Path(__file__).resolve().parent):
        for root in (start, *start.parents):
            if (root / "src/fortune_agent").is_dir():
                return root
    return None  # An installed Python package is also supported.


def main():
    parser = argparse.ArgumentParser(description="Fortune Agent Skill 本地工具适配器")
    parser.add_argument("--project", help="源码项目目录；也可设 FORTUNE_AGENT_HOME")
    parser.add_argument("action", choices=(*MODULES, "library", "export"))
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        root = locate_project(args.project)
        if root:
            paths = [root / "src", *(root / "work" / name for name in
                      ("vendor", "api-vendor", "astro-vendor"))]
            sys.path[:0] = [str(path) for path in paths if path.is_dir()]
        import fortune_agent  # noqa: F401
        if args.action in MODULES:
            sys.argv = ["fortune-" + args.action, *args.arguments]
            runpy.run_module("fortune_agent." + MODULES[args.action], run_name="__main__")
        elif args.action == "library":
            sub = argparse.ArgumentParser(description="已接入原文检索")
            sub.add_argument("query")
            sub.add_argument("--module", choices=("all", "bazi", "ziwei", "tarot", "iching"), default="all")
            sub.add_argument("--limit", type=int, choices=range(1, 31), default=10)
            values = sub.parse_args(args.arguments)
            from fortune_agent.library import search_library
            print(json.dumps(search_library(values.query, values.module, values.limit), ensure_ascii=False, indent=2))
        else:
            sub = argparse.ArgumentParser(description="从工具结果 JSON 导出报告")
            sub.add_argument("input", type=Path)
            sub.add_argument("output", type=Path)
            sub.add_argument("--format", choices=("html", "svg"), default="html")
            sub.add_argument("--mode", choices=("tarot", "daily", "bazi", "iching", "ziwei", "astrology", "daily-report"), help="原始 CLI JSON 的工具类型")
            sub.add_argument("--include-private", action="store_true")
            sub.add_argument("--without-sources", action="store_true")
            values = sub.parse_args(args.arguments)
            if values.input.stat().st_size > 4 * 1024 * 1024:
                raise ValueError("输入 JSON 超过4MB")
            data = json.loads(values.input.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("输入须为工具结果 JSON 对象")
            if values.mode:
                if data.get("mode") and data["mode"] != values.mode:
                    raise ValueError("指定工具类型与输入 mode 不一致")
                if values.mode in ("ziwei", "astrology") and "chart_result" not in data:
                    data = {"mode": values.mode, "chart_result": data,
                            "interpretation": data.get("interpretation")}
                else:
                    data = {**data, "mode": values.mode}
                if values.mode == "tarot" and "reading" not in data:
                    if "cards" not in data:
                        raise ValueError("塔罗 JSON 缺少实际牌面")
                    data["reading"] = {"cards": data["cards"]}
                if values.mode == "iching" and "cast" not in data:
                    raise ValueError("卦辞参考不是起卦报告，请使用实际起卦 JSON")
                if values.mode == "iching":
                    data.setdefault("evidence", data.get("selection", {}).get("passages", []))
            from fortune_agent.report_export import export_report
            result = export_report(data, values.format, values.include_private, not values.without_sources)
            # Exclusive creation prevents silently overwriting an existing report.
            with values.output.open("x", encoding="utf-8") as stream:
                stream.write(result["content"])
            print(json.dumps({"path": str(values.output.resolve()), "mime_type": result["mime_type"]}, ensure_ascii=False))
    except (ImportError, ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        parser.exit(1, f"本地工具未完成：{exc}\n请检查项目路径及 Python/Node 依赖；未生成替代计算结果。\n")


if __name__ == "__main__":
    main()
