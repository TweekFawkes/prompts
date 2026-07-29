---
name: gohome
description: Commit work in the current git worktree, fast-forward main with the new commit, delete the merged feature branch, and unregister the worktree from git (leaving its files on disk). Use when the user invokes "/gohome" or asks to "commit back to main and clean up the worktree" / "go home" after wrapping up a focused piece of work on a feature branch. Operates on the local repo only — does not push to remote unless asked.
---

# /gohome — Land the current worktree on main and clean up

You are wrapping up work in a git worktree. The flow assumes the user has been editing on a feature branch like `<username>/<slug>`, that all code changes for this task are now finished, and that `main` is the integration branch. The goal: one tidy commit on top of `main`, the feature branch deleted, the worktree unregistered from git (its directory left on disk so gitignored, hard-to-rebuild local state — env files, build/dependency caches — survives), leaving the user with only the main worktree as far as git is concerned.

This skill ONLY operates on local refs. Do not `git push` unless the user explicitly asks afterwards.

## Authoritative paths

- Current (feature) worktree: the cwd when the skill is invoked.
- Main worktree: the worktree whose branch reads `[main]`. Use `git worktree list` to confirm.
- Project conventions:
  - Match the repo's existing commit style — topic-prefixed, imperative subject lines (e.g. `api: add ...`, `cli: build for ...`, `tests: extend ...`). Follow the most recent few commits in `git log --oneline -5` for tone.
  - History stays linear — feature work is **rebased** onto `main`, then `main` is **fast-forwarded**. No merge commits.

## Required workflow

### 1. Reconnaissance (always run first)

Run these in parallel:

```
git worktree list
git status
git diff --stat HEAD
git log --oneline -5
git log --oneline HEAD..main
git log --oneline main..HEAD
```

From the output, identify:
- The current branch (must NOT be `main` — abort with a clear message if it is).
- The main worktree path (the row whose ref reads `[main]`).
- Whether main has moved ahead of the branch's base (commits in `HEAD..main`).
- Whether the branch already has its own commits (commits in `main..HEAD`).
- Any uncommitted changes (staged or unstaged) in `git status`.

If `git status` shows nothing AND `main..HEAD` is empty, there is nothing to land — tell the user and stop.

### 2. Stage + commit (only if there are uncommitted changes)

- Add **specific files** by name — never `git add -A` or `git add .`. Skip anything that looks like a secret (`.env`, `*.backup.*`, `credentials.*`) and warn the user if such a file is staged.
- Read `git log --oneline -5` to mirror the project's commit style (lowercase, topic-prefixed, no Conventional-Commits noise).
- Write the message via HEREDOC. Lead with one short subject line (`<topic>: <imperative>` under ~72 chars), then a blank line, then a body that captures the why and the user-visible shape of the change. If your harness's git guidance mandates a co-author trailer (e.g. `Co-Authored-By: <model> <noreply@anthropic.com>`), include it using whatever model that guidance names right now — never copy a hardcoded model name from an example, they go stale every release.
- Never use `--amend`, `--no-verify`, or `-n`. If a pre-commit hook fails, fix the underlying issue and create a fresh commit.
- After the commit, run `git status` to confirm a clean tree.

### 3. Rebase onto main (only if `HEAD..main` is non-empty)

```
git fetch  # safe even if no remote — surfaces upstream movement
git rebase main
```

If the rebase has conflicts, stop and surface the conflicting files. Do **not** abort or run `--skip` without asking the user.

### 4. Fast-forward main from the main worktree

`main` is checked out in the main worktree, so updating it from this worktree requires `git -C <main-path>`. The merge must be ff-only — that's the contract of this skill.

```
git -C <main-worktree-path> merge --ff-only <feature-branch>
```

If the ff-merge refuses (e.g. divergence somehow), stop and surface the situation — do not switch to a regular merge or force-push.

### 5. Delete the merged feature branch

After the ff-merge, the feature branch ref is redundant — `main` now points to the same commit. The branch still lives in the worktree's HEAD though, which means a regular `git branch -d` from the main worktree will refuse it ("checked out at <feature-worktree>"). That refusal is desirable: it forces step 6 to run before we delete the ref.

After step 6 unregisters the worktree, run:

```
git -C <main-worktree-path> branch -d <feature-branch>
```

`-d` (not `-D`) so git refuses if the branch isn't actually merged — defensive against a botched ff-merge.

### 6. Unregister the worktree from git (leave the files alone)

We deliberately **do not** delete the worktree directory. The tracked files in it are now byte-identical to `main`, but its gitignored local state (env files, build/dependency caches, seeded deploy artifacts) may be slow or annoying to rebuild, and the user prefers to keep it around. So we sever git's view of the worktree while leaving the directory itself on disk.

Two pieces of state link a worktree to its parent repo:
- A `.git` **file** (not a directory) inside the worktree, containing `gitdir: <main>/.git/worktrees/<name>`.
- The admin directory `<main>/.git/worktrees/<name>/`.

Removing the `.git` file from the worktree side and pruning from the main side cleanly unregisters it:

```
rm <feature-worktree-path>/.git
git -C <main-worktree-path> worktree prune
```

Run both from outside the worktree (the `rm` targets a file inside it but we don't `cd` into it; the `prune` runs with `-C <main>`). After this, `git worktree list` no longer mentions the directory, but every file in it — tracked, untracked, and gitignored — is untouched. The user can `rm -rf` the directory whenever they want, or leave it as a snapshot.

Do **not** use `git worktree remove` — that command deletes the directory too, which is exactly what we're avoiding.

### 7. Final report

Print a short summary, in this order:

1. The new commit's hash + subject line.
2. The branch that was deleted.
3. The worktree path that was unregistered (and a note that the files are still on disk).
4. The current `main` tip (`git -C <main-worktree-path> log --oneline -1`).
5. A one-liner reminding the user that nothing was pushed yet — they can `git -C <main-worktree-path> push` from the main worktree if they want the change on the remote.

## When to stop and ask

- Current branch is `main` — refuse, this skill is for feature branches only.
- `git status` shows files that look sensitive (`.env`, `credentials.json`, `*.pem`, `*.key`) — stop and surface them.
- A rebase conflict appears — stop, list the files, ask the user how to proceed.
- The ff-merge in step 4 refuses — stop, dump `git log --graph --oneline -10` and the relevant branch tips, and ask the user.
- The branch name is something other than the user's normal `<username>/<slug>` shape — confirm before proceeding.
- `git worktree prune` reports something other than the one expected entry being pruned — surface its output and stop, rather than silently cleaning up state we didn't intend to touch.

## What success looks like

```
Committed:  a1b2c3d  api: surface per-task results
Branch:     username/fix-login-bug (deleted)
Worktree:   /path/to/repo-worktrees/fix-login-bug (unregistered — files still on disk)
main:       a1b2c3d  api: surface per-task results
Not pushed — `git -C <main-worktree-path> push` from the main worktree to send it up.
```
