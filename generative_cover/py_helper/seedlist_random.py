#!/usr/bin/env uv run
"""Generate a random seedlist and store it in config.toml."""

import argparse
import random
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from py_helper import variables  # noqa: E402


def _format_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, list):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    raise TypeError(f"Unsupported TOML value: {type(value).__name__}")


def _write_toml(data: dict, path: Path) -> None:
    lines: list[str] = []

    root_items = [(k, v) for k, v in data.items() if not isinstance(v, dict)]
    for key, value in root_items:
        lines.append(f"{key} = {_format_value(value)}")
    if root_items:
        lines.append("")

    section_order = [k for k, v in data.items() if isinstance(v, dict)]
    for idx, section in enumerate(section_order):
        table = data.get(section, {})
        if not isinstance(table, dict):
            continue
        lines.append(f"[{section}]")
        for key in sorted(table.keys()):
            lines.append(f"    {key} = {_format_value(table[key])}")
        if idx != len(section_order) - 1:
            lines.append("")
            lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a random seed list.")
    parser.add_argument("count", type=int, help="How many seeds to generate.")
    parser.add_argument(
        "--min",
        dest="min_value",
        type=int,
        default=0,
        help="Minimum random value (inclusive).",
    )
    parser.add_argument(
        "--max",
        dest="max_value",
        type=int,
        default=9999,
        help="Maximum random value (inclusive).",
    )
    args = parser.parse_args()

    if args.count <= 0:
        raise ValueError("count must be a positive integer")
    if args.min_value > args.max_value:
        raise ValueError("--min must be <= --max")

    root = Path(__file__).resolve().parents[1]
    config_path = root / variables.CONFIG

    with config_path.open("rb") as f:
        config = tomllib.load(f)

    style = config.get("style")
    if style is None:
        style = {}
    if not isinstance(style, dict):
        raise TypeError("[style] must be a table in config.toml")

    rng = random.Random()
    style["seedlist"] = [
        rng.randint(args.min_value, args.max_value) for _ in range(args.count)
    ]
    config["style"] = style

    _write_toml(config, config_path)


if __name__ == "__main__":
    main()
