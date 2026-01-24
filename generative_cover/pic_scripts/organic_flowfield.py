#!/usr/bin/env uv run
"""Generate a flowfield SVG using config/variables paths."""

import math
import os
import random
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import svgwrite

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from py_helper import variables  # noqa: E402

# -------------------------
# Smooth 2D Value Noise (deterministic) + fBm
# -------------------------


def _hash_int(n: int) -> int:
    # simple 32-bit mix
    n = (n ^ 61) ^ (n >> 16)
    n = n + (n << 3)
    n = n ^ (n >> 4)
    n = n * 0x27D4EB2D
    n = n ^ (n >> 15)
    return n & 0xFFFFFFFF


def _rand2(ix: int, iy: int, seed: int) -> float:
    h = _hash_int(ix * 374761393 + iy * 668265263 + seed * 362437)
    # map to [0,1)
    return h / 2**32


def _fade(t: float) -> float:
    # Perlin fade curve
    return t * t * t * (t * (t * 6 - 15) + 10)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def value_noise_2d(x: float, y: float, seed: int) -> float:
    x0 = math.floor(x)
    y0 = math.floor(y)
    x1 = x0 + 1
    y1 = y0 + 1

    sx = _fade(x - x0)
    sy = _fade(y - y0)

    n00 = _rand2(x0, y0, seed)
    n10 = _rand2(x1, y0, seed)
    n01 = _rand2(x0, y1, seed)
    n11 = _rand2(x1, y1, seed)

    ix0 = _lerp(n00, n10, sx)
    ix1 = _lerp(n01, n11, sx)
    return _lerp(ix0, ix1, sy)  # [0,1]


def fbm_2d(
    x: float,
    y: float,
    seed: int,
    octaves: int = 4,
    lacunarity: float = 2.0,
    gain: float = 0.5,
) -> float:
    amp = 1.0
    freq = 1.0
    total = 0.0
    norm = 0.0
    for o in range(octaves):
        total += amp * value_noise_2d(x * freq, y * freq, seed + 1013 * o)
        norm += amp
        amp *= gain
        freq *= lacunarity
    return total / max(norm, 1e-9)  # ~[0,1]


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


# -------------------------
# Flow field art generator
# -------------------------


@dataclass
class Config:
    width: int = 1200
    height: int = 1200
    margin: int = 0

    seed: int = 42

    n_lines: int = 1400
    steps_per_line: int = 180
    step_len: float = 3.2

    # Field controls (core of "organic look")
    field_scale: float = 0.0048  # smaller => larger swirls; bigger => finer turbulence
    octaves: int = 5
    angle_turns: float = 1.0  # multiplier on angle range; 1.0 => full 0..2π

    # Styling
    background: str = "#0b0c10"
    stroke: str = "#f5f5f5"
    stroke_width: float = 0.8
    stroke_opacity_min: float = 0.06
    stroke_opacity_max: float = 0.20


def generate_flowfield_svg(
    out_file: str = "organic_flowfield.svg", cfg: Config = Config()
) -> None:
    rng = random.Random(cfg.seed)

    dwg = svgwrite.Drawing(out_file, size=(cfg.width, cfg.height))
    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill=cfg.background))

    def inside(px: float, py: float) -> bool:
        return (cfg.margin <= px <= cfg.width - cfg.margin) and (
            cfg.margin <= py <= cfg.height - cfg.margin
        )

    for _ in range(cfg.n_lines):
        # random start inside margins
        x = rng.uniform(cfg.margin, cfg.width - cfg.margin)
        y = rng.uniform(cfg.margin, cfg.height - cfg.margin)

        pts = [(x, y)]
        for _s in range(cfg.steps_per_line):
            nx = x * cfg.field_scale
            ny = y * cfg.field_scale

            n = fbm_2d(nx, ny, cfg.seed, octaves=cfg.octaves)
            angle = (2.0 * math.pi * cfg.angle_turns) * n  # [0, 2π*turns)

            x += math.cos(angle) * cfg.step_len
            y += math.sin(angle) * cfg.step_len

            if not inside(x, y):
                break
            pts.append((x, y))

        if len(pts) >= 8:
            op = rng.uniform(cfg.stroke_opacity_min, cfg.stroke_opacity_max)
            dwg.add(
                dwg.polyline(
                    pts,
                    fill="none",
                    stroke=cfg.stroke,
                    stroke_width=cfg.stroke_width,
                    stroke_opacity=op,
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

    cfg = Config(
        # Sie können hier schnell tunen:
        seed=_resolve_seed(config),
        n_lines=1600,
        steps_per_line=210,
        step_len=3.0,
        field_scale=0.0045,
        octaves=6,
        stroke_width=0.75,
        stroke_opacity_min=0.05,
        stroke_opacity_max=0.18,
        background=config["colors"]["bg"],
        stroke=config["colors"]["stroke"],
    )
    out_path = output_dir / "tmp.svg"
    generate_flowfield_svg(str(out_path), cfg)
    print(f"Wrote {out_path}")
