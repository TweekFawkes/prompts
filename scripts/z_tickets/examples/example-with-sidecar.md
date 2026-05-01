# Add a `--version` flag to the `tools/migrate.py` CLI

**Status:** Open. Chore — operator quality-of-life.

**Context:** `tools/migrate.py` is the project's database migration
runner. Operators frequently need to confirm which build of the script
they're running before pointing it at production. Right now there's no
way to do that without reading the source — `migrate.py --help` lists
every subcommand but says nothing about the version.

We tag releases as `migrate-vYYYYMMDD` and embed the same string in
`tools/migrate/_version.py` (`__version__ = "..."`). The CLI uses
`argparse` and the entry point is `main()` at the bottom of the file.

**Scope:**
- Add a `--version` action to the top-level `argparse.ArgumentParser`
  in `tools/migrate.py` that prints `__version__` and exits 0.
- Update `tools/migrate/README.md` to mention the flag in the "Common
  invocations" table.
- Add a unit test in `tests/tools/test_migrate_cli.py` asserting
  `migrate.py --version` exits 0 and the stdout matches the version
  string.

**Why now:** Tiny, but it comes up in every prod-touching ops thread
and is trivially correct.

**Effort:** Tiny.

**Out of scope:** Don't refactor the rest of the CLI. Don't switch to
`click` or `typer`. Don't change how versions are tagged.

---

**Why this ticket has a sidecar `.yaml`:** The change is mechanical, the
codebase is small, and there's no UI to drive — Haiku at low effort can
finish this in a fraction of the cost. Rather than clutter the ticket
body with frontmatter, the per-ticket overrides live in
`example-with-sidecar.yaml` next to this file. See README §"Per-ticket
overrides".
