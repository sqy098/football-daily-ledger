#!/usr/bin/env python3
"""Settle Asian handicap and Asian total picks from the frozen line."""

from __future__ import annotations

import argparse
import json
import math
import re
from typing import Iterable

RESULT_MAP = {
    ("win",): "赢",
    ("push",): "走水",
    ("loss",): "输",
    ("win", "win"): "赢",
    ("win", "push"): "赢半",
    ("push", "win"): "赢半",
    ("push", "push"): "走水",
    ("push", "loss"): "输半",
    ("loss", "push"): "输半",
    ("loss", "loss"): "输",
}

CHINESE_LINES = {
    "平手": 0.0,
    "平/半": 0.25,
    "平半": 0.25,
    "半球": 0.5,
    "半/一": 0.75,
    "半一": 0.75,
    "一球": 1.0,
    "一/球半": 1.25,
    "一球/球半": 1.25,
    "球半": 1.5,
    "球半/两": 1.75,
    "球半/两球": 1.75,
    "两球": 2.0,
    "两/两球半": 2.25,
    "两球/两球半": 2.25,
    "两球半": 2.5,
    "两球半/三": 2.75,
    "三球": 3.0,
}


def _float(value: str) -> float:
    value = value.strip().replace("−", "-").replace("＋", "+")
    if value in CHINESE_LINES:
        return CHINESE_LINES[value]
    return float(value)


def parse_line(line: str | float) -> list[float]:
    if isinstance(line, (int, float)):
        value = float(line)
        return split_quarter(value)

    text = str(line).strip()
    # Explicit split, e.g. 2/2.5 or -0.5/-1
    if "/" in text and text not in CHINESE_LINES:
        parts = [p.strip() for p in text.split("/")]
        if len(parts) == 2:
            return [_float(parts[0]), _float(parts[1])]
    return split_quarter(_float(text))


def split_quarter(value: float) -> list[float]:
    scaled = round(value * 4)
    if not math.isclose(value * 4, scaled, abs_tol=1e-7):
        raise ValueError("line must be in 0.25 increments")
    # Odd quarters split into adjacent half-step lines.
    if abs(scaled) % 2 == 1:
        lower = math.floor(value * 2) / 2
        upper = math.ceil(value * 2) / 2
        return [lower, upper]
    return [value]


def leg_result(value: float, tolerance: float = 1e-9) -> str:
    if value > tolerance:
        return "win"
    if value < -tolerance:
        return "loss"
    return "push"


def combine(results: Iterable[str]) -> str:
    key = tuple(results)
    if key in RESULT_MAP:
        return RESULT_MAP[key]
    raise ValueError(f"unsupported result combination: {key}")


def settle_handicap(pick: str, line: str | float, home_goals: int, away_goals: int) -> dict:
    pick = pick.lower()
    if pick not in {"home", "away"}:
        raise ValueError("pick must be home or away")
    if min(home_goals, away_goals) < 0:
        raise ValueError("goals cannot be negative")

    for_goals, against_goals = (
        (home_goals, away_goals) if pick == "home" else (away_goals, home_goals)
    )
    components = parse_line(line)
    legs = [leg_result(for_goals + component - against_goals) for component in components]
    return {
        "market": "handicap",
        "pick": pick,
        "line_components": components,
        "score": f"{home_goals}-{away_goals}",
        "leg_results": legs,
        "result": combine(legs),
    }


def settle_total(pick: str, line: str | float, home_goals: int, away_goals: int) -> dict:
    pick = pick.lower()
    if pick not in {"over", "under"}:
        raise ValueError("pick must be over or under")
    if min(home_goals, away_goals) < 0:
        raise ValueError("goals cannot be negative")

    total = home_goals + away_goals
    components = parse_line(line)
    if pick == "over":
        legs = [leg_result(total - component) for component in components]
    else:
        legs = [leg_result(component - total) for component in components]
    return {
        "market": "total",
        "pick": pick,
        "line_components": components,
        "score": f"{home_goals}-{away_goals}",
        "total_goals": total,
        "leg_results": legs,
        "result": combine(legs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="market", required=True)

    handicap = sub.add_parser("handicap")
    handicap.add_argument("--pick", choices=["home", "away"], required=True)
    handicap.add_argument("--line", required=True)
    handicap.add_argument("--home-goals", type=int, required=True)
    handicap.add_argument("--away-goals", type=int, required=True)

    total = sub.add_parser("total")
    total.add_argument("--pick", choices=["over", "under"], required=True)
    total.add_argument("--line", required=True)
    total.add_argument("--home-goals", type=int, required=True)
    total.add_argument("--away-goals", type=int, required=True)

    args = parser.parse_args()
    try:
        if args.market == "handicap":
            result = settle_handicap(args.pick, args.line, args.home_goals, args.away_goals)
        else:
            result = settle_total(args.pick, args.line, args.home_goals, args.away_goals)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
