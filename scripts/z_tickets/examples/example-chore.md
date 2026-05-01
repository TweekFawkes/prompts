# Replace deprecated `@foo/legacy-themes` package with `@foo/themes`

**Status:** Open. Chore — dependency hygiene.

**Context:** `@foo/legacy-themes@2.x` was renamed to `@foo/themes@3.x`
and the old package is now in maintenance-only mode. We're getting a
deprecation warning on every `npm install`. The migration is a
mechanical name change plus one renamed export
(`createPreset` → `definePreset`).

**Scope:**
- `frontend/package.json`: remove `@foo/legacy-themes`, add
  `@foo/themes` at the latest 3.x.
- Update the two import sites:
  - `frontend/src/main.js`
  - `frontend/src/themes/custom.js`
- Run `npm install` and `npm run build` to confirm the build still
  succeeds.
- No behavior change should be visible — the rendered theme should look
  identical before and after.

**Why now:** Routine deploy is the cheapest moment to do this. Doing it
now also unblocks a future ticket that needs an API only present in 3.x.

**Effort:** Tiny. One package swap, two import updates.

**Out of scope:** No theme refactors, no design changes. Just the
rename.
