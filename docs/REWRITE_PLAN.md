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
- ▶ Step 3 — **Vector output via matplotlib SVG/PDF** (simplified, see below)
- ⏳ Step 3.1 — Spec file I/O + overrides

Branch `rewrite-core`, 12 commits ahead of `main`. 87 tests passing. Not
pushed, not merged.

### Mid-plan course-correction (post-Step-2)

Two reversals happened in quick succession:

1. After Step 2 landed, the user asked "why not use matplotlib's SVG
   output?" The answer was: my reasoning for a custom SVG backend was
   thin. We agreed to drop the custom renderer and use matplotlib's
   built-in SVG + `set_gid`.
2. While drafting that simplification, the user noticed an untracked
   `accuratum/renderers/svg_backend.py` and `tests/renderers/test_svg_backend.py`
   already on disk. These were produced by a subagent earlier in the
   session; I had not run the agent's tests in the main thread and had
   forgotten the implementation existed. The custom renderer was real,
   working, and produced cleaner selector-derived ids than matplotlib's
   auto-SVG would.

Decision: **keep the agent-produced custom SVG backend.** It satisfies
the print-shop and millimeter-units requirements directly, exposes
clean ids for Inkscape edits, and is already covered by tests.

Lesson saved in project memory: always run subagent-produced tests in
the main thread before trusting the agent's claim of completion.

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

## ▶ Step 3 — Custom SVG renderer (subagent-produced, retained)

### Goal
Vector output for large-format panels (6 m × 2 m), with stable
selector-derived ids on every text and polyline so Inkscape edits and
future browser interactions can round-trip back to `LabelOverride`.

### Delivered
```
accuratum/renderers/svg_backend.py    ✅ render(plot, hints) -> str (SVG markup)
accuratum/cli.py                       ✅ dispatches by output extension:
                                          .svg  -> svg_backend
                                          else  -> matplotlib_backend
tests/renderers/test_svg_backend.py    ✅ structural tests: mm units,
                                          y-flip, polylines, selector ids,
                                          baseline/anchor mapping, plumb
                                          circle, base64 overlays, empty
                                          plot.
tests/test_cli.py                      ✅ end-to-end .svg test (asserts
                                          selector-derived ids present)
                                          and end-to-end .pdf test
                                          (PDF magic bytes).
```

### Key design decisions (as implemented)
- Pure-Python via `xml.etree`. No new dependency.
- mm canvas size via `RenderHints.canvas_size_mm` (defaults to A4 landscape
  297 × 210 mm; a 6 m × 2 m panel is just `(6000, 2000)`).
- Data `+y` points up; SVG `y` points down; `_emit_*` functions negate
  data `y` and the viewBox is set accordingly. One place, documented.
- `id="label-dayline-2026-01-15"` / `id="poly-dayline-2026-01-15"` /
  `id="label-hourline-7"` etc. Generated from the selector / metadata,
  not the rendered text — survives rendering changes.
- Overlays embedded as base64 data URIs so the SVG is self-contained
  (the print shop can copy one file).
- `ha`/`va` mapped to `text-anchor` / `dominant-baseline` with the
  y-flip taken into account (`va="top"` → `dominant-baseline="alphabetic"`).

### Acceptance criteria — met
- ✅ `accuratum … --output clock.svg` produces an SVG with selector ids.
- ✅ `accuratum … --output clock.pdf` produces a vector PDF (via
  matplotlib's PDF backend, since `.pdf` falls through to the mpl path).
- ✅ All 98 tests pass.
- ⏳ Visual verification in Inkscape at 6 m × 2 m (user pause).

### Subagent use
The renderer and structural tests were authored by a subagent earlier
in the rewrite. The tests had not been executed in the main thread;
once run, they passed and validated the implementation. Memory updated
with the lesson.

### PAUSE FOR VISUAL FEEDBACK
After committing, the assistant pauses and asks the user to open the
SVG output in Inkscape at 6 m × 2 m and try nudging a label by its id
before proceeding to Step 3.1.

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
4. ~~general-purpose — SVG snapshot fixtures~~ (cancelled by Step 3
   simplification).
5. ⏳ Plan — JSON schema review (start of Step 3.1).

### Pause points
- ✅ After Step 2: visual approval against v0.1.
- ⏳ After Step 3: SVG opens correctly in Inkscape at 6 m × 2 m.
- ⏳ After Step 3.1: human-in-the-loop save → edit → re-render flow works.
