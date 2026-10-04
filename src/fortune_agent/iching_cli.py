"""Local I Ching casting with an explicit record of all six results."""

import argparse
from dataclasses import asdict
import json

from .iching import build_cast, cast_coins, load_catalog
from .iching_reading import select_passages, reference_hexagram


def main():
    parser = argparse.ArgumentParser(description="周易三枚硬币起卦原型")
    parser.add_argument("--lines", nargs=6, type=int, help="用户六次结果，从初爻到上爻，例如 7 8 7 8 7 8")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--policy", choices=("moving-count-v1", "all-moving-v1"), default="moving-count-v1")
    parser.add_argument("--interpret", help="要解读的具体问题（调用中转站）")
    parser.add_argument("--style", choices=("direct", "gentle"), default="gentle")
    parser.add_argument("--reference", type=int, help="离线查看 1–64 中一卦的完整卦辞、六爻辞及特殊辞，不起卦")
    args = parser.parse_args()
    try:
        if args.reference is not None:
            if args.lines is not None or args.interpret:
                parser.error("查阅参考库不能同时起卦或请求解读")
            entry = reference_hexagram(args.reference)
            if args.json:
                print(json.dumps(entry, ensure_ascii=False, indent=2))
            else:
                print(f"第{entry['number']}卦 {entry['name']}\n卦辞：{entry['judgment']['text']}")
                for item in [*entry["lines"], *entry["special"].values()]:
                    print(item["text"])
                print(entry["source"]["url"])
            return
        result = build_cast(args.lines) if args.lines is not None else cast_coins()
        selection = select_passages(result, args.policy)
        interpreted = None
        if args.interpret:
            from .config import ApiConfig
            from .iching_agent import interpret_cast
            try:
                from openai import OpenAI, APIError
            except ImportError:
                parser.error("请安装模型依赖：pip install -e '.[agent]'")
            config = ApiConfig.from_env()
            try:
                interpreted = interpret_cast(result, args.interpret,
                    OpenAI(api_key=config.api_key, base_url=config.base_url, timeout=90, max_retries=0),
                    config.model, args.policy, args.style)
            except APIError as exc:
                parser.exit(1, f"中转站请求失败（{type(exc).__name__}）。\n")
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps({"cast": asdict(result), "selection": selection,
                          "interpretation": interpreted["interpretation"] if interpreted else None,
                          "analysis": interpreted["analysis"] if interpreted else None}, ensure_ascii=False, indent=2))
        return
    print(f"主卦：第 {result.main_hexagram['number']} 卦 {result.main_hexagram['name']}（上{result.main_hexagram['upper_trigram']}下{result.main_hexagram['lower_trigram']}）")
    print(f"变卦：第 {result.changed_hexagram['number']} 卦 {result.changed_hexagram['name']}")
    print(f"动爻：{', '.join(map(str,result.moving_positions)) or '无'}")
    for position in range(6, 0, -1):
        value = result.lines_bottom_to_top[position - 1]
        print(f"第{position}爻 {'━━━━━━' if value % 2 else '━━  ━━'} {value}{' 动' if position in result.moving_positions else ''}")
    print(result.convention)
    print(f"卦序来源：{load_catalog()['source']['url']}")
    print(f"取辞规则：{selection['title']}\n{' '.join(selection['rule_explanation'])}")
    for item in selection["passages"]:
        print(f"{item['heading']}{'（主辞）' if item['primary'] else ''}：{item['source_text']}\n{item['source_url']}")
        for note in item["notes"]:
            print(f"转录提示：{note}")
    if interpreted:
        print(f"\n解读：\n{interpreted['interpretation']}")


if __name__ == "__main__":
    main()
