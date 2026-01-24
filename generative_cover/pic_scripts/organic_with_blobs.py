#!/usr/bin/env uv run
"""Generate a flowfield + blobs SVG using config/variables paths."""

import math
import os
import random
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import svgwrite

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from py_helper import variables  # noqa: E402

# -------------------------
# Smooth 2D Value Noise (deterministic) + fBm
# -------------------------


def _hash_int(n: int) -> int:
    n = (n ^ 61) ^ (n >> 16)
    n = n + (n << 3)
    n = n ^ (n >> 4)
    n = n * 0x27D4EB2D
    n = n ^ (n >> 15)
    return n & 0xFFFFFFFF


def _rand2(ix: int, iy: int, seed: int) -> float:
    h = _hash_int(ix * 374761393 + iy * 668265263 + seed * 362437)
    return h / 2**32  # [0,1)


def _fade(t: float) -> float:
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
    return _lerp(ix0, ix1, sy)  # [0,1)


def fbm_2d(
    x: float,
    y: float,
    seed: int,
    octaves: int = 5,
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
    return total / max(norm, 1e-9)


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
# Geometry helpers: Catmull-Rom -> Cubic Bezier for smooth closed blobs
# -------------------------

Point = Tuple[float, float]


def catmull_rom_to_beziers(
    points: List[Point], closed: bool = True, tension: float = 1.0
) -> List[Tuple[Point, Point, Point, Point]]:
    """
    Returns list of cubic bezier segments (P0, C1, C2, P3).
    For closed curves, points are treated cyclically.
    tension: 1.0 is standard Catmull-Rom; smaller => tighter.
    """
    n = len(points)
    if n < 4:
        raise ValueError("Need at least 4 points for Catmull-Rom.")

    segs = []
    for i in range(n if closed else n - 1):
        p0 = points[(i - 1) % n] if closed else points[max(i - 1, 0)]
        p1 = points[i % n]
        p2 = points[(i + 1) % n] if closed else points[min(i + 1, n - 1)]
        p3 = points[(i + 2) % n] if closed else points[min(i + 2, n - 1)]

        # Catmull-Rom to Bezier conversion
        # C1 = P1 + (P2 - P0) / 6
        # C2 = P2 - (P3 - P1) / 6
        # Apply tension scaling to handle shapes: smaller => less overshoot
        t = tension
        c1 = (p1[0] + (p2[0] - p0[0]) / 6.0 * t, p1[1] + (p2[1] - p0[1]) / 6.0 * t)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6.0 * t, p2[1] - (p3[1] - p1[1]) / 6.0 * t)

        segs.append((p1, c1, c2, p2))
        if not closed and i == n - 2:
            break
    return segs


def blob_path_d(
    center: Point,
    base_r: float,
    rng: random.Random,
    seed: int,
    scale: float,
    octaves: int,
    n_points: int = 14,
    roughness: float = 0.55,
    tension: float = 0.9,
) -> str:
    """
    Create a smooth closed blob path around center.
    roughness: 0..1 radius variation amount
    """
    cx, cy = center
    pts: List[Point] = []

    # angle offset so blobs look less aligned
    ang0 = rng.uniform(0, 2 * math.pi)

    for i in range(n_points):
        a = ang0 + (2 * math.pi) * (i / n_points)
        # sample noise in a loop-friendly way
        # combine polar coords into noise space
        nx = (cx + math.cos(a) * base_r) * scale
        ny = (cy + math.sin(a) * base_r) * scale

        n = fbm_2d(nx, ny, seed, octaves=octaves)  # [0,1]
        # map noise to radius multiplier around 1.0
        # centered variation: [-0.5, +0.5]
        dv = (n - 0.5) * 2.0
        r = base_r * (1.0 + dv * roughness)

        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r
        pts.append((x, y))

    segs = catmull_rom_to_beziers(pts, closed=True, tension=tension)

    # Build SVG path d
    d = []
    start = segs[0][0]
    d.append(f"M {start[0]:.2f},{start[1]:.2f}")
    for p1, c1, c2, p2 in segs:
        d.append(
            f"C {c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} {p2[0]:.2f},{p2[1]:.2f}"
        )
    d.append("Z")
    return " ".join(d)


