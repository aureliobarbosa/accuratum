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


LANGUAGES = ["pt-BR", "en", "es", "fr"]


def test_every_language_has_the_same_keys():
    assert set(LOCALES) == set(LANGUAGES)
    for lang in LANGUAGES:
        assert list(LOCALES[lang]) == list(LOCALES["pt-BR"]), lang


@pytest.mark.parametrize("lang", LANGUAGES)
def test_every_language_is_offered(lang):
    assert f'<option value="{lang}">' in HTML
    assert f'"{lang}"' in (STATIC / "js" / "i18n.js").read_text(encoding="utf-8")


@pytest.mark.parametrize("lang", LANGUAGES)
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


def test_always_light_on_the_logo_white():
    # Owner's choice: white like the logo, whatever the visitor's dark-mode preference.
    css = (STATIC / "css" / "site.css").read_text(encoding="utf-8")
    assert "prefers-color-scheme" not in css
    assert "color-scheme: light" in css
    assert "--bg: #ffffff" in css
    assert '<meta name="color-scheme" content="light">' in HTML
