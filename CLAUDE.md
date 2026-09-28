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
uv sync --extra dev                                    # environment (Python 3.11 baseline)
uv run pytest -q                                       # all tests
uv run ruff check . && uv run ruff format --check .    # what CI enforces
uv run accuratum --lat-long=-15.78,-47.92 -o out.png   # render (negative coords need '=')
uv run accuratum --lat-long=-15.78,-47.92 --canvas-size-mm=6000,2000 -o panel.svg
uv run accuratum --help
```

Prototype notebooks live in `notebooks/`. They are for exploration, not
production code.

## Working conventions

- **Trunk Based Development:** work directly on `main`, with no feature
  branches.
- **Test Driven Development:** write the failing test first, see it fail, then
  write the code. The exception is rendered output
  (`renderers/matplotlib_backend.py`), which is checked visually. Structural facts about the output, such as SVG
  ids, units and file type, still get tests.
- **One commit per subtask, with its tests.** Use imperative messages with a
  prefix (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`) and
  explain the *why* in the body. Commit without asking.
- **Before each commit:** run `uv run pytest -q`, then
  `uv run ruff check --fix`, then `uv run ruff format`.
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
  through CI;
- deleting remote branches.

## Architecture

A pure-data pipeline: `SundialSpec → build_plot → Plot → renderer`.

| Module | Responsibility |
|---|---|
| `core/spec.py` | `SundialSpec` (Location, TimeFrame, GridConfig, LabelOverride) and its JSON dict round-trip |
| `core/spec_io.py` | `load_spec` / `save_spec` for the CLI's `--spec` / `--save-spec` |
| `core/astronomy.py`, `core/timegrid.py` | Sun alt/az, sunrise/sunset, day- and hour-line time grids (NaT below the horizon cut) |
| `core/builder.py` | `build_plot(spec) -> Plot`: grids → projection → metadata → default labels → overrides |
| `core/plot.py`, `core/metadata.py`, `core/hints.py` | `Plot`/`Polyline`/`Label` data; selector contract; `RenderHints` and overlays (kept out of the spec) |
| `projections/accuratum.py` | `project(alt, az, plumb_length)`, the plug-in point for other sundial types |
| `defaults/labels.py`, `defaults/placement.py` | Which labels exist, and the collision/placement heuristic |
| `renderers/matplotlib_backend.py`, `renderers/svg_backend.py` | `render(plot, hints)`: PNG/PDF via matplotlib, and SVG in real mm with selector-derived ids |
| `cli.py`, `location.py` | All I/O: argv, geocoding (Nominatim), timezone lookup, current time, file output |

- **`core/` imports neither matplotlib nor anything that does I/O.**
- **Renderers draw only what the `Plot` says;** no geometry lives in them.
- `tests/` mirrors the package structure.

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
