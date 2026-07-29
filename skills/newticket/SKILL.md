---
name: newticket
description: Plan and write one new backlog ticket from a short brief. Refreshes the checkout against the latest main, gathers project context (CLAUDE.md, existing tickets, the relevant area of the codebase), and writes a complete, well-formatted Markdown ticket to z_tickets/open/<YYYYMMDDHHMMSS>-<slug>.md following the convention in z_tickets/examples/_TEMPLATE.md. Use when invoked as "/newticket <brief>" — a one-liner or paragraph describing the work to be done. Pass --spec-only to write the ticket and stop, leaving it in the backlog for a later /dowork pass — otherwise it hands the ticket straight to a fresh worktree via /gitready. The skill drafts the spec only; it does NOT implement the work (that's the /dowork skill).
argument-hint: "<brief> — one line or a paragraph describing the work; add --spec-only to skip launching a worktree"
---

# /newticket — Author one new backlog ticket

Run this in your **main checkout** (the one where `main` is checked out), before creating a worktree for the work.

You are creating exactly ONE new ticket file in `z_tickets/open/` based on the brief in the user message that invoked this skill. Treat that brief as `$BRIEF` for the rest of this skill.

If the user message contains no brief, ask the user for one and stop. A brief can be one line or a few paragraphs — both are fine.

Use `--spec-only` when the ticket is genuinely being *deferred* — backlog for later, not work to start now.

## Authoritative paths

- Project root: the current working directory.
- Open tickets (your destination): `z_tickets/open/`
- Closed tickets (for naming + tone reference): `z_tickets/closed/`
- Onhold tickets (also reserved): `z_tickets/onhold/`
- Ticket template: `z_tickets/examples/_TEMPLATE.md`
- Project conventions: read `CLAUDE.md` at the repo root if present, and follow it.

## Operating principles (must follow)

1. **Plan, don't implement.** Your only output is a single Markdown file describing the work. No code edits. No tests. No commits. The `/dowork` skill does the implementation later.
2. **Smallest scope that makes sense.** A ticket should be roughly one PR's worth of work. If `$BRIEF` describes more than that, write the smallest first slice and note follow-ups in "Out of scope".
3. **Concrete over vague.** The "Scope" section should name files / routes / components / tests where you can. Vague tickets produce speculative diffs.
4. **Match the project's existing style.** Glance at 2-3 closed tickets to calibrate tone, length, and section conventions before drafting.
5. **One ticket per invocation.** If `$BRIEF` covers two unrelated pieces of work, pick the one the user clearly meant first and write only that. Mention the second as a TODO in your final summary so the human can re-invoke.

## Required workflow

### 1. Refresh the checkout to the latest main

The spec must be written against current code, so bring the checkout up to date first:

```bash
git status --short
git branch --show-current
git fetch origin
git pull --ff-only origin main
git status
```

- Expect `Your branch is up to date with 'origin/main'.` — report the resulting state.
- If the branch is **not** `main`, or the tree is dirty, or the fast-forward pull refuses: do **not** stash, reset, or force anything. Say exactly what you found, note that the ticket is being written against possibly-stale code, and continue to step 2.

### 2. Read the brief
- The user message contains `$BRIEF`.
- Restate the goal in one sentence in your own words. If the goal is genuinely ambiguous in a way that would substantially change the resulting ticket, ask ONE clarifying question and stop. Otherwise pick the smallest reasonable interpretation and proceed.

### 3. Gather context
- Read `CLAUDE.md` at the repo root if it exists.
- Read `z_tickets/examples/_TEMPLATE.md` once to confirm the section order.
- List `z_tickets/open/`, `z_tickets/closed/`, and `z_tickets/onhold/` to (a) avoid filename collisions and (b) match the project's slug style.
- Read 1–2 closed tickets in full to calibrate tone and length.
- Locate the relevant code: search the repo for the files / routes / components mentioned in or implied by `$BRIEF`, so you can name them concretely in Context and Scope.

### 4. Pick a slug
Format: short, lower-case, hyphenated, descriptive. Match the project's existing pattern (look at filenames in `closed/`).

- ✓ `add-password-reset.md`, `fix-tagged-emails-on-login.md`, `bump-pillow-to-11.md`, `migrate-themes-to-3x.md`
- ✗ `Ticket #4214.md`, `feature.md`, `my-todo.md`, `URGENT_FIX.md`
- A leading verb usually helps: `add-`, `fix-`, `remove-`, `bump-`, `migrate-`, `wire-`, `rename-`.
- If a ticket with the same slug already exists anywhere under `z_tickets/{open,closed,onhold}/` (ignore any leading numeric or timestamp prefix when comparing), pick a different one. Do NOT overwrite or revive someone else's ticket.

Pick the **slug only** in this step — the descriptive part shown above. The actual on-disk filename is formed in step 6 by prepending a creation timestamp.

### 5. Draft the ticket
Use the section order from `examples/_TEMPLATE.md`:

- **Title (H1)** — one short imperative sentence.
- **Status:** start with `Open.` plus a 3–6 word qualifier (`Open. User-reported on stage.`, `Open. Chore — dep hygiene.`).
- **Context:** one paragraph giving a future agent (and a human reviewer) enough background to know *why* this ticket exists. What's the current behavior, what user-visible problem does it cause, and where in the code is the relevant logic today? Name files / routes / components when you can.
- **Repro:** (bugs only) numbered steps, observed vs. expected.
- **Scope:** bullet list of concrete deliverables. Be specific enough that the agent can decide whether a change belongs in this ticket or a new one.
- **Why now:** one sentence on motivation — users blocked, parity gap, prerequisite for another ticket, etc.
- **Effort:** `small` / `medium` / `large` with one phrase of justification.
- **Out of scope:** things the agent might be tempted to bundle in but should NOT touch in this PR.

Length target: around the size of `examples/example-bugfix.md` or `examples/example-feature.md`. Don't pad with filler.

### 6. Stamp the filename and write it
The on-disk filename is the slug with a **creation timestamp prepended**, in `YYYYMMDDHHMMSS` format:

`z_tickets/open/<YYYYMMDDHHMMSS>-<slug>.md`  →  e.g. `z_tickets/open/20260601143022-add-password-reset.md`

1. Get the timestamp by running this exact command — do NOT guess or hand-compute the time:

   ```bash
   date +%Y%m%d%H%M%S
   ```

   It prints 14 digits. (Set `TZ` if you want a fixed timezone, e.g. `TZ='UTC' date +%Y%m%d%H%M%S`.)
2. Use the Write tool to create `z_tickets/open/<TIMESTAMP>-<slug>.md`, where `<TIMESTAMP>` is that command's exact output. Do NOT modify any other files. Do NOT stage or commit anything — leave that to `/dowork` / `/ship`.

### 7. Hand it to a worktree (skip if `--spec-only`)

Don't leave the ticket sitting in the backlog if the intent was to start now. Create an isolated worktree for it and kick off `/dowork` there, so no one has to switch directories and type the command by hand.

If your project uses a worktree-orchestration tool (see the [Orca section](../README.md#running-this-with-orca-or-a-similar-worktree-ide) in this repo's README) that can create a worktree AND launch an agent in one call, prefer that — it also gives the new session a visible place to report progress. Otherwise, invoke the **`/gitready`** skill (via the Skill tool) with the slug from step 4 to create the worktree, then start (or ask the user to start) a fresh agent session there with `/dowork <YYYYMMDDHHMMSS>-<slug>.md`.

Either way, the new worktree is a fresh checkout, so it will **not** contain the ticket file you just wrote — that file lives only in your main checkout until it's committed. Copy it over before the next agent needs it:

```bash
mkdir -p "<worktree-path>/z_tickets/open"
cp z_tickets/open/<filename> "<worktree-path>/z_tickets/open/<filename>"
```

Report the worktree path and branch. If worktree creation fails for any reason, don't retry blind — say so and tell the user the ticket is already written and safe; they can create a worktree and run `/dowork <filename>` themselves whenever they're ready.

### 8. Final summary
Print a short, high-signal summary in this exact shape so a runner / reviewer can grep it:

```
MAIN: <up to date with origin/main | the exact problem found in step 1>
TICKET CREATED: z_tickets/open/<YYYYMMDDHHMMSS>-<slug>.md
TITLE: <H1 of the ticket>
EFFORT: <small | medium | large>
SCOPE BULLETS: <count>
CONTEXT FILES NAMED: <comma-separated paths, or "none">
WORKTREE: <path> on branch <branch>, /dowork started
           (or "not created — --spec-only" / the exact failure)
NEXT: <nothing — the agent is working | run /dowork <filename> in a worktree>
```

If `$BRIEF` covered more than one unit of work, append a single line:

```
DEFERRED: <one sentence describing the second piece, suggesting the user re-invoke /newticket for it>
```

## Hard rules

- In your main checkout, never modify anything except the one new file in `z_tickets/open/`. (Creating a worktree in step 7 is expected; writing the ticket copy into that worktree is expected.)
- Never overwrite an existing ticket file in `open/`, `closed/`, or `onhold/`.
- Never include secrets, tokens, production URLs containing keys, or credentials in the ticket — even if `$BRIEF` mentions them. Sanitize first or refuse and ask the user to redact.
- Never add YAML frontmatter or a sibling `.yaml` config block unless `$BRIEF` explicitly asks for it (e.g. "use sonnet for this one"). The runner has its own auto-detect path that handles per-ticket config; pre-empting it just creates merge noise.
- Never start the work itself. Writing the spec is the entire job.
