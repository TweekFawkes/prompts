---
name: openpr
description: From the current git worktree, commit any pending changes, push the feature branch to origin (github.com), and open a GitHub pull request to merge it into main. Use when invoked as "/openpr" or asked to "open a PR", "push this and PR it", "PR these changes back to main", or "raise a pull request for this worktree". Unlike /gohome (which lands on main locally and never touches the remote), this skill pushes the branch and creates/updates a PR via the gh CLI — it does NOT merge.
---

# /openpr — Push the current worktree and open a PR into main

You are wrapping up work in a git worktree and want it reviewed/merged through GitHub rather than fast-forwarded locally. The goal: every change in this worktree lands on a feature branch, that branch is pushed to `origin`, and a pull request targeting `main` is open (or refreshed) on github.com — leaving the actual merge to a human on the PR page.

This is the remote counterpart to `/gohome`. `/gohome` lands work on `main` locally and never pushes; **`/openpr` pushes the branch and opens a PR and never merges.** Pick this one when the change should go through review.

## Authoritative facts (verify, don't assume)

- **Remote:** `origin` → your GitHub repo. Confirm with `git remote -v`.
- **Base branch:** `main`.
- **CLI:** use the `gh` CLI for all GitHub operations (confirm it's authenticated with `gh auth status`). Never hand-craft API calls or ask the user to click around if `gh` can do it.
- **Branch naming:** feature branches follow your convention (e.g. `<username>/<slug>`); agent branches may be `codex/<slug>` or `claude/<slug>`. Use the branch that's already checked out — do not rename it.
- **Merge style:** if the repo merges PRs as `Merge pull request #N from <branch>` with the PR **title** as the merge subject, write the PR title as the real change summary.
- **Worktree gitignored artifacts:** a worktree may carry seeded, gitignored local state (env files, dependency/build caches). These do NOT appear in `git status` (they're ignored) and must never be force-added.

## Required workflow

### 1. Reconnaissance (always run first, in parallel)

```
git remote -v
git worktree list
git branch --show-current
git status --short
git diff --stat HEAD
git log --oneline -5
git fetch origin
git log --oneline origin/main..HEAD     # commits this branch adds
git log --oneline HEAD..origin/main      # commits main has that we don't
gh pr list --head "$(git branch --show-current)" --state open --json number,url,title
```

From the output, determine:
- The current branch. **If it is `main` or empty/detached HEAD, abort** — this skill only PRs feature branches.
- Whether there are uncommitted changes (`git status --short` non-empty).
- Whether the branch already has commits beyond `origin/main` (the PR's content).
- Whether `origin/main` has moved ahead of the branch's base (informational — note it; do not auto-rebase, see step 4).
- Whether a PR for this branch is **already open** (then step 6 *updates* instead of *creates*).

If `git status --short` is empty AND `origin/main..HEAD` is empty AND no open PR exists, there is nothing to PR — tell the user and stop.

### 2. Guard rails

- Abort if on `main`, an empty branch, or detached HEAD — explain why.
- Scan `git status --short` for anything sensitive (`.env`, `*.backup.*`, `credentials.*`, `*.pem`, `*.key`, `id_*`). If present, stop and surface it before committing or pushing — a push is public-facing and hard to walk back.
- If the branch name isn't the user's usual `<username>/<slug>` shape, confirm before proceeding.

### 3. Commit pending changes (only if `git status --short` is non-empty)

- Add **specific files by name** — never `git add -A` or `git add .`. List the paths from `git status --short` and add exactly those (minus anything sensitive from step 2).
- Match the repo's commit style — read `git log -5 --format='%B'`. On this repo that is: a capitalized, imperative **subject line** (≤72 chars), a blank line, then a `-`-bulleted body explaining the *why* and the user-visible shape of the change. (It is NOT lowercase Conventional-Commits.)
- Write the message via HEREDOC. End the commit message with the trailer the harness mandates:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` (use whatever model the harness's current git guidance names).
- Never use `--amend`, `--no-verify`, or `-n`. If a pre-commit hook fails, fix the underlying cause and make a fresh commit — do not bypass it without explicit user approval.
- After committing, run `git status` to confirm a clean tree.

### 4. Sync decision (do NOT auto-rebase)

By default **do not rebase or force-push.** GitHub computes mergeability on the PR page; a branch that's merely behind `origin/main` still merges cleanly there. Auto-rebasing a branch that may already be pushed means a force-push, which can clobber a teammate's view — not worth it unprompted.

Only rebase if BOTH: (a) the user explicitly asks to bring the branch up to date, or the PR would have real conflicts, AND (b) you've surfaced the situation. If you do rebase, use `git rebase origin/main`, resolve carefully (stop and ask on conflicts), then push with `git push --force-with-lease` (never plain `--force`).

### 5. Push the branch to origin

```
git push -u origin "$(git branch --show-current)"
```

If the branch already exists on origin and the push is rejected as non-fast-forward (and you did NOT rebase), stop and surface it — something diverged that you didn't expect. Do not force-push to "fix" it without understanding why.

### 6. Create — or update — the pull request

Build the PR title and body from the branch's commits (`git log origin/main..HEAD`):
- **Title:** the real change summary (this becomes the merge-commit subject). If the branch is a single commit, reuse its subject; if several, write one umbrella line.
- **Body (HEREDOC):** a short `## Summary` (1–4 bullets of what changed and why) and a `## Test plan` / `## Verification` section (what you ran, e.g. live verification, unit tests — be honest about what was and wasn't run). End the body with the harness-mandated footer line:
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`

**If no open PR exists** for this branch (from step 1):

```
gh pr create --base main --head "$(git branch --show-current)" \
  --title "<title>" --body "$(cat <<'EOF'
## Summary
- ...

## Test plan
- ...

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**If a PR is already open** for this branch: the `git push` in step 5 already updated its diff. Don't open a duplicate. Refresh its metadata only if it's now stale:

```
gh pr edit <number> --title "<title>" --body "<updated body>"   # only if changed
gh pr view <number> --json url,state,title
```

Do **not** pass `--web` (it tries to open a browser) and do **not** merge the PR (`gh pr merge`) — merging is the human's call on the PR page.

### 7. Final report

Print a short summary:
1. The new commit hash + subject (if you committed this run).
2. The branch pushed (and `origin/<branch>`).
3. The PR URL + number, and whether it was **created** or **updated**.
4. The PR's base ← head (`main` ← `<branch>`).
5. A one-liner: the PR is open for review and has NOT been merged — a human merges it on github.com.

## When to stop and ask

- Current branch is `main`, empty, or detached HEAD — refuse.
- `git status` shows files that look sensitive — stop and surface them before any push.
- A push is rejected as non-fast-forward and you didn't rebase — stop, dump the branch tips, ask.
- A rebase (only if explicitly requested) hits conflicts — stop, list the files, ask how to proceed.
- `gh` is not authenticated (`gh auth status` fails) — tell the user to run `gh auth login` (suggest the `!` prefix to run it in-session) and stop.
- The branch name isn't the user's normal shape — confirm first.

## What success looks like

```
Committed:  a1b2c3d  Add retry handling for flaky upstream calls
Pushed:     username/add-retry-handling → origin
PR:         #123 (created)  https://github.com/<owner>/<repo>/pull/123
Merge into: main ← username/add-retry-handling
Open for review — not merged. Merge it on github.com when ready.
```

## Note on this skill's own file

This skill lives at `.claude/skills/openpr/SKILL.md`, which is git-tracked, so it ships in the repo like every other project skill. If you just created or edited it, it's an ordinary working-tree change — it will be included in the commit + PR that this skill produces (or the next one), nothing special required.
