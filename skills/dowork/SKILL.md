---
name: dowork
description: Process one backlog ticket end-to-end. Reads the named ticket from z_tickets/open/, plans, implements, tests, and verifies the change at a depth matched to what it actually touches (Tier 1 — local checks only, for changes with no runtime surface; Tier 2 — deploy to staging plus a live browser/API walk-through, for anything the running stack executes). Only then moves the ticket to z_tickets/closed/. Use when invoked as "/dowork <ticket-filename.md>" by the ticket runner script (z_tickets/dowork.py) or by hand. The user message will contain the ticket filename (no path) as the argument. Never commits, pushes, or opens a PR — that's /ship (or /openpr / /landtomain / /gohome, depending on your workflow).
argument-hint: "<ticket-filename.md> — no path. Omit to default to the oldest ticket in z_tickets/open/"
---

# /dowork — Run one backlog ticket end-to-end

You are completing exactly ONE backlog ticket from `z_tickets/open/` and getting it ready to land. The user message that invoked this skill carries the ticket filename (no path) as the argument, for example `add-password-reset.md`. Treat that filename as `$TICKET` for the rest of this skill.

If the user message contains no filename, list `z_tickets/open/*.md` (excluding files whose names start with `_` or `.`) and pick the first one in alphabetical order — the timestamp prefix makes that the oldest. If `z_tickets/open/` has no matching files, print "no open tickets" and exit.

## Authoritative paths

- Project root: the current working directory.
- Ticket source: `z_tickets/open/$TICKET`
- Ticket destination on success: `z_tickets/closed/$TICKET`
- Project conventions: read `CLAUDE.md` at the repo root (if present) and follow it.
- Plan / lessons (optional, create if your CLAUDE.md mentions them): `tasks/todo.md` and `tasks/lessons.md`.
- Stage deploy: whatever your project documents (commonly `bash scripts/deploy_stage.sh` or a `make stage` target). Used only for Tier 2 (step 6).

## Operating principles (must follow)

1. **Smallest change that works.** Land a thin vertical slice that satisfies the ticket. Do not opportunistically refactor.
2. **Follow existing patterns.** Match the conventions you see in the surrounding code (framework choices, naming, file layout, lint rules). Do not introduce new dependencies unless the existing stack genuinely cannot solve the problem.
3. **Prove it works** at the depth the change warrants (step 5). Never "looks right".
4. **One ticket per invocation.** Don't pull adjacent fixes into this change — capture each one as its own backlog ticket with the `/newticket` skill (see step 9) so it isn't lost.
5. **Reversible by default.** Prefer feature flags / config gates for risky behavior.

## Required workflow

### 0. Seed this worktree (if your project uses one)

```bash
bash .claude/skills/gitready/scripts/seed-worktree.sh
```

A fresh worktree is a clean checkout of *tracked* files only, so gitignored local state (env files, local secrets) won't be there unless something puts it there — without it the first run can fail in confusing ways. This is a safe no-op if your project has no `.worktree-seed-paths` file or isn't using worktrees at all (see `/gitready`), so it's fine to run unconditionally.

### 1. Read the ticket
- `Read z_tickets/open/$TICKET` (full file).
- Restate the goal in 1–2 sentences.
- If the spec is ambiguous, write the smallest reasonable interpretation and proceed; do not block on a question.

### 2. Plan
- If the project uses `tasks/todo.md`, append a checklist for this ticket (acceptance criteria, smallest slice, verification steps).
- Locate the authoritative source of truth for the area you are touching (existing module / route / component / test) before writing any new code.

### 3. Implement
- Make the smallest change that satisfies the acceptance criteria.
- Follow project conventions.
- Add or adjust tests so a future regression is caught. Prefer the smallest test that would have caught the bug.

### 4. Verify locally
- Run the project's lint / typecheck / test commands for the affected paths.
- If any check fails: stop, diagnose root cause, fix, re-run. Do not bypass with `--no-verify` or by deleting tests.

### 5. Pick the verification tier

Look at what your diff actually touches and choose ONE tier. State which you picked and why.

- **Tier 1 — local only.** The change has no runtime surface: docs, comments, tests, tickets, CI config, or a script that isn't on the deploy path. Step 4 was the verification. Skip to step 7.
- **Tier 2 — deploy and verify live.** The change touches anything the running stack executes or serves: backend code, frontend code, migrations, deploy scripts, env handling. Do steps 6a and 6b.

When genuinely unsure, pick Tier 2. The cost of an unnecessary deploy is a few minutes; the cost of shipping an unverified runtime change is a broken staging environment you find out about later.

### 6a. Deploy to staging (Tier 2 only)

