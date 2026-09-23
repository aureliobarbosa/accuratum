# Next step: set up machine 2 and roll out Claude sync to other projects

This file is for a Claude Code session running **on the host of machine 2, outside any
container**, plus the user. Ask the user before each destructive or outward-facing command
(deleting folders, committing, pushing). Never push without explicit approval.

## Background (what is already done on machine 1)

Claude Code session data for devcontainer projects is synced between machines with Dropbox:

- On each host, `~/Dropbox/claude-code/` holds seven folders: `projects`, `file-history`,
  `skills`, `agents`, `commands`, `plans`, `todos`.
- Each project's `.devcontainer/devcontainer.json` bind-mounts those seven folders into the
  container at `/home/vscode/.claude-code/<folder>` and sets
  `CLAUDE_CONFIG_DIR=/home/vscode/.claude-code`.
- Everything else Claude writes (login credentials, `.claude.json`, caches, `settings.json`)
  lives in a Docker named volume `claude-code-state`, one per machine, shared by all project
  containers on that machine. It never enters Dropbox, so there is nothing to exclude.
- Sessions are filed by the container path of the project (`/workspaces/<folder-name>` →
  `projects/-workspaces-<folder-name>/`). That is why the same session shows up on both
  machines, **as long as the project folder has the same name on both**.
- `accuratum` is migrated and verified on machine 1 (13 sessions visible after rebuild). The
  old in-repo `.claude-data/` folder is no longer used or tracked by git.

Only two machines are used for `accuratum`.

## Part A — Set up `accuratum` on machine 2

1. **Check prerequisites on the host.**
   - `id -u` prints `1000` (matches the container's `vscode` user, so files in Dropbox keep
     the right owner). If not, stop and tell the user.
   - Dropbox is running and up to date: `dropbox status` shows "Up to date".
   - The synced data has arrived:
     `ls ~/Dropbox/claude-code/projects/-workspaces-accuratum/*.jsonl | wc -l` prints 13 or
     more. If the folder is missing or smaller, wait for Dropbox; do not continue.
   - Dropbox must be at exactly `~/Dropbox` (the devcontainer uses
     `${localEnv:HOME}/Dropbox/claude-code`).

2. **Replace the old project folder.** The user decided to erase machine 2's copy of
   `accuratum` and start fresh, because almost all work was done on machine 1.
   - Show `git -C <old path> status --short` and `git -C <old path> log origin/main..` so the
     user can see anything unpushed, then ask for confirmation.
   - Delete the old folder (including its `.claude-data/`).
   - Clone again, keeping the folder name `accuratum`:
     `git clone https://github.com/aureliobarbosa/accuratum.git ~/mycode/accuratum`
     (adjust `~/mycode` if machine 2 uses a different parent folder; only the last folder
     name matters).

3. **Hand over to the user** (these need VS Code and a browser):
   - Open the folder in VS Code → "Dev Containers: Reopen in Container". The
     `initializeCommand` creates any missing Dropbox subfolders before the build.
   - Log in to Claude Code once inside the container (the `claude-code-state` volume starts
     empty on a new machine).
   - Open the Claude panel's past-conversations list: the old `accuratum` sessions should be
     there with their content.

4. **Rule for using both machines:** never keep the *same* session open on both machines at
   once. To move a session: close it, commit and push the branch, wait for Dropbox's ✓, then
   `git pull` and resume it on the other machine.

## Part B — Clean up (task 4)

Run only after Part A step 3 is confirmed working.

- **Machine 2:** nothing left; the old folder was deleted in Part A.
- **Machine 1:** the old `accuratum/.claude-data/` folder is still on disk but unused. It is
  deleted from the machine 1 container session, not from here.
- **Delete this file:** once both parts are done, remove `NEXT_STEP.md` from the repo in a
  commit on machine 1.

## Part C — Use the same setup in other projects (task 5)

Do this per project, only for projects the user names. Each project's devcontainer is in its
own git repo, so make the change once (on either machine), commit it, and `git pull` on the
other machine. Commit per project; do not push without approval.

### 1. Check the project first

- The container user must be `vscode` (true for `mcr.microsoft.com/devcontainers/*` images).
  If the image uses another user (e.g. `node` in node images), replace `/home/vscode` below
  with that user's home and `vscode:vscode` in the setup script with that user.
