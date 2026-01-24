#!/usr/bin/env uv run
"""Generate random-walk border lines over a bg/stroke gradient."""

import math
import os
import random
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import svgwrite

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from py_helper import variables  # noqa: E402

Point = Tuple[float, float]


@dataclass
class WalkConfig:
    width: int = 1200
    height: int = 1200
    margin: int = 0

    seed: int = 23
    n_lines: int = 34

    stroke_min: float = 1.2
    stroke_max: float = 6.0

    step_min: float = 10.0
    step_max: float = 400.0


def _resolve_seed(config: dict) -> int:
    env_seed = os.getenv("GEN_SEED")
    if env_seed:
        return int(env_seed)
    style = config.get("style", {})
    if style.get("seed") is not None:
        return int(style["seed"])
    seed_list = style.get("seedlist")
    if isinstance(seed_list, list) and seed_list:
        return int(seed_list[0])
    raise ValueError("Missing [style].seed or [style].seedlist in config.toml")


def _random_border_point(rng: random.Random, width: int, height: int) -> Point:
    side = rng.choice(["top", "right", "bottom", "left"])
    if side == "top":
        return (rng.uniform(0, width), 0.0)
    if side == "right":
        return (width, rng.uniform(0, height))
    if side == "bottom":
        return (rng.uniform(0, width), height)
    return (0.0, rng.uniform(0, height))


def _inside(x: float, y: float, width: int, height: int) -> bool:
    return 0 <= x <= width and 0 <= y <= height


def generate_random_walk_svg(
    out_file: str, colors: Dict[str, str], cfg: WalkConfig
) -> None:
    required = {"bg", "c1", "c2", "c3", "stroke"}
    missing = required - set(colors.keys())
    if missing:
        raise ValueError(
            f"Missing colors: {sorted(missing)}. Expected keys: {sorted(required)}"
        )

    rng = random.Random(cfg.seed)
    palette = [colors["c1"], colors["c2"], colors["c3"]]

    dwg = svgwrite.Drawing(out_file, size=(cfg.width, cfg.height))

    grad_id = "bg_grad"
    cx = rng.uniform(0, cfg.width)
    cy = rng.uniform(0, cfg.height)
    corners = [(0.0, 0.0), (cfg.width, 0.0), (cfg.width, cfg.height), (0.0, cfg.height)]
    radius = max(math.hypot(cx - x, cy - y) for x, y in corners)
    gradient = dwg.radialGradient(
        id=grad_id,
        center=(cx, cy),
        r=radius,
        gradientUnits="userSpaceOnUse",
    )
    gradient.add_stop_color(0, colors["bg"])
    gradient.add_stop_color(1, colors["stroke"])
    dwg.defs.add(gradient)

    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill=f"url(#{grad_id})"))

    for _ in range(cfg.n_lines):
        x, y = _random_border_point(rng, cfg.width, cfg.height)
        stroke = rng.choice(palette)
        stroke_width = rng.uniform(cfg.stroke_min, cfg.stroke_max)

        points: list[Point] = [(x, y)]
        angle = math.radians(rng.choice(range(0, 360, 10)))
        while True:
            delta = rng.uniform(-80, 80)
            angle = angle + math.radians(delta)
            angle_step = angle
            length = rng.uniform(cfg.step_min, cfg.step_max)
            x += math.cos(angle_step) * length
            y += math.sin(angle_step) * length
            points.append((x, y))
            if not _inside(x, y, cfg.width, cfg.height):
                break

        dwg.add(
            dwg.polyline(
                points,
                fill="none",
                stroke=stroke,
                stroke_width=stroke_width,
                stroke_linecap="round",
                stroke_linejoin="round",
            )
        )

    dwg.save()


if __name__ == "__main__":
    config_path = ROOT / variables.CONFIG
    output_dir = ROOT / variables.OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)

    with config_path.open("rb") as f:
        config = tomllib.load(f)

    colors = {
        "bg": config["colors"]["bg"],
        "c1": config["colors"]["c1"],
        "c2": config["colors"]["c2"],
        "c3": config["colors"]["c3"],
        "stroke": config["colors"]["stroke"],
    }

    cfg = WalkConfig(seed=_resolve_seed(config))
    out_path = output_dir / "tmp.svg"
    generate_random_walk_svg(str(out_path), colors, cfg)
    print(f"Wrote {out_path}")
