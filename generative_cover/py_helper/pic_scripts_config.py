#!/usr/bin/env uv run
"""Sync [pic_scripts] entries in config.toml with scripts in pic_scripts/."""

import tomllib
from pathlib import Path


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
    if "pic_scripts" in data and "pic_scripts" not in section_order:
        section_order.append("pic_scripts")

    for idx, section in enumerate(section_order):
        table = data.get(section, {})
        if not isinstance(table, dict):
            continue
        lines.append(f"[{section}]")
        keys = sorted(table.keys())
        for key in keys:
            lines.append(f"    {key} = {_format_value(table[key])}")
        if idx != len(section_order) - 1:
            lines.append("")
            lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config_path = root / "config.toml"
    scripts_dir = root / "pic_scripts"

    scripts = sorted(
        p.stem
        for p in scripts_dir.iterdir()
        if p.is_file() and p.suffix == ".py" and not p.name.startswith("_")
    )

    config_text = config_path.read_text(encoding="utf-8")
    data = tomllib.loads(config_text)

    pic_scripts = data.get("pic_scripts")
    if pic_scripts is None:
        pic_scripts = {}
    if not isinstance(pic_scripts, dict):
        raise TypeError("[pic_scripts] must be a table in config.toml")

    for name in scripts:
        pic_scripts.setdefault(name, False)

    for key in list(pic_scripts.keys()):
        if key not in scripts:
            del pic_scripts[key]

    data["pic_scripts"] = pic_scripts

    _write_toml(data, config_path)


if __name__ == "__main__":
    main()
