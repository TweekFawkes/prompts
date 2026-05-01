#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "claude-agent-sdk>=0.1.0",
# ]
# ///
"""
Drive every open backlog ticket through the Claude Agent SDK for Python.

For each ticket file in `z_tickets/open/`, this runner spawns a Claude Code
sub-agent that invokes the `/dowork` skill with the ticket filename as its
argument. Every event the sub-agent emits — assistant text, tool_use,
tool_result, system init, thinking, and the terminal result with token /
cost usage — is streamed to:

  - the screen, with YYYYMMDDHHMMSS timestamps and per-event tags
  - z_tickets/logs/runner-<start-ts>.log         (everything that hits screen)
  - z_tickets/logs/ticket-<stem>-<run-ts>.log    (human-readable per-ticket)
  - z_tickets/logs/ticket-<stem>-<run-ts>.jsonl  (raw events, one JSON / line)

Loop semantics:
  - Pick the next open ticket and drive it through the dowork skill.
  - When that ticket finishes, check for `STOP` in z_tickets/. If present,
    exit cleanly. Otherwise sleep SLEEP_SECONDS before the next iteration.
  - Exit when no open tickets remain.

The skill is responsible for moving the ticket out of `open/` (into
`closed/`) once it is genuinely done. If the file is still in `open/` after
the sub-agent returns, the runner notes that and will pick it up again on
the next pass.

Run from anywhere:
    z_tickets/run_tickets.py
or:
    uv run z_tickets/run_tickets.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import socket
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    UserMessage,
    query,
)
from claude_agent_sdk.types import (
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

# --- paths & config -------------------------------------------------------
#
# This script assumes the layout:
#
#   <project-root>/
#     z_tickets/
#       run_tickets.py        # this file
#       open/                 # one .md per open ticket
#       closed/               # one .md per closed ticket (skill moves them)
#       logs/                 # auto-created
#       STOP                  # touch this file to halt after current ticket
#     .claude/
#       skills/
#         dowork/
#           SKILL.md          # the per-ticket worker skill
#
# The runner spawns Claude Code with cwd=<project-root> so the sub-agent
# operates against your codebase, not against the z_tickets folder.

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
OPEN_DIR = HERE / "open"
CLOSED_DIR = HERE / "closed"
STOP_FILE = HERE / "STOP"
LOG_DIR = HERE / "logs"
SLEEP_SECONDS = 120
SLEEP_TICK_SECONDS = 30
TEXT_PREVIEW = 600
TOOL_INPUT_PREVIEW = 400
TOOL_RESULT_PREVIEW = 600

# Equivalent of:
#   claude --chrome --permission-mode bypassPermissions \
#          --effort max --model opus --fallback-model sonnet
#
# `bypassPermissions` is appropriate for unattended runs against a
# repo you trust. Drop it (or switch to "default") if you want each
# tool call confirmed interactively.
SDK_OPTIONS_BASE: dict[str, Any] = dict(
    permission_mode="bypassPermissions",
    model="opus",
    fallback_model="sonnet",
    cwd=str(PROJECT_ROOT),
    setting_sources=["user", "project", "local"],
    extra_args={
        "chrome": None,        # --chrome  (Claude in Chrome integration)
        "effort": "max",       # --effort max
    },
)

RUN_TS = datetime.now().strftime("%Y%m%d%H%M%S")
RUNNER_LOG = LOG_DIR / f"runner-{RUN_TS}.log"


# --- logging --------------------------------------------------------------

def now_ts() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


def make_logger(name: str, log_path: Path | None, also_stdout: bool) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y%m%d%H%M%S",
    )
    if also_stdout:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


# --- helpers --------------------------------------------------------------

def list_open_tickets() -> list[Path]:
    if not OPEN_DIR.is_dir():
        return []
    return sorted(
        p for p in OPEN_DIR.glob("*.md")
        if not p.name.startswith("_") and not p.name.startswith(".")
    )


def stop_requested() -> bool:
    return STOP_FILE.exists()


def first_line(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    return line[:120]
    except OSError:
        pass
    return ""


def fmt_elapsed(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def truncate(s: str, n: int) -> str:
    s = (s or "").replace("\n", " \\n ")
    return s if len(s) <= n else s[:n] + f"…(+{len(s) - n} chars)"


def to_jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if is_dataclass(obj):
        try:
            return asdict(obj)
        except TypeError:
            pass
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return {k: to_jsonable(v) for k, v in vars(obj).items()}
    return repr(obj)


# --- event rendering ------------------------------------------------------

def render_block(blk: Any) -> Iterable[tuple[str, str]]:
    bcls = type(blk).__name__
    if isinstance(blk, TextBlock):
        yield ("INFO", f"  └ TEXT       {truncate(blk.text, TEXT_PREVIEW)}")
        return
    if isinstance(blk, ThinkingBlock):
        text = getattr(blk, "thinking", "") or ""
        yield ("INFO", f"  └ THINKING   {truncate(text, TEXT_PREVIEW)}")
        return
    if isinstance(blk, ToolUseBlock):
        name = getattr(blk, "name", "?")
        tid = getattr(blk, "id", "?")
        tool_input = getattr(blk, "input", None)
        try:
            inp = (json.dumps(tool_input, default=str)
                   if tool_input is not None else "")
        except (TypeError, ValueError):
            inp = repr(tool_input)
        yield ("INFO",
               f"  └ TOOL_USE   id={tid} name={name} "
               f"input={truncate(inp, TOOL_INPUT_PREVIEW)}")
        return
    if isinstance(blk, ToolResultBlock):
        tid = getattr(blk, "tool_use_id", "?")
        is_err = getattr(blk, "is_error", False)
        content = getattr(blk, "content", "")
        if isinstance(content, list):
            try:
                content = json.dumps(content, default=str)
            except (TypeError, ValueError):
                content = repr(content)
        yield ("WARN" if is_err else "INFO",
               f"  └ TOOL_RESULT id={tid} is_error={is_err} "
               f"content={truncate(str(content), TOOL_RESULT_PREVIEW)}")
        return
    yield ("INFO", f"  └ {bcls}  {truncate(repr(blk), 200)}")


def render_event(msg: Any) -> Iterable[tuple[str, str]]:
    """Yield (level, message-line) tuples for one SDK event."""
    cls = type(msg).__name__

    if isinstance(msg, SystemMessage):
        subtype = getattr(msg, "subtype", "?")
        data = getattr(msg, "data", {}) or {}
        if isinstance(data, dict):
            keys = ", ".join(
                f"{k}={truncate(str(v), 80)}" for k, v in data.items()
            )
        else:
            keys = truncate(str(data), 200)
        yield ("INFO", f"SYSTEM/{subtype}  {keys}")
        return

    if isinstance(msg, AssistantMessage):
        model = getattr(msg, "model", "?")
        blocks = getattr(msg, "content", []) or []
        yield ("INFO", f"ASSISTANT  model={model}  blocks={len(blocks)}")
        for blk in blocks:
            yield from render_block(blk)
        return

    if isinstance(msg, UserMessage):
        # In streaming mode, UserMessages from the agent typically carry
        # tool_result blocks coming back from the CLI's tool calls.
        blocks = getattr(msg, "content", []) or []
        yield ("INFO", f"USER       blocks={len(blocks)}")
        for blk in blocks:
            yield from render_block(blk)
        return

    if isinstance(msg, ResultMessage):
        is_error = getattr(msg, "is_error", False)
        duration_ms = getattr(msg, "duration_ms", 0) or 0
        api_ms = getattr(msg, "duration_api_ms", 0) or 0
        turns = getattr(msg, "num_turns", "?")
        cost = getattr(msg, "total_cost_usd", None)
        usage = getattr(msg, "usage", {}) or {}
        if not isinstance(usage, dict):
            usage = to_jsonable(usage) or {}
        in_t = usage.get("input_tokens", "?") if isinstance(usage, dict) else "?"
        out_t = usage.get("output_tokens", "?") if isinstance(usage, dict) else "?"
        cache_r = (usage.get("cache_read_input_tokens", 0)
                   if isinstance(usage, dict) else 0)
        cache_w = (usage.get("cache_creation_input_tokens", 0)
                   if isinstance(usage, dict) else 0)
        cost_str = f"${cost:.4f}" if isinstance(cost, (int, float)) else str(cost)
        yield ("ERROR" if is_error else "INFO",
               f"RESULT     is_error={is_error} turns={turns} "
               f"duration={duration_ms}ms api={api_ms}ms "
               f"tokens_in={in_t} tokens_out={out_t} "
               f"cache_read={cache_r} cache_write={cache_w} cost={cost_str}")
        result = getattr(msg, "result", None)
        if result:
            yield ("INFO", f"RESULT.text  {truncate(str(result), TEXT_PREVIEW)}")
        return

    yield ("INFO", f"{cls}  {truncate(repr(msg), 200)}")


# --- ticket runner --------------------------------------------------------

async def run_ticket(
    ticket: Path,
    runner: logging.Logger,
) -> tuple[int, float, dict[str, int]]:
    """Drive one ticket through the SDK. Returns (rc, elapsed_s, counts)."""
    run_ts = now_ts()
    stem = ticket.stem
    text_log = LOG_DIR / f"ticket-{stem}-{run_ts}.log"
    jsonl_log = LOG_DIR / f"ticket-{stem}-{run_ts}.jsonl"
    ticket_logger = make_logger(
        f"ticket.{stem}.{run_ts}", text_log, also_stdout=False
    )

    runner.info(f"per-ticket text log = {text_log}")
    runner.info(f"per-ticket json log = {jsonl_log}")

    options = ClaudeAgentOptions(**SDK_OPTIONS_BASE)
    prompt = f"skill /dowork {ticket.name}"

    runner.info(f"prompt              = {prompt!r}")
    runner.info(
        f"sdk options         = "
        f"model={options.model} fallback={options.fallback_model} "
        f"perm={options.permission_mode} cwd={options.cwd} "
        f"setting_sources={options.setting_sources} "
        f"extra_args={options.extra_args}"
    )
    runner.info(f"claude start        = {now_ts()}")

    started = time.monotonic()
    counts: dict[str, int] = {
        "events": 0, "assistant": 0, "user": 0, "system": 0,
        "tool_use": 0, "tool_result": 0, "tool_error": 0,
        "text_blocks": 0, "thinking_blocks": 0,
    }
    final_rc = 0

    jsonl_log.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_log.open("w", encoding="utf-8") as jf:
        try:
            async for msg in query(prompt=prompt, options=options):
                counts["events"] += 1

                # JSONL: raw event dump (full fidelity, for forensics)
                rec = {
                    "ts": now_ts(),
                    "type": type(msg).__name__,
                    "data": to_jsonable(msg),
                }
                jf.write(json.dumps(rec, default=str, ensure_ascii=False) + "\n")
                jf.flush()

                # Tally counts
                if isinstance(msg, AssistantMessage):
                    counts["assistant"] += 1
                    for blk in (msg.content or []):
                        if isinstance(blk, TextBlock):
                            counts["text_blocks"] += 1
                        elif isinstance(blk, ThinkingBlock):
                            counts["thinking_blocks"] += 1
                        elif isinstance(blk, ToolUseBlock):
                            counts["tool_use"] += 1
                elif isinstance(msg, UserMessage):
                    counts["user"] += 1
                    for blk in (msg.content or []):
                        if isinstance(blk, ToolResultBlock):
                            counts["tool_result"] += 1
                            if getattr(blk, "is_error", False):
                                counts["tool_error"] += 1
                elif isinstance(msg, SystemMessage):
                    counts["system"] += 1
                elif isinstance(msg, ResultMessage):
                    if getattr(msg, "is_error", False):
                        final_rc = 1

                # Render to screen + per-ticket text log
                for level_name, line in render_event(msg):
                    lvl = getattr(logging, level_name, logging.INFO)
                    runner.log(lvl, line)
                    ticket_logger.log(lvl, line)
        except Exception as e:  # noqa: BLE001
            final_rc = 1
            runner.exception(f"SDK error while running ticket: {e!r}")
            ticket_logger.exception(f"SDK error: {e!r}")

    elapsed = time.monotonic() - started
    runner.info(
        f"claude end          = {now_ts()}  "
        f"(elapsed {fmt_elapsed(elapsed)}, rc={final_rc})"
    )
    runner.info(f"event tally         = {counts}")
    return final_rc, elapsed, counts


# --- loop -----------------------------------------------------------------

def banner(logger: logging.Logger, title: str) -> None:
    bar = "=" * 72
    logger.info(bar)
    logger.info(f"=== {title}")
    logger.info(bar)


async def amain() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    runner = make_logger("run_tickets", RUNNER_LOG, also_stdout=True)

    banner(runner, "ticket runner starting")
    runner.info(f"timestamp     = {now_ts()} (YYYYMMDDHHMMSS, local)")
    runner.info(f"hostname      = {socket.gethostname()}")
    runner.info(f"pid           = {os.getpid()}")
    runner.info(f"python        = {sys.version.split()[0]}")
    runner.info(f"script        = {Path(__file__).resolve()}")
    runner.info(f"project root  = {PROJECT_ROOT}")
    runner.info(f"open dir      = {OPEN_DIR}")
    runner.info(f"closed dir    = {CLOSED_DIR}")
    runner.info(f"stop file     = {STOP_FILE} (exists={STOP_FILE.exists()})")
    runner.info(f"log dir       = {LOG_DIR}")
    runner.info(f"runner log    = {RUNNER_LOG}")
    runner.info(
        f"sleep between = {SLEEP_SECONDS}s "
        f"(heartbeat every {SLEEP_TICK_SECONDS}s)"
    )
    runner.info(f"sdk base opts = {SDK_OPTIONS_BASE}")

    if not OPEN_DIR.is_dir():
        runner.error(f"open dir does not exist: {OPEN_DIR}")
        return 1

    initial = list_open_tickets()
    runner.info(f"discovered {len(initial)} open ticket(s):")
    for i, p in enumerate(initial, 1):
        runner.info(f"  {i:>2}. {p.name}  —  {first_line(p)!r}")

    iteration = 0
    processed = 0
    started_at = time.monotonic()
    while True:
        if stop_requested():
            runner.warning(
                f"STOP file present at {STOP_FILE} — exiting before next ticket."
            )
            break

        tickets = list_open_tickets()
        if not tickets:
            runner.info("no open tickets remain — done.")
            break

        ticket = tickets[0]
        iteration += 1
        banner(
            runner,
            f"iter {iteration}: {ticket.name}  ({len(tickets)} open total)",
        )
        runner.info(f"selected ticket = {ticket}")
        runner.info(f"first line      = {first_line(ticket)!r}")
        runner.info(f"size            = {ticket.stat().st_size} bytes")

        rc, elapsed, counts = await run_ticket(ticket, runner)
        processed += 1
        runner.info(
            f"iter {iteration} done. rc={rc}, "
            f"elapsed={fmt_elapsed(elapsed)}, counts={counts}"
        )

        if stop_requested():
            runner.warning(
                "STOP file present — finished current ticket, exiting."
            )
            break

        if ticket.exists():
            runner.warning(
                f"NOTE: {ticket.name} still in open/ — skill did not "
                "mark complete. It will be retried on the next pass."
            )
        else:
            runner.info(
                f"OK: {ticket.name} no longer in open/ — skill closed it."
            )

        remaining = list_open_tickets()
        if not remaining:
            runner.info("no more open tickets — done.")
            break

        runner.info(f"open dir now has {len(remaining)} ticket(s) remaining:")
        for i, p in enumerate(remaining, 1):
            runner.info(f"  {i:>2}. {p.name}")

        runner.info(
            f"sleeping {SLEEP_SECONDS}s before next ticket. "
            f"heartbeat every {SLEEP_TICK_SECONDS}s."
        )
        waited = 0
        while waited < SLEEP_SECONDS:
            chunk = min(SLEEP_TICK_SECONDS, SLEEP_SECONDS - waited)
            try:
                await asyncio.sleep(chunk)
            except asyncio.CancelledError:
                runner.warning("sleep cancelled — exiting.")
                return 130
            waited += chunk
            if stop_requested():
                runner.warning(
                    f"STOP file detected during sleep at {waited}s — "
                    "breaking sleep."
                )
                break
            if waited < SLEEP_SECONDS:
                runner.info(
                    f"...still sleeping. elapsed={waited}s, "
                    f"remaining={SLEEP_SECONDS - waited}s"
                )
        runner.info("sleep complete — proceeding to next iteration.")

    elapsed_total = time.monotonic() - started_at
    banner(runner, f"ticket runner exiting (processed={processed})")
    runner.info(f"total elapsed wall time = {fmt_elapsed(elapsed_total)}")
    runner.info(f"end timestamp           = {now_ts()}")
    return 0


def _handle_sigterm(signum: int, _frame) -> None:
    print(
        f"[{now_ts()}] [WARNING] [run_tickets] received signal {signum} — "
        "exiting.",
        flush=True,
    )
    sys.exit(143)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_sigterm)
    try:
        sys.exit(asyncio.run(amain()))
    except KeyboardInterrupt:
        print(
            f"[{now_ts()}] [WARNING] [run_tickets] interrupted — exiting.",
            flush=True,
        )
        sys.exit(130)
