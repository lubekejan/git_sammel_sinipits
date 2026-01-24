#!/usr/bin/env uv run
"""File utility helpers used across scripts."""

from pathlib import Path
from typing import Optional


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
    source: Path, target: Optional[Path] = None, dpi: Optional[float] = None
) -> Path:
    """
    Convert an SVG file to PNG using cairosvg.
    """
    if not source.exists():
        raise FileNotFoundError(source)

    output_path = target or source.with_suffix(".png")
    effective_dpi = 96 if dpi is None else int(dpi)

    try:
        import cairosvg
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "cairosvg is required for svg_to_png (add to pyproject.toml)."
        ) from exc

    cairosvg.svg2png(url=str(source), write_to=str(output_path), dpi=effective_dpi)
    return output_path
