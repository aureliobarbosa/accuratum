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

Commits c81b9f4 … ad69d87 (May 2026), merged into `main` in **fbe6857**
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
It was dropped for good in PLAN Step 2 (1543af6).

### Open when the branch stopped

Resolved by Step 1: the hand-edit round trip, and whether `dx/dy` moves both
endpoints (each endpoint is now its own label). The Inkscape check moved to
PLAN Step 2 (dropped with the SVG backend), and the matplotlib guard test is in the PLAN backlog.

## Project folders and editable labels

PLAN Step 1, 2026-09-28. Commits: 3c1cfa3 (labels), f6effd8 (project I/O),
adb38de (CLI).

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

PLAN Step 3, 2026-09-29. Commit bd3bc8d.

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

PLAN Step 2, 2026-09-29. Commit 1543af6. The user decided to simplify and
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

PLAN Step 4, 2026-09-29. Commit 5e58d54.

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

PLAN Step 5, 2026-09-29. Commits 77831fd, b113142, 1ce757f.

- **Sweep.** Dials at 0°, ±15°, ±30°, ±45°, ±55°, ±62° and Ferraz
  (62.08° S, 58.39° W), both periods, then 64°–80° and lon −170°…+170°.
  Up to ±55° nothing broke.
- **Polar-winter days (77831fd).** Past |lat| ≈ 56.5° (90° − 23.44° − 10°)
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
- **Longitude wrap (b113142), found by the sweep.** `hourline_grid`
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
- **MAX_LATITUDE = 75° (1ce757f).** With no further code changes, dials are
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

## Header band (Step 5.1)

PLAN Step 5.1, 2026-09-29. Commit 2c2ef86.

- **The bug.** Overlays (logo, compass) are figure-coordinate rects, drawn
  on top of the axes. The drawing's shape changes with latitude *and*
  period: Edinburgh p0's logo hid `06/07`, +62° p1's compass covered
  `06/21` and `08/02`, −62° p0 was just clear, and at ±75° the horseshoe
  fills both top corners. So "check the southern hemisphere, then pick the
  emptier corner" had no single answer, and the horseshoe has no empty
  corner.
- **Fix.** `RenderHints.axes_rect` (default `(0.07, 0.05, 0.9, 0.75)`) holds
  the drawing, with `ax.set_anchor("N")` so it hugs the top of that rect
  whether it is wide (tropics) or tall (high latitudes). The default overlays
  moved to `y = 0.82`, in the header band above. `bbox_inches="tight"`
  crops the unused margins.
- **Old projects keep their saved overlay rects** (`y = 0.75`), which still
  dip into the new axes area. There is no migration; re-render them with
  `--logo-rect`/`--compass-rect`, or edit `project.json`. The two example
  projects were edited.
- **Cosmetic, left as is.** Overlays are placed relative to the figure, not
  to the drawn axes, so on a tall (narrower) drawing the logo sits a little
  left of the frame.
- **No frame around the drawing** (user request). The axes spines were
  matplotlib's default, not a feature; the axis numbers (plumb lengths)
  stay.
- **Tests.** The renderer keeps wide, square and tall drawings inside
  `axes_rect` and pinned to its top; the CLI's default overlays lie above
  it.

## Title and subtitle (Steps 5.2–5.3)

PLAN Steps 5.2 and 5.3, 2026-09-29. Commits a6f7cf3 (first version),
6e9ec89 (moved into the `Plot`).

- **Defaults.** Title: the location name, or `15.60° S, 47.65° W` without
  one (`--lat-long`). Subtitle: the spec's timeframe as
  `yyyy-mm-dd / yyyy-mm-dd`, even past 56.5° where the dial ends before the
  winter solstice. Both in `defaults/titles.py`.
- **They are `Plot` data, like labels** (5.3). `build_plot` fills the
  defaults, `project.json` saves the exact text as top-level `title` and
  `subtitle` next to `labels`, and the renderer draws `plot.title` and
  `plot.subtitle` when non-empty. `""` leaves one out. Placement
  (`title_xy`, `subtitle_xy`, figure coords) and font sizes stay in
  `RenderHints`, like the overlay rects. A `project.json` without the keys
  gets the defaults on load.
- **Why 5.2's version was replaced.** 5.2 kept the texts in
  `RenderHints.title`, `null` meaning "default", resolved by the CLI's
  `_resolved(hints, spec)` because the renderer never sees the spec. So
  `render(build_plot(spec))` from Python drew no title, the website would
  have had to copy CLI code, and `"title": null` didn't show what was
  drawn. It never left the machine, so there is no migration.
- **Flags.** `--title`/`--subtitle` are saved when generating. With
  `--project` they apply to that run only, like every render flag.
- **`--regenerate`** keeps a text edited by hand and recomputes one still
  equal to the old default, so a new `period` updates the subtitle.
  **Trap:** "old default" comes from the spec as it is in `project.json`,
  i.e. after hand edits (only the timeframe is recomputed later). After
  editing `location` (the name, or lat/lon without a name) and
  regenerating, the old location's default title counts as edited and is
  kept. Rewrite `title` by hand then.
- **Renaming `location.name` no longer renames the title** (5.2 did). Edit
  `title` instead; the name still sets the default folder name.
- **Fit.** At 14 pt, a 38-character title fits between the default logo and
  compass; longer ones reach the overlays. No shrink-to-fit: edit
  `title_fontsize` in `project.json`.
- **Example projects** got `location.name` (`FUP Planaltina`,
  `Edinburgh`) and were re-saved, so their `project.json` shows the texts
  and every render hint. Their PNGs didn't change between 5.2 and 5.3.

## Line colors (Step 5.4)

PLAN Step 5.4, 2026-09-30.

