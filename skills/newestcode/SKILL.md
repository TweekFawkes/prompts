---
name: newestcode
description: Bring THIS checkout up to date with the latest merged code on origin/main — the PRs that landed while we were working — without losing local work. Fetches, reports which PRs are new, then integrates them the right way for the current branch state (fast-forward main, or merge/rebase origin/main into a feature branch), stopping on conflicts or dirty trees instead of guessing. Flags when the pulled diff touches dependencies/schemas (so the venv or deployed env is now stale) and offers to redeploy dev so the *running* code matches. Use when invoked as "/newestcode" or asked to "make sure we're running the latest code", "pull in the PRs merged since we started", "sync this checkout with main", "are we on stale code?".
argument-hint: "(optional) e.g. 'and redeploy dev' to opt into the deploy phase"
---

# /newestcode — Sync this checkout with the latest merged code

Other agents and the user merge PRs to `main` constantly. Work that started an hour ago may now be sitting on stale code. **Your job: make THIS checkout reflect the latest `origin/main`, safely, and tell the user exactly what changed — then, if the running environment needs to match, offer to redeploy.**

This is the **download** counterpart to the repo's "upload" skills. Don't confuse them:
- `/openpr`, `/landtomain`, `/gohome` push *this branch's* work *up* to `main`.
- **`/newestcode` (this skill)** pulls *the world's latest* `main` *down* into wherever we are. It creates no feature work and opens no PR.

The whole skill is built around one rule: **never destroy or orphan local work to get newer code.** A dirty tree, local commits, or a conflict means *stop and surface*, not *force through*.

## Authoritative facts (verify, don't assume)

- **Remote:** `origin` → your GitHub repo. Confirm with `git remote -v`.
- **Integration branch:** `main`. If PRs merge as **merge commits** titled `Merge pull request #N from <branch>`, `git log HEAD..origin/main` reads as a clean list of the PRs you're about to pull in.
- **One `.git`, many worktrees.** `git fetch` here updates `origin/*` for every worktree at once. But `main` is only ever checked out in ONE worktree (the canonical `main` checkout); every other worktree is on a feature/detached ref. The right integration move depends on which you're in — that's the phase-3 matrix.
- **"Latest code" has two layers.** (a) The *tracked files in this checkout* matching `origin/main` — always in scope. (b) The *thing actually running* (your deployed dev environment, and your local virtualenvs) matching that code — only as fresh as the last deploy / dependency sync. Pulling commits fixes (a); it does **not** fix (b). Phase 5 bridges the gap.
- **Deploy source is the checkout it's RUN FROM.** If your dev deploy syncs *the repo copy it runs from* onto the dev environment, a redeploy from a feature worktree silently *reverts* dev to that branch. Only offer the redeploy phase when on the canonical `main` checkout, unless the user explicitly wants this branch on dev.
- **Gitignored deploy artifacts are not "work."** Seeded env files and per-worktree dependency/build caches don't show in `git status` and are reproducible — never force-add them or treat them as something to rescue.

## Required workflow

### 1. Reconnaissance (always run first, in parallel)

```
git remote -v
git rev-parse --abbrev-ref HEAD          # branch name, or "HEAD" if detached
git worktree list                         # which row is [main]? are we it?
git status --porcelain                    # dirty tree? untracked non-ignored files?
git stash list
git fetch --prune origin                  # the only network step; updates origin/*
git log --oneline --left-right HEAD...origin/main   # < = ours only, > = theirs only
```

