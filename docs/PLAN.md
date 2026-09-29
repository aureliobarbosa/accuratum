# Accuratum — what's left to do

> **Status (2026-09-29):** Steps 0–5 are closed. Next: Steps 5.1 and 5.2. Steps 4–7 are the fast track to a hosted website, so the
> collaborators can meet and start the paper.

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

### Step 5.1 — Logo and compass overlap the drawing at high latitudes

At Edinburgh (55.95° N, 3.19° W; `example-projects/edinburgh_2026_p0`) the
UnB logo covers the top-left `06/07` date label, and the compass sits on
top of the lines at the top right. Overlays are fixed figure-coordinate
rects, while the drawing's shape changes with latitude. The overlap gets
more likely the farther from the equator, where the drawing grows toward
the top corners.

- By symmetry, the drawing is upside down in the southern hemisphere. Check
  whether the overlap happens only in the north (e.g. Edinburgh vs. 55.95° S)
  before choosing a fix.
  Step 5 renders (lon −47.92°): at +62° p1 the compass covers `06/21` and
  `08/02`; at −62° p0 the logo sits just clear of `05/03`; at ±74–75° the
  horseshoe reaches both top corners. It depends on hemisphere *and* period.
- A fix could place the overlays in free space outside the data bbox, or
  pick the emptier corners.

### Step 5.2 — Title and subtitle

- **Title:** the location name by default, or a user string (CLI flag or
  `project.json`).
- **Subtitle:** the timeframe by default, starting simply as
  `yyyy-mm-dd / yyyy-mm-dd`, or a user string (CLI flag or `project.json`).
- When the user gives a title or subtitle, it is written to `project.json`
  when the project is saved, so `--project` renders it again.

## Step 6 — Create the website

A web front end for generating sundials (goal 4). Scope to be decided at the
start of the step. It accepts latitudes within ±`MAX_LATITUDE` (75°).

## Step 7 — Host the website in the cloud

Once it's hosted, call the collaborators for a meeting and start writing the
paper (goal 5).

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