- **Why two colors.** Every line was `green`, so the date grid and the hour
  grid were told apart only by direction, which is hard where they cross
  at shallow angles (the dial's edges, high latitudes).
- **Why vermillion and blue.** They come from the Okabe–Ito palette, which
  was made for color-blind readers. A simulation (Machado et al. 2009,
  full severity, CIELAB distance) kept them far apart for every type:
  ΔE ≈ 115 normal, 92 protan, 108 deutan, 102 tritan. Red/green drops to
  ΔE ≈ 7 for deutans. Okabe–Ito orange `#e69f00` scores higher for
  protans but drops to 79 for tritans, and it is too light (L\* 71) for
  0.5 pt lines on white. Vermillion (L\* 54) and blue (L\* 46) both read
  well as thin lines. In deutan and protan vision they look olive and
  grey-blue; in tritan vision, pink and teal.
- **Which is which.** Hourlines are blue and daylines vermillion. There is
  no strong reason for this choice; swap them by flag if the collaborators
  prefer.
- **Labels stay black.** Colored labels were not asked for, and thin
  colored text is harder to read than thin colored lines.
- **Storage.** `RenderHints.dayline_color` and `hourline_color` replace
  `line_color`. They are render hints, so changing them never invalidates
  the geometry. The renderer picks the color by `Polyline.kind`. An old
  `project.json` with `line_color` loads with the new defaults (the old key
  is dropped like the SVG canvas keys), since no flag ever set it.
- **CLI.** `--dayline-color`/`--hourline-color` accept any matplotlib color
  (`orange`, `C1`, `#123ABC`) and `parse_color` saves it as lowercase
  `#rrggbb` through `matplotlib.colors.to_hex`, which drops any alpha. So
  `project.json` always holds the format that `<input type="color">`
  reads and writes. The website should accept that format only (see
  PLAN's security list).

## PyPI publishing (Step 5.5)

PLAN Step 5.5, 2026-10-01. Commits 24e6381 (plan, README), 6551fcc
(`publish.yml`), 0094653 (0.2.1), 5a197e8 (approval gate to the backlog),
0d5765b (moved into `ci.yml`). First upload: `v0.2.1`, about 3.5 minutes
after the tag; https://pypi.org/p/accuratum. 0.2.1 was deleted on
2026-10-04 with the old repo; the fresh repo's first upload is 0.2.2
(70fe0f4), about 3 minutes after the tag. The publisher matched
unchanged (same owner, repo name, workflow and environment), and
GitHub created the `pypi` environment on first use.

- **Why now.** PyPI was to wait for the paper. The user moved it ahead to
  secure the name: a PyPI *pending* publisher does not reserve it, and if
  someone else registers it first the pending publisher is invalidated.
  Accepted at the time: the wheel made the library's source public while
  the repo was still private, so the PyPI page's GitHub links didn't
  resolve yet.
- **Trusted Publishing, no token.** The `pypi` job (`id-token: write`, on
  that job only) gets a GitHub OIDC token. PyPI trades it for a short-lived
  upload token because it matches the registered publisher: owner
  `aureliobarbosa`, repo `accuratum`, workflow **`ci.yml`**, environment
  `pypi`. Renaming `ci.yml` or the environment breaks publishing until the
  publisher on PyPI is edited to match. The PEP 740 attestation on PyPI names
  these same four values.
- **Why in `ci.yml`, not `publish.yml`.** The first version was a separate
  `publish.yml` on the same `v*` tag. It ran in parallel with the tests,
  and `needs:` can't wait on a job in another workflow. A PyPI version can
  never be reused, only yanked, so the upload must follow the tests. In
  `ci.yml` the `pypi` job follows `build`, which waits for `test` and
  `lint`, and uploads the same wheel as the GitHub Release. Rejected:
  `workflow_run` (artifacts from another run, a trigger zizmor flags) and
  a reusable workflow (PyPI matches the caller's workflow, not the
  reusable one).
- **Wheel only.** `build` still makes the sdist for the GitHub Release; the
  `pypi` job deletes `dist/*.tar.gz` before uploading. The wheel is pure
  Python (`py3-none-any`), so no platform needs the sdist.
- **Tag = version.** `build` fails unless the tag is `v` + `uv version
  --short`, so a mistyped tag stops before PyPI.
- **No approval gate.** The GitHub environment `pypi` allows only `v*`
  tags. Required reviewers need a public repo on the owner's plan (the
  checkbox doesn't show on a private repo), so a tag whose tests pass
  uploads without a click. On the backlog for when the repo goes public.
  Creating a `v*` tag stays an ask-first action in CLAUDE.md.
- **Hardening.** `ci.yml` got a read-only default token
  (`permissions: contents: read`); `release` and `pypi` widen it for
  themselves. The publish action is pinned by SHA.
- **README is the PyPI description,** so its relative links became full
  GitHub URLs.

## Website groundwork (Step 6)

Prepared 2026-09-30, before Step 6 starts. Nothing is built yet.

**Reference: Bingo** ([github.com/aureliobarbosa/bingo](https://github.com/aureliobarbosa/bingo),
live at bingo410.web.app), the same author's earlier web service:

- A stateless FastAPI service: each request carries the whole config and
  gets a PDF back. The page is Bootstrap and plain JavaScript, with no
  build step.
- The user saves and opens a JSON config file; `localStorage` keeps the
  last one. An uploaded logo travels as a data URI inside the JSON.
- A multi-stage Dockerfile, with every stage on one base image.
- Cloud Run in `southamerica-east1`, behind Firebase Hosting for a free
  HTTPS address.
- `deploy.yml` logs in to Google without keys (WIF) and deploys the image
  by digest. It is kept apart from `ci.yml` so it never runs on pull
  requests.
- A CI job starts the container and runs a smoke test.
- Security headers (CSP), request size limits and a per-IP rate limit.

**Measurements** (this dev container; Brasília, one half-year, default
grid):

| | |
|---|---|
| `build_plot` | 10.2–10.5 s |
| Render (SVG, PNG or PDF) | 0.13–0.18 s |
| Output size | SVG 82 kB, PDF 31 kB, PNG 334 kB (200 dpi) |
| Geometry | 62 lines, 19,276 points; 321 kB as JSON with 4 decimals |
| Project folder | `project.json` 8 kB, `polylines.npz` 296 kB |
| Peak memory | 260 MB (Bingo: 47 MB) |
| Imports | 0.9 s |

**Where the time goes.** About 85% of `build_plot` is astropy's
high-precision ICRS→AltAz transform, mostly erfa `epv00` (Earth position)
and `pnm06a` (precession-nutation). astroplan's sunrise and sunset take
6.2 s of the 10, through the same transform. astropy's
`ErfaAstromInterpolator(300 s)` made it slower (13.0 s against 10.5 s),
with the same result to 1e-6 plumb lengths. Getting to about 1 s would
take grouping the 66 transform calls into a few, or a simpler
sun-position formula. The website doesn't need that.

**What must differ from Bingo:**

- **Two routes, not one.** Bingo regenerates everything on each edit
  (0.25 s, 400 ms debounce). Here, `/api/plot` (spec → geometry, labels,
  title) takes about 10 s and runs from a button. `/api/render` (project →
  SVG) is fast enough to update live. This is the CLI's own split between
  generating a project and `--project`. The browser keeps the geometry and
  sends it back with each preview (321 kB, under Bingo's 4 MB request
  cap), so the service stays stateless.
- **No astropy downloads at run time.** On first use astropy fetched
  `finals2000A.all` and `Leap_Second.dat` (they are in
  `~/.astropy/cache`). On Cloud Run every new instance would download them
  again, need a writable home folder, and fail when the server is down.
  `iers.conf.auto_download = False` uses the tables bundled in
  `astropy-iers-data`. The error is under 0.9 s of time (UT1−UTC), which
  doesn't matter for a sundial.
- **Renderer without pyplot.** `render` calls `plt.figure()`, whose global
  state isn't safe when FastAPI runs requests in parallel threads. Use
  `matplotlib.figure.Figure()`.
- **Resources.** At least 512 MiB of memory, few requests at a time per
  instance, and a much stricter rate limit on `/api/plot` than Bingo's 120
  per minute. Cap the grid settings or keep them off the page: small steps
  would pass the 60 s timeout of Cloud Run and of Firebase Hosting.
- **Place search.** Nominatim allows 1 request per second, forbids
  search-as-you-type, and would see every visitor's search from the
  server's IP. The alternatives are coordinates, a map click (Leaflet and
  OpenStreetMap tiles, allowed in the CSP), or a search from the visitor's
  browser.
- **Preview as an SVG image**, not a PDF in an `<iframe>`. That avoids
  Bingo's `blob:`/CSP/Firefox pdf.js traps.

**Repo layout: monorepo, with `web/` as its own project** (user's
decision, 2026-09-30). `web/` has its own `pyproject.toml` and joins the
library through a uv workspace. The library stays at the repo root.

- *Two repos* were rejected, though they have real advantages: a library
  repo that shows only the library (for the paper, PyPI and a DOI archive),
  independent release timing, no cloud deploy setup in the library repo,
  and a site that can only use the public API. Against them: most early
  changes touch both parts, which means two commits plus a tag or pin each
  time; a local-path override to try unreleased library code; and two sets
  of docs and CI to maintain.
- *The website inside the package* (`accuratum/web/`, an `accuratum[web]`
  extra) was rejected because the PyPI wheel would carry a web server,
  HTML and JavaScript, and every website change would become a library
  version.
- *Why this layout:* one developer, early changes touch both parts, one
  set of docs drives the sessions, and the wheel stays library + CLI only.
  Splitting later is one `git filter-repo --subdirectory-filter web`.

**Wheel and PyPI.** The wheel goes out through the existing `v*` GitHub
Releases (`ci.yml` runs `uv build`). PyPI was to wait until the first
version of the paper was submitted. The user reversed that on 2026-10-01:
the wheel goes to PyPI from 0.2.2 on (Step 5.5).

**Traps to carry into Step 6:**

- `v*` tags are library releases. Website deploys need another trigger: a
  `site-v*` tag, or a push that touches `web/`.
- `deploy.yml` must never run on pull requests; the library repo will take
  outside pull requests after publication.
- The workspace shares one `uv.lock`, so the website's dependencies must
  install on the library's Python 3.11 baseline.
- The website imports only the library's public API. What it needed from
  `cli.py` became public in Step 6.1 (next section).

## Library prep for the website (Step 6.1)

2026-09-30. Commits a65dccd (solstice_timeframe), 0f3e232 and c2ea342
(overlays, path confinement), e04ef01 (Figure), 2a10cf0 (IERS), c898fa0
(validation), 0bebd86 (wheel smoke test).

- **Public API for the site.** `core.spec.solstice_timeframe(year,
  period, tz)` (it now rejects periods other than 0/1).
  `defaults.overlays`: `DEFAULT_OVERLAYS`, `default_render_hints()` (fresh
  overlay list per call), `resolve_image_path()`. The CLI keeps only
  argv, file checks and output.
- **`accuratum:` paths are confined to the package.** The resolved path
  must stay under the package root; `accuratum:../..` raises
  `ValueError`, which the CLI prints as an error.
- **Bare `Figure`, no pyplot.** pyplot's global figure list isn't
  thread-safe. A bare `Figure` saves PNG/PDF/SVG without a backend, so
  the CLI dropped `matplotlib.use("Agg")` and `plt.close`. The PNG came
  out identical pixel for pixel.
- **IERS: bundled tables, no downloads** (option *a* of three; the
  others were fresh tables baked into the Docker image, or fetched from
  Cloud Storage at startup). `core/astronomy.py` sets
  `iers.conf.auto_download = False` **and** `auto_max_age = None`.
  Without the second, every computation raised, because the bundled
  predictions (astropy-iers-data 0.2026.4.13) are older than 30 days.
  Geometry vs. the downloaded tables: at most 6.3e-5 plumb lengths
  (0.06 mm with a 1 m plumb). Past the table's end (about April 2027)
  astropy warns and falls back to mean polar motion, as it did with
  downloads on. The tables refresh when `uv lock --upgrade` bumps
  astropy-iers-data. The test runs a subprocess with `HOME` at an empty
  folder and sockets blocked; astropy ignores `XDG_*` when
  `~/.astropy` exists, so `HOME` is what works.
- **Spec validation** (in `__post_init__`, so `spec_from_dict` gets it
  too; it also turns `KeyError`/`TypeError` into `ValueError`, so callers
  catch one error): finite lat/lon, lon within ±180°, a known IANA zone
  (also blocks `../` names), timeframe 0 < span ≤ 366 days,
  `line_points` 2–10,000, `time_step_minutes` 1–240, day steps 1–183,
  `horizon_degrees` 0–45, `plumb_length` finite and > 0, `year`
  1901–2100 (ERFA's `epv00` warns outside 1900–2100; period 0 starts in
  December of the year before), `period` 0/1. Integers reject bools and
  floats. `sundial_type` stays checked in `build_plot`, the plug-in point.
  The bounds stop absurd values, not slow ones, so the site must not
  expose the grid. A `SundialSpec` is mutable, so assignment after
  construction skips the checks.
- **The wheel from a clean install works offline**: `fig/` is in it, the
  PDF has both overlays, and astropy writes nothing to an empty home.
  matplotlib and fontconfig do write their font caches to `~/.cache`,
  so the site's Docker image should build them at build time or set
  `MPLCONFIGDIR` to a writable folder. CI's tag-only `build` job
  repeats this check.

## Website first version (Step 6.1)

2026-09-30. Commits 0a7c182 (workspace), 67c4f8e (service), 244676d
(route), f5f250e (headers, rate limit), a89b43b (page). The flow is in
[web/docs/UX.md](../web/docs/UX.md).

- **Workspace.** `web/pyproject.toml` is `accuratum-web`, a uv workspace
  member with `accuratum = { workspace = true }`; one `uv.lock`. Sync
  with `uv sync --all-packages --extra dev --group dev`: a plain
  `uv sync --extra dev` removes the website's packages (`uv run` is
  inexact and leaves them). ruff needs `known-first-party` for
  `accuratum_web`, or isort sorts it as third-party. CI has a
  `test-web` job.
- **One route, `POST /api/sundial`.** Multipart form in, JSON out (two
  base64 PNGs at 150 dpi, one base64 two-page PDF via `PdfPages`; about
  690 kB). No label editing, so no live render route. The grid is fixed
  server-side (`GridConfig()` defaults).
- **Trust boundary in `sundial.py`:** colors `#rrggbb` only; titles and
  subtitles ≤ 80 characters with `$` escaped (matplotlib parses `$…$`
  as mathtext; `\$` shows a dollar); uploads PNG/JPEG ≤ 2 MB and ≤ 2000
  px a side (checked before decoding pixels), re-encoded as PNG into a
  per-request temp folder. The spec's own validation covers the rest.
- **Limits in `app.py`:** request ≤ 4.1 MB (413), POST without
  Content-Length is a 411, ≤ 2 files and 20 fields; 6 sundials per client
  per 10 min (in memory, per instance; client = first X-Forwarded-For
  entry, forgeable, revisit in Step 7); one computation per instance,
  held by a thread semaphore **inside** the worker thread until the
  computation really ends, so a 504 can't lift the cap; 50 s timeout.
- **Parallel half-years:** a 2-process `ProcessPoolExecutor` with the
  *spawn* context (forking a threaded server can copy held locks):
  13–15 s instead of 23 s. `create_app(workers=0)` runs them in the
  thread, which the tests use with a fast grid.
- **CSP:** `default-src 'self'`, plus `img-src data:
  https://tile.openstreetmap.org` and `connect-src
  https://nominatim.openstreetmap.org`; no inline script or style (a test
  checks the markup). Leaflet 1.9.4 is vendored (hashes match its
  published SRI). Leaflet sets styles through the CSSOM, which the CSP
  allows. Upload thumbnails use FileReader data: URIs, since `blob:`
  images aren't allowed; the PDF download uses a `blob:` link, which
  isn't a CSP-governed load. `Referrer-Policy:
  strict-origin-when-cross-origin`, since OSM's tile policy needs a
  Referer.
- **Nominatim from the browser**, only on a search submit or a map click
  (reverse geocoding for the default title), spaced ≥ 1.1 s. Nothing
  geocodes on the server.
- **i18n:** markup carries only `data-i18n*` keys; `locales/pt-BR.json`
  (default), `en.json`, `es.json` and `fr.json`; the choice is kept in
  `localStorage` when allowed. Tests check that the tables match, cover
  every key used, and that each language is in the selector and in
  `i18n.js`'s `LANGUAGES`. Only the page is translated; the drawing and
  PDF are not. Nominatim gets the same code as `accept-language`.
- **Checked in a browser** with Playwright (`uv run --with playwright`,
  Chromium headless, not a project dependency): the whole flow, no
  console errors, CSP violations or failed requests, no horizontal
  scroll at 360 px. `pt-BR.json` and `site.css` were written by a Sonnet
  subagent and reviewed here.
- **Found:** a long title (e.g. "Universidade de Brasília - Campus UnB
  Ceilândia") runs under the logo. The renderer centers the title in the
  header without fitting it between the overlays; the CLI has the same
  issue.
- **No "Home" link in the top bar** (issue #3, owner's choice): the
  clickable "Accuratum" brand already goes to `#/`, so the nav holds only
  About and Contact. `test_the_brand_is_the_only_home_link_in_the_top_bar`
  keeps it that way; `nav.home` is gone from every locale.

## Generate button and timing (issue #6, 2026-11-25)

- **The Details button says "Generate"** (`details.generate`: Gerar /
  Generate / Generar / Générer), since it is the last step. The Location
  page keeps `common.next`.
- **No fixed time in the wait message.** The old "about 15 seconds" was
  the 13–15 s measured on the dev machine; the deployed site takes about
  a minute (owner, 2026-11-25), and an old Threadripper 10–20 s.
  `details.computing` now says "can take up to a minute" with a live
  `{seconds}` count; a test bans digits in it.
- **"Sundial generated in X seconds."** ends the result page
  (`result.elapsed`, `#elapsed`). The owner asked for it to check future
  speed-ups (cache, numerics) on the real site. It is timed in the
  browser, request to response, so it includes the network and any Cloud
  Run cold start: what the visitor waits for, not the computation alone.
- **Workers start with the server.** `ProcessPoolExecutor` starts its
  processes on the first job, and each spawned worker imports astropy,
  astroplan and matplotlib before computing. The lifespan submits one
  `_warm_up` job per worker (`app.state.warm_up`), so this happens at
  startup. It doesn't help a Cloud Run cold start (uvicorn runs the
  lifespan before it listens, so that request still waits) or a slow CPU.
  Why the site takes about a minute isn't measured yet: profile
  `make_sundial` on Cloud Run before optimizing.
