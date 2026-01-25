#!/usr/bin/env uv run
"""Generate an audio-based SVG using input files and config/variables paths."""

import math
import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
import svgwrite

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from py_helper import variables  # noqa: E402
from py_helper.file_utils import (  # noqa: E402
    list_files_by_extension,
    select_random_file,
)


@dataclass
class AudioVizConfig:
    width: int = 1200
    height: int = 1200
    seed: int = 23
    n_mels: int = 96
    hop_length: int = 512
    fmin: float = 30.0
    fmax: float = 16000.0
    power: float = 2.0
    db_min: float = -60.0
    draw_threshold: float = 0.08
    background: str = "#000000"
    palette: tuple[str, ...] = ("#ffffff", "#cccccc", "#999999")
    stroke: str = "#ffffff"
    turns: int = 10
    center_jitter: float = 0.01
    radius_scale: float = 0.42
    stroke_width: float = 1.9
    max_points: int = 1200


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


def _resolve_size(config: dict, fallback: AudioVizConfig) -> tuple[int, int]:
    style = config.get("style", {})
    width = int(style.get("width", fallback.width))
    height = int(style.get("height", fallback.height))
    return width, height


def _pick_palette_color(value: float, palette: tuple[str, ...]) -> str:
    if not palette:
        raise ValueError("palette must contain at least one color")
    if len(palette) == 1:
        return palette[0]
    idx = min(int(value * len(palette)), len(palette) - 1)
    return palette[idx]


def audio_to_svg(audio_path: Path, svg_path: Path, cfg: AudioVizConfig) -> None:
    y, sr = librosa.load(str(audio_path), sr=None, mono=True)

    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=cfg.hop_length)[0]
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=cfg.hop_length)
    chroma = librosa.feature.chroma_stft(
        y=y, sr=sr, hop_length=cfg.hop_length, n_chroma=12
    )

    frames = min(len(rms), len(onset), chroma.shape[1])
    rms = rms[:frames]
    onset = onset[:frames]
    chroma = chroma[:, :frames]

    def _norm(arr: np.ndarray) -> np.ndarray:
        if arr.size == 0:
            return arr
        max_val = float(np.max(arr))
        if max_val <= 0:
            return np.zeros_like(arr, dtype=np.float32)
        return (arr / max_val).astype(np.float32)

    rms_n = _norm(rms)
    onset_n = _norm(onset)
    chroma_n = _norm(chroma)

    if frames > cfg.max_points:
        step = int(np.ceil(frames / cfg.max_points))
        rms_n = rms_n[::step]
        onset_n = onset_n[::step]
        chroma_n = chroma_n[:, ::step]
        frames = rms_n.shape[0]

    # 4) SVG initialisieren
    dwg = svgwrite.Drawing(str(svg_path), size=(cfg.width, cfg.height))
    dwg.add(dwg.rect(insert=(0, 0), size=(cfg.width, cfg.height), fill=cfg.background))

    center_x = cfg.width / 2
    center_y = cfg.height / 2
    radius_max = min(cfg.width, cfg.height) * cfg.radius_scale

    angle_step = (2 * np.pi * cfg.turns) / max(frames, 1)
    base_radius = np.linspace(0.0, radius_max, frames, dtype=np.float32)

    jitter = cfg.center_jitter * min(cfg.width, cfg.height)
    rng = np.random.default_rng(cfg.seed)

    points: list[tuple[float, float]] = []
    opacities: list[float] = []

    for i in range(frames):
        v = float(rms_n[i])
        if v < cfg.draw_threshold:
            continue

        angle = i * angle_step + (onset_n[i] * 1.4)
        radius = base_radius[i] * (0.35 + 0.9 * v)

        jitter_x = float(rng.uniform(-jitter, jitter))
        jitter_y = float(rng.uniform(-jitter, jitter))

        x = center_x + math.cos(angle) * radius + jitter_x
        y = center_y + math.sin(angle) * radius + jitter_y

        opacity = 0.2 + 0.6 * v

        points.append((float(x), float(y)))
        opacities.append(opacity)

    if len(points) >= 2:
        grad_id = "radial_stroke"
        gradient = dwg.radialGradient(
            id=grad_id,
            center=(center_x, center_y),
            r=radius_max,
            gradientUnits="userSpaceOnUse",
        )
        gradient.add_stop_color(0.0, cfg.palette[0])
        gradient.add_stop_color(0.5, cfg.palette[1])
        gradient.add_stop_color(1.0, cfg.palette[2])
        dwg.defs.add(gradient)

        dwg.add(
            dwg.polyline(
                points,
                fill="none",
                stroke=f"url(#{grad_id})",
                stroke_width=f"{cfg.stroke_width:.3f}px",
                stroke_opacity=float(np.mean(opacities)) if opacities else 0.6,
                stroke_linecap="round",
                stroke_linejoin="round",
            )
        )

    # 6) Metadaten optional
    dwg.add(
        dwg.text(
            f"Source: {audio_path.name}",
            insert=(12, cfg.height - 12),
            fill=cfg.stroke,
            font_size="14px",
            opacity=0.65,
        )
    )

    dwg.save()
    print(f"SVG gespeichert: {svg_path} (Frames={frames})")


if __name__ == "__main__":
    config_path = ROOT / variables.CONFIG
    input_dir = ROOT / variables.INPUT
    output_dir = ROOT / variables.OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)

    with config_path.open("rb") as f:
        config: dict = tomllib.load(f)

    seed = _resolve_seed(config)
    cfg = AudioVizConfig(
        seed=seed,
        background=config["colors"]["bg"],
        palette=(
            config["colors"]["c1"],
            config["colors"]["c2"],
            config["colors"]["c3"],
        ),
        stroke=config["colors"]["stroke"],
    )
    width, height = _resolve_size(config, cfg)
    cfg.width = width
    cfg.height = height

    files = list_files_by_extension(input_dir, "mp3")
    audio_path = select_random_file(files, seed)

    out_path = output_dir / "tmp.svg"
    audio_to_svg(audio_path, out_path, cfg)  # pyright: ignore[reportArgumentType]
