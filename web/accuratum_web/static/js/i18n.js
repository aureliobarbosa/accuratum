// Translations: one JSON table per language in locales/. Markup carries only
// keys (data-i18n, data-i18n-placeholder, data-i18n-title); adding a language
// means adding one table and one <option>.
"use strict";

const I18N = (() => {
  const LANGUAGES = ["pt-BR", "en"];
  const DEFAULT = "pt-BR";
  let table = {};
  let current = DEFAULT;

  function stored() {
    try {
      return localStorage.getItem("lang");
    } catch {
      return null;
    }
  }

  function remember(lang) {
    try {
      localStorage.setItem("lang", lang);
    } catch {
      // Private windows may refuse storage; the choice then lasts the visit.
    }
  }

  function t(key, vars = {}) {
    const text = table[key] ?? key;
    return text.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? `{${name}}`);
  }

  function apply(root = document) {
    root.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
    root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => (el.placeholder = t(el.dataset.i18nPlaceholder)));
    root.querySelectorAll("[data-i18n-title]").forEach((el) => (el.title = t(el.dataset.i18nTitle)));
    document.documentElement.lang = current;
    document.title = t("page.title");
  }

  async function use(lang) {
    if (!LANGUAGES.includes(lang)) lang = DEFAULT;
    const response = await fetch(`locales/${lang}.json`);
    table = await response.json();
    current = lang;
    remember(lang);
    apply();
    document.dispatchEvent(new CustomEvent("languagechange"));
  }

  return { t, use, apply, get lang() { return current; }, initial: () => stored() || DEFAULT };
})();
