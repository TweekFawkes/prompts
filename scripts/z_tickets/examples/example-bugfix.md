# Login form rejects valid email addresses with a `+` tag

**Status:** Open. User-reported on stage.

**Context:** Users with Gmail-style tagged addresses (e.g.
`alice+work@example.com`) are seeing the login form reject their email
with "Invalid email format" before the request is even sent. The bug is
client-side only — the same address authenticates fine if the form is
bypassed and the request is made directly. The relevant validation is in
`frontend/src/views/LoginView.vue`, in the `validateEmail` computed.

The current regex disallows `+` in the local-part:
`/^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/`. RFC 5321 permits `+`
(among other chars) in the local-part, and Gmail relies on it heavily for
filtering.

**Repro:**
1. Open `/login` on stage.
2. Type `alice+work@example.com` in the email field.
3. Tab out — the field shows "Invalid email format" and the Submit
   button stays disabled.

**Scope:**
- Replace the inline regex with a permissive validator (allow `+`,
  multiple dots in local-part, longer TLDs). Either widen the regex or
  use a small library like `validator.isEmail`.
- Add a unit test in `frontend/tests/views/LoginView.spec.ts` that
  asserts `alice+work@example.com` is accepted and `not-an-email` is
  rejected.
- Server-side validation in `backend/app/auth.py` should already pass
  these addresses; verify and add a regression test if it doesn't.

**Why now:** Bounce rate on `/login` jumped 8% this week and Gmail-tag
users are the top complaint in support inbox.

**Effort:** Small — one file each side, two tests.

**Out of scope:** Don't refactor the rest of the LoginView form
validation. Don't migrate to a form library.
