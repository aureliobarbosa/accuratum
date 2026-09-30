import os

from accuratum.core.hints import RenderHints
from accuratum.defaults.overlays import DEFAULT_OVERLAYS, PACKAGE_PREFIX, default_render_hints, resolve_image_path


def test_default_overlays_sit_in_the_header_above_the_drawing():
    left, bottom, width, height = RenderHints().axes_rect
    for overlay in DEFAULT_OVERLAYS.values():
        assert overlay.rect[1] >= bottom + height
        assert overlay.rect[1] + overlay.rect[3] <= 1.0


def test_package_images_resolve_to_existing_files():
    for overlay in DEFAULT_OVERLAYS.values():
        assert overlay.image_path.startswith(PACKAGE_PREFIX)
        assert os.path.isfile(resolve_image_path(overlay.image_path))


def test_other_paths_are_left_alone():
    assert resolve_image_path("/some/where/logo.png") == "/some/where/logo.png"


def test_default_render_hints_carry_the_default_overlays():
    hints = default_render_hints()
    assert hints.overlays == list(DEFAULT_OVERLAYS.values())
    hints.overlays.clear()
    assert default_render_hints().overlays  # each call gets its own list
