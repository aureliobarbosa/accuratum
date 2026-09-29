# Accuratum — project knowledge

What has been learned and decided, and why. **This is not a history**: the
chronology is in `git log`. What lives here is the *why* — the alternative that
was dropped, the trap that shaped the current design — tagged with the commits
that carried it out, so `git show <hash>` gives the detail.

Don't read it whole: grep for the area you are touching. What is still to be
done is in [PLAN.md](PLAN.md); the one-line summary of the rules is in
[CLAUDE.md](../CLAUDE.md).

When a PLAN step closes, its findings, traps and commits move here in the same
commit that shrinks the step in PLAN.md.

---

## Domain

- **The sundial.** A vertical plumb (gnomon) of length `plumb_length` casts a
  shadow on a horizontal surface. Day lines trace the shadow tip over one day;
  hour lines trace it at a fixed clock time across many days. A year needs two
  solstice-to-solstice frames: Dec(prev)→Jun and Jun→Dec (`--period 0|1`).
- **Time is computed in UTC**; astropy/astroplan data are in UTC and
  astronomical units, not local time. The local timezone comes from
  `timezonefinder` (or `--timezone`) and is used only for labels and hour
  selection.
- **Hour lines are labelled in standard time** (see § DST hour labels).
- **Days are local days**, starting at local mean midnight, not 00 UTC
  (see § Latitude range).
- **Leap years need no special handling**; astropy takes care of them.
- **Resolution agreed with Paulo (the creator):** day lines every 7 days
  (`--dayline-day-step` default), hour lines every 20 minutes
  (`--time-step` default).

## Day/hour-line grids (v0.1, superseded)

Work from the `smart_hour_lines` branch (May 2026). The v0.1 modules were
replaced by the rewrite, but the grid logic carried over into
`core/astronomy.py` and `core/timegrid.py`, and so did these decisions.

- **Grids are bounded by real sunrise/sunset**, taken from
  `astroplan.Observer.sun_rise_time/sun_set_time` with `horizon=10°`. The
  sun below 10° gives shadows so long they wreck the drawing's scale. That
  dependency on astroplan is why the grid builders live in `astronomy.py` and
  not in `datetime_utils.py`.
- **`hourline_grid` masks sub-horizon samples as `NaT`**, so rows are ragged.
  `grid_to_shadow_xy` therefore always returns a list of 1-D rows, with NaT
  dropped per row, never a 2-D array (3ee10da, 0ae9294).
- **Rename and cleanup:** `smart_dayline_grid/smart_hourline_grid` became
  `dayline_grid/hourline_grid` (31343fa), the CLI switched to them (5db960d),
  and the old `build_*_grid` helpers were deleted (b78fed2).
- **Tests run faster** through CLI flags for grid resolution (`--line-points`,
  `--time-step`, `--*-day-step`) and coarser fixtures (172c6b1, e3a568c).
- **Logo overlay:** `--logo` / `--logo-rect`, with the default logo resolved
  through `importlib.resources` so it works from an installed wheel (06db857,
  9de9d52).

## Core rewrite: Spec → Plot → Renderer

Commits c81b9f4 … ad69d87 (May 2026), merged into `main` in **c003354**
(2026-09-28, PLAN Step 0). The only conflict was in `.gitignore`. 104 tests
pass after the merge (66 before). Motivation: v0.1 tangled geometry, label
heuristics and matplotlib in one module. The original step-by-step plan was
`docs/REWRITE_PLAN.md`; read it with `git show ad69d87:docs/REWRITE_PLAN.md`.
Afterwards `smart_hour_lines`, `rewrite-core` and `labels` were deleted,
locally and on origin. `labels` was never merged, so its code is gone; its
lessons are below. Both machines are set up for the synced Claude sessions.

### Architecture

