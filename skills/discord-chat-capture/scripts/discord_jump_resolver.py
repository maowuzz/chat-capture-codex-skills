#!/usr/bin/env python3
"""Resolve Discord deep links from captured JSONL and fetch their targets."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from discord_capture_lib import (
    CaptureError,
    DiscordRest,
    capture_authorization,
    connect_discord,
    extract_discord_links,
    fetch_thread_messages,
    local_iso,
    read_jsonl,
    utc_now_iso,
    write_jsonl,
)


THREAD_TYPES = {10, 11, 12}


def parse_jump(url: str) -> dict[str, str | None]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not (
        host == "discord.com"
        or host == "discordapp.com"
        or host.endswith(".discord.com")
        or host.endswith(".discordapp.com")
    ):
        raise ValueError("not a Discord URL")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 3 or parts[0] != "channels":
        raise ValueError("unsupported Discord route")
    guild_id = parts[1]
    parent_id: str | None = None
    message_id: str | None = None
    if len(parts) >= 5 and parts[3] == "threads":
        parent_id = parts[2]
        channel_id = parts[4]
        if len(parts) >= 6 and parts[5].isdigit():
            message_id = parts[5]
        route = "thread_route"
    else:
        channel_id = parts[2]
        if len(parts) >= 4 and parts[3].isdigit():
            message_id = parts[3]
        route = "channel_route"
    return {
        "guild_id": None if guild_id == "@me" else guild_id,
        "channel_id": channel_id,
        "parent_id": parent_id,
        "message_id": message_id,
        "route": route,
    }


def compact_author(message: dict[str, Any]) -> tuple[str, str]:
    author = message.get("author") or {}
    return (
        author.get("global_name") or author.get("username") or "",
        str(author.get("id", "")),
    )


def raw_message_record(message: dict[str, Any], channel: dict[str, Any]) -> dict[str, Any]:
    author, author_id = compact_author(message)
    timestamp = message.get("timestamp")
    return {
        "record_type": "channel",
        "guild_id": channel.get("guild_id"),
        "channel_id": str(channel.get("id", "")),
        "channel": channel.get("name", ""),
        "message_id": str(message.get("id", "")),
        "timestamp": timestamp,
        "time_local": local_iso(timestamp),
        "author": author,
        "author_id": author_id,
        "text": message.get("content", ""),
        "attachments": message.get("attachments") or [],
        "embeds": message.get("embeds") or [],
        "message_reference": message.get("message_reference"),
        "message_snapshots": message.get("message_snapshots") or [],
        "components": message.get("components") or [],
        "discord_links": extract_discord_links(message),
        "captured_at": utc_now_iso(),
    }


def fetch_message_context(
    api: DiscordRest,
    channel: dict[str, Any],
    message_id: str,
    context: int,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    channel_id = str(channel["id"])
    direct = api.get(f"/channels/{channel_id}/messages/{message_id}", allow_missing=True)
    page: list[dict[str, Any]] = []
    if isinstance(direct, dict):
        page = [direct]
    if not page:
        around = api.get(
            f"/channels/{channel_id}/messages",
            params={"around": message_id, "limit": max(1, min(100, context * 2 + 1))},
            allow_missing=True,
        )
        if isinstance(around, list):
            page = [item for item in around if isinstance(item, dict)]
    page.sort(key=lambda item: int(item.get("id", 0)))
    target = next((item for item in page if str(item.get("id")) == message_id), None)
    return target, [raw_message_record(item, channel) for item in page]


def source_links(rows: list[dict[str, Any]]) -> list[str]:
    links: set[str] = set()
    for row in rows:
        values = row.get("discord_links")
        if isinstance(values, list):
            links.update(str(value) for value in values if value)
        else:
            links.update(extract_discord_links(row))
    return sorted(links)


def summarize_target(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record.get(key)
        for key in (
            "message_id",
            "time_local",
            "author",
            "author_id",
            "content",
            "text",
            "attachments",
            "embeds",
            "message_reference",
            "referenced_message",
            "discord_links",
        )
        if record.get(key) not in (None, "", [], {})
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="captured Discord JSONL")
    parser.add_argument("--port", type=int, default=9333)
    parser.add_argument("--out", required=True, help="resolver manifest JSON")
    parser.add_argument("--target-dir", required=True, help="directory for fetched JSONL targets")
    parser.add_argument("--context", type=int, default=3, help="messages around a channel jump")
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--auth-timeout", type=int, default=45)
    parser.add_argument("--no-reload", action="store_true")
    args = parser.parse_args()

    rows = read_jsonl(args.input)
    links = source_links(rows)
    if not links:
        raise CaptureError("No Discord jump links were found in the input")

    source_thread_ids = {str(row.get("thread_id")) for row in rows if row.get("thread_id")}
    source_by_message = {
        str(row.get("message_id")): row for row in rows if row.get("message_id")
    }
    target_dir = Path(args.target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    _, client = connect_discord(args.port)
    try:
        authorization = capture_authorization(
            client, args.auth_timeout, reload_page=not args.no_reload
        )
    finally:
        client.close()
    api = DiscordRest(authorization)

    results: list[dict[str, Any]] = []
    thread_cache: dict[str, list[dict[str, Any]]] = {}
    for url in links:
        item: dict[str, Any] = {
            "url": url,
            "resolved_at": utc_now_iso(),
            "resolved": False,
        }
        try:
            location = parse_jump(url)
            item.update(location)
            channel_id = str(location["channel_id"])
            message_id = location["message_id"]
            item["same_thread"] = channel_id in source_thread_ids
            item["reference_scope"] = "message" if message_id else "thread_or_channel"

            if message_id == "0":
                item["zero_message_as_top"] = True
                item["message_id"] = None
                item["reference_scope"] = "thread_or_channel"
                message_id = None
                if item["same_thread"]:
                    source_title = next(
                        (row.get("thread_title") for row in rows if row.get("thread_title")),
                        "",
                    )
                    item.update(
                        {
                            "resolved": True,
                            "status": "same_thread_top",
                            "target_kind": "thread",
                            "target_title": source_title,
                        }
                    )
                    results.append(item)
                    continue

            if item["same_thread"] and message_id:
                record = source_by_message.get(str(message_id))
                if record:
                    item.update(
                        {
                            "resolved": True,
                            "status": "same_thread_message",
                            "target_kind": "thread_message",
                            "target_title": record.get("thread_title"),
                            "target_message": summarize_target(record),
                            "anchor": f"dc-{message_id}",
                        }
                    )
                else:
                    item.update(
                        {
                            "status": "same_thread_message_missing",
                            "target_kind": "thread_message",
                            "error": "message id is not present in the source capture",
                        }
                    )
                results.append(item)
                continue

            channel = api.get(f"/channels/{channel_id}", allow_missing=True)
            if not isinstance(channel, dict):
                item.update({"status": "channel_unavailable", "error": "channel metadata unavailable"})
                results.append(item)
                continue

            channel_type = channel.get("type")
            item.update(
                {
                    "target_kind": "thread" if channel_type in THREAD_TYPES else "channel",
                    "target_title": channel.get("name", ""),
                    "target_channel_type": channel_type,
                    "target_parent_id": channel.get("parent_id"),
                    "target_guild_id": channel.get("guild_id"),
                }
            )

            if channel_type in THREAD_TYPES:
                if message_id:
                    record = None
                    records = thread_cache.get(channel_id, [])
                    captured_count = 0
                    output_path: Path | None = None
                    if records:
                        record = next(
                            (
                                row
                                for row in records
                                if str(row.get("message_id")) == message_id
                            ),
                            None,
                        )
                        captured_count = len(records)
                        whole_output = target_dir / f"thread_{channel_id}.jsonl"
                        if whole_output.exists():
                            output_path = whole_output
                    if not record:
                        target, context_records = fetch_message_context(
                            api, channel, str(message_id), args.context
                        )
                        output = target_dir / f"thread_{channel_id}_message_{message_id}.jsonl"
                        if context_records:
                            write_jsonl(output, context_records)
                            output_path = output
                        captured_count = len(context_records)
                        if target:
                            record = raw_message_record(target, channel)
                    item.update(
                        {
                            "resolved": record is not None,
                            "status": "thread_message" if record else "thread_message_missing",
                            "captured_records": captured_count,
                            "output_file": str(output_path.resolve())
                            if output_path
                            else None,
                        }
                    )
                    if record:
                        item["target_message"] = summarize_target(record)
                        item["anchor"] = f"dc-{message_id}"
                    else:
                        item["error"] = "target thread was fetched but the cited message was absent"
                else:
                    output = target_dir / f"thread_{channel_id}.jsonl"
                    if channel_id not in thread_cache:
                        if output.exists():
                            thread_cache[channel_id] = read_jsonl(output)
                        else:
                            thread_cache[channel_id] = fetch_thread_messages(
                                api, channel, args.max_pages, cutoff=None
                            )
                            write_jsonl(output, thread_cache[channel_id])
                    records = thread_cache[channel_id]
                    item.update(
                        {
                            "resolved": True,
                            "status": "whole_thread",
                            "captured_records": len(records),
                            "output_file": str(output.resolve()),
                        }
                    )
                results.append(item)
                continue

            if message_id:
                target, context_records = fetch_message_context(
                    api, channel, str(message_id), args.context
                )
                output = target_dir / f"channel_{channel_id}_message_{message_id}.jsonl"
                if context_records:
                    write_jsonl(output, context_records)
                item.update(
                    {
                        "resolved": target is not None,
                        "status": "channel_message" if target else "channel_message_missing",
                        "captured_records": len(context_records),
                        "output_file": str(output.resolve()) if context_records else None,
                    }
                )
                if target:
                    item["target_message"] = summarize_target(
                        raw_message_record(target, channel)
                    )
                    item["anchor"] = f"dc-{message_id}"
                else:
                    item["error"] = "specific message was not returned"
            else:
                item.update(
                    {
                        "resolved": True,
                        "status": "whole_channel_metadata",
                        "captured_records": 0,
                    }
                )
            results.append(item)
        except (CaptureError, ValueError, KeyError) as exc:
            item.update({"status": "error", "error": str(exc)})
            results.append(item)

    counts = Counter(item.get("status", "unknown") for item in results)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input": str(Path(args.input).resolve()),
        "total_links": len(links),
        "resolved": sum(bool(item.get("resolved")) for item in results),
        "unresolved": sum(not bool(item.get("resolved")) for item in results),
        "status_counts": dict(counts),
        "links": results,
    }
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"links={len(links)} resolved={manifest['resolved']} "
        f"unresolved={manifest['unresolved']} output={output_path}"
    )
    return 0 if manifest["resolved"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureError as exc:
        raise SystemExit(f"error: {exc}")
