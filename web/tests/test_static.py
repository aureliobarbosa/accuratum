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


def test_the_brand_is_the_only_home_link_in_the_top_bar():
    # Owner's choice (issue #3): the clickable "Accuratum" brand already goes home,
    # so a separate "Home" link in the nav would be redundant.
    topbar = re.search(r'<header class="topbar">(.*?)</header>', HTML, re.S).group(1)
    assert '<a class="brand" href="#/">' in topbar
    assert re.findall(r'href="#/"', topbar) == ['href="#/"']
    assert "nav.home" not in HTML
    for lang in LANGUAGES:
        assert "nav.home" not in LOCALES[lang], lang


def test_the_last_details_button_says_generate():
    # Issue #6: Details is the last step, so its button generates, not "Next".
    button = re.search(r'<button id="generate".*?</button>', HTML, re.S).group(0)
    assert 'data-i18n="details.generate"' in button
    assert "common.next" not in button
    assert LOCALES["en"]["details.generate"] == "Generate"


@pytest.mark.parametrize("lang", LANGUAGES)
def test_the_wait_message_counts_instead_of_promising_a_time(lang):
    # Issue #6: "about 15 seconds" was a dev-machine figure; the site took a minute.
    message = LOCALES[lang]["details.computing"]
    assert not re.search(r"\d", message), message
    assert "{seconds}" in message
    assert "setInterval" in JS and "clearInterval" in JS


def test_the_result_page_says_how_long_the_sundial_took():
    # Issue #6: the owner checks future speed-ups against this figure.
    result = re.search(r'<section id="view-result".*?</section>', HTML, re.S).group(0)
    assert 'id="elapsed"' in result
    for lang in LANGUAGES:
        assert "{seconds}" in LOCALES[lang]["result.elapsed"], lang


def test_the_footer_shows_the_site_and_library_versions():
    # So a deploy is visible on the page itself, even one without visible changes.
    footer = re.search(r'<footer class="site-footer">(.*?)</footer>', HTML, re.S).group(1)
    assert 'id="version"' in footer
    assert 'fetch("api/health")' in JS
    assert 'I18N.t("footer.version"' in JS
    for lang in LANGUAGES:
        assert {"{site}", "{library}"} <= set(re.findall(r"\{\w+\}", LOCALES[lang]["footer.version"])), lang


# --- long texts: one HTML fragment per language ---------------------------------

TEXTS = ["about"]
ALLOWED_TAGS = {"p", "a", "em", "strong"}


def _fragment(name: str, lang: str) -> str:
    return (STATIC / "locales" / name / f"{lang}.html").read_text(encoding="utf-8")


def _paragraphs_of_html(html: str) -> list[str]:
    paragraphs = re.findall(r"<p>(.*?)</p>", html, re.S)
    return [" ".join(re.sub(r"<[^>]+>", "", p).split()) for p in paragraphs]


@pytest.mark.parametrize("name", TEXTS)
@pytest.mark.parametrize("lang", LANGUAGES)
def test_every_long_text_exists_in_every_language(name, lang):
    assert _fragment(name, lang).strip()


@pytest.mark.parametrize("name", TEXTS)
@pytest.mark.parametrize("lang", LANGUAGES)
def test_long_texts_use_only_plain_markup(name, lang):
    # The fragment goes in with innerHTML: no scripts, styles, handlers or loaded media.
    html = _fragment(name, lang)
    assert set(re.findall(r"<([a-z0-9]+)", html)) <= ALLOWED_TAGS
    assert not re.search(r"\s(on[a-z]+|style|src)=", html)
    for attrs in re.findall(r"<a\s([^>]*)>", html):
        assert re.fullmatch(r'href="https://[^"]+"', attrs), attrs


@pytest.mark.parametrize("name", TEXTS)
@pytest.mark.parametrize("lang", LANGUAGES)
def test_translations_keep_the_shape_of_the_original(name, lang):
    original, translated = _fragment(name, "pt-BR"), _fragment(name, lang)
    assert len(_paragraphs_of_html(translated)) == len(_paragraphs_of_html(original))
    for tag in ALLOWED_TAGS:
        assert translated.count(f"<{tag}") == original.count(f"<{tag}"), tag
    assert "https://github.com/aureliobarbosa/accuratum" in translated


def test_the_portuguese_about_is_the_owners_text_word_for_word():
    # web/docs/about.md is the owner's hand-written text; the page must not drift from it.
    markdown = (Path(__file__).parents[1] / "docs" / "about.md").read_text(encoding="utf-8")
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", markdown).replace("*", "")
    paragraphs = [" ".join(p.split()) for p in plain.split("\n\n") if p.strip()]
    assert _paragraphs_of_html(_fragment("about", "pt-BR")) == paragraphs


def test_the_about_view_loads_its_long_text():
    about = re.search(r'<section id="view-about".*?</section>', HTML, re.S).group(0)
    assert 'data-i18n-html="about"' in about
    assert "common.wip" not in about
    assert "locales/${name}/${lang}.html" in JS