- Commits: 9b0fe36 (button), 6a1155f (counter), 2bd46b4 (elapsed), 5bb9205
  (warm-up).

## Hosting (Step 7)

Live at https://accuratum.web.app since `site-v0.1.0` (2026-10-06); the
current deploy is `site-v0.1.5` (57943c0, the issue #4 label fixes). Bingo's Docker, Cloud Run,
Firebase Hosting and WIF setup carried over.

- **Client IP behind the CDN** (1b2b1e3): Firebase Hosting's Fastly CDN
  calls Cloud Run, so the rate limit reads `Fastly-Client-Ip` first.
- **Image** (6ebda9b): two stages on `python:3.11-slim-bookworm`, both
  packages installed as wheels, non-root, matplotlib's font cache built at
  image build time. `scripts/smoke.sh URL` posts one sundial and checks the
  PNGs, the PDF and the headers. No Docker in the dev container: the image
  is built and smoke-tested only in GitHub Actions.
- **`deploy.yml`** (f987a34): tests → build → smoke test under 2 CPUs/2 GB
  (prints peak memory) → push → deploy by digest → smoke test on the public
  URL. The Google steps run only on `site-v*` tags with the repo variables
  set; a manual run on `main` is a dry run of the image. Cloud Run: 2 vCPU,
  2 GiB, 0–3 instances, 60 s timeout, a runtime service account without
  roles, region `southamerica-east1` (in `deploy.yml`, `firebase.json` and
  `setup-gcp.sh`).
- **Google side** (854140b): `scripts/setup-gcp.sh` (idempotent; rerun it
  to re-apply the WIF condition, see § Agents on GitHub issues) and
  `firebase.json` (empty `hosting/public`, everything rewritten to Cloud
  Run).
- **Memory:** the dry run peaked at 1159 MiB, so `--memory=2Gi` stays
  (92e10b8). CPU, not memory, uses up the free tier first.
- **Speed:** the owner sees about a minute per sundial on the site, against
  10–20 s on their machine (2026-11-25); the result page now shows the
  time (§ Generate button and timing). A newer Python didn't close the
  gap; interpolating erfa's terms might (§ Speed: where the time goes).
- **First-deploy traps:** create the project from the Firebase console's
  *Add project* (it shows the terms; skipping them gives Bingo's misleading
  403 on `addfirebase`). `firebase hosting:sites:create` is the only command
  that says whether a site name is free. Analytics off, Blaze on the
  existing billing account, a budget alert of a few dollars.
- **Deploy traps:** see § Traps (`RepoDigests`, and how to check a deploy
  when the page looks unchanged).

## Version footer (2026-11-26)

- **`/api/health` returns `{"status", "site", "library"}`**, the installed
  versions of `accuratum-web` and `accuratum` (`importlib.metadata`). The
  page's footer fetches it and shows both (`footer.version`, worded by the
  owner, redrawn on a language change); `scripts/smoke.sh` prints it, so the deploy
  log names what went out.
