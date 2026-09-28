"""SVG renderer — turns a :class:`Plot` into an SVG document string.

Pure-Python via ``xml.etree``. Output uses real-world ``mm`` units (set
via :attr:`RenderHints.canvas_size_mm`), so a print shop can scale
directly to a 6 m × 2 m panel.

Labels are emitted as ``<text>`` elements with selector-derived ``id``
attributes — they're selectable and editable in Inkscape, which is the
killer feature for human-in-the-loop label nudging on big panels.

Coordinate convention: data ``+y`` points "up" on the rendered page.
SVG's native ``y`` points down, so all data ``y`` values are negated
on emission and the ``viewBox`` is set accordingly.
"""

import base64
import xml.etree.ElementTree as ET
from pathlib import Path

from accuratum.core.hints import RenderHints
from accuratum.core.plot import Label, Plot, Polyline

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)


def render(plot: Plot, hints: RenderHints | None = None) -> str:
    """Return an SVG document string rendering *plot*."""
    hints = hints or RenderHints()

    # Tight data bbox.
    data_xmin, data_xmax, data_ymin, data_ymax = _data_bbox(plot)
    data_w = data_xmax - data_xmin
    data_h = data_ymax - data_ymin

    # Margin around the data. TOP margin is large enough to hold overlays
    # (logo, compass) whose figure-coord rects sit at y≈0.75 by convention —
    # mirroring matplotlib's "figure has margins around the axes" so the
    # same default rects land above the data instead of on top of it.
    # Side and bottom margins fit endpoint labels.
    top_margin = 0.4 * data_h
    bottom_margin = 0.05 * data_h
    side_margin = 0.15 * data_w

    xmin = data_xmin - side_margin
    xmax = data_xmax + side_margin
    ymin = data_ymin - bottom_margin
    ymax = data_ymax + top_margin
    width_data = xmax - xmin
    height_data = ymax - ymin

    canvas_w_mm, canvas_h_mm = hints.canvas_size_mm or (297.0, 210.0)

    svg = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "width": f"{canvas_w_mm}mm",
            "height": f"{canvas_h_mm}mm",
            # viewBox: (x, y_svg_top, w, h). y_svg_top = -ymax so data +y points up.
            "viewBox": f"{xmin} {-ymax} {width_data} {height_data}",
            "preserveAspectRatio": "xMidYMid meet",
        },
    )

    # Stroke widths scale with data extent so they render at a sensible size.
    line_width = 0.003 * max(width_data, height_data)

    lines_group = ET.SubElement(
        svg,
        f"{{{SVG_NS}}}g",
        {"id": "polylines", "fill": "none", "stroke": hints.line_color, "stroke-width": f"{line_width}"},
    )
    for poly in plot.polylines:
        _emit_polyline(lines_group, poly)

    plumb_group = ET.SubElement(svg, f"{{{SVG_NS}}}g", {"id": "plumb"})
    xp, yp = plot.plumb_xy
    ET.SubElement(
        plumb_group,
        f"{{{SVG_NS}}}circle",
        {
            "cx": f"{xp}",
            "cy": f"{-yp}",
            "r": f"{line_width * 2}",
            "fill": "none",
            "stroke": "black",
            "stroke-width": f"{line_width}",
        },
    )

    labels_group = ET.SubElement(
        svg, f"{{{SVG_NS}}}g", {"id": "labels", "font-family": "sans-serif", "fill": hints.label_color}
    )
    for label in plot.labels:
        _emit_label(labels_group, label, hints.label_fontsize, data_extent=max(width_data, height_data))

    if hints.overlays:
        overlays_group = ET.SubElement(svg, f"{{{SVG_NS}}}g", {"id": "overlays"})
        for i, overlay in enumerate(hints.overlays):
            _emit_overlay(overlays_group, overlay, i, xmin, ymin, width_data, height_data)

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(svg, encoding="unicode")


# --- internals ---------------------------------------------------------------


