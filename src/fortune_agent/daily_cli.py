"""Command-line entry point for one-card daily tarot."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .daily import daily_draw
from .daily_service import get_daily


def main() -> None:
    parser = argparse.ArgumentParser(description="每日一张塔罗")
    parser.add_argument("--profile", required=True, help="自己选择的固定代号，不建议使用姓名")
    parser.add_argument("--timezone", required=True, help="IANA 时区，例如 Asia/Shanghai")
    parser.add_argument("--interpret", action="store_true", help="调用中转站并缓存当天首次解读")
    parser.add_argument("--style", choices=("direct", "gentle"), default="gentle")
    parser.add_argument("--cache", type=Path, default=Path("work/daily.sqlite3"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    instant = datetime.now(timezone.utc)

    try:
        if args.interpret:
            from .daily_store import DailyStore

            draw = daily_draw(args.profile, args.timezone, instant)
            store = DailyStore(args.cache)
            if store.get(draw) is not None:
                result = get_daily(args.profile, args.timezone, store=store, at=instant)
            else:
                from .config import ApiConfig

                config = ApiConfig.from_env()
                try:
                    from openai import APIError, APIStatusError, OpenAI
                except ImportError:
                    parser.error("请先安装 Agent 依赖：pip install -e '.[agent]'")
                client = OpenAI(api_key=config.api_key, base_url=config.base_url)
                try:
                    result = get_daily(
                        args.profile, args.timezone, store=store,
                        client=client, model=config.model, style=args.style, at=instant,
                    )
                except APIStatusError as exc:
                    parser.exit(1, f"中转站请求失败：HTTP {exc.status_code}，错误码 {exc.code or 'unknown'}。\n")
                except APIError as exc:
                    parser.exit(1, f"中转站连接失败：{type(exc).__name__}。\n")
        else:
            result = get_daily(args.profile, args.timezone, at=instant)
    except ValueError as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return

    card = result.reading.cards[0]
    print(f"日期：{result.day}（{result.timezone}）")
    print(f"今日提示：{card.card.name}（{'逆位' if card.reversed else '正位'}）")
    if result.interpretation is not None:
        style_label = "直接" if result.style == "direct" else "温和"
        print(f"回答风格：{style_label}")
        print(f"\n解读：\n{result.interpretation}")
        source = result.evidence[0]["source_url"] if result.evidence else None
        print(f"\n原书依据：{source or '该方向暂无核对资料'}")
        if result.cached:
            print("（读取当天已保存的解读）")


if __name__ == "__main__":
    main()