- **Why the health route and not a new one:** it was already public and
  already polled by the smoke test; one route answers both "is it up" and
  "which build is it". Only our own two packages are exposed, not astropy &c.
- **Bump `web/pyproject.toml` (and run `uv lock`) before each `site-v*`
  tag**, or the footer still shows the old number and the deploy looks
  like it didn't happen, which is the confusion this footer removes.
- Not checked in a browser here: Chromium needs system libraries the dev
  container lacks, and installing them with sudo was refused. Checked:
  structural tests, the route through uvicorn, and smoke.sh's output.
- **First deploy it confirms: `site-v0.1.3`** (1a4811b, 2026-11-26), green
  in Actions; `https://accuratum.web.app/api/health` answered site 0.1.3,
  library 0.2.3.

## About page (2026-11-27)

- **Long texts are one HTML fragment per language**,
  `static/locales/<name>/<lang>.html`, put by `i18n.js` into any element with
  `data-i18n-html="<name>"` (re-fetched on a language change; a missing
  language falls back to pt-BR). Short UI strings stay in the JSON tables.
- **Why not the other options** (owner chose, 2026-11-27): JSON keys per
  paragraph cut the prose into escaped one-line pieces and need HTML in
  strings for the links; Markdown rendered in the browser ships ~50 KB of JS
  for five paragraphs; Markdown rendered on the server adds a dependency
  and a route; every language inside `index.html` grows the main page. If
  long texts multiply (FAQ, method), rendering Markdown on the server
  (Python `markdown`) is the next step: it changes how fragments are
  made, not how the page loads them.
