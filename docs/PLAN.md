# Accuratum — what's left to do

> **Status (2026-09-29):** Steps 1 and 3 are done. Next: Step 2 (SVG parity).

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
   Brasília. This needs vector output with correct scaling: keep matplotlib,
   add SVG, no cairo.
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

## Step 2 — SVG output as good as matplotlib

User check, 2026-09-28: the SVG comes out at the right physical size
(6000 × 2000 mm), but its design falls short of the matplotlib output,
which is much better so far.

1. List the visual differences between `-o x.png` and `-o x.svg` for the
   same spec: fonts, stroke widths, label anchoring and overlays. Then close
   the gaps in `renderers/svg_backend.py`.
2. **Test the default A4 landscape canvas (297 × 210 mm) too**, not only the
   6 m × 2 m panel. It hasn't been checked yet.
3. The drawing is about 2.1 : 1 and the SVG keeps its proportions, so a 3 : 1
   panel gets empty side margins. Decide whether that is acceptable.
4. Inkscape check at 6 m × 2 m: nudge a label by its id
   (`label-dayline-2026-01-04-end`). It was carried over from the rewrite.

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
- **Import label positions nudged in Inkscape** back into `project.json`,
  through the SVG ids.
- **Custom overlay images are stored as absolute paths**, so a project folder
  that uses one isn't portable. Copy the image into the folder instead.
