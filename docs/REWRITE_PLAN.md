# Accuratum core rewrite — plan

Tagged baseline: **v0.1** (`main` at the time of this plan). The rewrite
restarts the package architecture; the `labels` branch is preserved as a
reference for the label-collision heuristic but will not be merged.

The rewrite is a strict chain: Step 1 unlocks Steps 2, 3, 3.1. Steps 2 and 3
can run in parallel after Step 1 if desired.

---

## Step 1 — Functional core: `Spec → Geometry → Plot`

### Goal
Make the library a pure data pipeline. No matplotlib, no I/O, no global
state inside the core. Renderers come later (Step 2+).

### Deliverables
```
accuratum/
  core/
    spec.py          # SundialSpec, RenderHints (dataclasses)
    plot.py          # Plot, Polyline, Label (pure data, no mpl)
    astronomy.py     # solar geometry (mostly moved from current astronomy.py)
    timegrid.py      # explicit date/time grid builders
  projections/
    accuratum.py     # project(altaz, plumb_length) -> (x, y)
  defaults/
    labels.py        # default label-selection rules (current per-month / per-hour logic)
    placement.py     # default endpoint placement & collision rules (current heuristic)
  __init__.py        # re-export public API: SundialSpec, build_plot(...)
```

**Public API:**
```python
spec = SundialSpec(location=..., dates=..., hours=..., overrides=...)
plot = build_plot(spec)              # pure data in, pure data out
# (Step 2 adds:) figure = render_matplotlib(plot)
```

### Key design decisions
- `SundialSpec` is JSON-serializable (primitive fields, ISO date strings,
  dicts of overrides). Enables Step 3.1, Step 4 (web), Step 5 (paper)
  without rework.
- No automatic solstice/timezone resolution inside the core. The CLI
  resolves those before constructing the Spec. The core takes explicit
  dates and times — deterministic and testable.
- `Plot` is a list of `Polyline` and `Label` objects with coordinates.
  No matplotlib types anywhere. Polylines carry a `kind` field
  (`"dayline"`, `"hourline"`, future types).
- Defaults are functions over a Spec, not baked into `build_plot`. Calling
  `build_plot(spec)` runs them; passing `spec.overrides` short-circuits any
  of them.

### Acceptance criteria
- CLI rebuilt on the new core produces output visually equivalent to v0.1
  for a fixed seed/location.
- `build_plot(spec)` is fully deterministic, no network, no matplotlib
  import.
- Every public function is testable with no I/O mocking other than the
  astropy geometry layer.
- Roundtrip: `Spec → JSON → Spec → Plot` gives the same plot.

### Test strategy
- TDD on `core/timegrid.py` and `defaults/*` (pure functions, easy).
- Regression tests on `projections/accuratum.py` against known
  lat/lon/time values from v0.1.
- Snapshot test for `Plot` from a fixed spec (small JSON in
  `tests/fixtures/`).
- `graph.py` (Step 2) remains TDD-exempt per Agents.md; `build_plot` is
  testable end-to-end without rendering.

### Effort & risk
~2–3 focused sessions. Most code already exists — this is re-shaping
boundaries plus adding the Spec/Plot dataclasses. Risk: scope creep into
"while we're here, let's improve…" — resist; the only job is restructuring.

### Subagent use (sequential)
1. **Pre-flight Explore:** inventory of current code — which functions are
   pure, which have hidden I/O, which have matplotlib coupling. Output: a
   short markdown report.
2. **Optional Plan agent at end:** one-shot review of the Spec/Plot
   dataclass design.

---

## Step 2 — Matplotlib renderer as a thin adapter

### Goal
Reproduce v0.1 output (lines, labels, compass, logo) by reading a `Plot`.
No core logic in the renderer.

### Deliverables
```
accuratum/
  renderers/
    matplotlib_backend.py   # render(plot, hints) -> matplotlib.Figure
```
Revive the CLI: `spec = …; plot = build_plot(spec); fig = render_matplotlib(plot); fig.savefig(...)`.

### Key design decisions
- Renderer takes a `Plot` and a small `RenderHints` dataclass (figsize,
  colors, font, output_dpi, overlay rects). No solar geometry inside.
- The `labels`-branch collision heuristic ports into
  `defaults/placement.py` and runs at *plot-build* time. The renderer just
  draws labels at the positions the Plot tells it to.
- Logo/compass overlays become `OverlayImage` entries in the `Plot`. Same
  primitive, two configurations.

### Acceptance criteria
- Reproduces v0.1 output for a fixed seed/location (visual diff acceptable;
  pixel diff not required).
- Existing CLI integration tests pass after Spec construction is wired in.
- All overlays handled via the generic `OverlayImage` mechanism.

### Test strategy
- Renderer remains TDD-exempt. End-to-end smoke test + manual visual
  review at one location.
- A guard test importing `accuratum.core.*` and asserting `matplotlib` is
  not importable from there.

### Effort & risk
~1 session. Risk: matplotlib types leaking into core via Plot field types.

