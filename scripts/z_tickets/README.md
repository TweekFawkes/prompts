# z_tickets — autonomous backlog runner for Claude Code

A tiny system for letting [Claude Code](https://docs.claude.com/en/docs/claude-code/overview)
work through your backlog one ticket at a time, without you babysitting it.

You drop one Markdown file per task into `z_tickets/open/`. A small runner
loops over those files, spawns a Claude Code sub-agent for each, and lets
the `/dowork` skill drive the ticket end-to-end: read the spec, plan,
implement, run tests, deploy to staging, verify in a real browser or via
the API, and only then move the ticket to `z_tickets/closed/`. If anything
fails the ticket stays in `open/` and the runner picks it up on the next
pass.

It is opinionated about one thing: **a ticket isn't done until it's been
verified end-to-end on a running system**. Not "tests pass". Not "looks
right". An actual click-through or API call against a deployed environment.

---

## What's in this folder

```
z_tickets/
├── README.md                      ← you are here
├── run_tickets.py                 ← the loop (Python, claude-agent-sdk)
├── run_tickets.sh                 ← convenience wrapper (uv run …)
├── stop.sh                        ← graceful halt: touches STOP file
├── .gitignore                     ← logs/, STOP, .DS_Store
│
├── .claude/
│   └── skills/
│       └── dowork/
│           └── SKILL.md           ← the per-ticket skill
│
├── open/                          ← drop your tickets here
├── closed/                        ← skill moves them here on success
├── onhold/                        ← optional: things you've parked
├── logs/                          ← runner + per-ticket logs (gitignored)
└── examples/                      ← four templates to copy from
    ├── _TEMPLATE.md
    ├── example-bugfix.md
    ├── example-feature.md
    └── example-chore.md
```

---

## Quick start

### Prerequisites

- **Python ≥ 3.11**
- **[uv](https://docs.astral.sh/uv/)** — manages the Python environment
  for `run_tickets.py` automatically (the script is PEP 723, so `uv run`
  resolves `claude-agent-sdk` for you; you never `pip install` anything).
- **The `claude` CLI** — installed and logged in
  ([install Claude Code](https://docs.claude.com/en/docs/claude-code/setup)).
- **Your project's local toolchain** — whatever your tests, linter, and
  staging deploy need (Node, Python, Docker, …). The runner doesn't know
  or care; it just hands the ticket to Claude.

### 1. Drop the system into your repo

Copy this entire `z_tickets/` directory into the root of your project:

```
your-repo/
├── .claude/                       ← merge with yours if it exists
│   └── skills/
│       └── dowork/
│           └── SKILL.md
├── z_tickets/
│   ├── run_tickets.py
│   ├── ...
│   └── open/
└── (your code)
```

The skill file lives at `.claude/skills/dowork/SKILL.md`. Claude Code
auto-discovers project skills from that path — nothing else to configure.

### 2. Write a ticket

Copy `examples/_TEMPLATE.md` (or one of the example files) into
`open/your-ticket-name.md` and fill it in. Keep it focused — one ticket
should be one PR's worth of work. See [Ticket format](#ticket-format)
below for the convention the skill expects.

### 3. Run the loop

```bash
./z_tickets/run_tickets.sh
```

You'll see a banner per ticket and a stream of timestamped events. The
runner:

- picks the alphabetically first file in `open/` (skipping `_*.md` and
  hidden files),
- spawns a Claude Code sub-agent with the prompt `skill /dowork
  <filename>`,
- streams every assistant message, tool call, tool result, and the
  final usage / cost summary,
- when that ticket finishes, sleeps 120 s and starts the next one,
- exits when `open/` is empty or you ask it to stop.

### 4. Stop it gracefully

```bash
./z_tickets/stop.sh
```

That just `touch`es a `STOP` file inside `z_tickets/`. The runner checks
between tickets and during sleep ticks, so it'll exit cleanly after the
current ticket finishes. Delete the file when you're ready to run again.

---

## Ticket format

A ticket is a Markdown file in `z_tickets/open/`. The filename becomes
the ticket ID — keep it short, lower-case, hyphenated, and descriptive
(`add-password-reset.md`, not `Ticket #4214.md`).

The skill is permissive about the *content* — Claude reads the file in
full and does whatever it says — but the four sections in
`examples/_TEMPLATE.md` are what we've found works:

- **Title (H1)** — one short imperative sentence.
- **Status** — `Open`, `Blocked`, etc. The skill only acts on files in
  `open/`, so this is mostly for humans.
- **Context** — why this ticket exists, what the current behavior is,
  where the relevant code lives. The agent uses this to decide what to
  read first.
- **Scope** — concrete deliverables. The more specific you are, the
  smaller the diff Claude produces. Vague scope → speculative changes.
- **Why now / Effort / Out of scope** — optional but useful for the
  agent to decide whether to expand or contract.

Files starting with `_` (e.g. `_priority.md`) and `.` are ignored by
the runner, so you can keep notes alongside the active backlog.

---

## How `/dowork` works

`/dowork` is a [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills)
defined in `.claude/skills/dowork/SKILL.md`. The skill instructs the
sub-agent to:

1. **Read** `z_tickets/open/$TICKET` and any project-level `CLAUDE.md`.
2. **Plan** — locate the existing code, append a checklist to
   `tasks/todo.md` if your project uses one.
3. **Implement** the smallest change that satisfies the scope.
4. **Verify locally** — lint / typecheck / tests for affected paths.
5. **Deploy to staging** (or run end-to-end locally if you have no
   staging environment).
6. **Verify end-to-end** with a browser MCP (Playwright, Claude in
   Chrome) or an API call. **This step is mandatory.** A ticket is not
   "done" until it's been exercised against a running system.
7. **Update docs** if the change is user-visible.
8. **`git mv` the ticket** from `open/` to `closed/` only if every step
   above passed.
9. **Print a structured summary** the runner's logs can grep for:
   ```
   TICKET: my-ticket.md
   STATUS: closed
   FILES CHANGED: src/foo.py, tests/test_foo.py
   TESTS ADDED: tests/test_foo.py
   STAGING URL: https://stage.example.com
   VERIFIED: clicked "Save", saw 200 + green toast
   ```

If anything fails (tests, deploy, e2e), the ticket stays in `open/` and
the agent emits a `STATUS: blocked` summary instead. The runner picks
it back up on the next pass — you can either fix the blocker manually
and re-run, or read the per-ticket log to see what got stuck.

The skill is intentionally generic. It assumes your repo has:

- a project-level `CLAUDE.md` (recommended but optional),
- *some* staging deploy command,
- *some* test command,
- *some* way to exercise the change (browser or API).

If your project has very different conventions, adjust the `Required
workflow` section of `SKILL.md` — it's just Markdown.

---

## Logs

Three files per run, all in `z_tickets/logs/` (gitignored):

| File | What's in it |
|---|---|
| `runner-<start-ts>.log` | Everything the runner prints to stdout. Top-level view of the whole session. |
| `ticket-<stem>-<run-ts>.log` | Human-readable, per-ticket: prompts, tool calls, tool results, final usage. |
| `ticket-<stem>-<run-ts>.jsonl` | Raw event dump from the SDK, one JSON object per line. Use this for forensics or replay. |

Timestamps are local time, format `YYYYMMDDHHMMSS`. The `.jsonl` file is
the source of truth — the human-readable log truncates long tool inputs
and outputs (configurable in `run_tickets.py`).

---

## Configuration

Defaults live at the top of `run_tickets.py`:

```python
SLEEP_SECONDS = 120          # gap between tickets
SLEEP_TICK_SECONDS = 30      # heartbeat during sleep

SDK_OPTIONS_BASE = dict(
    permission_mode="bypassPermissions",   # unattended runs
    model="opus",
    fallback_model="sonnet",
    cwd=str(PROJECT_ROOT),
    setting_sources=["user", "project", "local"],
    extra_args={
        "chrome": None,                    # --chrome (Claude in Chrome)
        "effort": "max",                   # --effort max
    },
)
```

A few worth knowing:

- `permission_mode="bypassPermissions"` lets the sub-agent run tools
  without per-call confirmation. **Only use this on a repo you
  trust.** Drop it (or set it to `"default"`) if you want to approve
  each tool call interactively.
- `model` / `fallback_model` map to `--model` / `--fallback-model`.
- `extra_args["chrome"] = None` enables the [Claude in Chrome](https://docs.claude.com/en/docs/claude-code/chrome)
  integration so the sub-agent can drive a browser for step 6. Remove
  the key if you don't have it installed; the skill will fall back to
  Playwright MCP / API checks.
- `setting_sources=["user", "project", "local"]` makes the sub-agent
  inherit your CLI settings, project `.claude/settings.json`, and
  local overrides — including your MCP servers. That's how the skill
  finds Playwright, browser tools, etc.

---

## Limits and gotchas

- **It costs real money.** Each ticket is a full Claude Code session,
  often dozens of tool calls. The per-ticket `RESULT` line in the logs
  shows the exact spend. Watch the first few runs and tune ticket
  scope accordingly — small, specific tickets are cheap; vague ones
  burn cache.
- **One ticket at a time.** The runner is sequential by design.
  Parallel runs would race on git state and on the staging
  environment.
- **The runner trusts the skill.** If the skill says "I closed this
  ticket", the runner believes it. The only thing the runner checks
  is whether the file is still in `open/` afterwards. Spot-check the
  first few runs.
- **Staging is required (or at least, *something* runnable).** Step 6
  of the skill is non-negotiable — a ticket is not closed until the
  change has been exercised against a running system. If your project
  has no staging environment, point the agent at a local end-to-end
  run instead (see `SKILL.md` step 5).
- **Don't put secrets in tickets.** The full ticket file ends up in
  the agent's context and in the `.jsonl` log on disk. Treat
  `z_tickets/open/` like any other source file.

---

## Customizing

The system is small on purpose. The pieces you'll most likely change:

| File | Why you'd edit it |
|---|---|
| `.claude/skills/dowork/SKILL.md` | Your project has unusual conventions (custom deploy command, no staging, different test runner). Adjust the `Required workflow` section. |
| `run_tickets.py` (`SDK_OPTIONS_BASE`) | Switch model, drop `bypassPermissions`, add MCP servers via `extra_args`. |
| `run_tickets.py` (`SLEEP_SECONDS`) | Tighter or looser pacing between tickets. |
| `examples/_TEMPLATE.md` | Match your team's preferred ticket shape. |

If you want the skill to **always** pull tickets from a folder other
than `z_tickets/open/`, change the path in `SKILL.md` (it's mentioned
in two places: the description and the Authoritative paths section).

---

## Why this exists

Backlog grooming is the part of the job most worth automating: lots of
small tickets, each well-specified, each done the same way. The
expensive part of getting an LLM to do real work isn't the model — it's
the workflow scaffolding around it: knowing when to stop, how to
verify, how to give up gracefully, and how to leave a clear trail for
the human reviewing later.

`z_tickets` is that scaffolding, in about 500 lines of Python and a
single SKILL.md. Use it, fork it, gut it — whatever fits your project.

---

## License

MIT. See the repo root for the full text.