- Remove any existing `CLAUDE_CONFIG_DIR` in `remoteEnv` and any existing Claude mounts.
- If the project already has sessions in a local config folder (e.g. an in-repo
  `.claude-data/`), copy them into Dropbox first, without overwriting newer files:
  `cp -a -u <project>/.claude-data/{projects,file-history,skills,plans} ~/Dropbox/claude-code/ 2>/dev/null`
  Their folder name under `projects/` (`-workspaces-<name>`) already matches, since it is
  based on the container path.

### 2. Add to `.devcontainer/devcontainer.json`

Merge these keys into the existing JSON (keep all other keys). If the project already has
`mounts` or `initializeCommand`, combine them rather than replacing.

```jsonc
"initializeCommand": [
  "bash",
  "-c",
  "mkdir -p \"$HOME\"/Dropbox/claude-code/{projects,file-history,skills,agents,commands,plans,todos}"
],
"mounts": [
  "source=claude-code-state,target=/home/vscode/.claude-code,type=volume",
  "source=${localEnv:HOME}/Dropbox/claude-code/projects,target=/home/vscode/.claude-code/projects,type=bind",
  "source=${localEnv:HOME}/Dropbox/claude-code/file-history,target=/home/vscode/.claude-code/file-history,type=bind",
  "source=${localEnv:HOME}/Dropbox/claude-code/skills,target=/home/vscode/.claude-code/skills,type=bind",
  "source=${localEnv:HOME}/Dropbox/claude-code/agents,target=/home/vscode/.claude-code/agents,type=bind",
  "source=${localEnv:HOME}/Dropbox/claude-code/commands,target=/home/vscode/.claude-code/commands,type=bind",
  "source=${localEnv:HOME}/Dropbox/claude-code/plans,target=/home/vscode/.claude-code/plans,type=bind",
  "source=${localEnv:HOME}/Dropbox/claude-code/todos,target=/home/vscode/.claude-code/todos,type=bind"
],
"remoteEnv": {
  "CLAUDE_CONFIG_DIR": "/home/vscode/.claude-code"
}
```

Why each part:

- `initializeCommand` runs on the host before the container is created. Bind-mount sources
  must exist, or Docker creates them owned by root. It is a `bash -c` array because Ubuntu's
  `/bin/sh` (dash) does not expand `{a,b}`.
- The volume line gives each machine its own login and state; the name `claude-code-state`
  is the same in every project, so one login covers all projects on that machine.
- Only folders are bind-mounted. A single-file bind mount breaks when a program saves the
  file by writing a new copy and renaming it, which is why `settings.json` is not synced.
- If a future Claude Code version adds a folder worth syncing, add one more bind line (and
  the folder name to `initializeCommand`) in every project. Until then it simply stays local.

### 3. Add to the top of the post-create script

If the project has no `postCreateCommand`, add `"postCreateCommand": "bash .devcontainer/setup.sh"`
and create the script. Put this right after `#!/bin/bash`:

```bash
# Claude Code config: the named volume is created root-owned
CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-/home/vscode/.claude-code}"
sudo chown vscode:vscode "$CLAUDE_CONFIG_DIR"

# Seed per-machine Claude settings (settings.json is not synced)
if [ ! -f "$CLAUDE_CONFIG_DIR/settings.json" ]; then
  cat > "$CLAUDE_CONFIG_DIR/settings.json" << 'EOF'
{
  "model": "opus",
  "effortLevel": "medium",
  "agentPushNotifEnabled": true,
  "cleanupPeriodDays": 100000
}
EOF
fi
```

- `chown`: Docker creates a new named volume owned by root; Claude runs as `vscode`.
- `settings.json` is seeded only if missing, so it never overwrites changes the user made.
  Because the volume is shared, the first project built on a machine creates it for all.
- `cleanupPeriodDays: 100000` stops Claude Code deleting transcripts older than 30 days,
  which is what wiped the old sessions.

### 4. Ignore old config folders

Add `.claude-data/` (or whatever the old in-repo config folder was called) to `.gitignore`,
and `git rm -r --cached` it if it was tracked. Do not delete the folder until the user has
checked their sessions after the rebuild.

### 5. Verify each project

The user rebuilds the container, then inside it:

- `echo $CLAUDE_CONFIG_DIR` prints `/home/vscode/.claude-code`.
- `mount | grep claude-code` lists the volume and the seven bind mounts.
- On the host, `ls -a ~/Dropbox/claude-code` shows no `.credentials.json` or `.claude.json`.
- A new session's `.jsonl` appears under
  `~/Dropbox/claude-code/projects/-workspaces-<name>/` on the other machine.
