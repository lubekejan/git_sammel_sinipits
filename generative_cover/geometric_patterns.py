import random
import math
import sys
from dataclasses import dataclass
from typing import Dict, Tuple

import svgwrite

# Python 3.11+: tomllib ist in der Standardbibliothek
try:
    import tomllib  # type: ignore
except ModuleNotFoundError:  # Python <= 3.10
    # pip install tomli
    import tomli as tomllib  # type: ignore


# -------------------------
# Configuration
# -------------------------

@dataclass
class PatternConfig:
    width: int = 1200
    height: int = 1200

    seed: int = 42
    background: str = "#FFFFFF"
    palette: Tuple[str, ...] = ("#000000", "#333333", "#666666")

    grid_size: int = 14
    padding: int = 40

    stroke_width: float = 3.2
    shape_fill_probability: float = 0.85  # sonst Outline

# -------------------------
# Shape generators
# -------------------------

def draw_circle(dwg, x, y, size, color, cfg, rng):
    r = size / 2
    filled = rng.random() < cfg.shape_fill_probability
    dwg.add(
        dwg.circle(
            center=(x + r, y + r),
            r=r * 0.9,
            fill=color if filled else "none",
            stroke="none" if filled else color,
            stroke_width=cfg.stroke_width,
        )
    )

def draw_rect(dwg, x, y, size, color, cfg, rng):
    filled = rng.random() < cfg.shape_fill_probability
    dwg.add(
        dwg.rect(
            insert=(x, y),
            size=(size, size),
            rx=size * 0.15,
            ry=size * 0.15,
            fill=color if filled else "none",
            stroke="none" if filled else color,
            stroke_width=cfg.stroke_width,
        )
    )

def draw_triangle(dwg, x, y, size, color, cfg, rng):
    h = size * math.sqrt(3) / 2
    pts = [
        (x + size / 2, y),
        (x, y + h),
        (x + size, y + h),
    ]
    filled = rng.random() < cfg.shape_fill_probability
    dwg.add(
        dwg.polygon(
            pts,
            fill=color if filled else "none",
            stroke="none" if filled else color,
            stroke_width=cfg.stroke_width,
        )
    )

def draw_lines(dwg, x, y, size, color, cfg, rng):
    count = rng.randint(3, 7)
    for i in range(count):
        offset = size * i / count
        dwg.add(
            dwg.line(
                start=(x + offset, y),
                end=(x + offset, y + size),
                stroke=color,
                stroke_width=cfg.stroke_width * 0.6,
            )
        )

# SHAPES = [draw_circle, draw_rect, draw_triangle, draw_lines]
SHAPES = [draw_circle, draw_triangle, draw_lines]

# -------------------------
# TOML loading
# -------------------------

def load_toml_config(path: str) -> Dict:
    with open(path, "rb") as f:
        return tomllib.load(f)

def cfg_from_toml(toml_data: Dict, fallback: PatternConfig | None = None) -> PatternConfig:
    cfg = fallback or PatternConfig()

    # Erwartet (wie in Ihrer Datei): [style].seed und [colors].bg/c1/c2/c3
    seed = toml_data.get("style", {}).get("seed", cfg.seed)
    colors = toml_data.get("colors", {})

    bg = colors.get("bg", cfg.background)
    c1 = colors.get("c1")
    c2 = colors.get("c2")
    c3 = colors.get("c3")

    missing = [k for k in ("c1", "c2", "c3") if colors.get(k) is None]
    if missing:
        raise ValueError(f"Im TOML fehlen Farben: {missing} (unter [colors]).")

    cfg.seed = int(seed)
    cfg.background = str(bg)
    cfg.palette = (str(c1), str(c2), str(c3))

    return cfg

# -------------------------
# Main generator
# -------------------------

def generate_geometric_pattern(out_file: str, cfg: PatternConfig) -> None:
    rng = random.Random(cfg.seed)

    dwg = svgwrite.Drawing(out_file, size=(cfg.width, cfg.height))
    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill=cfg.background))

    cell_w = (cfg.width - 2 * cfg.padding) / cfg.grid_size
    cell_h = (cfg.height - 2 * cfg.padding) / cfg.grid_size
    cell = min(cell_w, cell_h)

    for gy in range(cfg.grid_size):
        for gx in range(cfg.grid_size):
            if rng.random() < 0.15:
                continue  # Leerraum für Rhythmus

            x = cfg.padding + gx * cell
            y = cfg.padding + gy * cell

            color = rng.choice(cfg.palette)
            shape = rng.choice(SHAPES)
            shape(dwg, x, y, cell, color, cfg, rng)

    dwg.save()

# -------------------------
# Run
# -------------------------

if __name__ == "__main__":
    # Usage:
    #   python geometric_patterns_from_toml.py config.toml output.svg
    toml_path = sys.argv[1] if len(sys.argv) >= 2 else "config.toml"
    out_svg = sys.argv[2] if len(sys.argv) >= 3 else "geometric_pattern.svg"

    data = load_toml_config(toml_path)

    # Optional: hier können Sie Default-Parameter setzen, die nicht im TOML stehen
    base = PatternConfig(
        width=1200,
        height=1200,
        grid_size=11,
        padding=-15,
        stroke_width=3.2,
        shape_fill_probability=0.8,
    )

    cfg = cfg_from_toml(data, base)
    generate_geometric_pattern(out_svg, cfg)
    print(f"Wrote {out_svg} (seed={cfg.seed}, bg={cfg.background}, palette={cfg.palette})")
