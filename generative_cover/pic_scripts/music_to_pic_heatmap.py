#!/usr/bin/env uv run
"""Generate an audio-based SVG using input files and config/variables paths."""

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

    # 2) Mel-Spektrogramm
    S = librosa.feature.melspectrogram(
        y=y,
        sr=sr,
        n_mels=cfg.n_mels,
        hop_length=cfg.hop_length,
        fmin=cfg.fmin,
        fmax=cfg.fmax,
        power=cfg.power,
    )

    # 3) In dB skalieren und normalisieren (0..1)
    S_db = librosa.power_to_db(S, ref=np.max)
    S_db = np.clip(S_db, cfg.db_min, 0.0)

    # Normierung: db_min -> 0, 0 dB -> 1
    A = (S_db - cfg.db_min) / (0.0 - cfg.db_min)
    A = np.clip(A, 0.0, 1.0)

    # Optional: Zeitachse auf sinnvolle Spaltenzahl reduzieren (Dateigröße)
    # Ziel: ~1200 Spalten max (anpassbar)
    max_cols = 1200
    if A.shape[1] > max_cols:
        factor = int(np.ceil(A.shape[1] / max_cols))
        # Downsample per Mittelwert über Blöcke
        new_cols = int(np.ceil(A.shape[1] / factor))
        A_ds = np.zeros((A.shape[0], new_cols), dtype=np.float32)
        for i in range(new_cols):
            start = i * factor
            end = min((i + 1) * factor, A.shape[1])
            A_ds[:, i] = A[:, start:end].mean(axis=1)
        A = A_ds

    n_rows, n_cols = A.shape

    # 4) SVG initialisieren
    dwg = svgwrite.Drawing(str(svg_path), size=(cfg.width, cfg.height))
    dwg.add(dwg.rect(insert=(0, 0), size=(cfg.width, cfg.height), fill=cfg.background))

    cell_w = cfg.width / n_cols
    cell_h = cfg.height / n_rows

    # 5) Zeichnen: Rechtecke als Vektorelemente
    # Farbabbildung: einfache "glow"-Palette über HSL/HSV-ähnliche Logik (ohne externe libs)
    # Du kannst das beliebig anpassen.
    for r in range(n_rows):
        y0 = cfg.height - (r + 1) * cell_h
        row = A[r, :]
        for c in range(n_cols):
            v = float(row[c])
            if v < cfg.draw_threshold:
                continue

            x0 = c * cell_w

            fill = _pick_palette_color(v, cfg.palette)
            opacity = 0.15 + 0.85 * v

            dwg.add(
                dwg.rect(
                    insert=(x0, y0),
                    size=(cell_w + 0.2, cell_h + 0.2),
                    fill=fill,
                    fill_opacity=opacity,
                    stroke="none",
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
    print(f"SVG gespeichert: {svg_path} (Rows={n_rows}, Cols={n_cols})")


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
