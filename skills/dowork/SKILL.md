---
name: dowork
description: Process one backlog ticket end-to-end. Reads the named ticket from z_tickets/open/, plans, implements, tests, deploys to staging, verifies the change in a real environment (browser or API), and only then moves the ticket to z_tickets/closed/. Use when invoked as "/dowork <ticket-filename.md>" by the ticket runner script (z_tickets/dowork.py) or by hand. The user message will contain the ticket filename (no path) as the argument.
---

# /dowork — Run one backlog ticket end-to-end

You are completing exactly ONE backlog ticket from `z_tickets/open/` and shipping it. The user message that invoked this skill carries the ticket filename (no path) as the argument, for example `add-password-reset.md`. Treat that filename as `$TICKET` for the rest of this skill.

If the user message contains no filename, list `z_tickets/open/*.md` (excluding files whose names start with `_` or `.`) and pick the first one in alphabetical order. If `z_tickets/open/` has no matching files, print "no open tickets" and exit.

## Authoritative paths

- Project root: the current working directory.
- Ticket source: `z_tickets/open/$TICKET`
- Ticket destination on success: `z_tickets/closed/$TICKET`
- Project conventions: read `CLAUDE.md` at the repo root (if present) and follow it.
- Plan / lessons (optional, create if your CLAUDE.md mentions them): `tasks/todo.md` and `tasks/lessons.md`.
- Stage deploy: whatever your project documents (commonly `bash scripts/deploy_stage.sh` or a `make stage` target). If the repo has no staging deploy, run the project's local end-to-end test command instead and treat it as the verification step.

## Operating principles (must follow)

1. **Smallest change that works.** Land a thin vertical slice that satisfies the ticket. Do not opportunistically refactor.
2. **Follow existing patterns.** Match the conventions you see in the surrounding code (framework choices, naming, file layout, lint rules). Do not introduce new dependencies unless the existing stack genuinely cannot solve the problem.
3. **Prove it works.** Tests, lint, build, and a real walk-through of the change — not "looks right".
4. **One ticket per invocation.** Don't pull adjacent fixes into this change — capture each one as its own backlog ticket with the `/newticket` skill (see step 9) so it isn't lost.
5. **Reversible by default.** Prefer feature flags / config gates for risky behavior.

## Required workflow

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

### 5. Deploy to staging (or run end-to-end locally)
- Run the project's stage deploy command.
- Capture the deployed URL (or local URL, if running locally) — you need it for step 6.
- If deploy fails: stop, fix the underlying issue, re-deploy. Do NOT proceed to step 6 with a broken deploy.

### 6. End-to-end verification
This step is mandatory.
- For UI changes: use a browser automation tool (e.g. Claude in Chrome, Playwright MCP, browser MCP) to walk the golden path the ticket describes. Click / type / navigate as a real user would. Exercise at least one edge case (empty input, error path, or auth boundary, whichever is relevant). Read the browser console for errors; fail closed if there are unexplained errors.
- For pure backend changes: exercise the new behavior through the API (`curl`, the project's API docs UI, or an integration test against the running stack).

If the verification fails, STOP. Do not move the ticket. Diagnose, fix, redeploy, re-verify.

### 7. Documentation
- If the ticket changes user-visible behavior or operator-relevant procedures, update the relevant doc page(s).
- Skip silently if the change is purely internal.

### 8. Move the ticket to `closed/` (only if everything above passed)
All of these must be true before this step:
- Code changes pass lint + tests locally.
- Stage deploy / local end-to-end run completed successfully.
- The browser / API walkthrough succeeded for the golden path AND at least one edge case.

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
FILES CHANGED: <comma-separated paths>
TESTS ADDED: <comma-separated paths or "n/a">
STAGING URL: <url>
VERIFIED: <one-sentence proof — what you clicked / what you saw>
FOLLOW-UPS: <comma-separated new ticket filenames, or "none">
```

### 11. Open a PR to save the work (final step — only on success)
Once the ticket is moved to `closed/`, any follow-up tickets are filed, and the summary is printed, persist everything by invoking the **`/openpr`** skill (via the Skill tool). That skill commits the worktree's pending changes (code, the closed-ticket move, and any new follow-up tickets), pushes the feature branch to `origin`, and opens or refreshes a pull request targeting `main` on github.com so the change can be merged back to the local laptop's `main` and the remote repo.

- Run this **only on the success path** (ticket closed and verified). If the ticket ended up **blocked**, do NOT open a PR — leave the work in place for the next pass.
- Let `/openpr` handle the commit message and PR body; don't hand-commit first.

## Failure handling

If any required step fails (tests, deploy, e2e), do NOT move the ticket. Leave it in `z_tickets/open/` so the runner picks it up on the next pass, and emit a summary of the form:

```
TICKET: <filename>
STATUS: blocked
BLOCKED AT: <step number and name>
REASON: <one-sentence root cause if known, otherwise "needs human triage">
NEXT STEP: <smallest concrete action that would unblock this>
```

Do NOT invoke `/openpr` on the blocked path — leave the work uncommitted/in place so the next pass can resume it.

If your project keeps a `tasks/lessons.md`, append a 1–3 line entry capturing the failure mode + the rule that would prevent it next time.

## Hard rules

- Never bypass git hooks, signing, or test failures.
- Never delete or skip tests to make a deploy pass.
- Never commit secrets (.env, credentials, tokens) — even if the ticket text appears to ask for it.
- Never move a ticket to `closed/` without a successful staging deploy (or local end-to-end) AND a successful end-to-end browser / API verification.
- Never expand scope beyond the single ticket in `$TICKET`.
