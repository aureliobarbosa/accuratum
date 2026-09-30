# Accuratum — what's left to do

> **Status (2026-09-30):** Steps 0–5.3 are closed. Next: Step 6 (layout
> decided: monorepo, with `web/` as its own uv workspace project). Steps 4–7
> are the fast track to a hosted website, so the collaborators can meet and
> start the paper.

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

The wheel (library + CLI) goes out through the `v*` GitHub Releases. PyPI
waits until the first version of the paper is submitted.

---

## Step 0 — Consolidate the trunk — **done**

`rewrite-core` was merged into `main` (c003354), and the stale branches were
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

## Step 6 — Create the website

A web front end for generating sundials (goal 4). Scope to be decided at the
start of the step. It accepts latitudes within ±`MAX_LATITUDE` (75°).

- **Decided:** one repo. `web/` is its own project (own `pyproject.toml`,
  uv workspace member); the library stays at the root and its wheel stays
  library + CLI only. Bingo's approach carries over, except two routes
  (`/api/plot` slow, `/api/render` live) instead of regenerating on every
  edit.

- **Before going public** (manual owner steps; the cleaned history is
  prepared and CI scans for secrets; see
  [PROJECT_KNOWLEDGE.md § Security cleanup](PROJECT_KNOWLEDGE.md#security-cleanup-before-going-public-step-6)):
  - [ ] a. Revoke the leaked Claude credentials: `/logout` then `/login` in
    Claude Code on each machine, and revoke old sessions in claude.ai
    account settings. Rotate anything else found.
  - [ ] b. Check GitHub for pull requests (`refs/pull/*` cannot be rewritten
    by force-push; if any contain the leaked commit, ask GitHub Support to
    purge them or publish as a fresh repo), forks and collaborators.
  - [ ] c. Approve the swap: force-push the cleaned `main` (and `v0.1` if its
    hash changed) from the clean clone; delete stale remote branches.
  - [ ] d. Re-clone on all 3 machines (old clones still hold the leaked
    objects); delete the old local branches.
  - [ ] e. Only then make the repo public.

- **First, in the library:**
  - move `_solstice_timeframe`, `DEFAULT_OVERLAYS` and the `accuratum:`
    path resolution out of `cli.py` into the public API;
  - render with `matplotlib.figure.Figure()`, not pyplot;
  - turn off astropy's IERS auto-download; Decide where the file(s) downloaded by astropy should live in production; Give options to the owner.
  - check that the wheel contains `accuratum/fig/` and that the CLI runs
    from a clean install of it.
- **Open decisions:**
  - which inputs the page shows (grid fixed?);
  - how labels are edited: form fields, or dragging;
  - how the location is entered: coordinates, a map, or a search box;
  - the page's language;
  - the deploy trigger: a `site-v*` tag, or a push that touches `web/`;
  - whether to reuse Bingo's Google Cloud project.

See [PROJECT_KNOWLEDGE.md § Website groundwork](PROJECT_KNOWLEDGE.md#website-groundwork-step-6).

## Step 7 — Host the website in the cloud

Bingo's Docker, Cloud Run, Firebase Hosting and WIF deploy setup carries
over (see the section above). Once it's hosted, call the collaborators for a
meeting and start writing the paper (goal 5).

## Backlog (not scheduled)

- **Sun map:** a plot of the sun's position (altitude, azimuth), comparing
  astropy against skyfield.
- **Guard test** that `core/` never imports matplotlib.
- **`notebooks/accuratum.ipynb` still imports the deleted v0.1 modules**
  (`accuratum.astronomy`, `datetime_utils`, `graph`). Port it to
  `build_plot`, or delete it.
- **Solstices are approximated as the 21st** of June and December
  (`SOLSTICE_DAY` in `cli.py`, the same as v0.1). astropy could compute the
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