- **`web/docs/about.md` is the owner's original**, written by hand in
  Portuguese (only spelling, grammar and punctuation were corrected). A test
  checks the pt-BR fragment matches it word for word, so edit both. en, es
  and fr were translated by Claude straight from Portuguese, each linking
  the Tower of the Winds in its own Wikipedia.
- **Fragments go in with `innerHTML`**, so tests allow only `p`, `a`,
  `em`, `strong`, `href="https://…"` links, and no `src`/`style`/`on*`.
  They also check every translation has the original's paragraphs and tags.
- **Fact fixed in the text:** the Earth's orientation comes from the IERS
  tables bundled in `astropy-iers-data` (Bulletin A from the USNO, B from
  the Paris Observatory), not "NASA data"; the Sun's position is Astropy's
  own model (ERFA). The IERS gives the Earth's orientation only.
- Not checked in a browser (no Chromium here, see § Version footer):
  checked the structural tests and that uvicorn serves each fragment under
  the CSP.
- **Deployed as `site-v0.1.4`** (4c13ddc): live about 5 min after the tag
  push; `/api/health` answered site 0.1.4, library 0.2.3, and the four
  fragments return 200 on accuratum.web.app.

## Speed: where the time goes (2026-11-26)

Measured on the dev container, one core (`taskset`), Brasília, the website's
default grid, both half-years run one after the other.

- **A newer Python doesn't help, so the site stays on 3.11.** The frozen
  `uv.lock` installs on 3.14 from wheels alone (every compiled dependency
  has cp314 wheels; none has cp315 yet), but 3.11.16 and 3.14.10 time the
  same: compute 19.5 vs 19.9 s, render 2.7 vs 2.6 s. 3.14 imports slower
  (2.6 vs 0.8 s). This dropped the backlog's "newest Python" item before
  any Dockerfile change.
- **Why:** cProfile of one half-year (11.0 s): `erfa.epv00` 4.4 s (Earth
  position and velocity) and `erfa.pnm06a` 3.7 s (precession–nutation),
  plus `dtdb` 0.8 s, all C code under `SkyCoord.transform_to` → `apco`.
  They run for every sample, in `get_sun_altaz` (4.6 s) and in astroplan's
  sunrise/sunset search (6.4 s).
- **`ErfaAstromInterpolator`** (`astropy.coordinates.erfa_astrom`, a
  `ScienceState` used as `with erfa_astrom.set(...)`) computes those terms
  on a coarse grid and interpolates. Time and largest polyline
  difference from the exact run, in plumb lengths (span 5.7):

  | step | Brasília | 60°N 10°E | 0° 170°E | 75°N 10°E | max diff |
  |---|---|---|---|---|---|
  | exact | 19.8 s | 18.0 s | 19.5 s | 17.7 s | — |
  | 300 s | 25.8 s | 24.2 s | 25.6 s | | 1.3×10⁻⁶ |
  | 3600 s | 8.2 s | 7.4 s | 8.4 s | | 4.1×10⁻⁶ |
  | 6 h | 7.0 s | | | 5.7 s | 2.2×10⁻³ |
  | 1 day | 5.2 s | | | 4.4 s | 2.2×10⁻³ |

  Finer than the dial's own sampling is slower, not faster. The polylines
  kept the same shapes (same NaT cut) in every case.
- **Rendering** (PNG at 150 dpi + PDF, both pages) is about 2.7 s: not
  the bottleneck.
- The site's "about a minute" is these 20 s spread over 2 vCPUs, on
  slower cores, plus any cold start; not profiled on Cloud Run yet.

## Hour labels on the drawing (issue #4, 2026-11-27)

- **The bug.** Hour labels went below the *first* sample and above the
  *last*. That assumes every hour line runs bottom→top, true for the
  Dec→Jun frame only. In Jun→Dec (`--period 1`) the samples start at the
  June solstice, which is the upper curve at every latitude, so both labels
  pointed inward and sat on the solstice daylines (Caracas, Toronto,
  Santiago in the issue). `test_hourline_label_above_first_below_last`
  pinned the bug: its line ran downward.
- **The fix.** The side comes from geometry: the lower endpoint's label
  hangs below it (`va="top"`), the upper one's sits above it. Collisions
  are grouped by side (`va` for hours, `ha` for days) instead of by
  `selector["end"]`, since the bottom label is the `"start"` one in one
  frame and the `"end"` one in the other. Selectors keep `end`: it is the
  label's identity, not its side.
- **Unchanged:** Dec→Jun drawings, including both example projects
  (period 0). Hour lines that start or end mid-drawing (sun under the 10°
  cut, e.g. Toronto 07h/18h) still put their label inside the dial; that
  needs more than a side rule.

**Follow-up: text boxes** (owner's review on the same branch). Most hour
labels still touched a line with one corner ("0" or "h"), and a few hit a
date label (Edinburgh 11h under 12/21). The checks compared anchor points
only, and the text box started exactly at the endpoint while the solstice
curve under it is slanted.

- **Placement now knows the text size.** `font_size_in_data_units`
  rebuilds matplotlib's scale from the default `RenderHints` (axes size,
  equal aspect, 5 % autoscale margins) without importing matplotlib;
  `text_box` uses DejaVu Sans widths (0.64 em per digit or "h", 0.34 for
  "/"). A renderer test checks both against the drawn text, wide and tall.
