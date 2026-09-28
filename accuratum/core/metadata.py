"""Polyline metadata contract.

``Polyline.metadata`` identifies a line independently of its rendered text.
A label's ``selector`` is the same identity plus ``end`` (``"start"`` or
``"end"``), naming which endpoint the label sits at.

Built-in kinds are documented here as ``TypedDict``s so type checkers can
catch shape mistakes. Plugins are free to define their own kinds; the
contract is purely structural.
"""

from typing import Literal, TypedDict


class DaylineMetadata(TypedDict):
    kind: Literal["dayline"]
    date: str  # "YYYY-MM-DD" in the spec's local timezone


class HourlineMetadata(TypedDict):
    kind: Literal["hourline"]
    hour: int  # canonical target hour in 0..23, local timezone — stable identity
    minute_offset: int  # signed minutes between the sampled middle and ``hour:00``