def _data_bbox(plot: Plot) -> tuple[float, float, float, float]:
    xs = []
    ys = []
    for poly in plot.polylines:
        if poly.xs.size:
            xs.extend([float(poly.xs.min()), float(poly.xs.max())])
            ys.extend([float(poly.ys.min()), float(poly.ys.max())])
    if not xs:
        return -1.0, 1.0, -1.0, 1.0
    return min(xs), max(xs), min(ys), max(ys)


def _emit_polyline(parent: ET.Element, poly: Polyline) -> None:
    if poly.xs.size < 2:
        return
    points = " ".join(f"{float(x):.4f},{-float(y):.4f}" for x, y in zip(poly.xs, poly.ys))
    selector_id = _selector_id(poly.metadata)
    attrs = {"points": points}
    if selector_id:
        attrs["id"] = f"poly-{selector_id}"
    ET.SubElement(parent, f"{{{SVG_NS}}}polyline", attrs)


# Map matplotlib (ha, va) to SVG (text-anchor, dominant-baseline).
# Note y is flipped on emission, so the va meaning inverts.
_HA_TO_ANCHOR = {"left": "start", "center": "middle", "right": "end"}
_VA_TO_BASELINE_FLIPPED = {
    "top": "alphabetic",  # text below data point -> above SVG point
    "center": "middle",
    "bottom": "hanging",  # text above data point -> below SVG point
}


def _emit_label(parent: ET.Element, label: Label, fontsize_pt: float, data_extent: float) -> None:
    # Font size in data units: rough scaling — 1 pt ≈ 0.353 mm, but we're in
    # data coords, not mm. Use 0.5% of data_extent per point as a sensible default.
    font_size_data = fontsize_pt * 0.005 * data_extent
    selector_id = _selector_id(label.selector)
    attrs = {
        "x": f"{label.x:.4f}",
        "y": f"{-label.y:.4f}",
        "text-anchor": _HA_TO_ANCHOR.get(label.ha, "middle"),
        "dominant-baseline": _VA_TO_BASELINE_FLIPPED.get(label.va, "middle"),
        "font-size": f"{font_size_data}",
    }
    if selector_id:
        attrs["id"] = f"label-{selector_id}"
    text_el = ET.SubElement(parent, f"{{{SVG_NS}}}text", attrs)
    text_el.text = label.text


def _emit_overlay(
    parent: ET.Element,
    overlay,
    index: int,
    xmin: float,
    ymin: float,
    width: float,
    height: float,
) -> None:
    """Embed an overlay image as a base64 data URI at the given fig-coord rect."""
    left, bottom, w, h = overlay.rect  # 0..1 in figure coords
    x = xmin + left * width
    y_top_data = ymin + (bottom + h) * height
    w_data = w * width
    h_data = h * height
    mime, b64 = _image_data_uri(overlay.image_path)
    ET.SubElement(
        parent,
        f"{{{SVG_NS}}}image",
        {
            "x": f"{x:.4f}",
            "y": f"{-y_top_data:.4f}",
            "width": f"{w_data:.4f}",
            "height": f"{h_data:.4f}",
            f"{{{XLINK_NS}}}href": f"data:{mime};base64,{b64}",
            "id": f"overlay-{index}",
        },
    )


def _image_data_uri(path: str) -> tuple[str, str]:
    suffix = Path(path).suffix.lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml"}.get(
        suffix, "application/octet-stream"
    )
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    return mime, b64


def _selector_id(selector: dict) -> str:
    """Stable id slug from a selector dict, e.g. {'kind':'dayline','date':'2026-01-15'} -> 'dayline-2026-01-15'."""
    if not selector:
        return ""
    parts = []
    for key in sorted(selector.keys()):
        if key == "kind":
            parts.insert(0, str(selector[key]))
        else:
            parts.append(str(selector[key]))
    return "-".join(parts).replace("/", "-").replace(" ", "_")
