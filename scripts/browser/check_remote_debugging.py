#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets"]
# ///
"""Verify the browser's remote debugging port is working.

Connects to the CDP HTTP endpoint, opens a new tab, navigates to a URL via
the CDP WebSocket, waits for Page.loadEventFired, and reports the final
title/URL.

Usage:
  uv run check_remote_debugging.py
  uv run check_remote_debugging.py --port 9222 --url https://example.com/
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.request

import websockets


def http_json(url: str, method: str = "GET", timeout: float = 5.0) -> dict:
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def open_new_tab(base: str) -> dict:
    # Recent Chromium expects PUT on /json/new; older builds accepted GET.
    last_err: Exception | None = None
    for method in ("PUT", "GET"):
        try:
            return http_json(f"{base}/json/new", method=method)
        except urllib.error.HTTPError as e:
            if e.code in (404, 405):
                last_err = e
                continue
            raise
    raise RuntimeError(f"Could not open new tab via {base}/json/new ({last_err})")


async def drive_tab(ws_url: str, target_url: str, nav_timeout: float = 20.0) -> dict[str, str]:
    next_id = 0

    def msg_id() -> int:
        nonlocal next_id
        next_id += 1
        return next_id

    async def wait_for(ws, predicate, timeout: float) -> dict:
        async with asyncio.timeout(timeout):
            while True:
                msg = json.loads(await ws.recv())
                if predicate(msg):
                    return msg

    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        enable_id = msg_id()
        await ws.send(json.dumps({"id": enable_id, "method": "Page.enable"}))
        await wait_for(ws, lambda m: m.get("id") == enable_id, timeout=5)

        nav_id = msg_id()
        await ws.send(json.dumps({
            "id": nav_id,
            "method": "Page.navigate",
            "params": {"url": target_url},
        }))
        await wait_for(ws, lambda m: m.get("method") == "Page.loadEventFired", timeout=nav_timeout)

        eval_id = msg_id()
        await ws.send(json.dumps({
            "id": eval_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "JSON.stringify({title: document.title, url: location.href})",
                "returnByValue": True,
            },
        }))
        result = await wait_for(ws, lambda m: m.get("id") == eval_id, timeout=5)
        return json.loads(result["result"]["result"]["value"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--port", type=int, default=9222, help="Remote debugging port (default: 9222)")
    parser.add_argument("--url", default="https://example.com/", help="URL to navigate to")
    args = parser.parse_args()

    base = f"http://127.0.0.1:{args.port}"

    try:
        version = http_json(f"{base}/json/version")
    except Exception as e:
        print(f"[FAIL] Cannot reach {base}/json/version: {e}", file=sys.stderr)
        print(f"       Is the browser running with --remote-debugging-port={args.port}?", file=sys.stderr)
        return 1
    print("[ OK ] CDP HTTP endpoint reachable")
    print(f"       Browser : {version.get('Browser')}")
    print(f"       Protocol: {version.get('Protocol-Version')}")

    try:
        tab = open_new_tab(base)
    except Exception as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        return 1
    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        print(f"[FAIL] /json/new response missing webSocketDebuggerUrl: {tab}", file=sys.stderr)
        return 1
    print("[ OK ] Opened new tab")
    print(f"       id : {tab.get('id')}")

    try:
        info = asyncio.run(drive_tab(ws_url, args.url))
    except TimeoutError:
        print(f"[FAIL] Timed out waiting for {args.url} to load", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[FAIL] CDP error: {e}", file=sys.stderr)
        return 1

    print("[ OK ] Navigated and loaded")
    print(f"       title: {info['title']!r}")
    print(f"       url  : {info['url']!r}")

    expected_host = args.url.split("//", 1)[-1].split("/", 1)[0]
    if expected_host not in info["url"]:
        print(f"[FAIL] Final URL doesn't match requested host {expected_host!r}", file=sys.stderr)
        return 1

    print()
    print("Remote debugging is working as expected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
