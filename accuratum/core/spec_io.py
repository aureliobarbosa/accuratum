"""File I/O for :class:`SundialSpec` — JSON read/write.

Thin wrapper over :func:`spec_to_dict` / :func:`spec_from_dict`. Adds:

- pretty-printed JSON for hand-editing,
- a ``spec_version`` check that errors on unknown future versions.

Lives in :mod:`accuratum.core` because it's part of the data-model
contract (the schema is the Spec dataclasses); CLI argv handling stays
in :mod:`accuratum.cli`.
"""

import json
from pathlib import Path

from accuratum.core.spec import SPEC_VERSION, SundialSpec, spec_from_dict, spec_to_dict


def save_spec(spec: SundialSpec, path: str | Path) -> None:
    """Write *spec* to *path* as pretty-printed JSON (sorted keys)."""
    data = spec_to_dict(spec)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


def load_spec(path: str | Path) -> SundialSpec:
    """Load a spec from *path*. Raises ``ValueError`` on future versions."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    version = data.get("spec_version", SPEC_VERSION)
    if version > SPEC_VERSION:
        raise ValueError(
            f"spec at {path} declares version {version}; this build only "
            f"understands up to {SPEC_VERSION}. Upgrade the package."
        )
    return spec_from_dict(data)
