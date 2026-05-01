# Short, imperative title for the ticket

**Status:** Open.

**Context:** One paragraph that gives the AI agent (and a human reader)
enough background to know *why* this ticket exists. Where in the code is
the relevant logic today? What is the current behavior? What user-visible
problem does it cause? Link to the file / route / component if you can.

If the ticket is a bug, include a reproducible failure: the exact input,
the observed output, and the expected output. If it's a feature, describe
the smallest version that would feel "done".

**Scope:**

- Bullet list the concrete deliverables. Be specific enough that the
  agent can decide whether a change belongs in this ticket or in a new
  one. Examples:
- New route `POST /api/foo/bar` that accepts `{x: string}` and returns
  `{id: string}`.
- New table `foo_bar(id, user_id, created_at)`.
- Frontend: add a "Create Foo" button on `SettingsView.vue` that calls
  the new route and shows a toast on success.
- Tests: integration test covering the success and 400-on-empty cases.

**Why now:** One sentence. Are users blocked? Is this a parity gap with
a previous version? Is it a prerequisite for another ticket?

**Effort:** A rough size estimate (small / medium / large) so a reader
can decide whether to bundle this with another ticket or do it solo.

**Out of scope (optional):** Things the agent might be tempted to bundle
in but should NOT touch in this PR. List them so they don't drift in.
