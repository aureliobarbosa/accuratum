# Accuratum core rewrite — plan

Tagged baseline: **v0.1** (`main` at the time of this plan). The rewrite
restarts the package architecture; the `labels` branch is preserved as a
reference for the label-collision heuristic but will not be merged.

The rewrite is a strict chain: Step 1 unlocks Steps 2, 3, 3.1. Steps 2 and 3
can run in parallel after Step 1 if desired.

## Status legend

- ✅ done and committed
- ▶ in progress
- ⏳ pending

## Current position

- ✅ Step 1 — Functional core
- ✅ Step 2 — Matplotlib renderer + CLI rewire (user visually approved)
- ✅ Cleanup — old `astronomy.py` / `datetime_utils.py` / `graph.py` deleted
- ▶ Step 3 — SVG renderer (next)
- ⏳ Step 3.1 — Spec file I/O + overrides

Branch `rewrite-core`, 12 commits ahead of `main`. 87 tests passing. Not
pushed, not merged.

---

## ✅ Step 1 — Functional core: `Spec → Geometry → Plot`

### Goal
Make the library a pure data pipeline. No matplotlib, no I/O, no global
state inside the core. Renderers come later (Step 2+).

### Delivered
```
accuratum/
  core/
    spec.py        ✅ SundialSpec + JSON roundtrip helpers
    plot.py        ✅ Plot, Polyline, Label (frozen dataclasses, numpy xy)
    hints.py       ✅ Overlay, RenderHints (separated from Spec for portability)
    metadata.py    ✅ TypedDict contract shared by polyline metadata and selectors
    astronomy.py   ✅ build_altaz_frame, get_sun_altaz, get_sunrises_and_sunsets
    timegrid.py    ✅ dayline_grid, hourline_grid (Spec-driven)
    builder.py     ✅ build_plot(spec) -> Plot orchestrator
  projections/
    accuratum.py   ✅ project(alt_deg, az_deg, plumb_length) -> (xs, ys)
  defaults/
    labels.py      ✅ select_dayline_labels, select_hourline_labels
    placement.py   ✅ place_labels — collision heuristic from labels branch,
                       per-axis tolerance, plumb-exclusion radius, override
                       application by selector
```

**Public API** (current):
```python
from accuratum.core.builder import build_plot
from accuratum.core.spec import SundialSpec
plot = build_plot(spec)               # pure data in, pure data out
```

### Key design decisions (kept)
- `SundialSpec` is JSON-serializable via `spec_to_dict` / `spec_from_dict`
  (datetimes ↔ ISO strings; frozen subobjects rebuilt on load).
- Solstice resolution + timezone lookup live in the **CLI**, not the core.
  The core takes explicit `TimeFrame(start, end)`.
- `Plot` is pure data, no matplotlib types.
- Labels carry a `selector` dict so overrides match by metadata identity
  (e.g. `{"kind": "hourline", "hour": 6}`), surviving `time_step` changes.
- Overlays live in `RenderHints`, not `Spec` — saved spec stays portable.
- Heuristics live in `defaults/*`; `build_plot` calls them but they are
  short-circuited per-label by matching overrides.

### Acceptance criteria — met
- ✅ CLI rebuilt on the new core produces output visually equivalent to
  v0.1 (user-confirmed).
- ✅ `build_plot(spec)` is deterministic, no network, no matplotlib
  import (importable without matplotlib installed in core/ — confirmed
  by import graph).
- ✅ Public functions tested without I/O mocking other than astropy.
- ✅ JSON roundtrip test (`tests/core/test_spec.py`).

### Tests delivered
- `tests/core/test_metadata.py` — selector match semantics
- `tests/core/test_spec.py` — JSON roundtrip, frozen-subobject rebuild,
  tz-aware enforcement
- `tests/core/test_astronomy.py` — altaz query, rise/set, horizon shift
- `tests/core/test_timegrid.py` — grid shape, dtype, monotonicity, NaT masking
- `tests/core/test_builder.py` — end-to-end Spec → Plot, metadata shape,
  label format, selector presence, override hide, unsupported sundial_type
- `tests/projections/test_accuratum.py` — overhead → zero shadow, linear
  scaling with plumb_length, v0.1 sign convention locked
