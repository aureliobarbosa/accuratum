// The four views of web/docs/UX.md: home → location → details → result.
// Hash routing keeps the browser's Back button working.
"use strict";

const MAX_LATITUDE = 75;
const MAX_IMAGE_BYTES = 2 * 1024 * 1024;
const NOMINATIM = "https://nominatim.openstreetmap.org";
const NOMINATIM_GAP_MS = 1100; // Nominatim allows 1 request per second

const state = {
  place: null, // {lat, lon, name}
  result: null, // {pngs: [...], pdf: "..."}
  images: { logo: null, compass: null }, // File, or null for the default
  pdfUrl: null,
};

const $ = (selector) => document.querySelector(selector);

// --- routing -----------------------------------------------------------------

const VIEWS = ["home", "location", "details", "result", "about", "contact"];

function route() {
  let view = location.hash.replace(/^#\/?/, "") || "home";
  if (!VIEWS.includes(view)) view = "home";
  if (view === "details" && !state.place) view = "location";
  if (view === "result" && !state.result) view = state.place ? "details" : "location";
  if (location.hash !== `#/${view === "home" ? "" : view}`) {
    history.replaceState(null, "", `#/${view === "home" ? "" : view}`);
  }
  VIEWS.forEach((name) => ($(`#view-${name}`).hidden = name !== view));
  if (view === "location") showMap();
  if (view === "details") fillDetails();
  window.scrollTo(0, 0);
}

// --- location: map and search ------------------------------------------------

let map = null;
let marker = null;
let lastNominatim = 0;

function showMap() {
  if (!map) {
    map = L.map("map", { worldCopyJump: true }).setView([0, -20], 2);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
    map.on("click", (event) => {
      const { lat, lng } = event.latlng.wrap();
      choosePlace(lat, lng, null);
      reverseGeocode(lat, lng);
    });
  }
  map.invalidateSize(); // the container was hidden until now
  $("#place").textContent = state.place ? I18N.t("location.chosen", { place: placeLabel() }) : I18N.t("location.hint");
}

function formatCoords(lat, lon) {
  // The library's default title: 15.78° S, 47.92° W
  const ns = lat < 0 ? "S" : "N";
  const ew = lon < 0 ? "W" : "E";
  return `${Math.abs(lat).toFixed(2)}° ${ns}, ${Math.abs(lon).toFixed(2)}° ${ew}`;
}

function placeLabel() {
  return state.place.name || formatCoords(state.place.lat, state.place.lon);
}

function choosePlace(lat, lon, name) {
  if (Math.abs(lat) > MAX_LATITUDE) {
    $("#place").textContent = I18N.t("location.outOfRange", { lat: lat.toFixed(1) });
    return false;
  }
  const changed = !state.place || state.place.lat !== lat || state.place.lon !== lon;
  state.place = { lat, lon, name };
  if (changed) state.result = null;
  if (marker) marker.setLatLng([lat, lon]);
  else marker = L.marker([lat, lon]).addTo(map);
  $("#place").textContent = I18N.t("location.chosen", { place: placeLabel() });
  $("#to-details").disabled = false;
  resetTitles();
  return true;
}

async function nominatim(path, params) {
  const wait = lastNominatim + NOMINATIM_GAP_MS - Date.now();
  if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait));
  lastNominatim = Date.now();
  const query = new URLSearchParams({ format: "jsonv2", "accept-language": I18N.lang, ...params });
  const response = await fetch(`${NOMINATIM}/${path}?${query}`);
  if (!response.ok) throw new Error(`Nominatim ${response.status}`);
  return response.json();
}

async function reverseGeocode(lat, lon) {
  try {
    const found = await nominatim("reverse", { lat, lon, zoom: 16 });
    const a = found.address || {};
    const name = found.name || a.city || a.town || a.village || a.county || null;
    if (name && state.place && state.place.lat === lat && state.place.lon === lon) {
      state.place.name = name;
      $("#place").textContent = I18N.t("location.chosen", { place: placeLabel() });
      resetTitles();
    }
  } catch {
    // No name: the title falls back to the coordinates.
  }
}

async function search(event) {
  event.preventDefault();
  const q = $("#search-q").value.trim();
  if (!q) return;
  const button = $("#search-form button");
  const list = $("#search-results");
  button.disabled = true;
  list.replaceChildren();
  $("#search-status").textContent = I18N.t("location.searching");
  try {
    const results = await nominatim("search", { q, limit: 5 });
    $("#search-status").textContent = results.length ? "" : I18N.t("location.noResults");
    for (const r of results) {
      const item = document.createElement("li");
      const pick = document.createElement("button");
      pick.type = "button";
      pick.className = "link";
      pick.textContent = r.display_name;
      pick.addEventListener("click", () => {
        const lat = Number(r.lat);
        const lon = Number(r.lon);
        if (choosePlace(lat, lon, r.name || r.display_name.split(",")[0])) {
          map.setView([lat, lon], 14);
          list.replaceChildren();
        }
      });
      item.append(pick);
      list.append(item);
    }
  } catch {
    $("#search-status").textContent = I18N.t("location.searchFailed");
  } finally {
    button.disabled = false;
  }
}

