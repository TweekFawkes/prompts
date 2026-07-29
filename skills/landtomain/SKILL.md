---
name: landtomain
description: Land the current git worktree's branch into main and prove the worktree is safe to delete. Syncs with main, commits/pushes pending work, opens and MERGES a PR, then verifies nothing (commits, untracked files, new tickets, stashes) would be lost on delete and rescues anything that would. Use when invoked as "/landtomain" or asked to "land this to main", "merge this worktree back and make it safe to delete", "PR it, merge it, and confirm I can delete the worktree". Unlike /openpr (opens a PR but never merges) and /gohome (lands locally, never pushes), /landtomain pushes, merges on GitHub, and verifies deletion safety — but never deletes the worktree itself (the user does that).
---

# /landtomain — Merge this worktree into main, then prove it's safe to delete

You are wrapping up work in a git worktree. The goal: **every change in this worktree lands on `main` via a merged GitHub PR, and you prove that deleting the worktree afterward loses nothing.** You do the merge; you do NOT delete the worktree — the user deletes it once you've confirmed it's safe.

This is the "finish and clean up" counterpart to two narrower skills:
- `/openpr` pushes a branch and opens a PR but **never merges** — use it when the change needs human review.
- `/gohome` lands work on `main` **locally** and never pushes.
- **`/landtomain` (this skill)** syncs → pushes → opens PR → **merges it** → verifies the worktree is safe to delete → rescues anything at risk → reports. It stops short of the actual `git worktree remove`.

Work the phases in order. **Stop and ask** if any phase fails, is ambiguous, or surfaces something unexpected — landing to `main` and the subsequent delete are hard to walk back.

## Authoritative facts (verify, don't assume)

- **Remote:** `origin` → your GitHub repo. Confirm with `git remote -v`.
- **Base branch:** `main`.
- **CLI:** use the `gh` CLI for all GitHub operations (confirm with `gh auth status`). Never hand-craft API calls.
- **Branch naming:** feature branches follow your convention (e.g. `<username>/<slug>`); agent branches may be `codex/<slug>` or `claude/<slug>`. Use the branch already checked out — do not rename it.
- **Merge style:** if the repo merges PRs as a merge commit, `Merge pull request #N from <branch>`, with the PR **title** as the merge subject, write the PR title as the real change summary and merge with `gh pr merge --merge` (not squash/rebase) unless the user says otherwise.
- **Worktree gitignored artifacts:** a worktree may carry seeded, gitignored local state (env files, dependency/build caches). These do NOT appear in `git status` and are NOT "lost work" — they're reproducible and seeded fresh on every worktree. Never force-add them, and never count them as something to rescue.
- **What deleting a worktree actually loses:** only things that exist *solely* in this worktree's working tree and aren't on `main` — i.e. **uncommitted/unstaged changes, untracked non-ignored files (e.g. new `z_tickets/**` files), and unmerged local commits.** (Stashes are stored in the shared repo `.git`, not the worktree, so a stash survives the delete — but still surface it, per the brief.) Proving the worktree is safe to delete = proving none of those exist, or that you've rescued them.

## Required workflow

### 1. Reconnaissance (always run first, in parallel)

```
git remote -v
git worktree list
git branch --show-current
git status --porcelain          # uncommitted + untracked, machine-readable
git stash list
git diff --stat HEAD
git log --oneline -5
git fetch origin
git log --oneline origin/main..HEAD     # commits this branch adds (the PR content)
git log --oneline HEAD..origin/main      # commits main has that this branch lacks
gh pr list --head "$(git branch --show-current)" --state open --json number,url,title
gh auth status
```

