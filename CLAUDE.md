# CLAUDE.md — Project Instructions

## General

- Use **Python 3.11** as the baseline Python version for this project.
- You are running in an isolated devcontainer environment — be aware of this context.
- Do not read, print, or expose any secrets.

## Project Structure

| Module | Purpose |
|---|---|
| `accuratum/datetime_utils.py` | Solstice and datetime grid helpers |
| `accuratum/astronomy.py` | Astropy shadow calculations |
| `accuratum/graph.py` | Matplotlib rendering |
| `accuratum/cli.py` | Argparse CLI entry point |
| `accuratum/location.py` | Geocoding via geopy/Nominatim |
| `accuratum/notebooks/` | Prototype notebook — not production code |

## Planning

- Plan ahead before fixing an issue or developing a new feature.
- Break down larger problems into smaller ones during planning.
- Before coding, create an outline of the required files and stub functions with signatures.
- Ask permission before adding new modules, changing the package layout, or modifying `pyproject.toml`.

## Coding Tasks

- Run programs with `uv run`.
- Run tests with `uv run pytest`.
- Build the package with `uv build`.
- For every function, write tests before implementing it — follow TDD strictly.
  - Exception: `accuratum/graph.py` is exempt; no tests are required for it.
- After finishing a subtask, run the full test suite and commit if it passes.
- Before committing, run `uv run ruff check .` and `uv run ruff format .`.

## Git Workflow

- Never push or merge branches without explicit user authorization.
- Commit after each subtask or logical unit of work.

## Testing Notes

- Geocoding uses Nominatim (geopy), which has rate limits. Always mock
  `location_to_latitude_longitude` in tests — never call the real geocoder.
- The `tests/` directory mirrors the package structure; keep it that way.
