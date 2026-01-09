import math
import random
import svgwrite
from dataclasses import dataclass
from typing import Dict, List, Tuple

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
    return (h / 2**32)  # [0,1)

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

def fbm_2d(x: float, y: float, seed: int, octaves: int = 5, lacunarity: float = 2.0, gain: float = 0.5) -> float:
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

# -------------------------
# Geometry helpers: Catmull-Rom -> Cubic Bezier for smooth closed blobs
# -------------------------

Point = Tuple[float, float]

def catmull_rom_to_beziers(points: List[Point], closed: bool = True, tension: float = 0.75):
    n = len(points)
    if n < 4:
        raise ValueError("Need at least 4 points for Catmull-Rom.")
    segs = []
    for i in range(n if closed else n - 1):
        p0 = points[(i - 1) % n] if closed else points[max(i - 1, 0)]
        p1 = points[i % n]
        p2 = points[(i + 1) % n] if closed else points[min(i + 1, n - 1)]
        p3 = points[(i + 2) % n] if closed else points[min(i + 2, n - 1)]

        t = tension
        c1 = (p1[0] + (p2[0] - p0[0]) / 6.0 * t, p1[1] + (p2[1] - p0[1]) / 6.0 * t)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6.0 * t, p2[1] - (p3[1] - p1[1]) / 6.0 * t)

        segs.append((p1, c1, c2, p2))
        if not closed and i == n - 2:
            break
    return segs

def blob_path_d(center: Point, base_r: float, rng: random.Random, seed: int,
                scale: float, octaves: int,
                n_points: int = 18, roughness: float = 0.70, tension: float = 0.75) -> str:
    cx, cy = center
    pts: List[Point] = []
    ang0 = rng.uniform(0, 2 * math.pi)

    for i in range(n_points):
        a = ang0 + (2 * math.pi) * (i / n_points)

        nx = (cx + math.cos(a) * base_r) * scale
        ny = (cy + math.sin(a) * base_r) * scale

        n = fbm_2d(nx, ny, seed, octaves=octaves)  # [0,1]
        dv = (n - 0.5) * 2.0                       # [-1,1]
        r = base_r * (1.0 + dv * roughness)

        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r
        pts.append((x, y))

    segs = catmull_rom_to_beziers(pts, closed=True, tension=tension)

    d = []
    start = segs[0][0]
    d.append(f"M {start[0]:.2f},{start[1]:.2f}")
    for (_p1, c1, c2, p2) in segs:
        d.append(f"C {c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} {p2[0]:.2f},{p2[1]:.2f}")
    d.append("Z")
    return " ".join(d)

# -------------------------
# Blob-only generator
# -------------------------

@dataclass
class BlobConfig:
    width: int = 1200
    height: int = 1200
    margin: int = 40
    seed: int = 11

    n_blobs: int = 35
    min_r: float = 35
    max_r: float = 160

    points_min: int = 14
    points_max: int = 24

    roughness: float = 0.70     # mehr => fleckiger
    tension: float = 0.75       # kleiner => weniger "perfekt"
    noise_scale: float = 0.006  # kleiner => großflächigere Wellen
    octaves: int = 6

    opacity_min: float = 0.30
    opacity_max: float = 0.70

def generate_blobs_svg(out_file: str, colors: Dict[str, str], cfg: BlobConfig = BlobConfig()) -> None:
    required = {"bg", "c1", "c2", "c3"}
    missing = required - set(colors.keys())
    if missing:
        raise ValueError(f"Missing colors: {sorted(missing)}. Expected keys: {sorted(required)}")

    rng = random.Random(cfg.seed)
    palette = [colors["c1"], colors["c2"], colors["c3"]]

    dwg = svgwrite.Drawing(out_file, size=(cfg.width, cfg.height))
    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill=colors["bg"]))

    for _ in range(cfg.n_blobs):
        cx = rng.uniform(cfg.margin, cfg.width - cfg.margin)
        cy = rng.uniform(cfg.margin, cfg.height - cfg.margin)

        base_r = rng.uniform(cfg.min_r, cfg.max_r)
        npts = rng.randint(cfg.points_min, cfg.points_max)

        fill = rng.choice(palette)
        op = rng.uniform(cfg.opacity_min, cfg.opacity_max)

        d = blob_path_d(
            center=(cx, cy),
            base_r=base_r,
            rng=rng,
            seed=cfg.seed + 9991,
            scale=cfg.noise_scale,
            octaves=cfg.octaves,
            n_points=npts,
            roughness=cfg.roughness,
            tension=cfg.tension,
        )

        # Farbfleck ohne Kontur:
        dwg.add(dwg.path(d=d, fill=fill, fill_opacity=op, stroke="none"))

    dwg.save()

if __name__ == "__main__":
    colors = {
        "bg": "#BBE0EF",
        "c1": "#161E54",
        "c2": "#F16D34",
        "c3": "#FF986A",
    }

    cfg = BlobConfig(
        seed=random.randint(0,100),
        n_blobs=40,
        min_r=40,
        max_r=170,
        opacity_min=0.28,
        opacity_max=0.65,
        roughness=0.72,
        tension=0.72,
        noise_scale=0.006,
        octaves=6,
    )

    generate_blobs_svg("blobs_only.svg", colors, cfg)
    print("Wrote blobs_only.svg")
