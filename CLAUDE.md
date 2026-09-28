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
uv run accuratum --help
```

Prototype notebooks live in `notebooks/`. They are for exploration, not
production code.

## Working conventions

- **Trunk Based Development:** work directly on `main`, with no feature
  branches.
- **Test Driven Development:** write the failing test first, see it fail, then
  write the code. The exception is rendered output (the matplotlib drawing),
  which is checked visually. Structural facts about the output, such as SVG
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

**Pending [PLAN Step 0](docs/PLAN.md#step-0--consolidate-the-trunk-decision-pending).**
Two layouts exist:

- **`main` (v0.1):** `datetime_utils.py` (solstices, frames),
  `astronomy.py` (sunrise/sunset-bounded grids, shadow xy), `graph.py`
  (matplotlib), `location.py` (Nominatim geocoding) and `cli.py`.
- **`rewrite-core`:** a pure-data `SundialSpec → build_plot → Plot` core,
  with pluggable `projections/`, heuristics in `defaults/` and thin
  `renderers/` (matplotlib, SVG in mm). See PROJECT_KNOWLEDGE.md.

`tests/` mirrors the package structure.

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