- `tests/defaults/test_labels.py` — month-transition, on-the-hour
  threshold, non-matching kinds
- `tests/defaults/test_placement.py` — endpoint alignment, hour-yields-
  to-day, per-axis collision, plumb exclusion, override dx/dy/hide/text

### Deviations from the original plan
- `core/hints.py` was added as a separate module (originally lumped into
  `spec.py`). Justification from the Plan-agent review: overlay image
  paths shouldn't bake into a portable spec file.
- `core/builder.py` exists as its own module rather than living in
  `core/__init__.py` (cleaner imports, easier to read).
- `Label` carries a `selector` dict, not just a `kind` string — emerged
  from the override-by-identity decision.

### Subagent runs (sequential, as instructed)
- ✅ Explore — code inventory of v0.1 / labels branch
- ✅ claude — wrote `docs/LESSONS_LABELS.md`
- ✅ Plan — review of Spec/Plot dataclass design before implementation

---

## ✅ Step 2 — Matplotlib renderer as a thin adapter

### Goal
Reproduce v0.1 output by reading a `Plot`. No core logic in the renderer.

### Delivered
```
accuratum/renderers/matplotlib_backend.py   ✅ render(plot, hints) -> (Figure, Axes)
accuratum/cli.py                            ✅ rewired on SundialSpec + build_plot + render
```

CLI now does:
```python
spec = SundialSpec(location, timeframe, plumb_length, grid)
plot = build_plot(spec)
fig, _ = render(plot, hints)
fig.savefig(args.output, ...)
```

### Key design decisions (kept)
- Renderer takes `Plot` + `RenderHints`. No geometry.
- Overlay/logo/compass all flow through the same `Overlay` primitive in
  `RenderHints.overlays`.
- The labels-branch collision heuristic ran inside `defaults/placement.py`
  at plot-build time, not in the renderer.

### Acceptance criteria — met
- ✅ Visual diff vs v0.1: user-approved.
- ✅ CLI integration tests pass after Spec/Hints construction wired in.
- ✅ Overlays via the generic `OverlayImage` mechanism.

### Pause point — passed
The assistant paused after writing the renderer. User compared output
against v0.1 and signed off.

### Deviations from the original plan
- No explicit `assert matplotlib not importable from core/*` test was
  written; the dependency direction is enforced by code structure and
  test coverage rather than a guard test. May add later if it ever leaks.

---

## ✅ Cleanup — dead old code removed

After Step 2 signoff:
- Deleted `accuratum/astronomy.py`, `accuratum/datetime_utils.py`,
  `accuratum/graph.py`.
- Deleted `tests/test_astronomy.py`, `tests/test_datetime_utils.py`.
- `tests/test_smoke.py` updated to import the new modules.
- `tests/test_cli.py` retained as-is (the CLI flags it tests survived
  the rewrite).
- 87 tests passing afterwards.

---

## ▶ Step 3 — SVG renderer

### Goal
Second backend, same `Plot` input. Enables large-format printing (req 2)
and prepares the way for browser-side rendering later.

### Deliverables (planned)
```
accuratum/
  renderers/
    svg_backend.py    # render(plot, hints) -> str (SVG markup)
```
CLI gets `--format svg` (or infers from `--output *.svg`).

### Key design decisions
- Pure-Python SVG via `xml.etree`. No new dependency.
- Use millimeters, not pixels. A 6 m × 2 m panel is
  `width="6000mm" height="2000mm"`.
- Reuse the *same* `Plot` from Step 1. If a different intermediate is
  needed, fix Step 1 — don't fork.
- Text labels are real SVG `<text>` elements with selector-derived `id`
  attributes (selectable, editable in Inkscape) — enables print-shop
  nudges without re-running Python.

### Acceptance criteria
- SVG renders geometrically identical to the matplotlib output for one
  canonical Spec.
- Opens cleanly in Inkscape / a browser at screen size and at 6 m × 2 m.
- Snapshot tests for small fixed Plots pass.

### Test strategy
- SVG generator tested against snapshots of small fixed Plots (lines,
  labels, overlays). Subagent-friendly boilerplate.
- Manual: open the 6 m × 2 m output in Inkscape, eyeball, attempt one
  label nudge.

### Effort & risk
~1–2 sessions. Gotchas:
- SVG `text-anchor` / `dominant-baseline` semantics differ slightly from
  matplotlib `ha`/`va`. Mapping table required.
