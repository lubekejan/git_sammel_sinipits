#!/usr/bin/env uv run
"""File utility helpers used across scripts."""

import os
import sys
from pathlib import Path
from typing import Iterable


def rename_file(source: Path, new_name: str) -> Path:
    """
    Rename a file while keeping its current suffix unless new_name has one.
    Example: rename_file(Path("output/tmp.svg"), "foo_bar") -> output/foo_bar.svg
    """
    if not source.exists():
        raise FileNotFoundError(source)
    if not new_name:
        raise ValueError("new_name must be a non-empty string")

    target_name = new_name if Path(new_name).suffix else f"{new_name}{source.suffix}"
    target = source.with_name(Path(target_name).name)
    return source.rename(target)


def svg_to_png(
    source: Path, target: Path | None = None, dpi: float | None = None
) -> Path:
    """
    Convert an SVG file to PNG using cairosvg.
    """
    if not source.exists():
        raise FileNotFoundError(source)

    output_path = target or source.with_suffix(".png")
    effective_dpi = 96 if dpi is None else int(dpi)

    if sys.platform == "darwin":
        _ensure_macos_cairo_path()

    try:
        import cairosvg
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "cairosvg is required for svg_to_png (add to pyproject.toml)."
        ) from exc

    cairosvg.svg2png(url=str(source), write_to=str(output_path), dpi=effective_dpi)
    return output_path


def _ensure_macos_cairo_path() -> None:
    if os.environ.get("DYLD_FALLBACK_LIBRARY_PATH"):
        return

    candidates = ["/opt/homebrew/lib", "/usr/local/lib"]
    existing = [path for path in candidates if Path(path).is_dir()]
    if not existing:
        return

    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(existing)


def list_files_by_extension(directory: Path, extension: str) -> list[Path]:
    """
    Return sorted files in directory that match the given extension.

    Extension can be passed with or without leading dot, e.g. "mp3" or ".mp3".
    """
    if not directory.exists():
        raise FileNotFoundError(directory)
    if not directory.is_dir():
        raise NotADirectoryError(directory)

    normalized = extension.lower().lstrip(".")
    if not normalized:
        raise ValueError("extension must be a non-empty string")

    pattern = f"*.{normalized}"
    return sorted(path for path in directory.glob(pattern) if path.is_file())


def select_random_file(
    files: Iterable[Path], seed: int, *, require_non_empty: bool = True
) -> Path | None:
    """
    Select a random file from iterable using a deterministic seed.

    Returns None when files is empty and require_non_empty is False.
    """
    pool = list(files)
    if not pool:
        if require_non_empty:
            raise FileNotFoundError("No matching files found.")
        return None

    rng = __import__("random").Random(seed)
    return rng.choice(pool)
