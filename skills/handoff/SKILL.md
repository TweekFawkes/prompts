---
name: handoff
description: Compact the current conversation into a handoff document so a fresh agent can continue the work on this repo. Captures what was done, what's pending, key decisions, next steps, gotchas, and suggested skills to invoke next. Use when invoked as "/handoff" — optionally with a short description of what the next session will focus on.
argument-hint: "What will the next session be used for?"
---

# /handoff — Write a session handoff document

Write a handoff document summarising the current conversation so a fresh agent can continue the work.

## Ground the handoff in real repo state

Do not invent status. Before writing, collect the facts (run only what's relevant):

- `git status --short` and `git --no-pager log --oneline -10` — uncommitted changes and recent commits (use the real hashes).
- `git status -sb` — current branch and whether it's ahead of / behind its remote (i.e. whether commits are pushed).
- `ls z_tickets/open/` (ignore `.gitkeep` / dotfiles) — backlog tickets still open.
- Note any background tasks, deploys, or test runs from this session still in flight or left broken.

Use what you actually did this session as the spine, cross-checked against the state above so the doc matches reality. Be honest: if something failed, was skipped, or is uncertain, say so plainly.

## Save location

Save to the `z_handoff` directory (create it if it doesn't exist) with a file name of `YYYYMMDDHHMMSS-some_desc.md`. Get the timestamp from the `date +%Y%m%d%H%M%S` command — do not guess it. `some_desc` is a short kebab-case slug of the session's focus.

## Contents

Use Markdown, bullets over prose, skimmable. Cover:

- **Session summary** — 2-3 sentences on the focus.
- **Completed work** — finished tasks with concrete file paths and real commit hashes; note whether each is pushed.
- **Pending work** — prioritized checklist, including open `z_tickets/open/` tickets and any uncommitted working-tree changes.
- **Key decisions** — choices made and why, especially anything touching the architecture invariants in `CLAUDE.md`.
- **Next steps** — concrete, ordered actions for the next person.
- **Gotchas / warnings** — half-applied changes, stashes, flaky steps, env/deploy caveats, working-tree files intentionally left untouched.
- **Suggested skills** — which skills the next agent should invoke and when, drawn from your skill set, e.g.: `dowork` (run an open ticket end-to-end), `newticket` (draft a new backlog ticket), `openpr` (push the branch and open a PR), `gohome` (commit a worktree back to main and clean up).

Do not duplicate content already captured in other artifacts (tickets in `z_tickets/`, `tasks/lessons.md`, commits, diffs, PRs). Reference them by path or URL instead.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.

After writing, print a one-line confirmation with the file path.
