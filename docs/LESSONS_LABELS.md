# Label-placement lessons from the `labels` branch

Institutional memory from the (unmerged) `labels` branch. The heuristics below are real discoveries to re-implement cleanly in the rewrite.

## What labels are placed and where

Two label families anchor at the endpoints of each drawn line. Daylines carry an `MM/DD` tag at both ends (left of the first sample, right of the last). Hourlines carry an `HHh` tag at both ends (below the first sample, above the last). Nothing is drawn mid-line — endpoints only.

## Selection rules

- One dayline label per local-month transition (so ~12 labels per solstice interval, not one per day).
- One hourline label per row whose middle-sample local time falls within `time_step/2` of an exact hour.
- Use the **middle** sample of the hourline for TZ conversion, not the endpoint — avoids DST edge bias when the interval straddles a clock change.

## Suppression rules and why each exists

- Shared `placed` set across day and hour passes; daylines drawn first so hour labels yield to day labels on collision. **Why:** day and hour endpoints converge near the period edges; without a shared set the two passes overprint each other.
- Plumb exclusion radius applied to hour labels only — suppress any hour endpoint inside ~`0.5 * plumb_length` (auto-scaled, see below) of the origin. **Why:** kills the noon cluster where shadows are shortest and all hour endpoints pile on top of the plumb base. Daylines don't cluster there, so they are unaffected.
- Per-axis (1-D) collision check: daylines compare `|Δy|` only, hourlines compare `|Δx|` only. **Why:** daylines stack vertically at the left/right edges and hourlines stack horizontally at the top/bottom; a 2-D bounding-box check lets near-axis stacks slip through because the orthogonal coordinate barely moves.
- Auto-scale tolerance (~4% of `max(range_x, range_y)`) and exclusion radius (~12%) to data extent. **Why:** fixed-unit thresholds were calibrated on unit-ish prototypes and barely tripped on real ±6-unit plots; explicit user values still override.

## What still doesn't work

- Extreme latitudes are untested; the near-polar geometry (very long shadows, hour clusters in unusual places) may break the radius/tolerance ratios.
- Collision math is in **data coordinates**, not display coordinates. Label width is approximated as a fraction of data extent — works at common figsizes and aspect ratios, not guaranteed under arbitrary rendering.
- The whole thing is best-effort. It will always lose to a human who knows where they want the label — which is why the rewrite exposes per-label overrides via the `Spec`.

## Where this lives in the rewrite

Port to `accuratum/defaults/placement.py`; runs at plot-build time, so the renderer just draws what the `Plot` already says.
