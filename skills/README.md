# Claude Code Skills

A collection of [Claude Code](https://claude.com/claude-code) **skills** for an
agent-driven, ticket-based development workflow: draft tickets, work them
end-to-end, and land the result through git worktrees and pull requests.

Each skill is a directory containing a `SKILL.md` (YAML frontmatter + Markdown
instructions). Claude Code auto-loads any skill it finds and exposes it as a
slash command (e.g. `/dowork`). Skills can invoke each other via the Skill tool.

## The skills

### Tickets

| Skill | What it does |
|---|---|
| [`newticket`](newticket/) | Plan and write ONE backlog ticket from a short brief into `z_tickets/open/`, then hand it off to a fresh worktree. Drafts the spec only — does not implement. |
| [`dowork`](dowork/) | Take ONE open ticket and run it end-to-end: plan → implement → test → verify at a depth matched to what the change touches (local-only, or deploy + live check) → move the ticket to `closed/`. Never commits — that's `/ship` and friends. |
| [`z_sort`](z_sort/) | Triage every open ticket into `open_agent/` (the agent can finish it alone) vs `open_human/` (needs a human to unblock or approve). |
| [`fixbugs`](fixbugs/) | Standing loop that consumes bug reports written into `z_tickets/open_bugs/` by your test runner, fixes each one, and verifies it goes green. |

### Git, worktrees & PRs

| Skill | What it does |
|---|---|
| [`gitready`](gitready/) | Create an isolated git worktree (own branch, own deps, own state) for parallel agent work. Includes a `scripts/create_worktree.sh` helper. |
| [`gitclean`](gitclean/) | Retire a finished worktree: merge its branch to `main`, push, delete the merged branch, and move the worktree under a `delete_me/` folder. Includes a `scripts/gitclean.sh` helper. |
| [`gohome`](gohome/) | Land the current worktree on `main` **locally** (fast-forward, delete branch, unregister worktree) — never pushes. |
| [`openpr`](openpr/) | Commit, push the feature branch, and open/refresh a GitHub PR into `main` — never merges. |
| [`landtomain`](landtomain/) | Push → open PR → **merge** it on GitHub → prove the worktree is safe to delete (rescuing anything at risk). |
| [`ship`](ship/) | The same job as `landtomain`, phrased as the closing move of `/newticket` → `/dowork` → `/ship`: expects a ticket that just moved to `closed/`, and adds an optional last step to mark a worktree-orchestration tool's workspace complete. Functionally identical to `landtomain` otherwise — pick whichever name fits your workflow. |
| [`newestcode`](newestcode/) | Pull the latest merged `origin/main` *down* into this checkout safely, flag dependency/schema drift, and optionally redeploy dev. |

### Session

| Skill | What it does |
|---|---|
| [`handoff`](handoff/) | Compact the current conversation into a handoff document so a fresh agent can pick up the work. |

## The `z_tickets` workflow

Most of these skills assume a simple folder-based ticket queue at the repo root —
plain Markdown files moved between directories, all tracked in git:

```
z_tickets/
├── open/            # tickets ready to be worked        (newticket writes here)
├── closed/          # finished tickets                  (dowork moves here)
├── onhold/          # parked work
├── open_bugs/       # auto-filed bug reports            (fixbugs consumes)
├── open_agent/      # z_sort: agent can finish alone
├── open_human/      # z_sort: needs a human
└── examples/
    └── _TEMPLATE.md # the ticket format
```

The core loop:

```
/newticket <brief>   →   writes z_tickets/open/<timestamp>-<slug>.md,
                          then hands the ticket to a fresh worktree (via /gitready)
/dowork <ticket.md>  →   implements + verifies, moves it to closed/ — never commits
/ship                →   commits, pushes, opens a PR, merges it, and proves
                          the worktree is safe to delete
```

`/dowork` deliberately never commits — landing is a separate, reviewable step.
`/ship` is one option for that step; `/openpr` (push + PR, no merge) and
`/landtomain` (functionally the same as `/ship`) are the others — pick whichever
matches how much of this you want automated.

`z_sort` and `fixbugs` run alongside as triage/repair loops. The git skills
(`gitready` → work → `gohome` / `openpr` / `landtomain` / `ship` → `gitclean`)
manage the worktree lifecycle around all of it.

## Installing a skill

Copy a skill directory into a Claude Code skills location:

```bash
# Available in every project (personal):
cp -r skills/dowork ~/.claude/skills/

# Or scoped to one project (commit it with the repo):
cp -r skills/dowork /path/to/your-project/.claude/skills/
```

Then invoke it in Claude Code as `/dowork` (and so on). Edit any `SKILL.md` to
match your project's conventions — the placeholders (`<username>`, `<owner>/<repo>`,
`example.com`, `scripts/smoke.sh`, etc.) are meant to be adjusted.

