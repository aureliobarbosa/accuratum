# Accuratum — what's left to do

> **Status (2026-09-28):** back after a four-month break. `main` has the v0.1
> layout, and the core rewrite waits unmerged on `rewrite-core`. Next is
> **Step 0: pick the trunk**.

This file holds only what is **still to do**. When a step closes, it shrinks
here to one line per decision plus a pointer. The detail (findings, traps,
commits) moves to [PROJECT_KNOWLEDGE.md](PROJECT_KNOWLEDGE.md) in the same
commit. Working rules are in [CLAUDE.md](../CLAUDE.md).

## Long-term goals

Set by the user in May 2026, in priority order. Each one depends on the ones
before it.

1. **A library for drawing sundials**, starting with the accuratum type only.
   Other types can plug in later if the structure allows it. If it grows too
   complex, fall back to one simple program per sundial type with shared
   plotting.
2. **Large printed panels**, e.g. 6 m (east–west) × 2 m (north–south) in
   Brasília. This needs vector output with correct scaling: keep matplotlib,
   add SVG, no cairo.
3. **Human in the loop.** No single heuristic will place labels well from the
   poles to the equator, so the user gets fine control over which dates and
   hours are drawn and can nudge each label by hand.
4. **A web system** for generating sundials, started only after 1–3 succeed.
5. **A paper**, plus conferences on astronomy education and computer science,
   after the web system ships. Implement a second sundial type before
   publishing.

---

## Step 0 — Consolidate the trunk (decision pending)

The project moves to Trunk Based Development on `main`. Branch facts are in
[PROJECT_KNOWLEDGE.md § Core rewrite](PROJECT_KNOWLEDGE.md#core-rewrite--rewrite-core-branch-not-merged).

- `smart_hour_lines` is already fully contained in `main` and can be deleted.
- `rewrite-core` forks from `main@f3a45e3` and has 15 commits covering Steps
  1–3.1 of the rewrite. Since then `main` has gained only devcontainer and
  `.gitignore` commits, so a merge should conflict only on `.gitignore`.
- `labels` exists only on origin. Its lessons are already captured.

**Decision needed from the user:** merge `rewrite-core` into `main`
(recommended, since it serves goals 1–3) or keep v0.1 and park the rewrite.

After the decision:

1. Merge, or don't. Run `uv run pytest` and check that the CLI output still
   renders.
2. Delete `docs/REWRITE_PLAN.md` and `docs/LESSONS_LABELS.md` that arrive with
   the merge; their content is already in PROJECT_KNOWLEDGE.
3. Fill in the **Architecture** section of CLAUDE.md for the chosen layout.
4. Delete the stale branches (`smart_hour_lines`, `rewrite-core`, `labels`)
   locally and on origin. This needs push approval.
5. Confirm the second machine is set up for the Dropbox-synced Claude
   sessions. The old `NEXT_STEP.md` recipe now lives in
   [PROJECT_KNOWLEDGE.md § Dev environment](PROJECT_KNOWLEDGE.md#dev-environment-and-multi-machine-sync).
   On machine 1, the unused `.claude-data/` folder can be deleted.

## Step 1 — Sign-off of the rewrite (only if merged)

Checkpoints that only the user can close:

1. Open `uv run accuratum --lat-long=-15.78,-47.92 --canvas-size-mm=6000,2000 -o panel.svg`
   in Inkscape and nudge a label by its id.
2. Run `--save-spec clock.json`, hand-edit a label override, then
   `--spec clock.json`, and check that the label moved.
3. Answer the open question: should an override's `dx/dy` move **both**
   endpoint labels of a line, as it does now?

Then reassess the backlog below against goals 3–4.

## Backlog (not scheduled)

- **Extreme latitudes:** poles, the Arctic/Antarctic circles and the equator
  are untested. The label tolerances and exclusion radius may break there.
- **Sun map:** a plot of the sun's position (altitude, azimuth), comparing
  astropy against skyfield.
- **Guard test** that `core/` never imports matplotlib (if the rewrite is
  merged).
- **Second sundial type**, a prerequisite for goal 5.
