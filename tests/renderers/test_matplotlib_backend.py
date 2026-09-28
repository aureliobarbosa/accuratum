"""Structural tests for the matplotlib renderer. The look is checked visually."""

import numpy as np

from accuratum.core.plot import Label, Plot, Polyline
from accuratum.renderers.matplotlib_backend import render


def test_hidden_labels_are_not_drawn():
    plot = Plot(
        polylines=[
            Polyline(
                kind="hourline",
                xs=np.array([-3.0, 3.0]),
                ys=np.array([2.0, -2.0]),
                metadata={"kind": "hourline", "hour": 7, "minute_offset": 0},
            )
        ],
        labels=[
            Label(text="shown", x=-3.0, y=2.0, ha="center", va="top", kind="hourline"),
            Label(text="gone", x=3.0, y=-2.0, ha="center", va="bottom", kind="hourline", hidden=True),
        ],
        data_extent=6.0,
    )
    fig, ax = render(plot)
    texts = [t.get_text() for t in ax.texts]
    assert "shown" in texts
    assert "gone" not in texts