- **Height is hinted to whole pixels:** 0.86 em at 72 dpi, 1.03 at 100 and
  150 dpi (the site), 0.98 at 200 (the CLI). `TEXT_HEIGHT_EM` takes the
  tallest.
- **Each label moves outward until its box (+0.1 em) clears every line,**
  starting 0.2 em from the endpoint, up to 2 em. If that fails it tries
  the direction its own line would continue past the endpoint. At high
  latitude, lines meet the steep solstice curve almost flat, with
  neighbours just above and below and empty dial straight ahead
  (Reykjavik 06h/07h/20h/21h would be lost without it).
- **A label still blocked, or whose box overlaps a placed one, is
  hidden.** The anchor rules (per-axis tolerance, plumb disk) stay
  unchanged and run first.
- **Measured** with a script that renders each dial and intersects every
  drawn text box with the lines and the other boxes, in pixels: 26 dials
  (0° to 64°, both hemispheres, both frames) went from 4–12 labels
  touching a line per dial to none, with no overlapping pairs. Four
  hours lost their only label, all of which sat on crossing lines
  (Santiago 07h, Sydney 06h, Edinburgh 19h) or on a date (Edinburgh 11h).
- **Known limit:** the boxes assume the default figure size and label font.
  `--label-fontsize` and custom hints don't re-place labels.
- Both example projects were regenerated (they dated from 0.1.0: green
  lines, pre-Step-5 geometry) in a separate commit.
- **Released** as accuratum 0.2.4 and `site-v0.1.5` (57943c0), the branch
  fast-forwarded into `main`. CI passed and uploaded 0.2.4 to PyPI; the
  deploy went live with `/api/health` reporting site 0.1.5, library 0.2.4.

## Label placement lessons (from the unmerged `labels` branch)

Ported to `defaults/placement.py`. Originally recorded in
`docs/LESSONS_LABELS.md` (`git show ad69d87:docs/LESSONS_LABELS.md`).

- **Labels sit at line endpoints only.** Day lines get `MM/DD` left of the
  first sample and right of the last; hour lines get `HHh` below their lower
  endpoint and above their upper one (issue #4; see § Hour labels on the
  drawing).
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
- **Known limits:** extreme latitudes are untested. Collision math is in
  data coordinates, with text boxes estimated for the default render hints
  (see § Hour labels on the drawing). It is best-effort by design, which
  is why labels can be edited.

## Dev environment and multi-machine sync

- **Devcontainer:** `mcr.microsoft.com/devcontainers/python:3.11`, with the
  `.devcontainer/setup.sh` post-create script. uv for everything; build
  backend `uv_build`.
- **CI** (`.github/workflows/ci.yml`) runs `ruff check`, `ruff format --check`
  and `pytest` on pull requests and `v*` tags only. **A `v*` tag builds the
  wheel, publishes a GitHub Release and uploads the wheel to PyPI**
  (Step 5.5). A plain push to `main` triggers nothing.
- **Claude Code's state is per machine.** `CLAUDE_CONFIG_DIR` points to
  `/home/vscode/.claude-code`, which is the Docker volume `claude-code-state`
  (credentials, sessions, memory, plans), so it survives a container rebuild
  but never leaves the machine. `setup.sh` `chown`s the volume and seeds
  `settings.json` with `cleanupPeriodDays: 100000`, because the default
  30-day cleanup wiped the sessions during a 4-month break.
- **The Dropbox sync of sessions was dropped** (Step 6e, 2026-10-01). From
  1be0946 to then, the folders `projects, file-history, skills, agents,
  commands, plans, todos` were bind-mounted from `~/Dropbox/claude-code/`
  over that volume, so sessions moved between the 3 machines. It was dropped
  before going public: the `initializeCommand` created `~/Dropbox/` folders
  on the host of anyone opening the devcontainer, and the setup carried the
  same risk as the `.claude-data/` leak (transcripts next to the repo). The
  user wasn't using it on the main machine any more. `docs/` is the only
  shared context, and moving to another machine means a fresh session.
- **Trap: root-owned leftovers in the volume silently disable transcripts.**
  Docker created the Dropbox mount points (`projects`, `skills`, `agents`,
  `commands`) inside `claude-code-state` as root, and they stayed root-owned
  after the bind mounts were dropped. `setup.sh` only `chown`ed the top
  folder, once. Claude Code then failed every transcript write with
  `EACCES` (shown only in the extension's debug log), so sessions lived in
  memory alone. On 2026-11-23 a suspend/resume closed the VS Code panel and
  the session that made 97fe279 was lost for good, with nothing to
  `--resume`. Now `setup.sh` and `postStartCommand` both run `chown -R` on
  every container start. Check:
  `ls ~/.claude-code/projects/-workspaces-accuratum/*.jsonl`.
- **Only Claude editor tabs survive a restart.** After a suspend, a VS Code
  reopen or a container restart, the extension (v2.1.330) restores a
  session only from an editor tab (`claudeVSCodePanel`, which has a webview
  serializer). The primary and secondary sidebar views have none, so they
  always open a blank conversation (`resume: undefined` in the extension
  log), even though the transcript is safe on disk. Use "Claude Code: Open
  in New Tab" to keep sessions across restarts; otherwise reopen one from
  the Sessions list (Claude icon in the activity bar; its "active" filter
  hides finished sessions) or "Resume conversations". The extension's own
  binary, `~/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude --resume`,
  stands in for the CLI, which isn't installed in the container.
- **uv versions (2026-11-26).** `uv_build>=0.11.6,<0.14` in both
  `pyproject.toml` files, and `UV_VERSION=0.13.8` in the Dockerfile. With
  the old `<0.13` bound, uv 0.13 couldn't use the `uv_build` bundled in it:
  it warned and fetched an older one from PyPI. Now `uv build -v` says
  "Using bundled `uv_build` backend". `setup.sh` and CI's setup-uv install
  the newest uv, so widen the bound when uv's minor version moves (0.14).
  Checked for 0.13: none of 0.13.0's breaking changes touch us (Python 3.15
  becomes the default only for downloads, and the image runs with
  `UV_PYTHON_DOWNLOADS=never`), `uv lock` left `uv.lock` unchanged, and the
  0.2.3 wheel built with it has the same files as the one on PyPI (0.13
  switched its tar backend). Pick a uv release at least two weeks old.
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
- **A stale `accuratum.egg-info/` at the repo root hides the real
  version.** It's left over from the old setuptools build, and it's
  git-ignored. The repo root is on `sys.path`, so
  `importlib.metadata.version("accuratum")` reads it before the uv-build
  metadata. Found at 0.2.0: it still said 0.1.0, and so did the
  provenance in every new `project.json`. Delete it on each machine
  (`rm -rf accuratum.egg-info`). Bumping the version also needs
  `uv lock` (0b569cd).
