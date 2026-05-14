"""Render-side knobs — separate from :class:`SundialSpec` to keep specs portable.

``RenderHints`` carries things that are local to a single render or
machine: overlay image paths, canvas size in millimeters, fonts, colors.
A saved spec is shareable; a saved hints file (when we have one) is not.
Renderers take ``(plot, hints)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Overlay:
    image_path: str
    rect: tuple[float, float, float, float]


@dataclass
class RenderHints:
    overlays: list[Overlay] = field(default_factory=list)
    figsize: tuple[float, float] = (8.0, 6.0)
    canvas_size_mm: tuple[float, float] | None = None
    units: str = "mm"
    line_color: str = "green"
    line_width: float = 0.5
    label_color: str = "black"
    label_fontsize: float = 7.0
