"""Structural checks on the page; its look is checked in a browser."""

import json
import re
from pathlib import Path

import pytest

STATIC = Path(__file__).parents[1] / "accuratum_web" / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
JS = "\n".join(p.read_text(encoding="utf-8") for p in (STATIC / "js").glob("*.js"))
LOCALES = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (STATIC / "locales").glob("*.json")}


def _used_keys() -> set[str]:
    in_html = re.findall(r'data-i18n(?:-placeholder|-title)?="([^"]+)"', HTML)
    in_js = re.findall(r'I18N\.t\("([^"]+)"', JS)
    return set(in_html) | set(in_js) | {"page.title"}


def test_every_language_has_the_same_keys():
    assert set(LOCALES) == {"pt-BR", "en"}
    assert list(LOCALES["pt-BR"]) == list(LOCALES["en"])


@pytest.mark.parametrize("lang", ["pt-BR", "en"])
def test_every_key_in_the_page_is_translated(lang):
    assert _used_keys() <= set(LOCALES[lang])


def test_no_inline_scripts_or_styles():
    # The CSP allows neither; they would silently not run.
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", HTML)
    assert "<style" not in HTML
    assert not re.search(r"\sstyle=", HTML)
    assert not re.search(r"\son[a-z]+=", HTML)


def test_no_scripts_or_styles_from_other_sites():
    for ref in re.findall(r'(?:src|href)="([^"]+)"', HTML):
        if ref.startswith("http"):
            assert ref.startswith("https://github.com/"), ref  # links only, nothing loaded