- **`{{index .RepoDigests 0}}` broke the deploy (site-v0.1.1, 2026-11-25).**
  `ubuntu-latest` moved to Ubuntu 26.04 with Docker 29 from late
  October 2026, and Docker 29's containerd image store gives *every* name a
  digest entry, so the local `accuratum-web@sha256:…` came first. gcloud
  then looked for it on Docker Hub (`mirror.gcr.io/library/accuratum-web`):
  "Image … not found". deploy.yml now keeps only the entry starting with the
  Artifact Registry image name and fails if none matches. A tag runs the
  workflow file *at that tag*, so a fix needs a new `site-v*` tag.
  `site-v0.1.2` (4c67e6d) passed every step, the public smoke test
  included (confirmed 2026-11-26).
- **"I see no change on the site" doesn't mean the deploy failed.** Until
  the page shows its version, check the deploy from the outside:
  `curl -s https://api.github.com/repos/aureliobarbosa/accuratum/actions/workflows/deploy.yml/runs`
  (no login needed on a public repo, and no `gh` in the dev container),
  then `/actions/runs/<id>/jobs` for the steps. `curl -sI
  https://accuratum.web.app` shows a `last-modified` equal to the image's
  build time, since the static files' mtime is when the wheel was installed.

## Workflow lessons

- **Reassess the remaining steps after each one.** Finishing a step often
  makes a later one cheaper or unnecessary. Example: the planned custom SVG
  renderer looked replaceable by matplotlib's SVG output after Step 2.
  Propose the simplification before carrying on with the plan as written.
- **Run a subagent's tests in the main thread before trusting them.** Treat
  untracked files as possibly agent-written until you have checked them.
  Unverified agent output was almost deleted as "speculation" during the
  rewrite.

## Security cleanup before going public (Step 6)

- **What leaked:** commit ******* (2026-07-03, "add claude-data") committed
  all of `.claude-data/` (the Claude Code config dir): `.credentials.json`
  (OAuth tokens), `.claude.json` + `backups/`, `projects/` (session
  transcripts), `file-history/`, `shell-snapshots/`, `ide/`, `settings.json`,
  `mcp-needs-auth-cache.json`, `.last-cleanup`. 8b32634, ******* and 3be533e
  untracked it, but it stays in history of `main`, `origin/main` and the
  local branch `restore-claude-sessions`. Tag `v0.1` does not contain it. The
  repo was private, so only people with access could see it. Claude data then
  synced through Dropbox bind mounts, dropped in Step 6e; it now stays in
  the per-machine `claude-code-state` volume.
- **Scan (gitleaks 8.30.1, 195 commits, all refs):** one rule hit,
  `generic-api-key` in `.claude-data/ide/34437.lock` (*******). Trap:
  gitleaks did NOT flag the OAuth tokens in `.claude-data/.credentials.json`
  (*******, 8b32634); a pickaxe (`git log --all -S'sk-ant'`) found them.
  Treat the tokens as leaked regardless. The current tree (tracked and
  untracked) is clean. Non-secret personal data outside `.claude-data`:
  `/home/vscode` paths (harmless devcontainer user) and two emails (the
  author's, and the creator's credit in the docs).
- **Hardening (5636ae0):** `.gitignore` covers `.claude-data/`,
  `.claude/settings.local.json` (now untracked), `.credentials.json`, `.env*`.
  CI has a `secrets` job: gitleaks (pinned version and checksum, not the
  action, which needs a license for organizations) over the full history
  (`fetch-depth: 0`). It fails on the old history until it is rewritten.
- **Rewrite procedure** (never in the working repo): `git clone --no-local`
  into a separate folder, then `git filter-repo --invert-paths --path
  .claude-data/ --refs *******^..main`. Trap: a full-history filter-repo
  strips the GPG signatures GitHub puts on web-made commits, so it rewrote
  212 of 216 commits, `v0.1` and every PR ref. The range limit rewrote only
  the 42 commits from the leak on; older hashes, `v0.1` and the other
  branches kept theirs. Verify (`git log --all -- .claude-data` empty, main's
  tree unchanged, gitleaks clean), then map the doc hashes through
  `.git/filter-repo/commit-map`.
- **Image rights (2026-10-01).** `accuratum/fig/` ships in the wheel.
  - `rosa.png`, the default compass, is pixel-identical to Commons'
    3840 px rendering of
    [File:Rosa_dos_Ventos.svg](https://commons.wikimedia.org/wiki/File:Rosa_dos_Ventos.svg).
    That file is CC0 and needs no attribution; it is User:Rehua's
    derivative of an OpenClipart drawing. Found through the Commons API: a
    lookup by SHA-1 fails for renderings of SVGs, but the aspect ratio
    (540 × 545 ≈ 3840 × 3876) pointed to the file.
  - Look-alikes are CC BY-SA 3.0 and would need attribution: Compass Rose
    English North.svg and its translations, from Serg!o's BrújulaN.svg.
  - The UnB logo (`unb_basic.jpg`) is the university's, and UnB is named in
    LICENSE.md. The unused `unb.jpg` was removed (c68ed1f).
    `logo.png` is the project's own. `escola_nas_estrelas.jpeg` was unused
    and had no confirmed right, so it was removed (6967fcb). The 0.2.1
    wheel that still held it was deleted from PyPI.
- **A fresh repository, not a second rewrite (2026-10-04).** After the
  force-push, GitHub still served the pre-rewrite commits by hash, the leak
  included, and Support could take months to purge them. Hiding the hashes
  with another rewrite would not have made them unreachable in a public
  repo: the Activity page lists force-pushes with the old tip, Actions runs
  name their commits, short hashes resolve (4-hex prefixes can be
  brute-forced), and a new force-push leaves new dangling commits. A
  rewrite would also have changed 54 hashes and both 0.2.x tags. Instead
  the old repo was renamed, an empty `aureliobarbosa/accuratum` created,
  and the clean `main` pushed as-is, so no hash changed. The old repo was
  then deleted, which removes the leaked objects from GitHub. The two
  leaked hashes were masked as `*******` in the docs (0cc4ca4); older
  commits still name them, and they point to nothing.
- **Credentials (2026-10-04).** The leaked `.credentials.json`, run with
  `CLAUDE_CONFIG_DIR=<empty tmp> claude -p hi`, gave "OAuth session expired
  and could not be refreshed". The owner rotated all passwords and signed
  every device out of claude.ai. The scan of the leaked transcripts was
  skipped: the repo was private and is deleted.
- **What stayed behind:** tags `v0.1`, `v0.2.0`, `v0.2.1` and their GitHub
  Releases, PRs #2–#7, and PyPI 0.2.1 (deleted after 0.2.2 was up, so the
  project was never empty; delete a release, never the project, or the
  name is freed). New first release: v0.2.2 (70fe0f4).
