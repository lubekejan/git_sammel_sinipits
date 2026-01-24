#!/usr/bin/env uv run
"""Render simple 3D-looking solids with light and shadow."""

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
BBox = Tuple[float, float, float, float]


@dataclass
class SolidConfig:
    width: int = 1200
    height: int = 1200
    margin: int = 60

    seed: int = 23
    n_objects: int = 10

    shadow_opacity: float = 0.22
    stroke_width: float = 2.2


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


def _hex_to_rgb(color: str) -> Tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))  # pyright: ignore[reportReturnType]


def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _shade(color: str, factor: float) -> str:
    r, g, b = _hex_to_rgb(color)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return _rgb_to_hex((r, g, b))


def _random_light_pos(rng: random.Random, width: int, height: int) -> Point:
    side = rng.choice(["top", "right", "bottom", "left"])
    margin = max(width, height) * 0.2
    if side == "top":
        return (rng.uniform(-margin, width + margin), -margin)
    if side == "bottom":
        return (rng.uniform(-margin, width + margin), height + margin)
    if side == "left":
        return (-margin, rng.uniform(-margin, height + margin))
    return (width + margin, rng.uniform(-margin, height + margin))


def _add_shadow(
    dwg: svgwrite.Drawing,
    base_center: Point,
    size: float,
    light_pos: Point,
    opacity: float,
) -> None:
    lx, ly = light_pos
    bx, by = base_center
    vx = bx - lx
    vy = by - ly
    dist = math.hypot(vx, vy) or 1.0
    dx = vx / dist
    dy = vy / dist
    shadow_center = (bx + dx * size * 0.6, by + dy * size * 0.25)
    dwg.add(
        dwg.ellipse(
            center=shadow_center,
            r=(size * 0.55, size * 0.18),
            fill="#000000",
            fill_opacity=opacity,
            stroke="none",
        )
    )


def _draw_cube(
    dwg: svgwrite.Drawing,
    base: Point,
    size: float,
    base_color: str,
    stroke: str,
    stroke_width: float,
) -> None:
    x, y = base
    s = size
    dx = s * 0.6
    dy = s * 0.6

    a = (x, y)
    b = (x + s, y)
    c = (x + s, y - s)
    d = (x, y - s)

    e = (x + dx, y - dy)
    f = (x + s + dx, y - dy)
    g = (x + s + dx, y - s - dy)
    h = (x + dx, y - s - dy)

    front = [a, b, c, d]
    top = [d, c, g, h]
    left = [d, a, e, h]
    right = [c, b, f, g]

    dwg.add(
        dwg.polygon(
            right,
            fill=_shade(base_color, 0.78),
            stroke=stroke,
            stroke_width=stroke_width,
        )
    )
    dwg.add(
        dwg.polygon(
            left,
            fill=_shade(base_color, 0.92),
            stroke=stroke,
            stroke_width=stroke_width,
        )
    )
    dwg.add(
        dwg.polygon(
            front,
            fill=_shade(base_color, 1.0),
            stroke=stroke,
            stroke_width=stroke_width,
        )
    )
    dwg.add(
        dwg.polygon(
            top, fill=_shade(base_color, 1.18), stroke=stroke, stroke_width=stroke_width
        )
    )


def _draw_cylinder(
    dwg: svgwrite.Drawing,
    base_center: Point,
    size: float,
    base_color: str,
    stroke: str,
    stroke_width: float,
) -> None:
    x, base_y = base_center
    w = size
    h = size * 1.3
    rx = w / 2
    ry = w / 5

    rect_top = base_y - h - ry
    rect = dwg.rect(
        insert=(x - rx, rect_top),
        size=(w, h),
        fill=_shade(base_color, 0.9),
        stroke=stroke,
        stroke_width=stroke_width,
    )
    dwg.add(rect)
    dwg.add(
        dwg.ellipse(
            center=(x, rect_top),
            r=(rx, ry),
            fill=_shade(base_color, 1.12),
            stroke=stroke,
            stroke_width=stroke_width,
        )
    )
    dwg.add(
        dwg.ellipse(
            center=(x, rect_top + h),
            r=(rx, ry),
            fill=_shade(base_color, 0.8),
            stroke=stroke,
            stroke_width=stroke_width,
        )
    )


def _draw_cone(
    dwg: svgwrite.Drawing,
    base_center: Point,
    size: float,
    base_color: str,
    stroke: str,
    stroke_width: float,
) -> None:
    x, base_y = base_center
    w = size
    h = size * 1.4
    rx = w / 2
    ry = w / 6

    apex = (x, base_y - h - ry)
    left = (x - rx, base_y - ry)
    right = (x + rx, base_y - ry)

    dwg.add(
        dwg.polygon(
            [apex, right, left],
            fill=_shade(base_color, 0.88),
            stroke=stroke,
            stroke_width=stroke_width,
        )
    )
    dwg.add(
        dwg.ellipse(
            center=(x, base_y - ry),
            r=(rx, ry),
            fill=_shade(base_color, 0.75),
            stroke=stroke,
            stroke_width=stroke_width,
        )
    )


