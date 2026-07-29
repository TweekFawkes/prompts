# prompts

A curated, personal library of reusable material for **AI coding agents** —
agent guidelines, ready-to-adapt context blocks, per-technology stack notes,
vendor prompting guides, Claude Code skills, and a few utility scripts.

It's documentation-first: most of it is Markdown you copy into a project (or into
an agent's context) and adapt. Files use `snake_case` names and, where useful,
lightweight XML-tagged context blocks.

## What's here

| Directory | Contents |
|---|---|
| [`claude_md/`](claude_md/) | A flagship "AI Coding Agent Guidelines" doc (`claude.md`) plus Claude Code config templates (`settings.json_*` permission sets, `zshrc_*` aliases). |
| [`skills/`](skills/) | Twelve [Claude Code](https://claude.com/claude-code) skills for an agent-driven, ticket-based workflow (draft → work → ship via worktrees & PRs). See [`skills/README.md`](skills/README.md). |
| [`prompt_engineering_best_practices/`](prompt_engineering_best_practices/) | Vendor prompting guides for specific model releases (Anthropic Claude Opus, OpenAI GPT-4.1/5.x). |
| [`techstack/`](techstack/) | One note per technology — FastAPI, Vue, SQLite, Cloudflare (D1/R2), Fly.io, `uv`, and more. |
| [`context/`](context/) | Reusable, XML-tagged context snippets (file locations, URLs) — values redacted, meant as fill-in templates. |
| [`mcp_servers/`](mcp_servers/) | How-tos for running MCP servers (Perplexity, Playwright via Docker). |
| [`models/`](models/) | Model/provider notes (e.g. OpenRouter). |
| [`deployment/`](deployment/) | Deployment notes. |
| [`testing/`](testing/) | Testing and pentest workflow notes, test-case management. |
| [`webapps/`](webapps/) | Web app guides (e.g. a CORS audit). |
| [`examples/`](examples/) | Worked examples (e.g. a full-stack web app brief). |
| [`scripts/`](scripts/) | Small utilities: remote-debug Chrome launchers (`browser/`) and `ip_to_fqdn/`, a `uv` Python CLI (`ptrlookup`, `tlsinspect`). |

## Using it

Nothing to install for the docs — open a file and copy what you need. A few
pointers:

- **Agent guidelines:** drop `claude_md/claude.md` into a project as `CLAUDE.md`
  (or `AGENTS.md`) and trim it to fit.
- **Skills:** copy a skill directory into `~/.claude/skills/` (personal) or a
  project's `.claude/skills/` — details in [`skills/README.md`](skills/README.md).
- **Context templates:** the `context/` files use `_REDACTED_` placeholders;
  fill in your own paths and URLs.
- **`ip_to_fqdn` CLI:** a real `uv` package — see `scripts/ip_to_fqdn/`.

## License

Released into the public domain under [The Unlicense](LICENSE). Use it however
you like.
