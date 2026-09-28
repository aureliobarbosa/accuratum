"""A sundial project: the spec, its computed plot, render settings and provenance.

A project lives in a folder. ``project.json`` holds everything a human edits
or needs to regenerate the geometry (spec, render hints, labels, provenance);
``polylines.npz`` holds the computed geometry. Labels are plain data there:
move one by editing ``x``/``y``, hide or restore one with ``hidden``, or add
one by appending ``{"text": ..., "x": ..., "y": ...}``.

This module holds the pure conversions; :mod:`accuratum.core.project_io`
reads and writes the files.
"""

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from accuratum.core.hints import Overlay, RenderHints
from accuratum.core.plot import Label, Plot, Polyline, data_extent
from accuratum.core.spec import SundialSpec, spec_hash, spec_to_dict

PROJECT_FORMAT = "accuratum-project"
PROJECT_VERSION = 2
LABEL_DECIMALS = 4


@dataclass
class Project:
    spec: SundialSpec
    plot: Plot
    render: RenderHints = field(default_factory=RenderHints)
    provenance: dict[str, str] = field(default_factory=dict)


def project_to_dict(project: Project) -> dict[str, Any]:
    """The ``project.json`` content: everything except the polyline geometry."""
    return {
        "format": PROJECT_FORMAT,
        "version": PROJECT_VERSION,
        "provenance": project.provenance,
        "spec": spec_to_dict(project.spec),
        "spec_hash": spec_hash(project.spec),
        "render": asdict(project.render),
        "labels": [label_to_dict(lbl) for lbl in project.plot.labels],
    }


def plot_from_parts(polylines: list[Polyline], labels: list[Label]) -> Plot:
    """Rebuild a :class:`Plot`; ``data_extent`` is derived from the polylines."""
    return Plot(polylines=polylines, labels=labels, plumb_xy=(0.0, 0.0), data_extent=data_extent(polylines))


# --- labels -------------------------------------------------------------------


def label_to_dict(label: Label) -> dict[str, Any]:
    return {
        "text": label.text,
        "x": round(label.x, LABEL_DECIMALS),
        "y": round(label.y, LABEL_DECIMALS),
        "hidden": label.hidden,
        "ha": label.ha,
        "va": label.va,
        "kind": label.kind,
        "selector": label.selector,
    }


def label_from_dict(data: dict[str, Any]) -> Label:
    """Only ``text``, ``x`` and ``y`` are required, so a hand-added label can be short."""
    return Label(
        text=data["text"],
        x=float(data["x"]),
        y=float(data["y"]),
        ha=data.get("ha", "center"),
        va=data.get("va", "center"),
        kind=data.get("kind", "custom"),
        selector=data.get("selector", {}),
        hidden=data.get("hidden", False),
    )


# --- render hints -------------------------------------------------------------


def hints_from_dict(data: dict[str, Any]) -> RenderHints:
    """Inverse of ``asdict(hints)``: rebuilds overlays and re-tuplizes sizes."""
    data = dict(data)
    data["overlays"] = [Overlay(image_path=o["image_path"], rect=tuple(o["rect"])) for o in data.get("overlays", [])]
    if "figsize" in data:
        data["figsize"] = tuple(data["figsize"])
    if data.get("canvas_size_mm") is not None:
        data["canvas_size_mm"] = tuple(data["canvas_size_mm"])
    return RenderHints(**data)


# --- polylines <-> flat arrays --------------------------------------------------


def polylines_to_arrays(polylines: list[Polyline]) -> dict[str, np.ndarray]:
    """Flatten *polylines* into arrays for ``np.savez``.

    ``x``/``y`` hold every sample back to back and line ``i`` spans
    ``offsets[i]:offsets[i+1]``. Per-line metadata goes in parallel arrays,
    with ``""`` / ``-1`` where a key is absent.
    """
    lengths = [p.xs.size for p in polylines]
    return {
        "x": np.concatenate([p.xs for p in polylines]) if polylines else np.empty(0),
        "y": np.concatenate([p.ys for p in polylines]) if polylines else np.empty(0),
        "offsets": np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64),
        "kind": np.array([p.kind for p in polylines], dtype=str),
        "date": np.array([p.metadata.get("date", "") for p in polylines], dtype=str),
        "hour": np.array([p.metadata.get("hour", -1) for p in polylines], dtype=np.int64),
        "minute_offset": np.array([p.metadata.get("minute_offset", -1) for p in polylines], dtype=np.int64),
    }


def polylines_from_arrays(arrays: dict[str, np.ndarray]) -> list[Polyline]:
    """Inverse of :func:`polylines_to_arrays`."""
    offsets = arrays["offsets"]
    polylines = []
    for i, kind in enumerate(arrays["kind"]):
        kind = str(kind)
        lo, hi = int(offsets[i]), int(offsets[i + 1])
        metadata: dict[str, Any] = {}
        if kind == "dayline" and arrays["date"][i]:
            metadata = {"kind": kind, "date": str(arrays["date"][i])}
        elif kind == "hourline" and arrays["hour"][i] >= 0:
            metadata = {"kind": kind, "hour": int(arrays["hour"][i]), "minute_offset": int(arrays["minute_offset"][i])}
        polylines.append(Polyline(kind=kind, xs=arrays["x"][lo:hi], ys=arrays["y"][lo:hi], metadata=metadata))
    return polylines
