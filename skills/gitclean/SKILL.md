---
name: gitclean
description: Clean up a finished Git worktree after an agent task. Use when the user asks to run /gitclean, use $gitclean, clean up this worktree, merge a completed worktree back into main, retire a worktree, move a merged worktree under delete_me, or coordinate cleanup after multiple local agents worked on branches from the same repository. Merges the current branch into main, pushes main when appropriate, detaches/deletes the merged local branch when safe, and moves the old worktree folder under a sibling delete_me directory so agents stop using it.
---

# Gitclean

Use this skill only for a finished task branch that should be merged into the repository's main branch and then retired. The goal is to leave `main` current, preserve a visible retired worktree under `delete_me`, and reduce confusion for other local agents. For worktrees created by `gitready`, the default retirement path is a sibling `delete_me/` directory next to the worktree.

## Required Checks

1. Read the repo's `CLAUDE.md` (or `AGENTS.md`) and follow its Git, verification, and cleanup rules.
2. Identify the current worktree, current branch, main branch, and all local worktrees:

   ```bash
   git rev-parse --show-toplevel
   git branch --show-current
   git worktree list --porcelain
   git status --short
   ```

3. Stop if the current branch is `main`, `master`, or detached. This skill retires feature worktrees only.
4. Stop if this worktree or the main worktree is dirty. Review, stage, and commit intentional task changes first; never sweep unrelated files into a cleanup commit.
5. Run the repo's required verification before merging — for example:

   ```bash
   bash scripts/smoke.sh   # or the repo's test suite / lint / build
   ```

   If that is impossible, run the strongest relevant test/lint/build checks and state exactly what could not run.

## Preferred Automation

Use the bundled helper after the required checks pass:

```bash
bash .claude/skills/gitclean/scripts/gitclean.sh \
  --repo "$(pwd)" \
  --verified "bash scripts/smoke.sh"
```

Useful options:

- `--dry-run`: print the planned merge and retirement steps without changing files.
- `--main <branch>`: use a non-default main branch.
- `--no-push`: merge locally but do not push main.
- `--verified <text>`: record the verification command(s) that passed before cleanup.
- `--keep-branch`: keep the local task branch after detaching the retired worktree.
- `--delete-remote-branch`: delete the remote task branch after main is pushed. Use only when the user asked for remote branch cleanup or the repo clearly expects it.
- `--target-parent <path>`: place the retired worktree under a specific `delete_me` parent.

The helper creates a Git-common-dir lock (`gitclean-main.lock`) while merging so two local agents do not update `main` at the same time. If the lock already exists, it prints the recorded owner when available.

## Manual Workflow

If the helper is unavailable, do the same sequence manually:

1. From the task worktree, ensure the task branch is clean and committed.
2. Locate or create a clean worktree for `main`.
3. In the main worktree:

   ```bash
   git fetch --prune origin
   git pull --ff-only origin main
   git merge --no-ff <task-branch>
   ```

4. Run any post-merge verification that the repo requires if the merge changed generated files, lockfiles, migrations, or deployment config.
5. Push `main` unless the user requested local-only cleanup:

   ```bash
   git push origin main
   ```

6. Detach the old task worktree and delete the merged local branch when safe:

   ```bash
   git -C <task-worktree> checkout --detach HEAD
   git -C <main-worktree> branch -d <task-branch>
   ```

7. Move the retired worktree with Git metadata intact:

   ```bash
   mkdir -p "$(dirname "<task-worktree>")/delete_me"
   git -C <main-worktree> worktree move \
     <task-worktree> \
     "$(dirname "<task-worktree>")/delete_me/$(basename "<task-worktree>")-$(date +%Y%m%d%H%M%S)"
   git -C <main-worktree> worktree prune
   ```

Use `git worktree move`, not plain `mv`, so Git's worktree registry stays accurate.

## Stop Conditions

Stop and report the smallest next action if any of these happen:

- The task worktree has uncommitted or untracked files.
- The main worktree has local changes or is in the middle of a merge/rebase/cherry-pick.
- Required verification fails.
- `git pull --ff-only` cannot fast-forward.
- The merge conflicts.
- Another `gitclean` lock exists and appears active.
- The worktree path is already inside `delete_me`.

Do not use `git reset --hard`, `git checkout --`, `git clean -fd`, or hook bypasses unless the user explicitly asks for that exact destructive action.

## Final Report

Finish with a concise cleanup receipt:

```text
GITCLEAN: complete
BRANCH MERGED: <task-branch>
MAIN COMMIT: <sha>
PUSHED: yes|no
VERIFIED: <command(s)>
RETIRED WORKTREE: <absolute delete_me path>
BRANCH CLEANUP: local deleted|kept, remote deleted|kept
```

If cleanup stops, use:

```text
GITCLEAN: blocked
BLOCKED AT: <step>
REASON: <one sentence>
NEXT STEP: <smallest safe action>
```
