#!/usr/bin/env python3
"""Discover Discord guild threads/forum posts and capture bodies plus replies."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from typing import Any

from discord_capture_lib import (
    CaptureError,
    DiscordRest,
    capture_authorization,
    connect_discord,
    eprint,
    fetch_thread_messages,
    infer_guild_and_channel,
    parse_time,
    write_jsonl,
)


PARENT_CHANNEL_TYPES = {0, 5, 15, 16}  # text, announcement, forum, media
THREAD_CHANNEL_TYPES = {10, 11, 12}


def add_threads(destination: dict[str, dict[str, Any]], values: Any) -> None:
    if not isinstance(values, list):
        return
    for thread in values:
        if isinstance(thread, dict) and thread.get("id"):
            destination[str(thread["id"])] = thread


def discover_threads(
    api: DiscordRest,
    guild_id: str,
    cutoff: datetime | None,
    max_archive_pages: int,
) -> dict[str, dict[str, Any]]:
    discovered: dict[str, dict[str, Any]] = {}
    active = api.get(f"/guilds/{guild_id}/threads/active", allow_missing=True)
    if isinstance(active, dict):
        add_threads(discovered, active.get("threads"))

    channels = api.get(f"/guilds/{guild_id}/channels")
    if not isinstance(channels, list):
        raise CaptureError(f"Guild channel list was not returned for {guild_id}")

    for channel in channels:
        if not isinstance(channel, dict) or channel.get("type") not in PARENT_CHANNEL_TYPES:
            continue
        channel_id = str(channel.get("id", ""))
        before: str | None = None
        for _ in range(max_archive_pages):
            params: dict[str, Any] = {"limit": 100}
            if before:
                params["before"] = before
            archive = api.get(
                f"/channels/{channel_id}/threads/archived/public",
                params=params,
                allow_missing=True,
            )
            if not isinstance(archive, dict):
                break
            page_threads = archive.get("threads") or []
            add_threads(discovered, page_threads)
            if not page_threads or not archive.get("has_more"):
                break
            archive_times = [
                (thread.get("thread_metadata") or {}).get("archive_timestamp")
                for thread in page_threads
                if isinstance(thread, dict)
            ]
            archive_times = [value for value in archive_times if value]
            if not archive_times:
                break
            next_before = min(archive_times)
            if next_before == before:
                break
            before = next_before
            oldest = parse_time(next_before)
            if cutoff and oldest and oldest < cutoff:
                break
    return discovered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9333)
    parser.add_argument("--guild-id", help="defaults to the guild id in the current Discord URL")
    parser.add_argument("--days", type=int, default=15)
    parser.add_argument("--max-pages", type=int, default=200, help="maximum message pages per thread")
    parser.add_argument("--max-archive-pages", type=int, default=50, help="maximum archive pages per parent channel")
    parser.add_argument("--max-threads", type=int, default=0, help="0 means no explicit limit")
    parser.add_argument("--thread-id", action="append", default=[], help="also capture a specific thread id")
    parser.add_argument("--auth-timeout", type=int, default=30)
    parser.add_argument("--no-reload", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    target, client = connect_discord(args.port)
    current_guild, current_channel = infer_guild_and_channel(str(target.get("url", "")))
    guild_id = args.guild_id or current_guild
    if not guild_id:
        client.close()
        raise CaptureError("No --guild-id was supplied and the current Discord URL has no guild id")
    try:
        authorization = capture_authorization(client, args.auth_timeout, reload_page=not args.no_reload)
    finally:
        client.close()

    api = DiscordRest(authorization)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(args.days, 0)) if args.days else None
    threads = discover_threads(api, guild_id, cutoff, args.max_archive_pages)

    direct_ids = set(args.thread_id)
    if current_channel:
        current_meta = api.get(f"/channels/{current_channel}", allow_missing=True)
        if isinstance(current_meta, dict) and current_meta.get("type") in THREAD_CHANNEL_TYPES:
            direct_ids.add(current_channel)
    for thread_id in direct_ids:
        metadata = api.get(f"/channels/{thread_id}", allow_missing=True)
        if isinstance(metadata, dict):
            threads[str(thread_id)] = metadata

    ordered = sorted(
        threads.values(),
        key=lambda item: str((item.get("thread_metadata") or {}).get("archive_timestamp") or item.get("last_message_id") or ""),
        reverse=True,
    )
    if args.max_threads > 0:
        ordered = ordered[: args.max_threads]

    records: list[dict[str, Any]] = []
    skipped = 0
    for index, thread in enumerate(ordered, 1):
        thread.setdefault("guild_id", guild_id)
        thread_id = str(thread.get("id"))
        try:
            batch = fetch_thread_messages(api, thread, args.max_pages, cutoff)
            records.extend(batch)
            eprint(f"[{index}/{len(ordered)}] {thread_id} {thread.get('name', '')!r}: {len(batch)} records")
        except CaptureError as exc:
            skipped += 1
            eprint(f"[{index}/{len(ordered)}] skipped {thread_id}: {exc}")

    unique = {str(row.get("message_id")): row for row in records if row.get("message_id")}
    final_rows = sorted(unique.values(), key=lambda item: item.get("timestamp") or "")
    count = write_jsonl(args.out, final_rows)
    print(f"discovered={len(threads)} captured_records={count} skipped_threads={skipped} output={args.out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureError as exc:
        raise SystemExit(f"error: {exc}")