From the output, determine:
- The current branch. **If it is `main`, empty, or detached HEAD, abort** — this skill only lands feature branches.
- Whether there are uncommitted changes or untracked non-ignored files (`git status --porcelain` non-empty).
- Whether there are stashes (`git stash list` non-empty) — note them; they're not worktree-local but the brief asks you to account for them.
- Whether the branch already has commits beyond `origin/main` (the PR's content).
- Whether `origin/main` has moved ahead (you WILL sync in phase 3 — note the gap).
- Whether a PR for this branch is **already open** (phase 5 then *updates* instead of *creates*).

If there is genuinely nothing to land — `git status --porcelain` empty AND `origin/main..HEAD` empty AND no open PR — then this branch is already fully on `main`. Skip straight to phase 6 (verify safe-to-delete) and report; do not create an empty PR.

### 2. Guard rails

- Abort if on `main`, empty branch, or detached HEAD — explain why.
- Scan `git status --porcelain` for anything sensitive (`.env`, `*.backup.*`, `credentials.*`, `*.pem`, `*.key`, `id_*`). If present, stop and surface it before committing/pushing/merging — landing is public-facing and hard to undo.
- If `gh auth status` failed, tell the user to run `gh auth login` (suggest the `!` prefix to run it in-session) and stop.
- If the branch name isn't the usual `<username>/<slug>` shape, confirm before proceeding.

### 3. Commit pending changes (only if `git status --porcelain` is non-empty)

This is the FIRST half of "rescue" — anything real in the working tree should land via the PR, not get copied around later.

- Add **specific files by name** — never `git add -A` or `git add .`. List the paths from `git status --porcelain` and add exactly those (minus anything sensitive from phase 2).
- **Untracked files count.** New `z_tickets/**` files, new code, new docs — if they're real work, commit them so they land on `main` through the merge. If an untracked file is genuinely throwaway, say so in the report rather than silently committing it. When unsure whether an untracked file should land, stop and ask.
- Match the repo's commit style — read `git log -5 --format='%B'`: a capitalized, imperative **subject line** (≤72 chars), a blank line, then a `-`-bulleted body explaining the *why* and the user-visible shape of the change. (NOT lowercase Conventional-Commits.)
- Write the message via HEREDOC. End it with the harness-mandated trailer:
  `Co-Authored-By: <model> <noreply@anthropic.com>` — use whatever model the harness's current git guidance names right now; never copy a hardcoded model name from an example, they go stale every release.
- Never use `--amend`, `--no-verify`, or `-n`. If a pre-commit hook fails, fix the cause and make a fresh commit — do not bypass without explicit approval.
- After committing, run `git status --porcelain` to confirm a clean tree.

### 4. Sync with main FIRST, then re-run checks

Unlike `/openpr` (which defaults to NOT rebasing), `/landtomain` brings the branch up to date **before** merging, so the merge is clean and the checks you re-run reflect what will actually be on `main`.

- Default to a **merge**, which needs no force-push: `git merge origin/main`.
- Use a **rebase** only if the user wants linear history: `git rebase origin/main`, then push with `git push --force-with-lease` (never plain `--force`).
- **On conflicts: stop, list the conflicted files, and ask** how to resolve — do not guess.
- **Re-run the project's checks after syncing.** At minimum let pre-commit hooks run; if the work depended on a suite (e.g. a smoke test, unit tests, an end-to-end check), re-run it and report honestly what passed, what failed, and what you didn't run. A clean sync that breaks checks is NOT done.

### 5. Push, then open or update the PR

```
git push -u origin "$(git branch --show-current)"
```

If the push is rejected as non-fast-forward and you did NOT rebase, stop and surface it — something diverged unexpectedly. Do not force-push to "fix" it without understanding why.

Build the PR title/body from `git log origin/main..HEAD`:
- **Title:** the real change summary (becomes the merge-commit subject). Single commit → reuse its subject; several → one umbrella line.
- **Body (HEREDOC):** a short `## Summary` (1–4 bullets of what changed and why) and a `## Test plan` / `## Verification` section (what you ran in phase 4 — be honest). End with the harness-mandated footer:
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`

**If no open PR exists** for this branch:

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

**If a PR is already open:** the push above already updated its diff. Refresh its title/body only if stale (`gh pr edit <number> --title ... --body ...`); do not open a duplicate. Do not pass `--web`.

### 6. Merge the PR

```
gh pr view <number> --json number,mergeable,mergeStateStatus,reviewDecision,url
gh pr merge <number> --merge                # merge commit, matches repo style
```

- Do **not** pass `--delete-branch`: git can't delete a branch that's checked out in a worktree, and you're deliberately keeping this worktree alive until the user confirms the delete. (The stale remote branch can be cleaned up later.)
- **If the merge is blocked** by branch protection (required reviews/failing checks/conflicts), stop and surface exactly why. Only use `--admin` to override if the user has the rights AND explicitly approves it — never silently.
- After merging, sync local refs so verification sees the truth. If you're working from a **linked worktree** (created by `gitready` or similar), `main` is checked out somewhere else — usually the original clone — and a plain `git checkout main` from here will fail ("already used by worktree at …"). Find that worktree first and update it in place:

```
git fetch origin
MAIN_WT="$(git worktree list --porcelain | awk '/^worktree /{p=$2} /^branch refs\/heads\/main$/{print p}')"
if [ -n "$MAIN_WT" ]; then
  git -C "$MAIN_WT" pull --ff-only origin main       # main lives in a different worktree — update it there
else
  git checkout main && git pull --ff-only origin main && git checkout -   # single checkout — safe to switch in place
fi
```

### 7. Verify the worktree is safe to delete

Prove nothing unique-to-this-worktree remains. Run and **show the output** of each:

```
git status --porcelain                       # MUST be empty (ignored artifacts won't appear — expected)
git stash list                               # note any stashes (survive delete, but report them)
git fetch origin
git log --oneline origin/main..HEAD          # MUST be empty — all commits are now on main
git branch --merged origin/main | grep -F "$(git branch --show-current)"   # branch should show as merged
git status --porcelain --ignored | grep -v '<known gitignored artifacts>'  # sanity: only seeded artifacts remain ignored
```

The worktree is safe to delete **iff**: working tree clean (no uncommitted/untracked non-ignored files), `origin/main..HEAD` empty (every commit landed via the merge), and any stash is acknowledged. If `git log --oneline origin/main..HEAD` is non-empty after a merge-commit merge, the merge didn't capture those commits — investigate before declaring safe.

### 8. Rescue anything still at risk

If phase 7 surfaces anything not on `main`:
- **Untracked non-ignored files / uncommitted changes** that should be kept → go back to phase 3, commit them, and re-run from phase 5 (push → merge) so they land properly. Prefer landing through the PR over hand-copying.
- **If landing through the PR isn't possible** (e.g. the PR is already merged and the user wants the leftover file preserved without a new PR) → manually copy the file(s) into the primary `main` checkout's working tree, and tell the user they're now uncommitted there awaiting a decision. Never delete the source until the copy is confirmed.
- **Stashes** → list them with `git stash show -p` so the user can decide; do not drop them.
- Re-run phase 7 after any rescue until it comes back clean.

### 9. Final report (before any deletion)

Print a concise summary. Be precise — this is what the user acts on:

1. **Merged:** PR #N + URL, base ← head (`main` ← `<branch>`), the merge-commit hash/subject now on `main`, and the commit range that landed.
2. **Checks:** what you re-ran in phase 4 and the result (honest pass/fail/skipped).
3. **Safe-to-delete verdict:** an explicit **GO** or **NO-GO**.
   - GO → "Deleting this worktree loses nothing: working tree clean, all N commits on `main`, no untracked work, stash list `<empty | listed>`."
   - NO-GO → the precise list of what is NOT yet on `main` and what you did about it (rescued how, or still pending the user's decision).
4. **Reminder:** you did NOT delete the worktree. The user removes it with `git worktree remove <path>` (add `--force` only if they accept the listed leftovers) once they're satisfied with the GO.

## When to stop and ask

- Current branch is `main`, empty, or detached HEAD — refuse.
- `git status` shows files that look sensitive — surface before any push/merge.
- A sync (merge or rebase) hits conflicts — list the files, ask how to resolve.
- A push is rejected non-fast-forward and you didn't rebase — dump the branch tips, ask.
- `gh pr merge` is blocked by branch protection — surface the reason; get explicit approval before any `--admin` override.
- Phase 7 can't reach a clean GO and the rescue path isn't obvious — stop and ask rather than declaring safe.
- An untracked file's fate is unclear (keep vs. throwaway) — ask before committing or discarding it.

## What success looks like

```
Merged:    PR #123  https://github.com/<owner>/<repo>/pull/123
           main ← username/land-feature-x   (merge commit e9f0a1b)
           Landed 3 commits (a1b2c3d..d4e5f6a) + 5 new z_tickets/ files.
Checks:    smoke test ✓, pre-commit ✓ (no unit suite for this change)
Verdict:   GO — worktree safe to delete. Working tree clean, origin/main..HEAD empty,
           branch shows as merged, stash list empty.
Next:      the user deletes it: git worktree remove <path>   (I did not delete it.)
```

## Note on this skill's own file

This skill lives at `.claude/skills/landtomain/SKILL.md`, which is git-tracked, so it ships in the repo like every other project skill. If you just created or edited it, it's an ordinary working-tree change — it'll be included in the commit + PR this skill produces (phase 3), nothing special required.
