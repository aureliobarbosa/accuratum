# Accuratum — what's left to do

> **Status (2026-09-28):** the core rewrite is merged into `main`, which is now
> the only branch. Next: the user's sign-off checks in Step 1.

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

## Step 1 — Sign-off of the rewrite

Checkpoints that only the user can close:

1. Open `uv run accuratum --lat-long=-15.78,-47.92 --canvas-size-mm=6000,2000 -o panel.svg`
   in Inkscape and nudge a label by its id.
2. Run `--save-spec clock.json`, hand-edit a label override, then
   `--spec clock.json`, and check that the label moved.
3. Answer the open question: should an override's `dx/dy` move **both**
   endpoint labels of a line, as it does now?
4. Check the default label placement. In the Brasília PNG rendered after the
   merge, the day-line labels (`MM/DD`) appear only on the left edge, and the
   hour labels only for 07–08h and 15–17h. 09–14h are expected to be
   suppressed by the plumb-exclusion radius, but the missing right-edge day
   labels are unexplained.

Then reassess the backlog below against goals 3–4.

## Backlog (not scheduled)

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
