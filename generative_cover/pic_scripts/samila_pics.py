#!/usr/bin/env uv run
"""Generate a Samila SVG using config/variables paths."""

import math
import os
import random
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from samila import GenerativeImage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from py_helper import variables  # noqa: E402


@dataclass
class SamilaConfig:
    width: int = 1200
    height: int = 1200
    seed: int = 42
    background: str = "#FFFFFF"
    palette: tuple[str, ...] = ("#000000", "#333333", "#666666")
    spot_size: float = 0.6


def _resolve_seed(config: Mapping[str, object]) -> int:
    env_seed = os.getenv("GEN_SEED")
    if env_seed:
        return int(env_seed)
    style_obj = config.get("style", {})
    style = style_obj if isinstance(style_obj, dict) else {}
    if style.get("seed") is not None:
        return int(style["seed"])
    seed_list = style.get("seedlist")
    if isinstance(seed_list, list) and seed_list:
        return int(seed_list[0])
    raise ValueError("Missing [style].seed or [style].seedlist in config.toml")


def load_toml_config(path: str) -> dict[str, object]:
    with open(path, "rb") as f:
        return tomllib.load(f)


def cfg_from_toml(
    toml_data: Mapping[str, object], fallback: SamilaConfig | None = None
) -> SamilaConfig:
    cfg = fallback or SamilaConfig()

    colors_obj = toml_data.get("colors", {})
    colors = colors_obj if isinstance(colors_obj, dict) else {}
    bg = colors.get("bg", cfg.background)
    c1 = colors.get("c1")
    c2 = colors.get("c2")
    c3 = colors.get("c3")
    if c1 is None or c2 is None or c3 is None:
        raise ValueError("Im TOML fehlen Farben c1/c2/c3 unter [colors].")

    cfg.background = str(bg)
    cfg.palette = (str(c1), str(c2), str(c3))
    cfg.seed = _resolve_seed(toml_data)
    return cfg


def _build_functions() -> tuple[
    Callable[[float, float], float], Callable[[float, float], float]
]:
    def f1(x: float, y: float) -> float:
        return random.uniform(-1.0, 1.0) * x**2 - math.sin(y**2) + abs(y - x)

    def f2(x: float, y: float) -> float:
        return random.uniform(-1.0, 1.0) * y**3 - math.cos(x**2) + 2 * x

    return f1, f2


def generate_samila_svg(out_file: str, cfg: SamilaConfig) -> None:
    random.seed(cfg.seed)
    f1, f2 = _build_functions()

    image = GenerativeImage(f1, f2)
    image.generate(seed=cfg.seed)
    image.plot(
        cmap=list(cfg.palette),
        bgcolor=cfg.background,
        spot_size=cfg.spot_size,
    )
    image.save_image(out_file)


if __name__ == "__main__":
    config_path = ROOT / variables.CONFIG
    output_dir = ROOT / variables.OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)

    data = load_toml_config(str(config_path))
    cfg = cfg_from_toml(data)

    out_path = output_dir / "tmp.svg"
    generate_samila_svg(str(out_path), cfg)
    print(f"Wrote {out_path} (seed={cfg.seed}, bg={cfg.background})")
