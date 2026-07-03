#!/usr/bin/env python3
"""Clean, merge, deduplicate, and index Discord capture JSONL files."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from discord_capture_lib import CaptureError, ensure_parent, local_iso, parse_time, read_jsonl, write_jsonl


DEFAULT_ADULT_KEYWORDS = ["成人", "色情", "r18", "nsfw", "喝茶吹水"]


def stream_type(row: dict[str, Any]) -> str:
    value = str(row.get("record_type", "")).lower()
    if value in {"channel", "thread"}:
        return value
    return "thread" if row.get("thread_id") or row.get("thread_title") else "channel"


def record_time(row: dict[str, Any]) -> str:
    return str(row.get("time_local") or row.get("timestamp") or row.get("time") or "")


def normalize(row: dict[str, Any]) -> dict[str, Any] | None:
    message_id = str(row.get("message_id") or "").strip()
    if not message_id:
        return None
    result = dict(row)
    result["message_id"] = message_id
    result["record_type"] = stream_type(result)
    timestamp = result.get("timestamp") or result.get("time") or result.get("time_local")
    result["time_local"] = local_iso(str(timestamp)) if timestamp else result.get("time_local")
    if result["record_type"] == "thread":
        result["content"] = str(result.get("content") or result.get("text") or "").strip()
        result["thread_title"] = str(result.get("thread_title") or result.get("title") or "").strip()
    else:
        result["text"] = str(result.get("text") or result.get("content") or "").strip()
        result["channel"] = str(result.get("channel") or result.get("channel_text") or result.get("title") or "").strip()
    result["author"] = str(result.get("author") or result.get("username") or "").strip()
    return result


def is_excluded(row: dict[str, Any], keywords: list[str]) -> bool:
    haystack = "\n".join(
        str(row.get(key, ""))
        for key in ("channel", "channel_text", "thread_title", "title", "content", "text")
    ).lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def clean_rows(
    rows: list[dict[str, Any]],
    since: str | None = None,
    exclude_keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    cutoff = parse_time(since)
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for source in rows:
        row = normalize(source)
        if not row:
            continue
        timestamp = parse_time(record_time(row))
        if cutoff and timestamp and timestamp <= cutoff:
            continue
        if exclude_keywords and is_excluded(row, exclude_keywords):
            continue
        key = (row["record_type"], row["message_id"])
        previous = unique.get(key)
        if not previous or len(json.dumps(row, ensure_ascii=False)) >= len(json.dumps(previous, ensure_ascii=False)):
            unique[key] = row
    return sorted(unique.values(), key=lambda item: (record_time(item), item["record_type"], item["message_id"]))


def load_many(paths: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(read_jsonl(path))
    return rows


def write_sqlite(path: str, rows: list[dict[str, Any]]) -> tuple[int, int]:
    output = ensure_parent(path)
    connection = sqlite3.connect(output)
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS discord_channels(
                message_id TEXT PRIMARY KEY,
                time_local TEXT,
                channel TEXT,
                author TEXT,
                text TEXT,
                raw_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS discord_threads(
                message_id TEXT PRIMARY KEY,
                time_local TEXT,
                thread_title TEXT,
                author TEXT,
                content TEXT,
                raw_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_discord_channels_time ON discord_channels(time_local);
            CREATE INDEX IF NOT EXISTS idx_discord_threads_time ON discord_threads(time_local);
            """
        )
        channel_count = 0
        thread_count = 0
        for row in clean_rows(rows):
            raw = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            if row["record_type"] == "thread":
                connection.execute(
                    "INSERT OR REPLACE INTO discord_threads VALUES(?,?,?,?,?,?)",
                    (
                        row["message_id"],
                        record_time(row),
                        row.get("thread_title", ""),
                        row.get("author", ""),
                        row.get("content", ""),
                        raw,
                    ),
                )
                thread_count += 1
            else:
                connection.execute(
                    "INSERT OR REPLACE INTO discord_channels VALUES(?,?,?,?,?,?)",
                    (
                        row["message_id"],
                        record_time(row),
                        row.get("channel", ""),
                        row.get("author", ""),
                        row.get("text", ""),
                        raw,
                    ),
                )
                channel_count += 1
        connection.commit()
        return channel_count, thread_count
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    clean = commands.add_parser("clean")
    clean.add_argument("--input", required=True)
    clean.add_argument("--output", required=True)
    clean.add_argument("--since", help="ISO timestamp; keep records strictly after it")
    clean.add_argument("--exclude-adult", action="store_true")
    clean.add_argument("--exclude-keyword", action="append", default=[])

    merge = commands.add_parser("merge")
    merge.add_argument("--input", action="append", required=True)
    merge.add_argument("--output", required=True)
    merge.add_argument("--exclude-adult", action="store_true")
    merge.add_argument("--exclude-keyword", action="append", default=[])

    sqlite_command = commands.add_parser("sqlite")
    sqlite_command.add_argument("--input", action="append", required=True)
    sqlite_command.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "clean":
        keywords = list(args.exclude_keyword)
        if args.exclude_adult:
            keywords.extend(DEFAULT_ADULT_KEYWORDS)
        rows = clean_rows(read_jsonl(args.input), args.since, keywords)
        count = write_jsonl(args.output, rows)
        print(f"cleaned={count} output={args.output}")
        return 0
    if args.command == "merge":
        keywords = list(args.exclude_keyword)
        if args.exclude_adult:
            keywords.extend(DEFAULT_ADULT_KEYWORDS)
        rows = clean_rows(load_many(args.input), exclude_keywords=keywords)
        count = write_jsonl(args.output, rows)
        print(f"merged={count} output={args.output}")
        return 0
    if args.command == "sqlite":
        channels, threads = write_sqlite(args.output, load_many(args.input))
        print(f"channels={channels} threads={threads} output={args.output}")
        return 0
    raise CaptureError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureError as exc:
        raise SystemExit(f"error: {exc}")

