# Accuratum website — user experience

Set by the owner on 2026-09-30 (Step 6). This is the whole flow of the first
version: nothing more.

## Every page: the top bar

The top bar stays on every page. It holds:

- **Home**, which goes to the landing page;
- **About**;
- **Contact**;
- **a language selector**: `pt-BR` (the default) and `en`;
- **a GitHub icon** linking to
  [github.com/aureliobarbosa/accuratum](https://github.com/aureliobarbosa/accuratum).
  It is there even while the repo is private.

**Multilingual from the start.** Portuguese (Brazil) is the default
language. Every visible string comes from one translation table per
language, never written into the markup. Adding a language means adding
one table.

## 1. Landing page (`accuratum.web.app`)

From top to bottom:

1. the project logo (it doesn't exist yet and has to be created);
2. a one-line description of Accuratum;
3. a **Generate sundial** button;
4. a photo of a real Accuratum sundial.

The button leads to step 2. The top bar stays.

## 2. Location

A world map. The user clicks to pick the place of the sundial. A **Next**
button leads to step 3.

## 3. Details

A form with the remaining inputs. It is already filled with every value
that can be worked out automatically:

- **title**: the place's name (default: the name, or the coordinates when
  there is none; see `defaults/titles.py`);
- **subtitle**: the date range (default: `yyyy-mm-dd / yyyy-mm-dd`);
- **year**: the current year;
- **dayline color** and **hourline color**: two `<input type="color">`
  pickers, set to the library's defaults (`#d55e00`, `#0072b2`, chosen to
  stay distinct for color-blind readers; see PROJECT_KNOWLEDGE.md § Line
  colors).

There is no period field: the user always gets both halves of the year
(Dec→Jun and Jun→Dec), one page each, in a single PDF.

Two buttons change the images:

- **Customize logo**, which picks the logo image;
- a matching button for the **compass** image.

Each image can also be put back to the default (the package's logo or
compass).

**Next** is a button that spins while the sundial is computed (about 10 s),
then leads to step 4.

## 4. Result

A PNG preview of each half-year (plain `<img>`s) and a **Download PDF**
button for the two-page PDF. The same request returns all of them, so
the sundial isn't computed twice. There is no SVG download.

That is the end of the flow.

## Consequences for the implementation

- **Two sundials per request.** Both halves take about 20 s one after
  the other, or about 10 s if they're computed in parallel (two
  processes, so more memory per request). That is still under the 60 s
  timeouts.
- **No label editing on the website.** Goal 3 (human in the loop) stays
  with the CLI and project folders for now. So the planned live
  `/api/render` route is not needed: one call, spec + texts + images →
  PNG + PDF, is enough.
- **PNG preview, not a PDF viewer or an SVG preview** (owner's choice,
  2026-09-30). A PNG shows the same in every browser, mobile included,
  and it is the output that gets checked visually. It avoids Bingo's PDF
  traps (`blob:` URLs vs. the CSP, Firefox's pdf.js, mobile browsers that
  don't show PDFs inline). matplotlib's SVG hasn't been checked in a
  browser yet. The cost: no sharp zoom, and the page needs its own
  download button.
- **The logo and compass are uploads**, from the visitor's disk. They need
  size and type limits (PNG/JPEG only, decoded and re-encoded server-side),
  and never a server file path.
- **The map** needs a tile source allowed by the CSP (Leaflet + OSM tiles).
  The click is limited to ±75° of latitude.
- **The place name for the title** needs reverse geocoding (coordinates →
  name). Do it from the browser, or from the server with a cache and
  1 req/s. Otherwise the title falls back to the coordinates.

## Open questions

Answered 2026-09-30: both halves, one page each in one PDF; the logo and
compass can go back to the default; no SVG download.

1. **About and Contact:** what text do they hold? Should Contact show an
   e-mail address, or link to GitHub issues?
2. **Sundial photo and one-line description:** the owner supplies them.
3. **Map search:** is clicking the map enough, or does it also need a place
   search box or typed coordinates?
