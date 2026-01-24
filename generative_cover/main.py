#!/usr/bin/env uv run
"""Run enabled pic_scripts and post-process output SVGs."""

import os
import subprocess
import tomllib
from pathlib import Path

from py_helper import variables
from py_helper.file_utils import rename_file, svg_to_png


def main() -> None:
    root: Path = Path(__file__).resolve().parent
    config_path: Path = root / variables.CONFIG
    output_dir: Path = root / variables.OUTPUT
    scripts_dir: Path = root / variables.PIC_SCRIPTS

    output_dir.mkdir(parents=True, exist_ok=True)

    with config_path.open("rb") as f:
        config: dict = tomllib.load(f)

    seed_list = config.get("style", {}).get("seedlist")
    if seed_list is None:
        raise ValueError("Missing [style].seedlist in config.toml")
    if not isinstance(seed_list, list) or not seed_list:
        raise ValueError("[style].seedlist must be a non-empty list in config.toml")
    seeds = [int(value) for value in seed_list]

    pic_scripts: dict = config.get("pic_scripts", {})
    if not isinstance(pic_scripts, dict):
        raise TypeError("[pic_scripts] must be a table in config.toml")

    for script_name, enabled in pic_scripts.items():
        if not enabled:
            continue

        script_path = scripts_dir / f"{script_name}.py"
        if not script_path.exists():
            raise FileNotFoundError(script_path)

        for seed in seeds:
            env = os.environ.copy()
            env["GEN_SEED"] = str(seed)

            subprocess.run(
                ["uv", "run", str(script_path)], check=True, cwd=root, env=env
            )

            tmp_svg = output_dir / "tmp.svg"
            if not tmp_svg.exists():
                raise FileNotFoundError(tmp_svg)

            png_path = svg_to_png(tmp_svg)
            tmp_svg.unlink()

            new_name = f"{script_name}_{seed}"
            rename_file(png_path, new_name)


if __name__ == "__main__":
    main()