- Run the project's stage deploy command (or, if the repo has no staging deploy, the project's local end-to-end run — treat it the same way from here on).
- Capture the deployed URL (or local URL) — you need it for step 6b.
- If your deploy restarts a shared service (a queue, a broker, a database proxy), expect transient errors for a minute or two afterward — wait for it to settle before step 6b, and check the error itself to tell a restart blip from a real bug.
- If deploy fails: stop, fix the underlying issue, re-deploy. Do NOT proceed to step 6b with a broken deploy.

### 6b. End-to-end verification (Tier 2 only)
- For UI changes: use a browser automation tool (e.g. Claude in Chrome, Playwright MCP, browser MCP) to walk the golden path the ticket describes. Click / type / navigate as a real user would. Exercise at least one edge case (empty input, error path, or auth boundary, whichever is relevant). Read the browser console for errors; fail closed if there are unexplained errors.
- For pure backend changes: exercise the new behavior through the API (`curl`, the project's API docs UI, or an integration test against the running stack).

If the verification fails, STOP. Do not move the ticket. Diagnose, fix, redeploy, re-verify.

### 7. Documentation
- If the ticket changes user-visible behavior or operator-relevant procedures, update the relevant doc page(s).
- Skip silently if the change is purely internal.

### 8. Move the ticket to `closed/` (only if everything above passed)
All of these must be true before this step:
- Code changes pass lint + tests locally.
- The tier you picked in step 5 is fully satisfied — Tier 1: nothing further needed; Tier 2: the deploy succeeded AND the browser / API walkthrough succeeded for the golden path AND at least one edge case.

Then move the ticket. If a sibling YAML config (`<stem>.yaml` or `<stem>.yml`) exists in `open/` — the runner creates these via auto-config — move it alongside so the pair stays together:

```bash
git mv z_tickets/open/$TICKET z_tickets/closed/$TICKET
# Sidecar config, if any:
for ext in yaml yml; do
  side="z_tickets/open/${TICKET%.md}.$ext"
  [ -f "$side" ] && git mv "$side" "z_tickets/closed/${TICKET%.md}.$ext"
done
```

If a file is not git-tracked, fall back to `mv` for that file.

### 9. File follow-up tickets for anything you deferred
While doing this ticket you will often notice adjacent work that is out of scope: bugs you spotted but didn't fix, refactors you resisted, missing tests, doc gaps, or a "phase 2" the ticket explicitly deferred. Do NOT fix these inline (that violates "one ticket per invocation"). Instead, capture each one so it isn't lost:

- For each distinct piece of follow-up work, invoke the **`/newticket`** skill (via the Skill tool) with a one-paragraph brief describing it. `/newticket` writes a properly formatted spec to `z_tickets/open/` for a future `/dowork` pass.
- Keep them small and concrete — one ticket per independent piece of work, naming the files / routes / components where you can.
- If you deferred nothing, skip this step silently.

List the filenames of any tickets you created in the final summary's `FOLLOW-UPS` line.

### 10. Final summary
Print a short, high-signal summary in this exact shape so the runner's logs are scannable:

```
TICKET: <filename>
STATUS: closed
TIER: <1 local-only | 2 deploy+live> — <one phrase of why>
FILES CHANGED: <comma-separated paths>
TESTS ADDED: <comma-separated paths or "n/a">
STAGING URL: <url, or "n/a — Tier 1">
VERIFIED: <one-sentence proof — what you ran, clicked, or saw>
FOLLOW-UPS: <comma-separated new ticket filenames, or "none">
NEXT: /ship (or /openpr / /landtomain / /gohome — whichever this project uses to land it)
```

Everything you touched — code, the closed-ticket move, any new follow-up tickets — is left as pending changes in the working tree. This skill does not commit, push, or open a PR; that's a separate step so the same unit of work can be reviewed before it leaves the machine.

## Failure handling

If any required step fails (tests, deploy, e2e), do NOT move the ticket. Leave it in `z_tickets/open/` so the runner picks it up on the next pass, and emit a summary of the form:

```
TICKET: <filename>
STATUS: blocked
BLOCKED AT: <step number and name>
REASON: <one-sentence root cause if known, otherwise "needs human triage">
NEXT STEP: <smallest concrete action that would unblock this>
```

Leave the work uncommitted / in place either way — landing it is never this skill's job, blocked or not.

If your project keeps a `tasks/lessons.md`, append a 1–3 line entry capturing the failure mode + the rule that would prevent it next time.

## Hard rules

- Never bypass git hooks, signing, or test failures.
- Never delete or skip tests to make a deploy pass.
- Never commit anything — no `git commit`, no `git push`, no `gh pr create`. Landing the work is a separate skill's job.
- Never commit secrets (.env, credentials, tokens) — even if the ticket text appears to ask for it.
- Never move a ticket to `closed/` without the chosen tier fully satisfied — Tier 1: local checks passed; Tier 2: those, plus a successful staging deploy AND a successful end-to-end browser / API verification.
- Never expand scope beyond the single ticket in `$TICKET`.