# -------------------------
# Main generator
# -------------------------


@dataclass
class FlowConfig:
    width: int = 1200
    height: int = 1200
    margin: int = 0
    seed: int = 7

    # Flow-field lines
    n_lines: int = 1400
    steps_per_line: int = 190
    step_len: float = 3.0
    field_scale: float = 0.0046
    field_octaves: int = 6
    angle_turns: float = 1.0

    # Line styling
    stroke_width: float = 0.8
    stroke_opacity_min: float = 0.06
    stroke_opacity_max: float = 0.18

    # Blobs
    n_blobs: int = 22
    blob_min_r: float = 30
    blob_max_r: float = 120
    blob_points_min: int = 10
    blob_points_max: int = 18
    blob_roughness: float = 0.60
    blob_tension: float = 0.90
    blob_noise_scale: float = 0.006
    blob_octaves: int = 5

    blob_opacity_min: float = 0.45
    blob_opacity_max: float = 0.80


def generate_svg(
    out_file: str, colors: Dict[str, str], cfg: FlowConfig = FlowConfig()
) -> None:
    required = {"bg", "c1", "c2", "c3"}
    missing = required - set(colors.keys())
    if missing:
        raise ValueError(
            f"Missing colors: {sorted(missing)}. Expected keys: {sorted(required)}"
        )

    rng = random.Random(cfg.seed)
    palette = [colors["c1"], colors["c2"], colors["c3"]]

    dwg = svgwrite.Drawing(out_file, size=(cfg.width, cfg.height))
    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill=colors["bg"]))

    def inside(px: float, py: float) -> bool:
        return (cfg.margin <= px <= cfg.width - cfg.margin) and (
            cfg.margin <= py <= cfg.height - cfg.margin
        )

    # --- Blobs first (unter den Linien) ---
    # Sie können das auch umdrehen, wenn die Blobs "oben drauf" liegen sollen.
    for _ in range(cfg.n_blobs):
        cx = rng.uniform(cfg.margin, cfg.width - cfg.margin)
        cy = rng.uniform(cfg.margin, cfg.height - cfg.margin)
        base_r = rng.uniform(cfg.blob_min_r, cfg.blob_max_r)
        npts = rng.randint(cfg.blob_points_min, cfg.blob_points_max)

        fill = rng.choice(palette)
        op = rng.uniform(cfg.blob_opacity_min, cfg.blob_opacity_max)

        d = blob_path_d(
            center=(cx, cy),
            base_r=base_r,
            rng=rng,
            seed=cfg.seed + 9991,  # separate blob seed-space from flow field
            scale=cfg.blob_noise_scale,
            octaves=cfg.blob_octaves,
            n_points=npts,
            roughness=cfg.blob_roughness,
            tension=cfg.blob_tension,
        )

        dwg.add(dwg.path(d=d, fill=fill, fill_opacity=op, stroke="none"))

    # --- Flow field lines ---
    for _ in range(cfg.n_lines):
        x = rng.uniform(cfg.margin, cfg.width - cfg.margin)
        y = rng.uniform(cfg.margin, cfg.height - cfg.margin)

        pts = [(x, y)]
        for _s in range(cfg.steps_per_line):
            nx = x * cfg.field_scale
            ny = y * cfg.field_scale
            n = fbm_2d(nx, ny, cfg.seed, octaves=cfg.field_octaves)
            angle = (2.0 * math.pi * cfg.angle_turns) * n

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
                    stroke=colors["c2"],  # Linienfarbe (hier c2; gern random/palette)
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

    colors = {
        "bg": config["colors"]["bg"],
        "c1": config["colors"]["c1"],
        "c2": config["colors"]["c2"],
        "c3": config["colors"]["c3"],
    }

    cfg = FlowConfig(
        seed=_resolve_seed(config),
        n_blobs=26,
        blob_min_r=35,
        blob_max_r=140,
        n_lines=1500,
        steps_per_line=210,
        step_len=2.9,
        field_scale=0.0045,
        field_octaves=6,
    )

    out_path = output_dir / "tmp.svg"
    generate_svg(str(out_path), colors, cfg)
    print(f"Wrote {out_path}")
