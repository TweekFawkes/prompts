---
name: z_sort
description: Triage every open backlog ticket in z_tickets/open/ and sort each into z_tickets/open_agent/ (the agent can complete it end-to-end with no human help) or z_tickets/open_human/ (a human must do or unblock part of it). Reads each ticket, applies the project's gating rules (production is gated, dev/test/staging and read-only verification are not, external/dashboard-only actions need a human), verifies live state when a recent deploy or out-of-band change could have moved a ticket, then moves the files with git mv. Use when invoked as "/z_sort" or asked to "sort the open tickets into agent/human".
---

# /z_sort — Sort open tickets into agent-doable vs human-needed

You are triaging the backlog. For every open ticket, decide whether **the agent (you)** can carry it from start to finish with **zero help from a human**, and physically move the file into the matching folder.

- Sort, don't implement. This skill only classifies and moves files — it does NOT do the ticket work. (That's `/dowork`.)

## Authoritative paths

- Project root: the current working directory.
- Source: `z_tickets/open/*.md`
- Destinations: `z_tickets/open_agent/` and `z_tickets/open_human/`

Create both destination folders if missing (`mkdir -p`). Ignore files whose names start with `_` or `.`.

## The decision rule

A ticket goes to **`open_human`** if completing it (closing it fully, not just advancing it) requires **any** of the following — i.e. anything the agent cannot or must not do alone:

- **A production mutation.** Treat production as gated. Any prod deploy, prod DNS cutover, prod env/secret change, prod data change, or an "explicit user confirmation before prod" requirement → human. (Adjust to your project's policy — e.g. dev pre-authorized, test/staging not gated.)
- **An out-of-band / external party.** Anything that needs someone else to act — e.g. an API-key owner, a domain registrar, a third-party support desk, or a credential the agent doesn't hold.
- **A console/dashboard-only action with no API/CLI path.** E.g. a change that can only be made by clicking through a third-party web dashboard → must be done by a human.
- **An explicit human-approval gate** written into the ticket ("pause for user confirmation", "gated", "do not do autonomously"), or an irreversible/destructive step the ticket says to confirm first.
- **A judgment call reserved for the user** — a product/policy decision the ticket leaves open.

Otherwise the ticket goes to **`open_agent`**: the agent can do every remaining step alone. Things the agent CAN typically do without a human:

- Dev work of any kind, plus non-gated test/staging deploys and verification.
- Read-only inspection of environments (`curl`, `dig`, DB reads, log reads).
- Code changes, tests, lint/build, smoke tests, opening PRs.
- Local file/git operations, env-file hygiene on dev.

**Partial progress is not enough.** If a ticket is 90% done but the last step is gated (e.g. a final prod deploy), it still goes to `open_human` — the agent can't *close* it alone. When in doubt, prefer `open_human` and say why.

## Procedure

1. `mkdir -p z_tickets/open_agent z_tickets/open_human`.
2. List `z_tickets/open/*.md` (skip `_*`/`.*`). If none, print "no open tickets to sort" and stop.
3. Read `CLAUDE.md` and any project gating rules for the current policy, then read **each** ticket in full.
4. **Check for stale status.** Tickets often record their own blocker (e.g. "BLOCKED on a prod deploy of #91"). If a recent deploy or out-of-band change might have cleared that blocker, **verify live** before deciding — don't trust the ticket's stale note. Use read-only checks only:
   - `curl -sSI` for HTTP/redirect/cert state, `dig +short` for DNS,
   - a read-only query against the running service or database.
   Only spend verification effort where it could change the sort decision.
5. Decide `agent` or `human` per the rule above. Move with **`git mv`** to preserve history (tickets are tracked):
   ```
   git mv z_tickets/open/<file>.md z_tickets/open_agent/    # or open_human/
   ```
   A ticket already sitting in `open_agent`/`open_human` from a prior run may need to move *between* them if its status changed — handle that too.
6. Do NOT commit unless the user asks. Leave the moves staged.

## Report

Print a compact per-ticket table/summary: ticket → destination → one-line reason (the specific gate for a human, or "no gate, agent can finish" for the agent). Call out any ticket whose status **changed** since a prior sort (e.g. "was blocked on prod deploy; deploy shipped, now verified → moved to open_agent"). End with the counts in each folder and a reminder that nothing is committed.

## Notes / gotchas

- Worktree gitignored artifacts: seeded env files may be absent from a fresh worktree, so a ticket's env state may only be truthfully checkable on the canonical checkout or the deployed environment — note this rather than guessing.
- This skill is read-mostly: the only writes are `mkdir`, `git mv`, and verification commands that must stay read-only against production.
