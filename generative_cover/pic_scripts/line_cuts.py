#!/usr/bin/env uv run
"""Generate line-cut regions and fill random faces from the line arrangement."""

import math
import os
import random
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import svgwrite
from shapely.geometry import LineString, Polygon, box
from shapely.ops import split

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from py_helper import variables  # noqa: E402

Point = Tuple[float, float]


@dataclass
class LineCutConfig:
    width: int = 1200
    height: int = 1200
    margin: int = 0

    seed: int = 23
    n_lines: int = 18
    stroke_width: float = 2.0

    fill_probability: float = 0.35


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


def _line_through_rect(
    rng: random.Random, width: int, height: int, margin: int
) -> LineString:
    cx = width / 2
    cy = height / 2
    angle = rng.uniform(0, 3.141592653589793)
    nx = -math.sin(angle)
    ny = math.cos(angle)
    offset = rng.uniform(
        -min(width, height) / 2 + margin, min(width, height) / 2 - margin
    )

    pts: List[Point] = []
    for x in (margin, width - margin):
        y = cy + (offset - (x - cx) * nx) / ny if ny != 0 else None
        if y is not None and margin <= y <= height - margin:
            pts.append((x, y))
    for y in (margin, height - margin):
        x = cx + (offset - (y - cy) * ny) / nx if nx != 0 else None
        if x is not None and margin <= x <= width - margin:
            pts.append((x, y))

    if len(pts) >= 2:
        return LineString([pts[0], pts[1]])

    x1 = margin
    y1 = margin
    x2 = width - margin
    y2 = height - margin
    return LineString([(x1, y1), (x2, y2)])


def _split_polygons(polygons: List[Polygon], cutter: LineString) -> List[Polygon]:
    result: List[Polygon] = []
    for poly in polygons:
        pieces = split(poly, cutter)
        for geom in pieces.geoms:
            if isinstance(geom, Polygon) and geom.area > 1.0:
                result.append(geom)
    return result or polygons


def generate_line_cuts_svg(
    out_file: str, colors: Dict[str, str], cfg: LineCutConfig
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
    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill=colors["bg"]))

    rect = box(cfg.margin, cfg.margin, cfg.width - cfg.margin, cfg.height - cfg.margin)
    polygons: List[Polygon] = [rect]
    lines: List[LineString] = []

    for _ in range(cfg.n_lines):
        line = _line_through_rect(rng, cfg.width, cfg.height, cfg.margin)
        lines.append(line)
        polygons = _split_polygons(polygons, line)

    for poly in polygons:
        if rng.random() >= cfg.fill_probability:
            continue
        color = rng.choice(palette)
        coords = [(round(x, 2), round(y, 2)) for x, y in list(poly.exterior.coords)]
        dwg.add(dwg.polygon(coords, fill=color, stroke="none"))

    for line in lines:
        (x1, y1), (x2, y2) = list(line.coords)
        dwg.add(
            dwg.line(
                start=(x1, y1),
                end=(x2, y2),
                stroke=colors["stroke"],
                stroke_width=cfg.stroke_width,
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

    seed = _resolve_seed(config)
    rng = random.Random(seed)
    n_lines = rng.randint(15, 30)

    cfg = LineCutConfig(seed=seed, n_lines=n_lines)
    out_path = output_dir / "tmp.svg"
    generate_line_cuts_svg(str(out_path), colors, cfg)
    print(f"Wrote {out_path}")