- y-axis points down in SVG, up in data coords. Flip in the viewBox.
- Overlay images: SVG supports `<image>` with external `href` or embedded
  data URIs. Pick one; if external, the SVG isn't portable in isolation.

Risk: discovering the `Plot` needs more metadata (e.g., per-label
alignment beyond `ha`/`va`). If so, fix Step 1 cleanly.

### Subagent use (sequential)
1. **general-purpose**: generate SVG snapshot fixtures + tests once the
   generator is drafted.

### PAUSE FOR VISUAL FEEDBACK
After this step, the assistant pauses and asks the user to open the SVG
output in Inkscape (and/or browser at 6 m × 2 m) before proceeding to
Step 3.1.

---

## ⏳ Step 3.1 — Spec file I/O and override mechanism

### Goal
Make the `Spec` the actual interface. Hand-edit a JSON file, render, see
the change. Pre-web stage where label-nudge tooling becomes real without
committing to a UI framework.

### Deliverables
```
accuratum/
  spec_io.py        # load_spec(path), save_spec(spec, path) — JSON
  cli.py            # accepts --spec <file>; --save-spec <file> dumps invocation
```
The override mechanism is wired up:
`LabelOverride(selector={"kind": "hourline", "hour": 6}, dx=0.1, dy=-0.2)`
survives a round-trip and applies in `build_plot`. (The dataclass and the
roundtrip are already in place from Step 1 — Step 3.1 is the file I/O
and CLI surface.)

### Key design decisions
- **JSON**, not YAML/TOML. The eventual web app eats JSON natively.
- CLI gains two modes:
  - **One-shot mode** (current): all args on CLI, no spec file.
  - **Spec-file mode**: `--spec clock.json` is source of truth; CLI args
    still override fields if given.
- `--save-spec` dumps the CLI invocation to JSON; iterate by editing.
- `spec_version` already present (Step 1).

### Acceptance criteria
- `accuratum --lat-long=… --save-spec clock.json` produces a spec.
- `accuratum --spec clock.json` reproduces the same output.
- Edit a label override in `clock.json`, re-render, see the label move.
- All existing CLI tests pass; new tests cover roundtrip and override
  application end-to-end.

### Test strategy
- Already have unit tests for `spec_to_dict` / `spec_from_dict` (Step 1).
- Add file-I/O tests (load/save, malformed-file errors, version handling).
- Integration test: save → edit → load → render → check the label moved.

### Effort & risk
~1 session. Risk: schema bikeshedding — decide once with
`dataclasses.asdict` defaults; refine only when overrides reveal a real
problem.

### Subagent use (sequential)
1. **Plan agent**: one-shot review of the JSON schema / CLI semantics
   before implementation.

### PAUSE FOR VISUAL FEEDBACK
After this step, the assistant pauses and asks the user to test the
save → edit → re-render flow before declaring the rewrite stage complete.

---

## Cross-cutting

### ✅ Lessons from the `labels` branch
Captured in [`docs/LESSONS_LABELS.md`](./LESSONS_LABELS.md) — the
heuristic discoveries (auto-scale tolerance, plumb exclusion radius, 1-D
collision per axis, shared placed-labels set, hour-yields-to-day
priority). Institutional memory; prevents rediscovery.

### Branch strategy
- `rewrite-core` branch off `main` (already created).
- Commit per subtask, per Agents.md.
- Not yet pushed; do not push to `main` until the user explicitly
  authorizes.
- `labels` branch will not be merged into `main`.

### Subagent execution
Per user instruction: **agents run in sequence, not parallel.**
1. ✅ Explore — code inventory (before Step 1 implementation).
2. ✅ claude — wrote `LESSONS_LABELS.md`.
3. ✅ Plan — Spec/Plot dataclass design review (end of Step 1a).
4. ⏳ general-purpose — SVG snapshot fixtures and tests (during Step 3).
5. ⏳ Plan — JSON schema review (start of Step 3.1).

### Pause points
- ✅ After Step 2: visual approval against v0.1.
- ⏳ After Step 3: SVG opens correctly in Inkscape at 6 m × 2 m.
- ⏳ After Step 3.1: human-in-the-loop save → edit → re-render flow works.
