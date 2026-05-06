# TODO

Working notes for the next agent picking up the `smart_hour_lines` branch (and one item to be addressed elsewhere). Conversation context that motivated each item is included so the work can be resumed without re-deriving it.

## Branch goal recap

Replace `build_dayline_grid` / `build_hourline_grid` (in `accuratum/datetime_utils.py`) with `smart_dayline_grid` / `smart_hourline_grid` (in `accuratum/astronomy.py`). The "smart" versions bound their grids by real sunrise/sunset (via `get_sunrises_and_sunsets`, which depends on `astroplan`), so they live in `astronomy.py`. `smart_hourline_grid` marks moments where the sun is below 10° altitude as `np.datetime64('NaT')`.

## On THIS branch

### 1. `compute_blocks` and downstream rendering — migrate to new contract (HIGH)

`grid_to_shadow_xy` was just changed to always return `tuple[list[np.ndarray], list[np.ndarray]]`:

- No-NaT path: a length-1 list wrapping the original 2-D ndarray.
- NaT path: one 1-D ndarray per row, NaT entries dropped.

`accuratum/astronomy.py::compute_blocks` was deliberately **not** updated yet. It still does:

```python
x, y = grid_to_shadow_xy(grid, frame, plumb_length=plumb_length)
blocks_x.append(x)  # x is now a list, not an ndarray
```

So `compute_blocks` now returns `list[list[np.ndarray]]` for x and y (one level deeper than before).

`accuratum/graph.py::plot_solar_clock` iterates:

```python
for x, y in zip(blocks_x, blocks_y):
    for row in range(len(x)):
        ax.plot(x[row], y[row], "-", ...)
```

With the new shape, `x[row]` may be a 2-D ndarray (no-NaT case) or a 1-D ndarray (NaT case). Matplotlib will still draw, but verify visually that the no-NaT 2-D path renders the same as before, and the NaT path renders correctly (one polyline per row).

Decide where to flatten: probably update `compute_blocks` to return `list[np.ndarray]` (per row) by iterating each grid's row-list and extending `blocks_x` / `blocks_y`, OR keep `compute_blocks` as-is and adjust `plot_solar_clock` to handle both shapes. Pick one and update tests accordingly. The current `test_compute_blocks_returns_two_lists_of_arrays` checks `blocks_x[0][0].shape == dl.shape`, which assumes the temporary list-of-lists shape — revisit when this is finalized.

### 2. Mask logic in `smart_hourline_grid`

`accuratum/astronomy.py:115` has the comment:

```python
mask = (rises <= grid) & (grid <= sets)  # CHECK WHETHER THIS IS REASONABLE.
```

Confirm the mask is correct (boundary inclusivity, broadcasting against `rises`/`sets` reshaped to `(1, n_days)`). Remove the comment once verified.

### 3. Pre-existing dtype failures (likely originated on this branch)

Two tests fail with `datetime64[ns]` vs expected `datetime64[s]`:

- `tests/test_astronomy.py::test_get_sunrises_and_sunsets_dtype`
- `tests/test_astronomy.py::test_smart_dayline_grid_dtype`

`get_sunrises_and_sunsets` returns `astroplan`'s `datetime64[ns]`. The cast at `accuratum/astronomy.py:53` is currently commented out:

```python
# return sunrises.datetime64.astype("datetime64[s]"), sunsets.datetime64.astype("datetime64[s]")
return sunrises.datetime64, sunsets.datetime64
```

Either restore the cast (preferred — the rest of the code and tests assume seconds resolution) or change the test contract. `smart_dayline_grid`'s dtype test fails because it builds its grid from these values.

### 4. CLI still uses the old grid builders

`accuratum/cli.py` imports and uses `build_dayline_grid` / `build_hourline_grid`. Migrate to `smart_dayline_grid` / `smart_hourline_grid` once the rendering pipeline (item 1) is settled.

### 5. Notebook consolidation

`accuratum/notebooks/accuratum.ipynb` currently exercises both the old (`build_*`) and new (`smart_*`) flows side-by-side. Once items 1 and 4 are done, simplify the notebook to use only the `smart_*` path. The user is testing the implementation manually here and will return.

### 6. Delete obsolete builders

Once items 1, 4, and 5 are complete, delete `build_dayline_grid` and `build_hourline_grid` from `accuratum/datetime_utils.py` plus their tests in `tests/test_datetime_utils.py`. Check that nothing else imports them.

### 7. Direct tests for `smart_hourline_grid`

`smart_dayline_grid` has shape/dtype/ordering tests in `tests/test_astronomy.py`. `smart_hourline_grid` has none yet (only indirect coverage via `test_grid_to_shadow_xy_skips_nat_per_line`). Add equivalents: shape, dtype, NaT pattern (per-row NaT count should match expected sub-horizon coverage), monotonicity within a row.

User noted `smart_dayline_grid` was tested manually/visually and prefers to keep it that way for now — that exemption does **not** extend to `smart_hourline_grid`.

## On a DIFFERENT branch (not here)

### Nominatim test rate-limit fix

`tests/test_location.py::test_existing_location[Paris, France]` fails intermittently with `geopy.exc.GeocoderTimedOut: Service timed out`. Root cause: the test calls real Nominatim (user prefers this over mocking) and the inter-call sleep is too short.

`tests/test_location.py:28` has:

```python
sleep(0.1)
```

Nominatim's usage policy is **1 request per second max**. Bump to `sleep(1.0)` and add an equivalent sleep to `test_non_existing_location` (which currently has none and could starve the next geocoding test in the run). Consider a session/autouse fixture that enforces a 1s gap between calls.

Note: `Agents.md` says "Always mock `location_to_latitude_longitude` in tests — never call the real geocoder." User has explicitly accepted calling the real service in this project, so update `Agents.md` (or split test classes — mocked unit tests + a small real-service integration suite) when this fix is made.

## Notes for the next agent

- Current branch is `smart_hour_lines`. Do not push or merge without explicit user authorization (per `Agents.md`).
- TDD applies (per `Agents.md`), except for `accuratum/graph.py`.
- After each subtask, run the matching test; after the full set of items, run `uv run pytest`, then `uv run ruff check --fix` and `uv run ruff format`. Commit each subtask.
- The fix for `grid_to_shadow_xy` (NaT handling, list return contract) is already done and tested — see `accuratum/astronomy.py:22-58` and the new `test_grid_to_shadow_xy_skips_nat_per_line` in `tests/test_astronomy.py`.