// --- details -----------------------------------------------------------------

const form = () => $("#details-form");
const edited = new Set(); // title/subtitle fields the visitor has typed in

function subtitleFor(year, period) {
  // The library's default subtitle: the solstice-to-solstice dates.
  return period === 0 ? `${year - 1}-12-21 / ${year}-06-21` : `${year}-06-21 / ${year}-12-21`;
}

function fillDetails() {
  const f = form();
  if (!f.year.value) f.year.value = new Date().getFullYear();
  resetTitles();
}

function resetTitles() {
  const f = form();
  const year = Number(f.year.value) || new Date().getFullYear();
  for (const period of [0, 1]) {
    if (state.place && !edited.has(`title${period}`)) f[`title${period}`].value = placeLabel();
    if (!edited.has(`subtitle${period}`)) f[`subtitle${period}`].value = subtitleFor(year, period);
  }
}

function setupImageChoice(box) {
  const name = box.dataset.name;
  const thumb = box.querySelector("img");
  const input = box.querySelector("input[type=file]");
  const defaultSrc = thumb.src;
  input.addEventListener("change", () => {
    const file = input.files[0];
    const status = $("#details-status");
    status.textContent = "";
    if (!file) return;
    if (!["image/png", "image/jpeg"].includes(file.type)) {
      status.textContent = I18N.t("details.imageType");
    } else if (file.size > MAX_IMAGE_BYTES) {
      status.textContent = I18N.t("details.imageTooBig");
    } else {
      state.images[name] = file;
      state.result = null;
      const reader = new FileReader(); // a data: URI; the CSP allows no blob: images
      reader.onload = () => (thumb.src = reader.result);
      reader.readAsDataURL(file);
    }
    input.value = "";
  });
  box.querySelector(".reset").addEventListener("click", () => {
    state.images[name] = null;
    state.result = null;
    thumb.src = defaultSrc;
  });
}

function errorMessage(status, body) {
  if (status === 429) return I18N.t("details.tooMany");
  if (status === 504 || status === 503) return I18N.t("details.busy");
  return I18N.t("details.failed", { reason: (body && body.detail) || status });
}

async function generate(event) {
  event.preventDefault();
  const f = form();
  const button = $("#generate");
  const status = $("#details-status");
  const data = new FormData();
  data.set("lat", state.place.lat);
  data.set("lon", state.place.lon);
  for (const name of ["year", "dayline_color", "hourline_color", "title0", "subtitle0", "title1", "subtitle1"]) {
    data.set(name, f[name].value);
  }
  for (const [name, file] of Object.entries(state.images)) if (file) data.set(name, file);

  button.disabled = true;
  button.classList.add("busy");
  status.textContent = I18N.t("details.computing");
  try {
    const response = await fetch("api/sundial", { method: "POST", body: data });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      status.textContent = errorMessage(response.status, body);
      return;
    }
    status.textContent = "";
    showResult(body, f.title0.value, f.year.value);
  } catch {
    status.textContent = I18N.t("details.network");
  } finally {
    button.disabled = false;
    button.classList.remove("busy");
  }
}

// --- result ------------------------------------------------------------------

function slug(text) {
  const s = text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  return s.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "accuratum";
}

function showResult(result, title, year) {
  state.result = result;
  result.pngs.forEach((png, i) => ($(`#preview${i}`).src = `data:image/png;base64,${png}`));
  const bytes = Uint8Array.from(atob(result.pdf), (c) => c.charCodeAt(0));
  if (state.pdfUrl) URL.revokeObjectURL(state.pdfUrl);
  state.pdfUrl = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
  const download = $("#download");
  download.href = state.pdfUrl;
  download.download = `accuratum-${slug(title)}-${year}.pdf`;
  location.hash = "#/result";
}

// --- start -------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", async () => {
  const lang = $("#lang");
  await I18N.use(I18N.initial());
  lang.value = I18N.lang;
  lang.addEventListener("change", () => I18N.use(lang.value));
  document.addEventListener("languagechange", () => {
    if (!$("#view-location").hidden) showMap();
  });

  $("#search-form").addEventListener("submit", search);
  $("#to-details").addEventListener("click", () => (location.hash = "#/details"));
  form().addEventListener("submit", generate);
  form().addEventListener("input", (event) => {
    const name = event.target.name || "";
    if (/^(sub)?title[01]$/.test(name)) edited.add(name);
    if (name === "year") resetTitles();
    if (name) state.result = null;
  });
  document.querySelectorAll(".image-choice").forEach(setupImageChoice);

  window.addEventListener("hashchange", route);
  route();
});
