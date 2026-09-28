"""Structural tests for the SVG renderer.

These tests assert *shape* (right elements, right attributes, stable ids)
rather than pixel-level fidelity — that's Inkscape's job.
"""

import re
import xml.etree.ElementTree as ET

import numpy as np

from accuratum.core.hints import Overlay, RenderHints
from accuratum.core.plot import Label, Plot, Polyline
from accuratum.renderers.svg_backend import render

SVG = "{http://www.w3.org/2000/svg}"


def _minimal_plot() -> Plot:
    return Plot(
        polylines=[
            Polyline(
                kind="dayline",
                xs=np.array([-5.0, 0.0, 5.0]),
                ys=np.array([0.5, 0.0, 2.0]),
                metadata={"kind": "dayline", "date": "2026-01-15"},
            ),
            Polyline(
                kind="hourline",
                xs=np.array([-3.0, 3.0]),
                ys=np.array([2.0, -2.0]),
                metadata={"kind": "hourline", "hour": 7, "minute_offset": 0},
            ),
        ],
        labels=[
            Label(
                text="01/15",
                x=-5.0,
                y=0.5,
                ha="right",
                va="center",
                kind="dayline",
                selector={"kind": "dayline", "date": "2026-01-15", "end": "start"},
            ),
            Label(
                text="07h",
                x=-3.0,
                y=2.0,
                ha="center",
                va="top",
                kind="hourline",
                selector={"kind": "hourline", "hour": 7, "end": "start"},
            ),
            Label(
                text="07h",
                x=3.0,
                y=-2.0,
                ha="center",
                va="bottom",
                kind="hourline",
                selector={"kind": "hourline", "hour": 7, "end": "end"},
                hidden=True,
            ),
        ],
        plumb_xy=(0.0, 0.0),
        data_extent=10.0,
    )


def test_render_returns_well_formed_svg_string():
    svg = render(_minimal_plot())
    assert svg.startswith("<?xml")
    # parses without raising
    root = ET.fromstring(svg.split("\n", 1)[1])
    assert root.tag == f"{SVG}svg"


def test_canvas_size_uses_mm_units():
    svg = render(_minimal_plot(), RenderHints(canvas_size_mm=(6000.0, 2000.0)))
    root = ET.fromstring(svg.split("\n", 1)[1])
    assert root.attrib["width"] == "6000.0mm"
    assert root.attrib["height"] == "2000.0mm"


def test_viewbox_inverts_y_for_data_up_convention():
    svg = render(_minimal_plot())
    root = ET.fromstring(svg.split("\n", 1)[1])
    vb = root.attrib["viewBox"].split()
    # 4 numbers: x ymin_svg width height
    assert len(vb) == 4
    # y axis: viewBox y == -ymax_data + padding (negative because data +y is up)
    assert float(vb[1]) < 0


def test_polylines_present_and_y_is_flipped():
    svg = render(_minimal_plot())
    root = ET.fromstring(svg.split("\n", 1)[1])
    polylines = root.findall(f".//{SVG}polyline")
    assert len(polylines) == 2
    # First polyline: data ys = [0.5, 0.0, 2.0] -> SVG ys = [-0.5, 0.0, -2.0]
    points = polylines[0].attrib["points"]
    coords = re.findall(r"-?\d+\.\d+", points)
    assert float(coords[1]) == -0.5
    assert float(coords[5]) == -2.0


def test_labels_present_with_stable_selector_ids():
    svg = render(_minimal_plot())
    root = ET.fromstring(svg.split("\n", 1)[1])
    texts = root.findall(f".//{SVG}text")
    ids = {t.attrib.get("id") for t in texts}
    assert "label-dayline-2026-01-15-start" in ids
    assert "label-hourline-7-start" in ids


def test_hidden_labels_are_not_emitted():
    svg = render(_minimal_plot())
    root = ET.fromstring(svg.split("\n", 1)[1])
    ids = [t.attrib.get("id") for t in root.findall(f".//{SVG}text")]
    assert "label-hourline-7-end" not in ids
    assert len(ids) == 2


def test_label_anchor_and_baseline_mapping():
    svg = render(_minimal_plot())
    root = ET.fromstring(svg.split("\n", 1)[1])
    texts = root.findall(f".//{SVG}text")
    by_id = {t.attrib["id"]: t for t in texts}

    day = by_id["label-dayline-2026-01-15-start"]
    assert day.attrib["text-anchor"] == "end"
    assert day.attrib["dominant-baseline"] == "middle"

    hour = by_id["label-hourline-7-start"]
    assert hour.attrib["text-anchor"] == "middle"
    # va="top" + y-flip → "alphabetic" baseline (text above SVG y position)
    assert hour.attrib["dominant-baseline"] == "alphabetic"


def test_plumb_circle_present():
    svg = render(_minimal_plot())
    root = ET.fromstring(svg.split("\n", 1)[1])
    circles = root.findall(f".//{SVG}circle")
    assert len(circles) == 1
    assert float(circles[0].attrib["cx"]) == 0.0
    assert float(circles[0].attrib["cy"]) == 0.0


def test_overlays_embedded_as_data_uri(tmp_path):
    fake_png = tmp_path / "logo.png"
    # minimal 1x1 PNG bytes
    fake_png.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    hints = RenderHints(overlays=[Overlay(image_path=str(fake_png), rect=(0.1, 0.8, 0.1, 0.1))])
    svg = render(_minimal_plot(), hints)
    assert "data:image/png;base64," in svg


def test_empty_plot_returns_valid_svg():
    plot = Plot(polylines=[], labels=[], plumb_xy=(0.0, 0.0), data_extent=1.0)
    svg = render(plot)
    root = ET.fromstring(svg.split("\n", 1)[1])
    assert root.tag == f"{SVG}svg"
