"""Three-coin casting and main/changed hexagrams, in bottom-to-top order."""

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
import json
from random import SystemRandom


@lru_cache(maxsize=1)
def load_catalog():
    return json.loads(files("fortune_agent").joinpath("data/iching_hexagrams.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class CoinCast:
    lines_bottom_to_top: tuple[int, ...]
    coins_bottom_to_top: tuple[tuple[int, ...], ...] | None
    moving_positions: tuple[int, ...]
    main_hexagram: dict
    changed_hexagram: dict
    input_method: str
    convention: str = "三枚硬币法：每枚正面计 3、反面计 2；由下至上记录六爻；6 老阴、7 少阳、8 少阴、9 老阳；6 与 9 翻转形成变卦。"


def build_cast(lines, coins=None) -> CoinCast:
    if not isinstance(lines, (tuple, list)) or len(lines) != 6:
        raise ValueError("需要六次结果，按初爻到上爻顺序填写")
    if any(type(value) is not int or value not in (6, 7, 8, 9) for value in lines):
        raise ValueError("每爻必须为整数 6、7、8 或 9")
    bits = "".join(str(value % 2) for value in lines)
    changed = "".join(str(1 - value % 2 if value in (6, 9) else value % 2) for value in lines)
    lookup = {entry["bits_bottom_to_top"]: entry for entry in load_catalog()["hexagrams"]}
    return CoinCast(tuple(lines), coins, tuple(i + 1 for i, value in enumerate(lines) if value in (6, 9)),
                    lookup[bits], lookup[changed], "程序模拟三枚硬币" if coins else "用户提供六次硬币和数")


def cast_coins(rng=None) -> CoinCast:
    source = rng if rng is not None else SystemRandom()
    coins = tuple(tuple(2 + source.randrange(2) for _ in range(3)) for _ in range(6))
    return build_cast(tuple(sum(throw) for throw in coins), coins)
