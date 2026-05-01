# Add "Copy link" button to shareable report pages

**Status:** Open. New feature.

**Context:** Reports rendered at `/reports/{id}` are publicly viewable
once the owner toggles `is_public=true`, but there's no easy way for a
viewer or owner to copy the canonical link. Today users right-click the
address bar or share the wrong URL (often a deep link with internal
query params).

We want a small, unobtrusive "Copy link" button in the report header
that copies a clean canonical URL (`https://<host>/reports/{id}`, no
query string) and shows a toast confirming the copy.

**Scope:**
- Frontend (`frontend/src/views/ReportView.vue`): add a button next to
  the report title using the project's existing icon-button pattern.
  On click, call `navigator.clipboard.writeText(canonicalUrl)` and show
  a toast ("Link copied").
- The canonical URL is derived from `window.location.origin` plus the
  route, with no query/hash. Compute it once on mount.
- Hide the button when the report is not public (no point in copying a
  link that only the owner can open).
- Tests: a small component test that mounts ReportView with a mocked
  clipboard and asserts `writeText` was called with the right URL.

**Why now:** Sales team is sharing report links manually for demos and
losing prospects to copy-paste mistakes.

**Effort:** Small — one component change, one test.

**Out of scope:** No QR codes, no share-to-X buttons, no shortened
URLs. Just clipboard.
