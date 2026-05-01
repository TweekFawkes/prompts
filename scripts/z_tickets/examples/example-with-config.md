---
# Per-ticket overrides for run_tickets.py — see README §"Per-ticket overrides".
# Everything here is optional. Delete this whole block to fall back to
# SDK_OPTIONS_BASE.
model: sonnet
fallback_model: haiku
effort: low
---

# Bump copyright year in the public site footer

**Status:** Open. Chore — annual maintenance.

**Context:** `frontend/src/components/SiteFooter.vue` hard-codes the
copyright year as `2025`. We just rolled into the new year and the
footer is visibly out of date on every public page.

**Scope:**
- Replace the literal `2025` in `SiteFooter.vue` with a small computed
  that reads `new Date().getFullYear()`.
- Update the snapshot test in
  `frontend/tests/components/SiteFooter.spec.ts` to assert the current
  year rather than a hard-coded value.
- Verify on staging that the rendered footer shows the right year.

**Why now:** Tiny but user-visible — we look sloppy until it's fixed.

**Effort:** Tiny. One component, one test, one assertion.

**Out of scope:** Don't redesign the footer. Don't extract a shared
`<CopyrightLine>` component "while we're in there".

---

**Why this ticket carries config:** This change is mechanical, low-risk,
and nowhere near worth Opus + max effort. The frontmatter at the top of
this file tells the runner to use Sonnet on low effort for this one
ticket. Same effect, much cheaper. The README documents the full set of
overrides.