def _draw_sphere(
    dwg: svgwrite.Drawing,
    base_center: Point,
    size: float,
    base_color: str,
    stroke: str,
    stroke_width: float,
    light: Point,
) -> None:
    x, base_y = base_center
    r = size / 2
    y = base_y - r
    grad_id = f"sphere_{int(x)}_{int(y)}"
    gradient = dwg.radialGradient(id=grad_id, center=(0.35, 0.35), r="70%")
    gradient.add_stop_color(0, _shade(base_color, 1.25))
    gradient.add_stop_color(1, _shade(base_color, 0.75))
    dwg.defs.add(gradient)

    dwg.add(
        dwg.circle(
            center=(x, y),
            r=r,
            fill=f"url(#{grad_id})",
            stroke=stroke,
            stroke_width=stroke_width,
        )
    )


def generate_solids_svg(
    out_file: str, colors: Dict[str, str], cfg: SolidConfig
) -> None:
    required = {"bg", "c1", "c2", "c3", "stroke"}
    missing = required - set(colors.keys())
    if missing:
        raise ValueError(
            f"Missing colors: {sorted(missing)}. Expected keys: {sorted(required)}"
        )

    rng = random.Random(cfg.seed)
    palette = [colors["c1"], colors["c2"], colors["c3"]]
    light_pos = _random_light_pos(rng, cfg.width, cfg.height)

    dwg = svgwrite.Drawing(out_file, size=(cfg.width, cfg.height))
    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill=colors["bg"]))

    grid_step = rng.randint(80, 160)
    for x in range(0, cfg.width + 1, grid_step):
        dwg.add(
            dwg.line(
                start=(x, 0),
                end=(x, cfg.height),
                stroke=colors["stroke"],
                stroke_width=1.0,
                stroke_opacity=0.35,
            )
        )
    for y in range(0, cfg.height + 1, grid_step):
        dwg.add(
            dwg.line(
                start=(0, y),
                end=(cfg.width, y),
                stroke=colors["stroke"],
                stroke_width=1.0,
                stroke_opacity=0.35,
            )
        )

    placed: list[BBox] = []
    objects: list[tuple[str, Point, float, str]] = []

    def overlaps(bbox: BBox) -> bool:
        x1, y1, x2, y2 = bbox
        for ox1, oy1, ox2, oy2 in placed:
            if x1 < ox2 and x2 > ox1 and y1 < oy2 and y2 > oy1:
                return True
        return False

    for _ in range(cfg.n_objects):
        for _attempt in range(120):
            shape = rng.choice(["cube", "cylinder", "cone", "sphere"])
            size = rng.uniform(90, 180)

            if shape == "cube":
                s = size * 0.75
                dx = s * 0.6
                dy = s * 0.6
                width = s + dx
                height = s + dy
                base_x = rng.uniform(cfg.margin, cfg.width - cfg.margin - width)
                base_y = rng.uniform(cfg.margin + height, cfg.height - cfg.margin)
                base_center = (base_x, base_y)
                bbox = (base_x, base_y - height, base_x + width, base_y)
            elif shape == "cylinder":
                s = size * 0.7
                rx = s / 2
                ry = s / 5
                h = s * 1.3
                base_x = rng.uniform(cfg.margin + rx, cfg.width - cfg.margin - rx)
                base_y = rng.uniform(cfg.margin + h + 2 * ry, cfg.height - cfg.margin)
                base_center = (base_x, base_y)
                bbox = (base_x - rx, base_y - h - 2 * ry, base_x + rx, base_y)
            elif shape == "cone":
                s = size * 0.7
                rx = s / 2
                ry = s / 6
                h = s * 1.4
                base_x = rng.uniform(cfg.margin + rx, cfg.width - cfg.margin - rx)
                base_y = rng.uniform(cfg.margin + h + ry, cfg.height - cfg.margin)
                base_center = (base_x, base_y)
                bbox = (base_x - rx, base_y - h - ry, base_x + rx, base_y)
            else:
                s = size * 0.75
                r = s / 2
                base_x = rng.uniform(cfg.margin + r, cfg.width - cfg.margin - r)
                base_y = rng.uniform(cfg.margin + 2 * r, cfg.height - cfg.margin)
                base_center = (base_x, base_y)
                bbox = (base_x - r, base_y - 2 * r, base_x + r, base_y)

            if overlaps(bbox):
                continue

            placed.append(bbox)
            base_color = rng.choice(palette)
            objects.append((shape, base_center, size, base_color))
            break

    for shape, base_center, size, base_color in objects:
        if shape == "cube":
            _draw_cube(
                dwg,
                (base_center[0] - (size * 0.75) / 2, base_center[1]),
                size * 0.75,
                base_color,
                colors["stroke"],
                cfg.stroke_width,
            )
        elif shape == "cylinder":
            _draw_cylinder(
                dwg,
                base_center,
                size * 0.7,
                base_color,
                colors["stroke"],
                cfg.stroke_width,
            )
        elif shape == "cone":
            _draw_cone(
                dwg,
                base_center,
                size * 0.7,
                base_color,
                colors["stroke"],
                cfg.stroke_width,
            )
        else:
            _draw_sphere(
                dwg,
                base_center,
                size * 0.75,
                base_color,
                colors["stroke"],
                cfg.stroke_width,
                light_pos,
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

    cfg = SolidConfig(seed=_resolve_seed(config))
    out_path = output_dir / "tmp.svg"
    generate_solids_svg(str(out_path), colors, cfg)
    print(f"Wrote {out_path}")