```
accuratum/core/        spec.py (SundialSpec + JSON), plot.py (Plot/Polyline/Label),
                       hints.py (Overlay, RenderHints), metadata.py (metadata TypedDicts),
                       astronomy.py, timegrid.py, builder.py (build_plot),
                       project.py + project_io.py (project folders, since PLAN Step 1)
accuratum/projections/ accuratum.py — project(alt, az, plumb_length) -> (xs, ys)
accuratum/defaults/    labels.py (which labels), placement.py (collision heuristic; suppressed → hidden)
accuratum/renderers/   matplotlib_backend.py — render(plot, hints)
```

Public API: `build_plot(SundialSpec) -> Plot`, which is pure data. No
matplotlib, no I/O and no network inside `core/`.

### Decisions kept

- **Plugin point for other sundial types:** `projections/<name>.py`, chosen
  over a class hierarchy (long-term goal 1).
- **`SundialSpec` round-trips through JSON** (`spec_to_dict/spec_from_dict`;
  ISO datetimes; frozen sub-objects rebuilt on load). JSON rather than
  YAML/TOML because the future web app consumes it natively. Versioning
  moved to the project file (`version: 2`) in Step 1.
- **The core takes an explicit `TimeFrame(start, end)`.** Solstice resolution
  and timezone lookup stay in the CLI.