Then characterize the situation precisely (you'll branch on this in phase 3):

- **Behind only** (`>` commits, no `<`): clean catch-up — the easy, common case.
- **Up to date** (no `>`): already on the newest `main`. Report that and stop — do not fetch-loop or invent work.
- **Diverged** (`<` *and* `>`): we have local commits AND `main` moved. Needs a real merge/rebase — handle carefully.
- **Dirty tree** (`git status --porcelain` non-empty): there are uncommitted/untracked changes to protect *before* any integration.

Also note: is `origin/main` ahead at all? Which PR numbers are in the `>` list (`git log HEAD..origin/main` — the merge-commit subjects name them)? Optionally enrich with `gh pr list --state merged --limit 20 --json number,title,mergedAt` if `gh` is authed, but git alone is sufficient — don't block on `gh`.

### 2. Protect local work before touching history

- **Dirty tree.** A merge/rebase refuses to run over uncommitted changes, and a stale `git checkout`/reset would eat them. Default: `git stash push -u -m "newestcode autostash <slug>"` to set the changes aside, integrate, then `git stash pop` and surface any pop-conflicts. If the changes look substantial or are clearly mid-task work the user may want to commit first, **stop and ask** whether to stash or commit rather than deciding for them. Never `git checkout -- .`, `git reset --hard`, or `git clean` to "clean up" before pulling.
- **Sensitive files in the dirty set** (`.env`, `*.pem`, `*.key`, `credentials.*`, `id_*`): surface them and confirm before stashing/committing — stashes are recoverable but easy to forget.
- **Stashes already present:** note them in the report; they survive everything this skill does, but flag them so they aren't forgotten.

### 3. Integrate — pick the move by branch state

| You are on… | `origin/main` relationship | Do this |
|---|---|---|
| **`main`** (canonical checkout) | behind only | `git pull --ff-only origin main` |
| **`main`** | diverged (local commits on main) | **Stop and ask.** Local commits on `main` are unusual — the user decides rebase-onto-main vs. moving them to a branch. Don't force it. |
| **feature branch** | behind only / diverged | Default **merge**: `git merge origin/main` (no force-push needed, preserves the branch). Use **rebase** (`git rebase origin/main`) only if the user wants linear history — and only if the branch is unpushed or the user accepts a later `--force-with-lease`. |
| **detached HEAD** | any | **Stop and ask.** Detached HEAD usually means an automation/codex worktree; integrating could strand commits. Surface `git log --oneline -3` and let the user point you at a branch. |
| **up to date** (any branch) | no `>` commits | Nothing to do — skip to phase 6. |

Rules that apply to every integration:
- **Conflicts → stop.** List the conflicted files (`git diff --name-only --diff-filter=U`) and ask how to resolve. Never auto-resolve, `--skip`, or `--strategy=theirs` to push through.
- `--ff-only` is deliberate on `main`: if it refuses, history diverged and you must not paper over it with a merge commit — surface it.
- After a clean integration, re-run `git status --porcelain` (should be clean) and `git log --oneline --left-right HEAD...origin/main` (the `>` list should now be empty).

### 4. Restore protected work

- If you stashed in phase 2: `git stash pop`. If it conflicts, **stop**, show the conflicted files, and let the user resolve — do not drop the stash. Confirm the stash is gone from `git stash list` only after a clean pop.
- Confirm the working tree matches the user's intent: the newer code is in, and their in-progress changes are back on top.

### 5. Did "latest code" actually reach what's *running*? (drift check)

Pulling commits updated the *files*. Now decide whether the *running* code is stale, by inspecting what the pulled diff (`git diff --stat <old-HEAD>..HEAD`, where `<old-HEAD>` is the pre-integration tip from phase 1) actually touched:

- **Dependency / lockfile changes** (`pyproject.toml`, `uv.lock`, `package.json`, a local path-dependency): your local virtualenv / `node_modules` is now stale. Flag it. For a path-dependency content change, a targeted reinstall (e.g. `uv sync --reinstall-package <pkg>`) recovers a stale env. Don't blanket-reinstall unprompted — name what changed and let the user run it.
- **Schema / model changes** (shared schema files, vendored model packages): if the project has a no-deploy preflight or smoke check that fails on schema/model drift, run it — a cheap way to confirm the checkout is self-consistent.
- **Anything that changes runtime behavior** AND the user wants dev to match: the dev environment is only as new as its last deploy. This is the only point where a redeploy is in scope (phase 6).

If the pulled diff is docs/tickets/tests-only, say so — no redeploy or resync needed.

### 6. Offer to make the *running* env match (only if warranted)

Redeploying is heavy and reverts dev to whatever checkout runs it. So treat it as **opt-in**, not automatic:

- **Offer it when:** phase 5 found runtime-affecting changes AND we're on the canonical `main` checkout AND (the invocation asked for it, e.g. "/newestcode and redeploy dev", OR the user confirms). Run the project's dev-deploy command. If the deploy has a known post-restart window where the running service errors transiently, expect it and re-verify once it has reconnected.
- **Do NOT redeploy when:** on a feature/detached worktree (it would silently revert dev), or the diff was docs/tickets/tests-only, or the user didn't ask and the change is low-risk. Say what you'd run and let the user decide.
- This skill never deploys to test/stage/prod. Prod is gated regardless.

### 7. Final report

Print a concise, skimmable summary:

```
On:        <branch>  (<canonical main checkout | feature worktree | detached>)
Was at:    <short-sha>  "<old subject>"
Now at:    <short-sha>  "<new subject>"
Pulled in: N commits  (PRs: #246, #245, …  — or "none, already current")
Local work: <stash popped clean | committed | none | NEEDS ATTENTION: …>
Drift:     <docs/tickets only — nothing to redeploy
            | touches deps/schema/runtime — venv resync and/or dev redeploy may be needed>
Running env: <not touched | redeployed dev, re-verify once the service has restarted>
```

If anything is unresolved (conflict, ambiguous stash, diverged `main`), make the **first line** a clear `NEEDS DECISION:` with the precise question — don't bury it.

## When to stop and ask

- Diverged `main`, or detached HEAD — don't guess how to integrate.
- A merge/rebase conflict, or a `git stash pop` conflict — list files, ask.
- `--ff-only` refuses on `main` — history diverged; surface, don't merge-commit around it.
- The dirty tree looks like real in-progress work the user may want to commit (vs. throwaway) — ask before stashing.
- A redeploy would run from a non-canonical checkout (would revert dev) — confirm first.
- Sensitive files in the working set — surface before stashing/committing.

## What success looks like

```
On:        main  (canonical checkout)
Was at:    7ede4b7  "Merge pull request #246 …"
Now at:    a1b2c3d  "Merge pull request #251 …"
Pulled in: 5 commits  (PRs #247–#251)
Local work: none (clean tree)
Drift:     #249 touched a shared schema — ran the preflight check, no drift; env resync not needed (no lockfile change)
Running env: not touched — say the word to redeploy dev.
```

## Note on this skill's own file

This skill lives at `.claude/skills/newestcode/SKILL.md` (git-tracked). It's currently **untracked/new** in the working tree, so a `/newestcode` run that stashes will carry it along — and if the user later lands it, it ships like any other project skill. Nothing special required here.
