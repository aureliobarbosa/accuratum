"""File I/O for a project folder: ``project.json`` plus ``polylines.npz``.

Both files carry the spec's hash (:func:`accuratum.core.spec.spec_hash`).
On load:

- the hash of the spec in ``project.json`` must match the hash stored next
  to it; otherwise the spec was hand-edited after the geometry was computed,
  and the project must be regenerated (:class:`StaleProjectError`);
- a missing ``polylines.npz`` is recomputed from the spec and written back.
  Labels are kept, since the geometry is identical;
- an ``npz`` computed from a different spec is rejected.
"""

import json
from pathlib import Path
from typing import Any

import numpy as np

from accuratum.core.builder import build_plot
from accuratum.core.project import (
    PROJECT_VERSION,
    Project,
    hints_from_dict,
    label_from_dict,
    plot_from_parts,
    polylines_from_arrays,
    polylines_to_arrays,
    project_to_dict,
)
from accuratum.core.spec import spec_from_dict, spec_hash

PROJECT_FILE = "project.json"
DATASET_FILE = "polylines.npz"


class StaleProjectError(ValueError):
    """The spec and the saved geometry no longer belong together."""


def save_project(project: Project, directory: str | Path) -> None:
    """Write *project* into *directory*, creating it if needed."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / PROJECT_FILE).write_text(_format_project_json(project_to_dict(project)), encoding="utf-8")
    _save_dataset(project, directory)


def load_project(directory: str | Path) -> Project:
    """Load the project in *directory*. See the module docstring for the rules."""
    directory = Path(directory)
    data = json.loads((directory / PROJECT_FILE).read_text(encoding="utf-8"))
    version = data.get("version", PROJECT_VERSION)
    if version > PROJECT_VERSION:
        raise ValueError(
            f"project in {directory} declares version {version}; this build only "
            f"understands up to {PROJECT_VERSION}. Upgrade the package."
        )

    spec = spec_from_dict(data["spec"])
    expected = spec_hash(spec)
    if data.get("spec_hash") != expected:
        raise StaleProjectError(
            f"the spec in {directory / PROJECT_FILE} was edited after its geometry was computed; "
            "regenerate the project (label edits will be lost)."
        )

    labels = [label_from_dict(lbl) for lbl in data.get("labels", [])]
    dataset = directory / DATASET_FILE
    if dataset.is_file():
        with np.load(dataset, allow_pickle=False) as npz:
            if str(npz["spec_hash"]) != expected:
                raise StaleProjectError(f"{dataset} was computed from a different spec than {PROJECT_FILE}.")
            polylines = polylines_from_arrays(dict(npz))
    else:
        polylines = build_plot(spec).polylines

    project = Project(
        spec=spec,
        plot=plot_from_parts(polylines, labels),
        render=hints_from_dict(data.get("render", {})),
        provenance=data.get("provenance", {}),
    )
    if not dataset.is_file():
        _save_dataset(project, directory)
    return project


def _save_dataset(project: Project, directory: Path) -> None:
    arrays = polylines_to_arrays(project.plot.polylines)
    np.savez_compressed(directory / DATASET_FILE, spec_hash=np.array(spec_hash(project.spec)), **arrays)


def _format_project_json(data: dict[str, Any]) -> str:
    """Pretty JSON that stays short to read and edit: one label per line, and
    lists of numbers (rects, sizes) inline."""
    return _pretty(data, 0) + "\n"


def _pretty(value: Any, level: int) -> str:
    pad = "  " * (level + 1)
    if isinstance(value, dict) and value:
        items = [f"{pad}{json.dumps(k)}: {_pretty_item(k, v, level + 1)}" for k, v in value.items()]
        return "{\n" + ",\n".join(items) + "\n" + "  " * level + "}"
    if isinstance(value, list) and value and any(isinstance(v, (dict, list)) for v in value):
        return "[\n" + ",\n".join(pad + _pretty(v, level + 1) for v in value) + "\n" + "  " * level + "]"
    return json.dumps(value)


def _pretty_item(key: str, value: Any, level: int) -> str:
    if key == "labels" and value:
        pad = "  " * (level + 1)
        return "[\n" + ",\n".join(pad + json.dumps(lbl) for lbl in value) + "\n" + "  " * level + "]"
    return _pretty(value, level)
