# Accuratum — what's left to do

> **Status (2026-10-04):** Steps 0–5.5 are closed, and the repo is public
> (0.2.2 is on PyPI).
> Next: the rest of Step 6 (layout decided: monorepo, with `web/` as its own
> uv workspace project). Steps 4–7 are the fast track to a hosted website,
> so the collaborators can meet and start the paper.

This file holds only what is **still to do**. When a step closes, it shrinks
here to one line per decision plus a pointer. The detail (findings, traps,
commits) moves to [PROJECT_KNOWLEDGE.md](PROJECT_KNOWLEDGE.md) in the same
commit. Working rules are in [CLAUDE.md](../CLAUDE.md).

## Long-term goals

Set by the user in May 2026, in priority order. Each one depends on the ones
before it.

1. **A library for drawing sundials**, starting with the accuratum type only.
   Other types can plug in later if the structure allows it. If it grows too
   complex, fall back to one simple program per sundial type with shared
   plotting.
2. **Large printed panels**, e.g. 6 m (east–west) × 2 m (north–south) in
   Brasília. Vector output (SVG/PDF) through matplotlib, scaled to the panel
   at print time. No cairo, no custom SVG writer.
3. **Human in the loop.** No single heuristic will place labels well from the
   poles to the equator, so the user gets fine control over which dates and
   hours are drawn and can nudge each label by hand.
4. **A web system** for generating sundials, started only after 1–3 succeed.
5. **A paper**, plus conferences on astronomy education and computer science,
   after the web system ships. A second sundial type was a prerequisite;
   since 2026-09-29 comparing against other people's sundial software may
   replace it (see the backlog).

The wheel (library + CLI) goes out on every `v*` tag, to the GitHub Releases
and, from 0.2.2 on, to PyPI (Step 5.5). The user moved PyPI ahead of the
paper on 2026-10-01.

---

## Step 0 — Consolidate the trunk — **done**

