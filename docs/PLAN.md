# Accuratum — what's left to do

> **Status (2026-09-28):** the core rewrite is merged into `main`, which is now
> the only branch. Next: Step 1 (spec round-trip and
> override semantics); Steps 2–3 come from the user's review of the output.

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

## Step 1 — Spec file round-trip and override semantics — **next**

1. Run `--save-spec clock.json`, hand-edit a label override, then render with
   `--spec clock.json` and check that the label moved.
2. Answer the open question: should an override's `dx/dy` move **both**
   endpoint labels of a line, as it does now?
3. **Decide whether overrides need more power (finding, 2026-09-28).** The
   spec has no `labels` field by design: `build_plot` recomputes the labels on
   every render, and the spec keeps only corrections, in `overrides`. Each
   override matches a label by `selector` (`{"kind": "dayline", "date":
   "YYYY-MM-DD"}` or `{"kind": "hourline", "hour": H}`) and can set
   `dx`/`dy`, `text` or `hidden`. The limit: `_apply_overrides` runs only
   *after* a label survives the plumb-exclusion and collision checks in
   `defaults/placement.py::_try_place`. So an override can't bring back a
   label the heuristic dropped, and can't add a label for a date or hour the
   heuristic didn't pick. For goal 3 (human in the loop) that is likely too
   weak. Options: a `force: true` flag that bypasses the suppression checks,
   and/or overrides that add labels. Example spec to test with:
   `example-projects/specs/fup_planaltina.json`.

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

## Step 3 — Which side the date labels go on

With "Brasilia" or "planaltina" as the location, the day-line labels
(`MM/DD`) appear only on the left edge. The user's view: date labels should
go on either the left or the right side, and which side is right depends on
latitude and can be completely different from place to place. **Root cause, found 2026-09-28 — a bug, not a latitude effect.** In
`defaults/placement.py::place_labels`, day-line labels use a 1-D collision
check on `|Δy|` against *every* placed label, including the left label of
the same line. A day line's two endpoints sit at almost the same height. For
the Planaltina spec the difference is under 0.02, while the tolerance is
`0.04 × data_extent`, about 0.5. So every right-side label is dropped as
colliding with its own left twin: 6 left labels, 0 right. The fix is to
check collisions only among labels on the same side, then define the rule
for choosing the side. Test it across latitudes (southern and northern
hemisphere, tropics, high latitudes).

The hour labels show only 07–08h and 15–17h. Missing 09–14h is expected from
the plumb-exclusion radius, but review it in the same step.

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
