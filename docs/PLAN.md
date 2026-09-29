# Accuratum — what's left to do

> **Status (2026-09-29):** Steps 0–3 are closed. Next: pick from the backlog
> toward goals 4–5 (website, paper).

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
   after the web system ships. Implement a second sundial type before
   publishing.

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

## Backlog (not scheduled)

- **Duplicate hour label under DST** (bug): Edinburgh, period 0, gets two
  hour lines labelled `12h` and none `14h`, so two labels share a selector.
  Look at the hour pick in `defaults/labels.py` (middle sample vs. the DST
  switch).
- **Extreme latitudes:** poles, the Arctic/Antarctic circles and the equator
  are untested. The label tolerances and exclusion radius may break there.
- **Sun map:** a plot of the sun's position (altitude, azimuth), comparing
  astropy against skyfield.
- **Guard test** that `core/` never imports matplotlib.
- **`notebooks/accuratum.ipynb` still imports the deleted v0.1 modules**
  (`accuratum.astronomy`, `datetime_utils`, `graph`). Port it to
  `build_plot`, or delete it.
- **Solstices are approximated as the 21st** of June and December
  (`SOLSTICE_DAY` in `cli.py`, the same as v0.1). astropy could compute the
  exact instant.
- **Second sundial type**, a prerequisite for goal 5.
- **Keep label edits across `--regenerate`**, by matching labels by
  `selector`. Today a regenerate resets the labels.
- **Custom overlay images are stored as absolute paths**, so a project folder
  that uses one isn't portable. Copy the image into the folder instead.
