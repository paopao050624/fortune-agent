"""Small command-line interface for inspecting tarot draws."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .tarot import draw_reading


def main() -> None:
    parser = argparse.ArgumentParser(description="塔罗抽牌原型")
    parser.add_argument("question", help="想问的问题")
    parser.add_argument("--spread", choices=("single", "three"), default="single")
    parser.add_argument(
        "--pick",
        type=int,
        nargs="+",
        metavar="N",
        help="自行选择洗牌后的位置（1 到 78）；不填则自动抽牌",
    )
    parser.add_argument("--json", action="store_true", help="输出结构化 JSON")
    parser.add_argument("--interpret", action="store_true", help="调用兼容 OpenAI 的中转站解牌")
    parser.add_argument("--style", choices=("direct", "gentle"), default="gentle")
    args = parser.parse_args()

    try:
        picks = tuple(args.pick) if args.pick is not None else None
        if args.interpret:
            from .config import ApiConfig

            config = ApiConfig.from_env()
            try:
                from openai import APIError, APIStatusError, OpenAI
            except ImportError:
                parser.error("请先安装 Agent 依赖：pip install -e '.[agent]'")
            from .agent import TarotAgent

            client = OpenAI(api_key=config.api_key, base_url=config.base_url)
            try:
                result = TarotAgent(client, config.model).read(args.question, args.spread, picks, args.style)
            except APIStatusError as exc:
                if exc.code == "model_not_found":
                    parser.exit(1, "中转站当前密钥分组没有该模型的可用通道；请检查模型授权和分组设置。\n")
                parser.exit(1, f"中转站请求失败：HTTP {exc.status_code}，错误码 {exc.code or 'unknown'}。\n")
            except APIError as exc:
                parser.exit(1, f"中转站连接失败：{type(exc).__name__}。\n")
            reading = result.reading
        else:
            reading = draw_reading(args.question, args.spread, picks)
    except ValueError as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps(asdict(result if args.interpret else reading), ensure_ascii=False, indent=2))
        return

    print(f"问题：{reading.question}")
    for item in reading.cards:
        orientation = "逆位" if item.reversed else "正位"
        print(f"{item.position}：{item.card.name}（{orientation}）")
    if args.interpret:
        print(f"\n解读：\n{result.interpretation}")
        if result.evidence:
            print("\n原书依据：")
            for item, evidence in zip(reading.cards, result.evidence, strict=True):
                source = evidence["source_url"] or "该方向暂无核对资料"
                print(f"{item.card.name}：{source}")


if __name__ == "__main__":
    main()
