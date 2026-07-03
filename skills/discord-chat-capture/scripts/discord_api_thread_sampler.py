#!/usr/bin/env python3
"""Capture one Discord forum post/thread body and replies through Desktop CDP."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from discord_capture_lib import (
    CaptureError,
    DiscordRest,
    capture_authorization,
    connect_discord,
    fetch_thread_messages,
    infer_guild_and_channel,
    write_jsonl,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9333)
    parser.add_argument("--thread-id", help="defaults to the channel/thread id in the current Discord URL")
    parser.add_argument("--days", type=int, default=15, help="keep recent replies; always keep the starter body")
    parser.add_argument("--max-pages", type=int, default=80)
    parser.add_argument("--auth-timeout", type=int, default=30)
    parser.add_argument("--no-reload", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    target, client = connect_discord(args.port)
    current_guild, current_channel = infer_guild_and_channel(str(target.get("url", "")))
    thread_id = args.thread_id or current_channel
    if not thread_id:
        client.close()
        raise CaptureError("No --thread-id was supplied and the current Discord URL has no channel id")
    try:
        authorization = capture_authorization(client, args.auth_timeout, reload_page=not args.no_reload)
    finally:
        client.close()

    api = DiscordRest(authorization)
    thread = api.get(f"/channels/{thread_id}")
    if not isinstance(thread, dict):
        raise CaptureError(f"Thread metadata was not returned for {thread_id}")
    if current_guild and not thread.get("guild_id"):
        thread["guild_id"] = current_guild
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(args.days, 0)) if args.days else None
    records = fetch_thread_messages(api, thread, args.max_pages, cutoff)
    count = write_jsonl(args.out, records)
    print(f"captured thread={thread_id} title={thread.get('name', '')!r} records={count} output={args.out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureError as exc:
        raise SystemExit(f"error: {exc}")

