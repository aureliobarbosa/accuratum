# Accuratum — sundial generator

A Python library and CLI that draws an *Accuratum* sundial for any place on
Earth. It computes the shadow of a vertical plumb (gnomon) on a horizontal
surface with astropy/astroplan. A full year needs two solstice-to-solstice
frames: Dec→Jun and Jun→Dec (`--period 0|1`). Creator: Paulo Eduardo de Brito.
Maintainer: Marco Aurélio A. Barbosa, the sole developer.

**What's left to do is in [docs/PLAN.md](docs/PLAN.md). Read it before
starting a new step.** Why each finished thing is the way it is, plus traps
and lessons, is in [docs/PROJECT_KNOWLEDGE.md](docs/PROJECT_KNOWLEDGE.md).
Grep it when you touch a finished area; don't read it whole.

## How to run

```bash
uv sync --all-packages --extra dev --group dev         # environment: library + web/ (Python 3.11 baseline)
uv run pytest -q                                       # library tests
(cd web && uv run pytest -q)                           # website tests
uv run ruff check . && uv run ruff format --check .    # what CI enforces
uv run accuratum --lat-long=-15.78,-47.92 --year 2026   # generate a project folder (negative coords need '=')
uv run accuratum --project lat-15.78_lon-47.92_2026_p0 -o panel.svg   # .png/.pdf/.svg, all via matplotlib
uv run accuratum --help
(cd web && uv run uvicorn accuratum_web.app:app --reload)   # website at http://127.0.0.1:8000
```

Prototype notebooks live in `notebooks/`. They are for exploration, not
production code.

## Working conventions

- **Trunk Based Development:** work directly on `main`, with no feature
  branches.
- **Test Driven Development:** write the failing test first, see it fail, then
  write the code. The exception is rendered output
  (`renderers/matplotlib_backend.py`), which is checked visually. Structural facts about the output, such as the
  file type, still get tests.
- **One commit per subtask, with its tests.** Use imperative messages with a
  prefix (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`) and
  explain the *why* in the body. Commit without asking.
- **Before each commit:** run `uv run pytest -q`, then
  `uv run ruff check --fix`, then `uv run ruff format`.
- **One issue per Claude session is preferred.** Close a session once its
  issue is done and recorded in `docs/`, and start the next issue in a fresh
  session. The docs carry the context between sessions, not the
  conversation.
- **Checkpoints:** at the end of each PLAN step, stop and ask the user to
  review before starting the next one. When the step changes the drawing,
  render a PNG and look at it yourself first, then hand it over for the
  user's visual approval.
- **A closed step shrinks in PLAN.md** to one line per decision plus a
  pointer. The findings, traps and commit hashes go to PROJECT_KNOWLEDGE.md
  in the same commit. PLAN.md is only what is *left*.
- **Reassess after every step.** Check whether the remaining steps can shrink,
  merge or disappear given what was just learned. Propose the simplification
  instead of executing the plan as written.
- **Subagents are fine when they help.** Run the tests they wrote in the main
  thread before trusting their work.
- **English** for code, docs and commit messages.
- **Project context lives in `docs/`, not in Claude's auto-memory.** Git
  carries `docs/` to every machine. Record a decision there before switching
  machines.

## Autonomy

You may, without asking:

- add, rename, move or delete modules, files and folders, and restructure the
  package;
- edit `pyproject.toml` and add or remove dependencies. Run `uv lock` and
  commit `uv.lock` in the same commit;
- rewrite tests and docs, including this file, when the workflow changes.

Record the *why* of any structural change in PROJECT_KNOWLEDGE.md.

**Always ask first** before any of these:

- `git push`;
- force-pushing or rewriting published history;
- creating tags, because a `v*` tag builds and publishes a GitHub Release
  and uploads the wheel to PyPI through CI (a PyPI version can't be reused);
- deleting remote branches.

## Architecture

A pure-data pipeline: `SundialSpec → build_plot → Plot → renderer`. A run is
saved as a project folder (`project.json`: spec, render settings, editable
labels; `polylines.npz`: geometry), and `--project` renders it without
recomputing.

| Module | Responsibility |
|---|---|
| `core/spec.py` | `SundialSpec` (Location, TimeFrame, GridConfig, year/period), its JSON dict round-trip, `spec_hash` |
| `core/project.py`, `core/project_io.py` | `Project` (spec + plot + render + provenance); `save_project` / `load_project` for a folder, with the stale-spec checks |
| `core/astronomy.py`, `core/timegrid.py` | Sun alt/az, sunrise/sunset, day- and hour-line time grids (NaT below the horizon cut) |
| `core/builder.py` | `build_plot(spec) -> Plot`: grids → projection → metadata → default labels |
| `core/plot.py`, `core/metadata.py`, `core/hints.py` | `Plot`/`Polyline`/`Label` data (labels may be `hidden`; the plot carries the title and subtitle texts); metadata contract; `RenderHints` and overlays |
| `projections/accuratum.py` | `project(alt, az, plumb_length)`, the plug-in point for other sundial types |
| `defaults/labels.py`, `defaults/placement.py`, `defaults/titles.py` | Which labels exist; the collision/placement heuristic (suppressed → `hidden`); the default title and subtitle texts |
| `renderers/matplotlib_backend.py` | `render(plot, hints)`: one matplotlib figure; the output extension picks PNG, PDF or SVG |
| `cli.py`, `location.py` | All I/O: argv, project folders, geocoding (Nominatim), timezone lookup, current time, file output |
| `web/accuratum_web/sundial.py` | The website's trust boundary: one request → both half-years → two PNGs + a two-page PDF |
| `web/accuratum_web/app.py`, `static/` | FastAPI (`POST /api/sundial`, limits, CSP) and the page (plain JS, `locales/*.json`) |

- **`core/` imports no matplotlib and does no I/O**, except file reads and
  writes in `core/project_io.py`.
- **Renderers draw only what the `Plot` says;** no geometry lives in them.
- `tests/` mirrors the package structure; `web/tests/` covers the website.
- **The website is its own uv workspace project** (`web/pyproject.toml`)
  and imports only the library's public API. Its flow is fixed in
  [web/docs/UX.md](web/docs/UX.md).

## Traps

- **Mock the geocoder in tests** by patching `accuratum.location.Nominatim`
  with `pytest-mock`. Nominatim allows 1 request per second and times out at
  random.
- **astroplan returns `datetime64[ns]`;** the rest of the code expects `[s]`.
  Cast at the boundary.
- **Changing dependencies means running `uv lock`.** A stale `uv.lock` breaks
  every other machine's `uv sync`.
- **CI runs only on pull requests and `v*` tags.** A push to `main` is not
  checked by CI, so run the checks locally.
