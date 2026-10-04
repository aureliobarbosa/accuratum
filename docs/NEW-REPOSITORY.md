# New repository — going public without waiting for GitHub Support

> **Status (2026-10-02):** planned, not started. Replaces waiting on PLAN.md
> Step 6g; ends with Step 6i (public). Delete this file once it is done and
> its outcome is recorded in PROJECT_KNOWLEDGE.md and PLAN.md.

> **Before starting on another machine:** that machine's old clone still
> holds the leaked history (PLAN.md Step 6d). Work only in a **fresh clone**
> made after the 2026-09-30 rewrite. Never push from the old one: it would
> put the leak into the new repo.

## Context

The cleaned history is on `main`, but GitHub still serves the force-pushed
commits by hash (`*******`, the `.claude-data/` leak, and `*******`). The
owner asked Support to purge them (2026-10-01), which may take months. The
owner first proposed: confirm the leaked credentials are dead, remove the
hash mentions from the repo with `git filter-repo`, force-push, then go
public. Commits and pushes happen only with the owner's OK.

## Why not a second rewrite

1. **Checking the credentials is right, but not enough.** The leaked commit
   also holds session transcripts, `file-history/`, `shell-snapshots/` and
   `.claude.json`. These can't be revoked; if the commit is reachable, they
   are public. gitleaks also missed the OAuth tokens there, so a clean scan
   proves little.
2. **Hiding the hash doesn't make the commits unreachable.** In a public
   repo they can still be found:
   - the repo's **Activity** page lists force-pushes with the old and new
     tip hashes, and the old tip leads to the whole old history;
   - **Actions runs** list the commit each run used;
   - GitHub resolves **short hashes**, and security researchers (Truffle
     Security, 2024) showed that 4-hex prefixes can be brute-forced
     (65,536 tries);
   - the **new force-push creates new dangling commits** whose docs still
     contain the hashes, and it shows up in the Activity page too.
   It only stops casual discovery.
3. **Another rewrite has a cost.** 54 commits since 2026-09-30 get new
   hashes, including tags `v0.2.0` and `v0.2.1`. The PyPI attestation of
   0.2.1 names commit `0d5765b`, which would then be dangling. Every hash
   cited in the docs since then goes stale, the other machines' clones
   diverge further, and it breaks the "no more history rewriting" rule.

## Decision (owner, 2026-10-02)

A fresh repository, plus the credential test and a skim of the leaked
transcripts. The old tags (`v0.1`, `v0.2.0`, `v0.2.1`) stay behind,
0.2.1 is deleted from PyPI, and the new repo's first release is
**v0.2.2**. Who does what: the owner does the GitHub and PyPI web steps;
Claude does the local steps and asks before every push and commit.

## Plan: a fresh repository with the same name

GitHub's own fallback, already named in PLAN item 6b. The leaked objects
live only in the old repo, so a new repo that never received them has
nothing dangling. The clean history is pushed as-is, so **no hash changes**:
the docs, the tags and PyPI's provenance stay valid, and `*******` in the
docs points to nothing.

1. **Verify the credentials are dead** (owner's own account, isolated;
   do it before the old repo is deleted):
   - Owner: open the commit page signed in and copy the full hash of
     `*******` (and `*******`).
   - Claude: in a temp dir outside the repo, `git init` + `git fetch
     <origin url> <full-hash>` (GitHub serves unreferenced objects by full
     hash). Never inside the working repo.
   - Claude: copy `.claude-data/.credentials.json` into an empty temp dir
     and run `CLAUDE_CONFIG_DIR=<tmp> claude -p "hi"`. An auth error means
     the tokens are dead. If it answers, the refresh token was still valid:
     the owner signs out of all sessions on claude.ai, and we test again.
   - Claude: grep the transcripts, `file-history/` and `shell-snapshots/`
     for keys, passwords and tokens (pickaxe-style patterns, not only
     gitleaks), and report what to rotate. Nothing is printed unredacted.
   - Delete the temp dir and the scratch clone afterwards.
2. **Save what the old repo has** (owner): the repo description and
   topics, and the `pypi` environment rules. Issues and PRs #2–#7 don't
   carry over. The old tags and Releases are left behind on purpose.
3. **Rename the old repo** to e.g. `accuratum-leaked` (owner; stays private).
4. **Create a new, empty, private `aureliobarbosa/accuratum`** (owner; no
   README/license, so the first push is a plain fast-forward).
5. **Push `main` only** (Claude, asks first), from the fresh clone, after
   pointing `origin` at the new repo. Before that, delete the local tags
   `v0.1`, `v0.2.0`, `v0.2.1` there (`git tag -d`), so no
   `--tags`/`--follow-tags` push can carry them over. A push to `main`
   doesn't trigger CI.
6. **Recreate the settings** (owner): environment `pypi` limited to `v*`
   tags; require approval for fork PR workflows; rulesets on `main` (no
   force-push or deletion) and on `v*` tags (only the owner creates them).
7. **Release 0.2.2 from the new repo:**
   - Claude: `uv version --bump patch` (0.2.1 → 0.2.2) + `uv lock`, tests,
     commit (asks first), push `main`, then tag `v0.2.2` and push it
     (asks first).
   - CI runs tests → build (tag check, smoke test) → GitHub Release + PyPI.
     This also proves the PyPI trusted publisher (owner, repo name,
     `ci.yml`, `pypi`) still matches the new repo. If it fails with a
     publisher mismatch, the owner re-adds the publisher on PyPI and we
     re-run the job.
8. **Delete 0.2.1 from PyPI** (owner, after 0.2.2 is up, so the project is
   never empty): pypi.org → Your projects → accuratum → Manage → Releases →
   0.2.1 → Delete. Implications:
   - permanent: the version 0.2.1 and its file name can never be uploaded
     again;
   - anyone pinned to `==0.2.1` breaks (nobody is known to be);
   - it also drops the wheel that still held `escola_nas_estrelas.jpeg` and
     `unb.jpg`;
   - delete the **release only, never the project**: deleting the project
     frees the name `accuratum` for anyone.
9. **Make the new repo public** (owner). Then add the owner as required
   reviewer of `pypi` (the backlog item, now possible).
10. **Delete the old repo** (owner) once nothing more is needed from it.
    Deletion is what actually removes the leaked objects from GitHub; then
    close the Support ticket.
11. **Docs** (Claude, commit only with the owner's OK):
    - PROJECT_KNOWLEDGE.md § Security cleanup: why a fresh repo (not a
      second rewrite: Activity page, Actions runs, short hashes), and that
      the old tags and PyPI 0.2.1 were dropped;
    - § PyPI publishing: first upload is now 0.2.2;
    - PLAN.md: 6g/6i shrink, the PyPI-reviewer backlog item goes;
    - 6d stays: an old clone pushing now would put the leak into the
      *public* repo.

## Verification

- `git ls-remote` on the new repo lists only `main` and `v0.2.2` (no
  `refs/pull/*`, no old tags), with the same hashes as the fresh clone.
- Signed out, `github.com/aureliobarbosa/accuratum/commit/*******` gives a
  404, and the Activity page shows no force-push.
- gitleaks over a fresh `--mirror` clone of the new repo: no findings.
- PyPI lists only 0.2.2; `uvx --refresh accuratum --help` installs 0.2.2
  in a clean environment; its attestation names the new repo, `ci.yml`
  and `pypi`.