- **Overlays live in `RenderHints`, not in the spec.** Since Step 1 the
  project saves them next to the spec, outside `spec_hash`; see
  [Project folders](#project-folders-and-editable-labels).
- **Labels carry a `selector` dict**, which is the line's identity plus the
  endpoint (`{"kind": "hourline", "hour": 6, "end": "start"}`). The
  `LabelOverride` mechanism it once served was removed in Step 1.
- **Heuristics run at plot-build time** in `defaults/`. Renderers only draw
  what the `Plot` says.
- **One renderer: matplotlib.** The output extension picks the format
  (`.png`, `.pdf`, `.svg`, ...) through `fig.savefig`. A custom SVG backend
  existed until PLAN Step 2 and was dropped; see
  [SVG backend dropped](#svg-backend-dropped-step-2).
- **The CLI saves project folders** (Step 1), which replaced the
  `--spec`/`--save-spec` file mode from ad69d87.
- **Old modules were deleted** after the user approved the visual comparison
  with v0.1 (4d4d48e). The README library example was rewritten for
  `build_plot` after the merge.
- **Solstices stay approximated as the 21st** of June and December
  (`SOLSTICE_DAY` in `cli.py`), the same as v0.1's `get_solstices`.

### The mid-plan reversal (Step 3)

After Step 2 the plan was simplified to "use matplotlib's own SVG output".
Then an untracked, working `svg_backend.py` with its tests turned up on disk.
A subagent had written it earlier, and the tests had never been run in the
main thread. It was kept: it gives mm units and clean selector ids for
Inkscape, which matplotlib's SVG doesn't. See the workflow lessons below.
It was dropped for good in PLAN Step 2 (7b778d4).

### Open when the branch stopped

Resolved by Step 1: the hand-edit round trip, and whether `dx/dy` moves both
endpoints (each endpoint is now its own label). The Inkscape check moved to
PLAN Step 2 (dropped with the SVG backend), and the matplotlib guard test is in the PLAN backlog.

## Project folders and editable labels

PLAN Step 1, 2026-09-28. Commits: ff6d444 (labels), f8a9637 (project I/O),
8131f06 (CLI).

**Why.** Before, the spec kept only parameters plus `overrides`, and
`build_plot` recomputed the labels on every render. An override ran after
the heuristic's suppression checks, so it couldn't restore a dropped label
or add one. It also moved both endpoint labels at once, because both shared
one selector (the same shared selector later meant duplicate SVG ids). The
user proposed treating a run like a simulation instead: save the parameters
together with the computed result, and render from the saved result. Labels
then become plain data to edit, and overrides disappear.

**Layout.** One folder per project, `<location-slug>_<year>_p<period>` by
default (`--project-dir` sets it):

- `project.json` is short (about 90 lines for a full year) and holds
  `format`, `version: 2`, `provenance` (accuratum and astropy versions,
  creation time), `spec`, `spec_hash`, `render`, and `labels` one per line.
- `polylines.npz` holds flat `x`/`y`/`offsets` arrays plus per-line
  `kind`/`date`/`hour`/`minute_offset`, with `""`/`-1` where a key is absent,
  and the `spec_hash`. It loads with `allow_pickle=False`.

The Planaltina example lives in `example-projects/fup_planaltina_2026_p0/`.

**Format choices.**

- A single JSON file holding the geometry was rejected by the user, because
  0.5 MB of numbers is a mess to check by hand.
- Parquet would need pyarrow (about 40 MB, and neither pandas nor pyarrow was
  installed).
- CSV was offered. The user chose `.npz`: no new dependency, compact,
  numpy-native. Only the reader and writer in `core/project.py` would change
  for another format.

**Rules.**

- **`spec_hash`** is a SHA-256 of the canonical spec JSON, **excluding
  `location.name`**, so renaming a place doesn't invalidate the geometry.
  `render` is outside it too, since render settings never change geometry.
- **Loading a project:**
  - an edited spec raises `StaleProjectError`; the CLI then asks for
    `--regenerate`;
  - an npz computed from another spec is rejected;
  - a missing npz is recomputed, and the labels are kept.
- **`--regenerate`** derives the timeframe from `year` and `period` when both
  are set, so switching halves of the year is a one-field edit. A timeframe
  edited by hand is overwritten in that case. It backs up `project.json.bak`
  and resets the labels (keeping label edits is in the backlog).
- **Overwrite protection.** Generating into a folder that already holds a
  `project.json` needs `--force`.
- **Render settings.** CLI render flags override the saved `render` settings
  for that run only; they are not written back. `Overlay` gained a `name`
  (`logo`, `compass`), so a flag replaces the right one.
- **Image paths.** Package images are stored as `accuratum:fig/...` and
  resolved at render time. User images are stored as absolute paths, which
  isn't portable (backlog).
- **Precision.** Label `x`/`y` are rounded to 4 decimals on save. The data
  extent is about 11 units, so that is invisible.

**Findings.**

- In the Planaltina example, 25 of 36 candidate labels come out hidden:
  every right-side date (the Step 3 bug) and 09h–14h plus some ends (the
  plumb exclusion). Flipping `hidden` on three right-side dates, moving 07h
  and adding a free "PLANALTINA" label all rendered as expected.
- A full-year generation takes about 14 s. `--project` skips it.

**Traps.**

- **Generating writes a folder into the current directory.** CLI tests
  therefore `monkeypatch.chdir(tmp_path)` (an autouse fixture in
  `tests/test_cli.py`), and `.gitignore` has `/*_p[01]/` for runs at the
  repo root.

## Label sides (Step 3)

PLAN Step 3, 2026-09-29. Commit 3589472.

- **The bug.** `place_labels` checked each label against every placed label
  on one axis. A day line's endpoints differ in y by under 0.02 (Planaltina)
  against a 0.5 tolerance, so each right-side date was hidden behind its own
  left twin. Hour lines had the same bug on x (16h, 17h lost their bottom
  label).
- **The fix.** A label collides only with labels of the same kind and end
  (left/right dates, below/above hours). Hour labels still yield to every
  day label on `|Δx|`.
- **No latitude rule for the side.** Rendered at 0°, 10.5°, −15.6°, −30°,
  −54.8°, 51.5° and 56°: dates show on both sides everywhere, so the
  planned rule was dropped. The Planaltina example went from 25 to 16
  hidden labels of 36.
- **Seen but not fixed:** at high latitudes the hour labels are sparse and
  some sit mid-drawing (Ushuaia 09h), the logo overlaps the top-left date
  when the drawing fills the axes (Edinburgh), and Edinburgh gets a
  duplicate `12h` (backlog).

## SVG backend dropped (Step 2)

PLAN Step 2, 2026-09-29. Commit 7b778d4. The user decided to simplify and
ship instead of matching the custom SVG output to matplotlib's.

- **Why not match them.** `svg_backend.py` re-implemented matplotlib's
  layout with guesses: fixed margins (0.4·h top, 0.15·w sides), font size
  `pt × 0.005 × data_extent`, stroke `0.003 × extent`, and `ha`/`va` mapped
  to `dominant-baseline`, which Inkscape renders inconsistently. Every
  renderer change would have had to be made twice.
- **What it was for, and what replaces it.** The exact-mm canvas: any
  vector file (PDF/SVG) scales to a panel at print time, with labels and
  strokes growing with the drawing. Selector ids for nudging labels in
  Inkscape: labels are hand-editable in `project.json` since Step 1.
- **Now.** `.svg` falls through to `fig.savefig`, so it is the same drawing
  as the PNG. `--canvas-size-mm` and `RenderHints.canvas_size_mm`/`units`
  are gone. `hints_from_dict` ignores unknown keys, so old `project.json`
  files still load.
- **PDF page-size limit.** Acrobat caps a page at 14,400 units per side
  (200 in = 5080 mm) unless the file sets `UserUnit` (PDF 1.6+), and
  matplotlib doesn't set it. A 6000 mm side is ~17,008 pt, over the cap.
  For a 6 m panel, prefer SVG (no limit), or a smaller PDF scaled up at print.
- **If exact-mm files are ever needed** (a print shop insists), it's about
  half a day in the matplotlib backend, prototyped and working:
  `figsize = mm / 25.4` (SVG width comes out exact, in pt), scale font and
  line width by `canvas_w / 297` (or define them in mm), no
  `bbox_inches="tight"` for that path, `rcParams["svg.fonttype"] = "none"`
  to keep labels as `<text>`, and `artist.set_gid("label-" + selector_slug)`.
  matplotlib puts the gid on a `<g>` wrapping the element. Importing
  Inkscape nudges back would then need the inverse of `ax.transData`
  (figure pt, not data units), e.g. stored in the SVG `<metadata>`.

## DST hour labels (Step 4)

PLAN Step 4, 2026-09-29. Commit 963e20c.

- **The bug.** Edinburgh, period 0: two hour lines labelled `12h` (sharing a
  selector), none `14h`.
- **Cause.** An hour line is one fixed UTC time of day across the half-year
  (`hourline_grid` anchors rows at UTC offsets). It was labelled with the
  local clock at its middle *valid* sample. Rows have different numbers of
  valid samples (the horizon cut masks winter mornings and evenings), so
  their middle samples fall on different dates, on both sides of the
  29 March switch to BST. Neighbouring rows then read different clocks.
- **Fix.** `_utc_dt64_to_standard_time` in `core/builder.py` removes
  `dst()` from the local time, so each line carries the zone's standard
  hour. Lines don't move. Sundials conventionally read standard time; a
  line can't carry both clocks, because the DST shift happens partway along
  the same curve. Splitting each line at the switch was rejected: two clocks
  on one dial.
- **Checked.** Edinburgh now runs 05h–19h GMT. `12h` sits just before the
  centre line, matching solar noon ≈ 12:13 GMT at 3.19° W. Planaltina (no
  DST) regenerates with identical labels.
- **Test.** `test_hour_lines_are_unique_and_consecutive_across_dst` needs a
  fine hourline grid (7-day step, 20-min time step) to reproduce the
  duplicate; the module's coarse `FAST_GRID` doesn't.

## Latitude range (Step 5)

PLAN Step 5, 2026-09-29. Commits 2966726, a28f3af, a290a3a.

- **Sweep.** Dials at 0°, ±15°, ±30°, ±45°, ±55°, ±62° and Ferraz
  (62.08° S, 58.39° W), both periods, then 64°–80° and lon −170°…+170°.
  Up to ±55° nothing broke.
- **Polar-winter days (2966726).** Past |lat| ≈ 56.5° (90° − 23.44° − 10°)
  the winter noon sun stays below the 10° horizon cut. astroplan then
  returns *masked* rise times (with a `TargetNeverUpWarning`), and
  `sun_set_time(masked)` crashed with a `numpy.einsum` TypeError.
  `get_sunrises_and_sunsets` now returns NaT for those days (and silences
  the warning), `hourline_grid` ignores them when sizing its window, and
  `build_plot` drops empty polylines. The dial simply ends before the
  winter solstice: at ±62° about May–July (south) or Nov–Jan (north) is
  missing. That's the cut, not a bug.
- **The 10° cut stays; no latitude-dependent cut (user decision).** A
  lower cut would keep the winter solstice, but shadow length is
  `plumb / tan(alt)`: 5.7× the plumb at 10°, 12.7× at 4.5°. The panel's
  size is set by its longest shadow, so a few winter weeks would more than
  double its north–south extent and shrink the part used all year. Long
  shadows also have blurry tips (the sun is ~0.5° wide), and a low sun is
  the first to be blocked by terrain and buildings. A panel you can build
  beats a full year. Don't add features in that direction.
- **Longitude wrap (a28f3af), found by the sweep.** `hourline_grid`
  measured each sunset from *its own* UTC date. Wherever the local day
  straddles 00 UTC (lon ±120°…±170°: US west coast, East Asia, Australia,
  New Zealand), a sunset after 00 UTC wrapped to a few minutes and the dial
  had **no hour lines at all**, at any latitude. Days are now local days:
  rise/set are searched from *local mean midnight* (00 UTC − 4 min per
  degree of longitude, rounded to the minute, `local_mean_midnights` in
  `core/astronomy.py`) and measured from it. The frame's days are its
  local dates (`_frame_days`): 21 Jun 00:00 in Sydney is 20 Jun in UTC.
  Hour lines where nothing wrapped are identical; day-line ends move by
  <0.003 plumb lengths (astroplan's solver starting elsewhere).
- **MAX_LATITUDE = 75° (a290a3a).** With no further code changes, dials are
  clean at ±75° at every longitude tried. At ±75.5° label selectors repeat.
  The summer sun then stays above the 10° cut nearly all day, the hour window
  nears 24 h, and two lines round to the same hour (the selector carries the
  hour, not `minute_offset`). The theoretical wall is 76.56°
  (90° − 23.44° + 10°): there the summer sun never drops below 10°, and
  summer days drop out as well. `Location.__post_init__` rejects |lat| > 75; the CLI
  exits before the timezone lookup.
- **Not bugs.** Hooks on early/late hour lines near the cut (e.g. −55° p1,
  Sydney) are the analemma turning at the solstice. A p0 dial's top line
  is labelled with June's *first* day line (e.g. `06/07`), not `06/21`:
  the month-transition label rule.
- **Tests.** Edge builds at ±62° and ±75° (`test_builder.py`), never-up
  days (`test_astronomy.py`, `test_timegrid.py`), the wrap at four
  longitudes, and local frame dates in Sydney.

## Label placement lessons (from the unmerged `labels` branch)

Ported to `defaults/placement.py`. Originally recorded in
`docs/LESSONS_LABELS.md` (`git show ad69d87:docs/LESSONS_LABELS.md`).

- **Labels sit at line endpoints only.** Day lines get `MM/DD` left of the
  first sample and right of the last; hour lines get `HHh` below the first and
  above the last.
- **One day-line label per local month transition.** One hour-line label per
  row whose *middle* sample falls within `time_step/2` of an exact hour. The
  middle sample avoids DST bias at the ends.
- **Day and hour passes share one set of placed labels**, with days first. At
  the period edges their endpoints converge, and hour labels must yield to day
  labels.
- **Plumb exclusion radius, hour labels only** (~12% of the data extent). It
  kills the noon cluster at the plumb base.
- **Collisions are checked per axis:** day lines compare `|Δy|`, hour lines
  compare `|Δx|`. A 2-D box check let near-axis stacks slip through. Only
  labels on the same side are compared (Step 3).
- **Tolerances scale with the data extent** (~4% of `max(range_x, range_y)`).
  Fixed thresholds calibrated on unit-sized prototypes failed on ±6-unit
  plots.
- **Known limits:** extreme latitudes are untested, and collision math uses
  data coordinates rather than display coordinates. It is best-effort by
  design, which is why overrides exist.

## Dev environment and multi-machine sync

- **Devcontainer:** `mcr.microsoft.com/devcontainers/python:3.11`, with the
  `.devcontainer/setup.sh` post-create script. uv for everything; build
  backend `uv_build`.
- **CI** (`.github/workflows/ci.yml`) runs `ruff check`, `ruff format --check`
  and `pytest` on pull requests and `v*` tags only. **A `v*` tag builds the
  wheel and publishes a GitHub Release.** A plain push to `main` triggers
  nothing.
- **Claude sessions sync through Dropbox** (d941f09, 380e420, b556631,
  7b9b70f).
  - The folders `projects, file-history, skills, agents, commands, plans,
    todos` are bind-mounted from `~/Dropbox/claude-code/` into
    `/home/vscode/.claude-code/`, with `CLAUDE_CONFIG_DIR` pointing there.
  - Credentials, `.claude.json` and `settings.json` stay in the per-machine
    Docker volume `claude-code-state` and never reach Dropbox.
  - Sessions are filed by container path (`/workspaces/<folder>`), so **the
    project folder must have the same name on every machine**.
  - `cleanupPeriodDays: 100000` in the seeded `settings.json`: the default
    30-day cleanup wiped the sessions during the 4-month break.
  - **Never keep the same session open on two machines.** To move one: close
    it, commit and push, wait for Dropbox's ✓, then pull and resume on the
    other machine.
  - To reuse this in another project, copy the `initializeCommand`, `mounts`
    and `remoteEnv` keys of `.devcontainer/devcontainer.json`, plus the top
    of `setup.sh` (the `chown` of the volume and the `settings.json` seed).
    The container user must be `vscode`, or both paths need adjusting.
- **Git is the source of truth for code and project context.** `.venv` and
  generated images don't travel. `uv.lock` is committed together with any
  dependency change.

## Traps

- **astroplan returns `datetime64[ns]`.** Everything else assumes `[s]`, so
  cast on the way out of `get_sunrises_and_sunsets` (b7aa3fd).
- **Nominatim allows at most 1 request per second** and the free service
  times out at random. Tests mock `accuratum.location.Nominatim` via
  `pytest-mock`. Real calls made CI flaky (fixed in PR #7, 8710e2e). In the
  README and CLI, `--lat-long` is the reproducible path.
- **Negative CLI coordinates need `=`:** `--lat-long=-15.78,-47.92`,
  otherwise argparse reads `-15.78` as a flag.
- **Single-file bind mounts break** when a program saves by writing a new file
  and renaming it. That's why only folders are mounted and `settings.json`
  isn't synced.
- **Ubuntu's `/bin/sh` is dash, which doesn't expand `{a,b}`**, so the
  devcontainer's `initializeCommand` runs through `bash -c`.
- **Bind-mount sources must exist before the container starts**, or Docker
  creates them owned by root. `initializeCommand` runs `mkdir -p` on the host
  first.
- **Generated PNG/SVG at the repo root are ignored** (`/*.png`, `/*.svg`,
  1f10f86). Assets in subfolders (`accuratum/fig/`, `images/`)
  stay tracked.

## Workflow lessons

- **Reassess the remaining steps after each one.** Finishing a step often
  makes a later one cheaper or unnecessary. Example: the planned custom SVG
  renderer looked replaceable by matplotlib's SVG output after Step 2.
  Propose the simplification before carrying on with the plan as written.
- **Run a subagent's tests in the main thread before trusting them.** Treat
  untracked files as possibly agent-written until you have checked them.
  Unverified agent output was almost deleted as "speculation" during the
  rewrite.