- **Who can open PRs (2026-10-04).** Settings → General → Pull requests
  is set to *Collaborators only* (a GitHub option since 2026-02): outsiders
  can still fork, read and comment, but not open a PR. As a second layer,
  Settings → Actions → General requires approval before workflows run on
  PRs from all external contributors. `ci.yml` already used `pull_request`
  (not `pull_request_target`) with a `contents: read` token, so a fork PR
  never saw secrets; the risk removed is wasted runner minutes and cache
  poisoning. Before approving an outside run, read its diff to
  `.github/workflows/`, `pyproject.toml` and the tests: approving runs
  their code. Collaborators on a personal repo can push to `main`, hence
  the planned ruleset.
- **Dropped: sharing Claude's setup in the repo** (skills, plans, memory
  under `.claude/`). Keeping Claude's data in the repo is what led to the
  leak.

## Agents on GitHub issues (2026-11-23)

Goal: agents pick up issues without a machine left on, ask before coding,
and hand over a PR for review.

- **Chosen: `anthropics/claude-code-action`** (`.github/workflows/claude.yml`).
  It runs on GitHub's runners, is started from the issue itself, and CI
  already runs on PRs. Rejected: an always-on home machine running headless
  `claude` (credentials and uptime to look after, and no `gh` in the dev
  container), and a self-hosted Actions runner (on a public repo, PR code
  could run on the machine). Claude Code on the web with a scheduled routine
  stays an option if polling for issues is ever wanted.
- **Branching:** trunk-based development stays for the owner. Agents work on
  short-lived `claude/…` branches (the action's default prefix), one per
  issue, merged by the owner. CLAUDE.md § Unattended agents has the rules:
  plan comment → `@claude go` → PR. That's the Checkpoints rule, moved onto
  GitHub.
- **Who can start it:** only `github.repository_owner`, by the `agent` label
  or an `@claude` comment. Outsiders can still comment on a public repo, so
  the action's write-access check alone wasn't relied on.
- **WIF trap found while wiring it:** the provider condition was
  `assertion.repository == repo`, so *any* workflow in the repo holding
  `id-token: write` could get deploy credentials. `claude.yml` needs that
  permission (the action trades the OIDC token for the Claude App's token;
  GITHUB_TOKEN pushes don't trigger CI). The condition now also requires
  `workflow_ref` to start with `<repo>/.github/workflows/deploy.yml@refs/tags/site-v`.
  `setup-gcp.sh` re-applies it with `update-oidc` on every run, so rerunning
  the script fixes a provider created earlier.
- **Layers, from the outside in:** owner-only `if:` → the App's permissions
  (no `workflows`) → rulesets on `main` and on the `v*`/`site-v*` tags →
  WIF pinned to deploy.yml on tags. `--allowedTools` only saves prompts; it
  isn't a sandbox.
- **Rendered PNGs** go to `agent-out/` (gitignored), which the workflow
  uploads as an artifact, so visual approval works without committing images.
- **Setup traps hit on the way (2026-11-23/25):** the release tags need a
  *tag* ruleset (a branch ruleset turns `v*` into `refs/heads/v*` and
  leaves the tags open). `CLAUDE_CODE_OAUTH_TOKEN` copied from a terminal
  that wrapped it gets a space in the middle; the action then fails 2 s in
  with `Claude execution failed: result is_error:true` and no clearer
  message in the public view. Clean the token in an editor before pasting.
  `claude setup-token` bills whichever account is logged in on claude.ai in
  the browser. No `gh` in the dev container, so the App and the secret were
  set by hand instead of `/install-github-app`; the CLI is at
  `~/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude`.
  First successful run: issue #6, plan in 39 s.
- **Trial closed (2026-11-26).** After `@claude go` the App opened PR #7
  (issue #6) and then PR #8 (issue #3) by itself, so *Collaborators only*
  doesn't block it and the "Create PR" link isn't needed. CI ran on both
  (an App's pushes trigger workflows, unlike GITHUB_TOKEN's) and passed.

## GitHub Actions versions (2026-11-25)

All actions bumped to their latest release. GitHub removed Node 20 from
runners on 2026-09-23 (Node 24 the default since 2026-06-16), so the
`node20` actions were already being forced onto Node 24; the bump makes that
official and drops the warning. Node 24 itself changes nothing here: the
project runs no Node code, the runners are GitHub-hosted (always newer than
the 2.327.1 minimum), and Node 24's lost platforms (macOS ≤ 13.4, ARM32) are
not used. What was checked in each major we crossed:

- **`actions/checkout` v4/v5 → v7.** v5: Node 24. v6: credentials persist to
  a separate file under `$RUNNER_TEMP` (claude-code-action's own examples use
  v6+, so the agent's git setup is fine). v7: ESM, and refuses fork-PR
  checkouts on `pull_request_target`/`workflow_run`, events we don't use.
  The `build` job was still on v4, out of line with the rest.
- **`actions/upload-artifact` v4 → v7.** v5/v6: Node 24. v7: ESM, opt-in
  `archive: false`. Our inputs (`name`, `path`, `if-no-files-found`,
  `retention-days`) are unchanged.
- **`actions/download-artifact` v4 → v8.** v5: single downloads *by ID* no
  longer nest; we download by `name`, unchanged. v6/v7: Node 24. v8: ESM,
  non-zip files are not unzipped, and a digest mismatch now fails the job
  (was a warning). Upload v7 and download v8 are the matching pair.
- **`astral-sh/setup-uv` v8.1.0 → v10.4.0** (still SHA-pinned; it publishes
  no floating major tags). v9: `prune-cache` defaults to `false`, so caches
  grow; the public repo's free 10 GB cache with LRU eviction absorbs it.
  v10: `enable-cache: auto` turns the cache off on `pull_request_target`,
  `workflow_run` and `release`, none of which we use.
- **`pypa/gh-action-pypi-publish` v1.14.2 → v1.14.3** (SHA-pinned; the SHA is
  the commit, `v1.14.3^{}`, not the annotated tag object). A security
  release (GHSA-5xjx-3w67-w9x9) with hash-checked dependencies inside.
- Already on the latest major via floating tags: docker/setup-buildx-action
  v4, docker/build-push-action v7, docker/login-action v4,
  google-github-actions/auth v3 and deploy-cloudrun v3,
  softprops/action-gh-release v3, anthropics/claude-code-action v1. All run
  `node24` or are composite.
- **Confirmed (2026-11-26):** the `v0.2.3` tag ran the build, Release and
  PyPI jobs, and PRs #7 and #8 ran checkout/setup-uv on `pull_request`,
  all green.
- **How to recheck:** `curl -s https://api.github.com/repos/<owner>/<action>/releases`
  for the tags, and the `runs.using:` line of `action.yml` at a tag for the
  runtime. No `gh` in the dev container.
