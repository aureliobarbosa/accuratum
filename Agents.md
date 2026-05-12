## Accuratum sundial

Overview: Accuratum is a simple and precise solar clock (sundial): given your position on Earth and the current date, simulate the shadow of a plumb (or gnomon) on a horizontal surface using astropy, between solstices. For covering a whole year you need two solstice intervals, december-june and june-december . This software draws an image for the accuratum sundial using the user's location and date.

Project Structure

| Module | Purpose |
|---|---|
| `accuratum/datetime_utils.py` | Solstice and datetime grid helpers |
| `accuratum/astronomy.py` | Astropy shadow calculations |
| `accuratum/graph.py` | Matplotlib rendering |
| `accuratum/cli.py` | Argparse CLI entry point |
| `accuratum/location.py` | Geocoding via geopy/Nominatim |
| `notebooks/` | Prototype notebooks (top-level, not shipped in wheel) — not production code |

Plan ahead on any task; Break down larger problems into smaller ones; Create an outline of the required files and stub functions with signatures before coding; Ask permission before adding new modules, changing the package layout, or modifying `pyproject.toml`. Package management with uv in the front end and uv_build in the backend. Tests are managed with pytest. Development is done inside a devcontainer. Code formatting uses ruff.

Follow Test Driven Development, except for `accuratum/graph.py`
After finishing a task run the corresponding test (if test is available); once finishing an issue/bug/feature, run the full test suite (`uv run pytest`); after getting tests approved, run `uv run ruff check --fix` then `uv run ruff format`; Commit your work as you go; commit each subtask; Never push or merge branches without explicit user authorization. Geocoding uses Nominatim (geopy), which has rate limits. Always mock
  `location_to_latitude_longitude` in tests — never call the real geocoder.
The `tests/` directory mirrors the package structure.

The CLI entry point is `uv run accuratum`.

Branch strategy: if on `main`, create a new branch before making changes. If a branch already exists, keep working on it. Never push or merge without explicit user authorization.