## Running this with Orca (or a similar worktree IDE)

These skills were originally written for **Orca**, a desktop app + CLI for
running several coding agents in parallel, each in its own git worktree. Orca
is not required — every skill above works from a plain terminal — but if you
have it, it removes some of the manual steps:

- Each repo is registered once (`orca repo add`); every task after that is
  `orca worktree create --name <slug> --agent <agent> --prompt "<first message>"`,
  which creates the branch, the worktree, *and* starts the agent in one call.
- Every worktree is a visible card with a status (`orca worktree set --workspace-status …`),
  so a glance at the app shows what every agent is doing without opening a terminal.
- It bundles a per-worktree terminal manager, browser automation, and an
  inter-agent messaging/task-dispatch layer (`orca orchestration …`) for cases
  where agents need to hand work to each other rather than to a human.
- `orca worktree rm` retires a worktree the same way `gitclean` does here — merge
  awareness plus a clean removal, instead of a bare `rm -rf`.
- Each repo can have a **setup script** attached (configured in the Orca app —
  there's no CLI flag to set the script itself, only `--setup run|skip|inherit`
  on `worktree create` to control whether it fires). Orca runs it automatically
  right after creating a worktree, typically to seed gitignored local state
  (env files, secrets) that a fresh checkout doesn't have. `gitready/scripts/seed-worktree.sh`
  is that same idea without Orca: a script you (or `/dowork`'s step 0) call by hand.

The concepts map onto these skills roughly like this:

| Orca concept | Skill equivalent here |
|---|---|
| `orca worktree create --agent … --prompt …` | `/gitready`, then starting an agent in the new worktree |
| Per-repo setup script (fires on worktree creation) | `gitready/scripts/seed-worktree.sh`, run manually or from `/dowork`'s step 0 |
| A worktree's status card | The `TICKET` / `STATUS` lines each skill prints in its final summary |
| `orca worktree set --workspace-status completed` | The optional last step in `/ship` |
| `orca worktree rm` | `/gitclean` |
| `orca orchestration dispatch` (hand a task to another agent) | Filing a follow-up ticket with `/newticket` for a future `/dowork` pass |

### Setting up the same pattern without Orca

If you don't have Orca (or any worktree-orchestration tool) and just want the
underlying workflow — a ticket queue plus one-task-one-worktree discipline —
paste this into a fresh Claude Code session at the root of your repo:

```
Set up an agent-driven, ticket-based development workflow in this repo:

1. Create the z_tickets/ folder structure: open/, closed/, onhold/, examples/,
   with examples/_TEMPLATE.md containing a minimal ticket template (Title,
   Status, Context, Scope, Why now, Effort, Out of scope).
2. Copy the newticket, dowork, ship (or landtomain), gitready, and gitclean
   skills from https://github.com/TweekFawkes/prompts/tree/main/skills into
   .claude/skills/ in this repo, so they're available as slash commands here.
3. Adjust each SKILL.md's placeholders (branch naming convention, lint/test/
   deploy commands, remote) to match this project.
4. Check whether this project has any gitignored local state a fresh worktree
   would need to actually run (env files, local secrets, seeded config). If
   so, copy .claude/skills/gitready/scripts/worktree-seed-paths.example to
   .worktree-seed-paths at the repo root, fill in the real paths, and create
   a worktree to confirm .claude/skills/gitready/scripts/seed-worktree.sh
   copies them correctly. If there's nothing like that, skip this step.
5. Summarize the resulting loop back to me: /newticket <brief> to spec work,
   /gitready to hand it to an isolated worktree (seeding it per step 4 if
   configured), /dowork <ticket> to implement and verify it there, then /ship
   (or /landtomain) to land it and confirm the worktree is safe to delete.
```

Swap the repo URL for wherever you're hosting your own copy of these skills
(or paste the `SKILL.md` files directly if you're not fetching from GitHub).

## Notes

- These skills were genericized for public sharing; swap the placeholders for your
  own repo, branch convention, domains, and verification commands.
- They're written for Claude Code but the instructions are model-agnostic enough
  to adapt to other agent CLIs.
