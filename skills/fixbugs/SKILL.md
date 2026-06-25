---
name: fixbugs
description: Continuously auto-fix the bug reports that your test runner files into z_tickets/open_bugs/. Invoked as "/fixbugs" — starts a recurring loop (via the built-in `loop` skill) that scans z_tickets/open_bugs/ for *.md bug reports, fixes each one (smallest change that works), verifies it goes green by re-running the exact command in the report's Context, then moves it to z_tickets/closed/ and commits on a branch. Optional single argument is the interval in seconds (default 300). This is the consumer half of an auto-testing rotation; run it in a SEPARATE CLI session from the producer (whatever writes the bug reports) so the two sessions don't collide.
argument-hint: "[interval-seconds, default 300]"
---

# /fixbugs — auto-fix the bug reports filed by the auto-testing rotation

This is the standing wrapper for the `/loop` prompt that runs after each
auto-testing pass. Instead of pasting that long string by hand, the user runs
`/fixbugs` and the agent starts the same recurring fix loop.

## Context

- The PRODUCER is whatever writes bug reports — a test runner, a scheduled test
  rotation, or CI. It runs the test suite(s) and writes every failure as a
  `*.md` bug report into `z_tickets/open_bugs/` (each report's "Context" section
  names the exact command that reproduces the failure).
- This skill is the CONSUMER: it watches that directory and fixes the reports.
- Run `/fixbugs` in a **separate** CLI session from the producer so the two
  sessions don't fight over the same working tree / branch.

## What to do

1. Parse the argument after `/fixbugs` as `$INTERVAL` (integer seconds). If
   absent or invalid, use `300`. Enforce a floor of 60.

2. Invoke the built-in `loop` skill with exactly this prompt, substituting
   `$INTERVAL`:

   ```
   /loop --interval $INTERVAL Scan z_tickets/open_bugs/ for *.md bug reports (skip files starting with _ or .). For each bug, oldest first: read it, reproduce the failure using the exact command in its Context, find and fix the root cause (smallest change that works), then re-run that exact command to verify it is green. On success, move the file to z_tickets/closed/ and commit on a branch. If you cannot fix or reproduce it, leave the file in place, append a short "Investigation" note, and move on. If z_tickets/open_bugs/ is empty, do nothing this iteration.
   ```

3. Honor the project's guardrails while fixing: smallest change that works,
   never mix formatting with behavioral changes, never `--no-verify` without
   approval, and keep each fix on its own branch. Production is gated — do not
   deploy to prod as part of a fix without explicit approval.
