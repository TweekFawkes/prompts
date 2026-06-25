---
name: gitready
description: "Prepare isolated Git worktrees for parallel agent work. Use when the user invokes gitready or /gitready, asks to create a new Git worktree, wants a new agent workspace, starts multiple agents on the same repo, or needs safer same-laptop multi-agent Git setup."
---

# /gitready - Prepare an isolated agent worktree

Use this skill to give each agent its own branch, worktree, dependency install, local runtime state, and handoff note. The default posture is: one task, one worktree, one branch, one agent.

## Quick Start

1. Read the repo root `CLAUDE.md` (or `AGENTS.md`) and any local `tasks/lessons.md` before creating the worktree.
2. Choose a short task slug: lowercase words separated by hyphens, such as `fix-rbac-export`.
3. From anywhere inside the source repo, run:

```bash
repo_root="$(git rev-parse --show-toplevel)"
bash "$repo_root/.claude/skills/gitready/scripts/create_worktree.sh" <task-slug>
```

Useful options:

```bash
bash "$repo_root/.claude/skills/gitready/scripts/create_worktree.sh" <task-slug> --dry-run
bash "$repo_root/.claude/skills/gitready/scripts/create_worktree.sh" <task-slug> --base origin/main
bash "$repo_root/.claude/skills/gitready/scripts/create_worktree.sh" <task-slug> --branch agent/<task-slug>
bash "$repo_root/.claude/skills/gitready/scripts/create_worktree.sh" <task-slug> --path /absolute/worktree/path
bash "$repo_root/.claude/skills/gitready/scripts/create_worktree.sh" <task-slug> --no-fetch
```

The helper creates a timestamped `agent/<task-slug>-<YYYYMMDDHHMMSS>` branch by default and places the worktree in a sibling directory named `<repo>-worktrees/<task-slug>-<timestamp>`, outside the tracked repo. For a repo at `/path/to/repo`, worktrees land under `/path/to/repo-worktrees/`, and `gitclean` retires them under `/path/to/repo-worktrees/delete_me/`.

Generated branch/path collisions in the same second get a deterministic numeric suffix such as `-2`. A custom `--path` must be outside the tracked repository.

## Workflow

1. Inspect current Git state:

```bash
git status --short
git branch --show-current
git worktree list
```

2. If the source worktree has uncommitted changes, say clearly that those changes will not be present in the new worktree. Do not copy, stash, or patch them into the new worktree unless the user explicitly asks.
3. Create the worktree with the helper script. Prefer `origin/main` as the base after `git fetch --prune origin`; fall back to `main`, then `HEAD`, only when needed.
4. Move into the new worktree and re-read the local instructions there:

```bash
cd <new-worktree-path>
sed -n '1,220p' CLAUDE.md
[ -f tasks/lessons.md ] && sed -n '1,220p' tasks/lessons.md
```

5. Install or prepare dependencies inside the new worktree only when the task needs it. Avoid sharing mutable dependency directories between agents.
6. Before handing off, report the source repo, new worktree path, branch, base ref, dirty-state warning if any, and the next command the agent should run.

## Multi-Agent Hygiene

- Keep each agent on a separate branch. Do not let two agents commit to the same branch unless the user explicitly asks for a handoff.
- Keep worktrees outside the tracked repo, preferably in the sibling `<repo>-worktrees/` directory, so the source worktree does not gain noisy untracked folders.
- Use per-worktree `.venv`, `node_modules`, build outputs, and caches. Do not reuse an environment that another agent may mutate while tests are running.
- Treat `.env` files and secrets as local state. If a worktree needs one, first verify it is ignored, then copy only what is needed. Never commit secrets.
- For Docker Compose or container stacks, use a unique `COMPOSE_PROJECT_NAME` per worktree and ensure ports, volumes, and database files do not collide before starting a second stack.
- Preserve any architecture invariants documented in your `CLAUDE.md` / `AGENTS.md`, and run the project's smoke/health check as the proof step before calling implementation work done.
- If the local tool supports worktree comments or thread titles, record the task slug, branch, path, and current status there so agents can see who owns what.
- Keep final handoffs concrete: changed files, tests run, remaining risks, and whether the branch is ready to merge.

## Cleanup

Only clean up a worktree after its branch has been merged, abandoned, or explicitly handed off. For finished task worktrees, prefer `$gitclean`; it merges back to `main` and moves the retired worktree under a sibling `delete_me/` directory.

```bash
git worktree list
git worktree remove <worktree-path>
git branch -d <branch-name>
git worktree prune
```

Use `git branch -D` or `git worktree remove --force` only after explicit user approval.

## Stop And Ask

Ask one targeted question before proceeding when:

- The user wants uncommitted changes from the source worktree included in the new worktree.
- The requested base ref, branch, or path is ambiguous or already in use.
- Running another local stack would collide on fixed ports, shared volumes, or a shared database file.
- Cleanup would delete another agent's active worktree, branch, or unmerged commits.
