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
| [`newticket`](newticket/) | Plan and write ONE backlog ticket from a short brief into `z_tickets/open/`. Drafts the spec only — does not implement. |
| [`dowork`](dowork/) | Take ONE open ticket and ship it end-to-end: plan → implement → test → deploy to staging → verify in a real environment → move the ticket to `closed/`. |
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
/newticket <brief>   →   writes z_tickets/open/<timestamp>-<slug>.md
/dowork <ticket.md>  →   implements + verifies, moves it to closed/, then calls…
/openpr              →   pushes the branch and opens a PR into main
```

`z_sort` and `fixbugs` run alongside as triage/repair loops. The git skills
(`gitready` → work → `gohome` / `openpr` / `landtomain` → `gitclean`) manage the
worktree lifecycle around all of it.

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

## Notes

- These skills were genericized for public sharing; swap the placeholders for your
  own repo, branch convention, domains, and verification commands.
- They're written for Claude Code but the instructions are model-agnostic enough
  to adapt to other agent CLIs.
