---
name: ship
description: Finish a unit of work started with /newticket + /dowork — commit pending changes (code, the closed-ticket move, any follow-up tickets), push the branch, open a PR into main, sync with origin/main resolving any conflicts, merge the PR, fast-forward the main checkout, and verify the worktree is safe to delete. Use when invoked as "/ship" or asked to "ship this", "PR and merge this", "land this to main". Pass "--pr-only" ("/ship --pr-only") to stop after opening the PR without merging. Never implements anything — that's /dowork — and never deletes the worktree.
argument-hint: "(optional) --pr-only to open the PR without merging"
---

# /ship — Commit, PR, merge, and prove this worktree is safe to delete

Run this **inside the feature worktree**, after `/dowork` has finished (or after any other change you're ready to land).

Goal: every change in this worktree lands on `main` through a merged GitHub PR, the main checkout is current, and you can state plainly whether deleting the worktree would lose anything. You do the merge; the user deletes the worktree.

This does the same job as `/landtomain`, tuned for the `/newticket` → `/dowork` → `/ship` pipeline: it expects (but doesn't require) a ticket that just moved to `z_tickets/closed/`, and it fast-forwards `main` correctly even when `main` is checked out in a *different* worktree than this one — the normal setup once you're running multiple worktrees off one repo (see `/gitready`). If your worktree setup always keeps `main` checked out right here, `/landtomain` and `/ship` behave identically; pick whichever name matches your muscle memory.

**`--pr-only`:** stop cleanly after phase 4 (PR open, nothing merged) and say so. Use it when the PR should sit for review. Everything after phase 4 is skipped, including phase 7.

Work the phases in order. **Stop and ask** if any phase fails or surfaces something unexpected — a merge to `main` and the delete that follows are hard to walk back.

## Authoritative facts (verify, don't assume)

- **Remote:** `origin` → your GitHub repo. Confirm with `git remote -v`.
- **Base branch:** `main`. **Main checkout:** discover it, don't hardcode. Two shapes are common:
  - **Linked worktrees off one shared repo** (what `/gitready` sets up): `main` stays checked out in one worktree — usually the original clone — while every task gets its own linked worktree on a feature branch. `git checkout main` from a *linked* worktree fails ("already used by worktree at …") because git refuses to have the same branch checked out twice. Find the worktree with `main` checked out via `git worktree list --porcelain` (the entry whose `branch` line reads `refs/heads/main`) and run anything that touches local `main` as `git -C "$MAIN_WT" …`.
  - **A single checkout, branch-switching in place:** there is no separate `main` worktree — `git checkout main` works directly. The commands below handle both; the worktree-list lookup simply comes back empty and you fall back to a plain checkout.
- **CLI:** use `gh` for all GitHub operations. Never hand-craft API calls.
- **Branch naming:** feature branches follow your convention (e.g. `<username>/<slug>`); agent branches may be `codex/<slug>` or `claude/<slug>`. Use whatever branch is checked out — never rename it.
- **Merge style:** a merge commit — `gh pr merge <n> --merge`. Not squash, not rebase, so the PR **title** becomes the merge subject. Write the title as the real change summary. (Use squash/rebase instead if that's your repo's convention — just be consistent with your last few merges.)
- **Worktree gitignored artifacts:** env files, dependency caches, and other seeded-but-ignored local state never appear in `git status`, are never force-added, and are never "lost work" — they're reproducible.
- **What deleting a worktree actually loses:** only things that exist *solely* in this working tree and aren't on `main` — uncommitted changes, untracked non-ignored files (e.g. a new `z_tickets/**` file), and unmerged local commits. Stashes live in the shared `.git` and survive the delete, but still report them.

## Required workflow

### 1. Reconnaissance (run first, in parallel)

```bash
git remote -v
git worktree list --porcelain
git branch --show-current
git status --porcelain
git stash list
git diff --stat HEAD
git log --oneline -5
git fetch origin
git log --oneline origin/main..HEAD     # commits this branch adds
git log --oneline HEAD..origin/main     # commits main has that this branch lacks
gh pr list --head "$(git branch --show-current)" --state open --json number,url,title,isDraft
gh auth status
```

Determine:
- The current branch. **If it is `main`, empty, or a detached HEAD, abort** — this skill only ships feature branches.
- Whether there are uncommitted or untracked non-ignored changes (phase 3 commits them) — this includes the `z_tickets/closed/<ticket>.md` move `/dowork` made, and any follow-up tickets it filed.
- Whether the branch already has commits beyond `origin/main`.
- Whether a PR is **already open** for this branch — phase 4 updates it instead of creating one.
- Whether there are stashes — note them for the report.

If `git status --porcelain` is empty AND `origin/main..HEAD` is empty AND no PR is open, this branch is already fully on `main`. Skip to phase 6 and report; do not create an empty PR.

### 2. Guard rails

- Abort on `main`, an empty branch, or detached HEAD — explain why.
- Scan `git status --porcelain` for anything sensitive (`.env`, `*.pem`, `*.key`, `credentials.*`, `id_*`, `*.backup.*`). If present, stop and surface it before committing — a push is public-facing and hard to walk back.
- If `gh auth status` failed, tell the user to run `gh auth login` (suggest the `!` prefix to run it in-session) and stop.
- If the branch name isn't the usual shape for this repo, confirm before proceeding.

### 3. Commit pending changes (skip if the tree is already clean)

- Add **specific files by name** — never `git add -A` or `git add .`. Take the paths from `git status --porcelain`, minus anything flagged in phase 2. This includes the ticket move `/dowork` made into `z_tickets/closed/` and any new files under `z_tickets/open/` it filed as follow-ups.
- Match the repo's commit style — check `git log -5 --format='%B'` and mirror it (subject line, body conventions, trailer style). Don't assume Conventional Commits unless the log shows it.
- Write the message via HEREDOC. If your harness's git guidance mandates a co-author trailer, include it with whatever it names right now — never copy a hardcoded model name from an example, they go stale every release.
- Never use `--amend`, `--no-verify`, or `-n`. If a pre-commit hook fails, fix the cause and make a fresh commit; do not bypass it without explicit approval.
- If an untracked file's fate is unclear (keep vs. throwaway), stop and ask before it gets committed.
- Run `git status` afterward to confirm a clean tree.

### 4. Push and open (or update) the PR

```bash
git push -u origin "$(git branch --show-current)"
```

If the push is rejected as non-fast-forward, stop and surface it — something diverged unexpectedly. Do not force-push to "fix" it.

Build the title and body from `git log origin/main..HEAD`:
- **Title:** the real change summary — this becomes the merge-commit subject. Reuse the single commit's subject if there's one commit; write one umbrella line if there are several.
- **Body:** a short `## Summary` (1–4 bullets of what changed and why) and a `## Test plan` section stating honestly what was run — local checks, the tier `/dowork` picked, the live walk-through if it did one — and what was not.

**No open PR yet:**

```bash
gh pr create --base main --head "$(git branch --show-current)" \
  --title "<title>" --body "$(cat <<'EOF'
## Summary
- ...

## Test plan
- ...
EOF
)"
```

**PR already open:** the push above already refreshed its diff — do not open a duplicate. Update its metadata only if it is now stale (`gh pr edit <number> --title … --body …`).

Never pass `--web` (it tries to open a browser).

**If the invocation said `--pr-only`, stop here.** Report the PR URL and that nothing was merged.

### 5. Sync, merge, and fast-forward the main checkout

Bring the branch up to date first, so the merge is clean and any conflict is resolved here rather than on the PR page:

```bash
git merge origin/main
```

- A merge needs no force-push. Use `git rebase origin/main` only if you want linear history, then push with `git push --force-with-lease` — never plain `--force`.
- **On conflicts: stop, list the conflicted files, and ask how to resolve.** Do not guess.
- If the sync brought in changes, re-run the checks the work depended on (lint, the affected test suites) and report honestly what passed, what failed, and what you didn't run. A clean sync that breaks the tests is not done.
- Push the sync so the PR diff is current: `git push`.

Then merge:

```bash
gh pr view <number> --json number,isDraft,mergeable,mergeStateStatus,url
gh pr merge <number> --merge
```

- If the PR is a draft, `gh pr ready <number>` first.
- Do **not** pass `--delete-branch`: git cannot delete a branch checked out in a worktree, and this worktree stays alive until the user confirms the delete. Clean up the stale remote branch later.
- If the merge is blocked (branch protection, a red required check), surface the exact reason and stop. Get explicit approval before any `--admin` override.

Then fast-forward the main checkout — this is the step that differs from a plain single-checkout repo:

```bash
git fetch origin
MAIN_WT="$(git worktree list --porcelain | awk '/^worktree /{p=$2} /^branch refs\/heads\/main$/{print p}')"
if [ -n "$MAIN_WT" ]; then
  git -C "$MAIN_WT" pull --ff-only origin main        # main lives in a different worktree — update it there
else
  git checkout main && git pull --ff-only origin main && git checkout -   # single checkout — safe to switch in place
fi
```

- The fetch updates `origin/main` so phase 6 sees the truth. Never `git checkout main` from *this* worktree if `$MAIN_WT` resolved to a different path — git will refuse.
- This is what keeps the next worktree branching from the tip, and keeps anything deployed from the main checkout shipping what you just merged. Post-merge it is a pure fast-forward, zero risk.
- If the pull refuses (main checkout diverged, or local changes there would be overwritten), do not force or reset anything — report it as a `NEEDS ATTENTION` line in phase 8 and move on. The safe-to-delete verdict below depends only on `origin/main`.

If phase 6 surfaces anything not yet on `main` — an untracked file that should be kept, or commits that didn't land — go back to phase 3, land it (the old PR is merged, so phase 4 opens a new one), then re-run phases 5–6. List any stash with `git stash show -p` so the user can decide; never drop one.

### 6. Verify the worktree is safe to delete

Run these and **show the output**:

```bash
git status --porcelain                      # MUST be empty
git stash list                              # note any stashes
git log --oneline origin/main..HEAD         # MUST be empty — every commit is on main
git branch --merged origin/main | grep -F "$(git branch --show-current)"
```

Safe to delete **iff** the working tree is clean, `origin/main..HEAD` is empty, and any stash is acknowledged. If commits remain after the merge, the merge didn't capture them — investigate before declaring safe.

### 7. Mark the workspace complete (only on a GO verdict, skip with `--pr-only`)

If this worktree was created and tracked by a worktree-orchestration tool (something that shows each task as a card or workspace — Orca is one example; see [this repo's README](../README.md#running-this-with-orca-or-a-similar-worktree-ide) for what that pattern looks like), flip its status now so the board reflects reality, e.g.:

```bash
orca worktree set --worktree active --workspace-status completed --json
```

If you're not using a tool like that, skip this step silently — there's nothing to update.

### 8. Final report

```
Merged:    PR #42  https://github.com/<owner>/<repo>/pull/42
           main ← <branch>   (merge commit e9f0a1b)
           Landed 3 commits (a1b2c3d..d4e5f6a) + the closed ticket.
Checks:    <what you re-ran in phase 5 and the honest result>
Main:      fast-forwarded to e9f0a1b (via <main-checkout-path or "this worktree">)
Verdict:   GO — deleting this worktree loses nothing: tree clean,
           origin/main..HEAD empty, branch merged, stash list empty.
Next:      delete the worktree yourself, e.g. `git worktree remove <path>`.
           (I did not delete it.)
```

A `NO-GO` verdict must list precisely what is not yet on `main` and what you did about it.

## When to stop and ask

- Current branch is `main`, empty, or detached HEAD.
- `git status` shows anything that looks sensitive.
- An untracked file's fate is unclear.
- A push is rejected as non-fast-forward.
- The sync hits conflicts — list the files and ask.
- The merge is blocked by branch protection or a red check.
- `gh` is not authenticated, or the branch name isn't the usual shape.
- Phase 6 can't reach a clean GO and the fix isn't obvious.

## Hard rules

- Never delete the worktree — the user does that after reading your verdict.
- Never implement, test, or deploy anything — if the work isn't done, run `/dowork` first.
- Never `git add -A` / `git add .`, and never force-add a gitignored artifact.
- Never force-push, reset, or `--admin`-override without explicit approval.
