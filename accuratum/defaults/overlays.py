"""The default overlay images and render settings, and package image paths.

Package images are stored in project files as ``accuratum:<path>``, so a
project folder works on any machine with the package installed. Both
default overlays sit in the header band above ``RenderHints.axes_rect``.
"""

from importlib.resources import files

from accuratum.core.hints import Overlay, RenderHints

PACKAGE_PREFIX = "accuratum:"
DEFAULT_LABEL_FONTSIZE = 7.0
DEFAULT_OVERLAYS = {
    "logo": Overlay(image_path=PACKAGE_PREFIX + "fig/unb_basic.jpg", rect=(0.12, 0.82, 0.12, 0.12), name="logo"),
    "compass": Overlay(image_path=PACKAGE_PREFIX + "fig/rosa.png", rect=(0.78, 0.82, 0.12, 0.12), name="compass"),
}


def default_render_hints() -> RenderHints:
    """Render settings for a new project: the default overlays and label size."""
    return RenderHints(overlays=list(DEFAULT_OVERLAYS.values()), label_fontsize=DEFAULT_LABEL_FONTSIZE)


def resolve_image_path(path: str) -> str:
    """Turn an ``accuratum:`` path into a file path inside the installed package."""
    if not path.startswith(PACKAGE_PREFIX):
        return path
    return str(files("accuratum").joinpath(path.removeprefix(PACKAGE_PREFIX)))
