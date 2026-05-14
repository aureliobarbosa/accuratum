"""Polyline metadata and override selector contract.

Both ``Polyline.metadata`` (on the rendered plot) and ``LabelOverride.selector``
(on the user-editable Spec) use this same shape. They must agree by
construction: an override's selector matches a polyline iff every key in
the selector is present in the polyline's metadata with the same value.

Built-in kinds are documented here as ``TypedDict``s so type checkers can
catch shape mistakes. Plugins are free to define their own kinds; the
contract is purely structural.
"""

from __future__ import annotations

from typing import Literal, TypedDict


class DaylineMetadata(TypedDict):
    kind: Literal["dayline"]
    date: str  # "YYYY-MM-DD" in the spec's local timezone


class HourlineMetadata(TypedDict):
    kind: Literal["hourline"]
    hour: int
    minute: int


def selector_matches(selector: dict, metadata: dict) -> bool:
    """True iff every (key, value) in *selector* appears in *metadata*."""
    return all(metadata.get(k) == v for k, v in selector.items())