### Subagent use
Main thread. Renderer is small (~200 lines) and needs visual iteration.

### PAUSE FOR VISUAL FEEDBACK
After this step completes, the assistant **pauses and asks the user to
visually compare the new output against v0.1** before proceeding to
Step 3.

---

## Step 3 — SVG renderer

### Goal
Second backend, same `Plot` input. Enables large-format printing (req 2)
and prepares the way for browser-side rendering later.

### Deliverables
```
accuratum/
  renderers/
    svg_backend.py    # render(plot, hints) -> str (SVG markup)
```
CLI gets `--format svg` (or infers from `--output *.svg`).

### Key design decisions
- Pure-Python SVG via string templates / `xml.etree`. No new dependency.
- Use millimeters, not pixels. A 6 m × 2 m panel is
  `width="6000mm" height="2000mm"`.
- Reuse the *same* `Plot` from Step 1. If a different intermediate is
  needed, fix Step 1 — don't fork.
- Text labels are real SVG `<text>` elements (selectable, editable in
  Inkscape) — enables print-shop nudges without re-running Python.

### Acceptance criteria
- SVG renders geometrically identical to the matplotlib PDF output for one
  canonical Spec.
- Opens cleanly in Inkscape / a browser at screen size and at 6 m × 2 m.
- Snapshot tests for small fixed Plots pass.

### Test strategy
- SVG generator tested against snapshots of small fixed Plots (lines,
  labels, overlays). Subagent-friendly boilerplate.
- Manual: open the 6 m × 2 m output in Inkscape, eyeball, attempt one
  label nudge.

### Effort & risk
~1–2 sessions. Gotcha: SVG `text-anchor` semantics differ slightly from
matplotlib `ha`/`va`. Risk: discovering the Plot needs more metadata
(e.g., per-label alignment). If so, fix Step 1 cleanly.

### Subagent use (sequential)
1. **general-purpose**: generate SVG snapshot fixtures + tests once the
   generator is drafted.

### PAUSE FOR VISUAL FEEDBACK
After this step, the assistant pauses and asks the user to open the SVG
output in Inkscape (and/or browser at 6 m × 2 m) before proceeding to
Step 3.1.

---

## Step 3.1 — Spec file I/O and override mechanism

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
The override mechanism is wired up: `spec.overrides.label_positions["06h"] =
(dx, dy)` survives a round-trip and applies in `build_plot`.

### Key design decisions
- **JSON**, not YAML/TOML. The eventual web app eats JSON natively.
- CLI gains two modes:
  - **One-shot mode** (today): all args on CLI, no spec file.
  - **Spec-file mode**: `--spec clock.json` is source of truth; CLI args
    still override fields if given.
- `--save-spec` lets a user dump their CLI invocation to JSON, then
  iterate by editing the file. Smallest possible human-in-the-loop UX.
- Include a `spec_version` field from day 1.

### Acceptance criteria
- `accuratum --lat-long=… --save-spec clock.json` produces a spec.
- `accuratum --spec clock.json` reproduces the same output.
- Edit a label override in `clock.json`, re-render, see the label move.
- All existing CLI tests pass; new tests cover roundtrip and override
  application.

### Test strategy
- TDD on `spec_io.py` (roundtrip, version handling, malformed-file errors).
- Integration test: save → edit → load → render → check the label moved.

### Effort & risk
~1 session. Risk: schema bikeshedding — decide once with
`dataclasses.asdict` defaults; refine only when overrides reveal a real
problem.

### Subagent use (sequential)
1. **Plan agent**: one-shot review of the JSON schema (field names,
   version strategy, override key conventions) before implementation.

### PAUSE FOR VISUAL FEEDBACK
After this step, the assistant pauses and asks the user to test the
save → edit → re-render flow before declaring the rewrite stage complete.

---

## Cross-cutting

### Lessons from the `labels` branch
Write `docs/LESSONS_LABELS.md` early — half a page summarizing the
heuristic discoveries (auto-scale tolerance, plumb exclusion radius, 1-D
collision per axis, shared placed-labels set, hour-yields-to-day
priority). Institutional memory; prevents rediscovery.

### Branch strategy
- `rewrite-core` branch off `main` (already created).
- Commit per subtask, per Agents.md.
- Do not push to `main` until at least Step 1 + Step 2 land and the user
  has visually approved.
- Do not merge `labels` branch into `main`.

### Subagent execution
Per user instruction: **agents run in sequence, not parallel.**
1. Explore agent — code inventory (before Step 1 implementation).
2. claude agent — write `LESSONS_LABELS.md`.
3. Plan agent — review Spec/Plot dataclass design (end of Step 1).
4. general-purpose — SVG snapshot fixtures and tests (during Step 3).
5. Plan agent — JSON schema review (start of Step 3.1).

### Pause points
- After Step 2: visual approval against v0.1.
- After Step 3: SVG opens correctly in Inkscape at 6 m × 2 m.
- After Step 3.1: human-in-the-loop save → edit → re-render flow works.