`rewrite-core` was merged into `main` (fbe6857), and the stale branches were
deleted locally and on origin. See
[PROJECT_KNOWLEDGE.md § Core rewrite](PROJECT_KNOWLEDGE.md#core-rewrite-spec--plot--renderer).

## Step 1 — Project folders with editable labels — **done**

- A run is saved like a simulation result, in a project folder:
  `project.json` (spec, render settings, labels, provenance) and
  `polylines.npz` (geometry).
- Labels are plain data. Suppressed labels are kept with `hidden: true`, and
  every endpoint has its own selector. This replaces overrides.
- `--project DIR` renders without recomputing. An edited spec is refused
  until `--regenerate` is run.
- `--year` added, and `year` and `period` are recorded in the spec.

See [PROJECT_KNOWLEDGE.md § Project folders](PROJECT_KNOWLEDGE.md#project-folders-and-editable-labels).

## Step 2 — SVG output as good as matplotlib — **dropped**

- The custom SVG backend was removed instead of matched to matplotlib.
  `.svg` goes through `fig.savefig`, the same drawing as the PNG.
- `--canvas-size-mm` is gone; a print shop scales the vector file.
- Labels are nudged in `project.json`, not in Inkscape.

See [PROJECT_KNOWLEDGE.md § SVG backend dropped](PROJECT_KNOWLEDGE.md#svg-backend-dropped-step-2).

## Step 3 — Which side the date labels go on — **done**

- It was a bug, not a latitude effect: each label collided with its own
  twin. Labels now collide only with labels on the same side.
- No "choose the side by latitude" rule: dates show on both sides at every
  latitude checked (0° to ±56°).
- Missing 09h–14h at Planaltina is the plumb exclusion, as expected.

See [PROJECT_KNOWLEDGE.md § Label sides](PROJECT_KNOWLEDGE.md#label-sides-step-3).

## Step 4 — Duplicate hour label under daylight saving time — **done**

- Hour lines are labelled in the zone's standard time (`utcoffset − dst`),
  not the DST clock. Lines don't move; zones without DST are unchanged.
- The README tells dial users to add an hour in summer.

See [PROJECT_KNOWLEDGE.md § DST hour labels](PROJECT_KNOWLEDGE.md#dst-hour-labels-step-4).

## Step 5 — Latitudes from −75° to +75° — **done**

- Days with the sun below the 10° cut all day (|lat| > 56.5°, winter) are
  skipped; the dial ends before the winter solstice there.
- Days are local days from local mean midnight: hour lines had vanished
  wherever the local day straddles 00 UTC (lon ±120°…±170°).
- `MAX_LATITUDE = 75` (target was ±62°; confirmed by the user): clean at
  every longitude tried; hour labels repeat from ~75.5°. Library and CLI
  reject the rest.
- The 10° horizon cut stays fixed. Losing winter weeks at high latitudes is
  accepted; no feature should lower the cut.

See [PROJECT_KNOWLEDGE.md § Latitude range](PROJECT_KNOWLEDGE.md#latitude-range-step-5).

### Step 5.1 — Logo and compass overlap the drawing — **done**

- A header band above the drawing holds the overlays (`RenderHints.axes_rect`,
  drawing anchored to its top). No corner heuristic: the overlap depended on
  hemisphere *and* period.

See [PROJECT_KNOWLEDGE.md § Header band](PROJECT_KNOWLEDGE.md#header-band-step-51).

### Step 5.2 — Title and subtitle — **done**

- Centered in the header band, between the logo and the compass. Defaults:
  the location name (coordinates without one) and `yyyy-mm-dd / yyyy-mm-dd`.
- `--title`/`--subtitle` (`""` leaves one out). Placement and font sizes
  are render hints.

### Step 5.3 — One definition of the title and subtitle — **done**

- The texts are `Plot` data like labels: `build_plot` fills the defaults,
  `project.json` saves the exact text, every renderer draws it. Replaced
  5.2's `render.title` with `null` meaning "default", resolved only by the
  CLI.
- `--regenerate` keeps an edited text and recomputes a default one.

See [PROJECT_KNOWLEDGE.md § Title and subtitle](PROJECT_KNOWLEDGE.md#title-and-subtitle-steps-5253).

### Step 5.4 — Dayline and hourline colors — **done**

- Two colors instead of one green: daylines Okabe–Ito vermillion
  `#d55e00`, hourlines blue `#0072b2`. They stay apart under protan-,
  deutan- and tritanopia.
- `--dayline-color`/`--hourline-color` take any matplotlib color and save
  it as `#rrggbb`, the format of a browser's `<input type="color">`.

See [PROJECT_KNOWLEDGE.md § Line colors](PROJECT_KNOWLEDGE.md#line-colors-step-54).

### Step 5.5 — Publish the wheel on PyPI — **done**

- A `pypi` job in `ci.yml` uploads the wheel only, through Trusted
  Publishing (no token), after the tests. It runs on every `v*` tag.
- It's in `ci.yml`, not in its own workflow, because `needs:` can't wait on
  another workflow's tests.
- First upload: 0.2.1 (2026-10-01), ahead of the paper, to secure the name.
  Deleted on 2026-10-04 with the old repo; 0.2.2 replaced it.
- No approval gate until the repo is public (backlog).

See [PROJECT_KNOWLEDGE.md § PyPI publishing](PROJECT_KNOWLEDGE.md#pypi-publishing-step-55).

## Step 6 — Create the website

A web front end for generating sundials (goal 4). Scope to be decided at the
start of the step. It accepts latitudes within ±`MAX_LATITUDE` (75°).

- **Decided:** one repo. `web/` is its own project (own `pyproject.toml`,
  uv workspace member); the library stays at the root and its wheel stays
  library + CLI only. Bingo's approach carries over, except two routes
  (`/api/plot` slow, `/api/render` live) instead of regenerating on every
  edit (superseded by the single route in UX.md, see below).

- **Going public — done** (2026-10-04):
  - the leaked `.claude-data/` commit was cut from history (2026-09-30),
    then the clean `main` went to a fresh repo, since the old one still
    served the leak by hash; the old repo is deleted;
  - the leaked OAuth tokens were tested dead; passwords rotated, devices
    signed out; every machine works from a fresh clone;
  - the old tags and PyPI 0.2.1 stayed behind; the new repo's first
    release is v0.2.2;
  - keeping Claude's setup in the repo was dropped: it caused the leak.

  See [PROJECT_KNOWLEDGE.md § Security cleanup](PROJECT_KNOWLEDGE.md#security-cleanup-before-going-public-step-6).

- **Library prep — done** (2026-09-30): `solstice_timeframe` in
  `core/spec`, default overlays and `resolve_image_path` (confined to the
  package) in `defaults/overlays`; rendering on a bare `Figure`; IERS
  tables bundled, no downloads; every `SundialSpec` input validated; the
  wheel smoke-tested in CI. See
  [PROJECT_KNOWLEDGE.md § Library prep for the website](PROJECT_KNOWLEDGE.md#library-prep-for-the-website-step-61).
- **Website, first version — done** (2026-09-30): `web/` workspace
  project; `POST /api/sundial` (both half-years, parallel, 13–15 s);
  limits, CSP and rate limit; the four-view page in pt-BR/en with map,
  search, upload and PDF download. See
  [PROJECT_KNOWLEDGE.md § Website first version](PROJECT_KNOWLEDGE.md#website-first-version-step-61).
- **Done since** (2026-09-30): long titles and their subtitles shrink by
  one factor to fit between the overlays (b471546); a one-image carousel
  of ten university sundials on the landing page (bf6caa1), titled by
  city, with the Accuratum logo except at UnB; the project logo
  (`fig/logo.png`, `ACCURATUM_LOGO`) on the landing page (17aeb6e).
- **Left in Step 6:**
  - the one-line description (owner);
  - About and Contact pages (owner, work in progress).
- **Security requirements for `web/`** (the trust boundary):
  - no file paths from users: logo and compass uploads with size and type
    limits, re-encoded server-side; never load a user's project folder
    as-is, since its overlay paths would be trusted;
  - never expose the grid: the spec bounds stop absurd values, not slow
    ones (1-minute steps at 10,000 points would take minutes);
  - cap the length of the title, subtitle and label texts (matplotlib
    parses `$…$` as math);
  - accept line colors only as `#rrggbb` (a regex), not any string
    matplotlib would parse;
  - geocoding: cache or rate-limit Nominatim (1 req/s per app), or geocode
    in the browser;
  - the server picks the output file name and format;
  - a timeout per request, a cap on concurrent renders, and Cloud Run
    memory and concurrency limits.
- **User experience decided** (2026-09-30), in
  [web/docs/UX.md](../web/docs/UX.md): landing page → world map → form
  → PNG preview + Download PDF. pt-BR by default, multilingual from the start. No label
  editing on the site, so a single spec → PNG + PDF route replaces the
  `/api/plot` + `/api/render` pair. The logo and compass are uploads.
  UX.md lists its own open questions.
- **Decided** (2026-10-06): the site deploys on a `site-v*` tag, apart
  from the `v*` tags that publish the wheel. Bingo stays as it is, and
  the site gets its own Cloud Run service behind Firebase Hosting at
  `accuratum.web.app`, if that name is free.
- **Decided** (2026-10-06): a new Google Cloud/Firebase project for the
  site, on the same billing account as Bingo, so the two stay separate. The
  free tier is shared either way, since it's counted per billing account.
  Cloud Run runs with `--max-instances 3`, so a spike can't run up the bill.

See [PROJECT_KNOWLEDGE.md § Website groundwork](PROJECT_KNOWLEDGE.md#website-groundwork-step-6).

## Step 7 — Host the website in the cloud

Bingo's Docker, Cloud Run, Firebase Hosting and WIF deploy setup carries
over (see the section above). Once it's hosted, call the collaborators for a
meeting and start writing the paper (goal 5).

There's no Docker in the dev container, so the image is built and
smoke-tested only in GitHub Actions (`deploy.yml`, also runnable by hand).

- **7a — client IP behind the CDN — done:** the rate limit reads
  `Fastly-Client-Ip` first (Firebase Hosting's CDN calls Cloud Run).
- **7b — Dockerfile and smoke test:** multi-stage, one Python 3.11 base,
  only the website and the library, non-root user, matplotlib font cache
  built at build time; `scripts/smoke.sh URL` checks the page, a static
  file and one real `POST /api/sundial`.
- **7c — `deploy.yml`:** on `site-v*` tags and by hand; build → smoke →
  push → deploy by digest → smoke on the public URL. WIF, no keys. The
  Google steps are skipped until the repo variables exist. Cloud Run:
  `--max-instances=3`, `--min-instances=0`, 2 vCPU (one process per
  half-year), memory set from the smoke run.
- **7d — Google side:** `scripts/setup-gcp.sh` (APIs, Artifact Registry
  with a cleanup policy, deploy and runtime service accounts, WIF pinned
  to this repo), `firebase.json` rewriting `**` to the service. The owner
  creates the Firebase project, the `accuratum` site and a budget alert.
- **7e — first deploy:** the owner sets the repo variables; a `site-v0.1.0`
  tag (ask first); smoke test on `accuratum.web.app`; check the headers.

## Backlog (not scheduled)

- **Sun map:** a plot of the sun's position (altitude, azimuth), comparing
  astropy against skyfield.
- **Guard test** that `core/` never imports matplotlib.
- **`notebooks/accuratum.ipynb` still imports the deleted v0.1 modules**
  (`accuratum.astronomy`, `datetime_utils`, `graph`). Port it to
  `build_plot`, or delete it.
- **Solstices are approximated as the 21st** of June and December
  (`SOLSTICE_DAY` in `core/spec.py`, the same as v0.1). astropy could compute the
  exact instant.
- **Second sundial type**, once a prerequisite for goal 5. Before building
  one, look for open-source packages that draw sundials on the web. The
  user's view (2026-09-29): comparing Accuratum against someone else's
  software may be enough for the paper, and such a package could even serve
  as a backend later. Delivering the website and the paper fast comes first.
- **Hour-line selectors carry `hour` but not `minute_offset`**, so two
  lines rounding to the same hour collide. Only happens past 75.5° today.
- **Keep label edits across `--regenerate`**, by matching labels by
  `selector`. Today a regenerate resets the labels.
- **Custom overlay images are stored as absolute paths**, so a project folder
  that uses one isn't portable. Copy the image into the folder instead.
- **Approval gate for PyPI uploads**, now that the repo is public:
  add the owner as required reviewer of the GitHub environment `pypi`
  (Settings → Environments). Until then a `v*` tag uploads to PyPI without
  a click (Step 5.5).
- **GitHub hardening, in progress** (2026-10-04). Done: PRs restricted to
  collaborators, and fork-PR workflows need approval (see
  PROJECT_KNOWLEDGE.md § Security cleanup). Left: a ruleset blocking
  force-push and deletion of `main` and limiting `v*` tags to the owner,
  plus the `pypi` reviewer above.
