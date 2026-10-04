"""Local I Ching casting with an explicit record of all six results."""

import argparse
from dataclasses import asdict
import json

from .iching import build_cast, cast_coins, load_catalog


def main():
    parser = argparse.ArgumentParser(description="周易三枚硬币起卦原型")
    parser.add_argument("--lines", nargs=6, type=int, help="用户六次结果，从初爻到上爻，例如 7 8 7 8 7 8")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = build_cast(args.lines) if args.lines is not None else cast_coins()
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return
    print(f"主卦：第 {result.main_hexagram['number']} 卦 {result.main_hexagram['name']}（上{result.main_hexagram['upper_trigram']}下{result.main_hexagram['lower_trigram']}）")
    print(f"变卦：第 {result.changed_hexagram['number']} 卦 {result.changed_hexagram['name']}")
    print(f"动爻：{', '.join(map(str,result.moving_positions)) or '无'}")
    for position in range(6, 0, -1):
        value = result.lines_bottom_to_top[position - 1]
        print(f"第{position}爻 {'━━━━━━' if value % 2 else '━━  ━━'} {value}{' 动' if position in result.moving_positions else ''}")
    print(result.convention)
    print(f"卦序来源：{load_catalog()['source']['url']}")
    print("当前仅计算主卦、变卦和动爻，尚未接入卦辞、爻辞及解读。")


if __name__ == "__main__":
    main()
