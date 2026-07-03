#!/usr/bin/env python3
"""Shared helpers for Discord Desktop capture through Chrome DevTools Protocol.

Authorization is held only in process memory and is never logged or written.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
import websocket


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


DISCORD_API = "https://discord.com/api/v9"
DISCORD_EPOCH_MS = 1420070400000
DISCORD_LINK_PATTERN = re.compile(
    r"https?://(?:(?:ptb|canary)\.)?discord(?:app)?\.com/channels/[^\s)>\]}]+",
    re.IGNORECASE,
)


class CaptureError(RuntimeError):
    pass


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def local_iso(value: str | None) -> str | None:
    parsed = parse_time(value)
    return parsed.astimezone().isoformat() if parsed else value


def snowflake_time(snowflake: str | int | None) -> datetime | None:
    try:
        milliseconds = (int(snowflake) >> 22) + DISCORD_EPOCH_MS
        return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def ensure_parent(path: str | os.PathLike[str]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def write_jsonl(path: str | os.PathLike[str], rows: Iterable[dict[str, Any]]) -> int:
    output = ensure_parent(path)
    temporary = output.with_suffix(output.suffix + ".tmp")
    count = 0
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    temporary.replace(output)
    return count


def read_jsonl(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CaptureError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if isinstance(value, dict):
                rows.append(value)
    return rows


def get_targets(port: int) -> list[dict[str, Any]]:
    endpoint = f"http://127.0.0.1:{port}/json/list"
    try:
        response = requests.get(endpoint, timeout=5)
        response.raise_for_status()
        value = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise CaptureError(
            f"Discord debug endpoint is unavailable at {endpoint}. "
            "Start Discord Desktop with --remote-debugging-port before retrying."
        ) from exc
    if not isinstance(value, list):
        raise CaptureError(f"Unexpected response from {endpoint}")
    return [item for item in value if isinstance(item, dict)]


def select_discord_target(targets: list[dict[str, Any]]) -> dict[str, Any]:
    pages = [target for target in targets if target.get("type") in (None, "page", "webview")]
    ranked = sorted(
        pages,
        key=lambda target: (
            "discord.com/channels" in str(target.get("url", "")),
            "discord" in str(target.get("title", "")).lower(),
        ),
        reverse=True,
    )
    for target in ranked:
        if target.get("webSocketDebuggerUrl") and (
            "discord" in str(target.get("url", "")).lower()
            or "discord" in str(target.get("title", "")).lower()
        ):
            return target
    raise CaptureError("No Discord page target with webSocketDebuggerUrl was found")


class CDPClient:
    def __init__(self, url: str, timeout: float = 10) -> None:
        self.socket = websocket.create_connection(url, timeout=timeout, suppress_origin=True)
        self.next_id = 0
        self.events: list[dict[str, Any]] = []

    def close(self) -> None:
        self.socket.close()

    def __enter__(self) -> "CDPClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _receive(self) -> dict[str, Any]:
        message = self.socket.recv()
        if not message:
            raise CaptureError("DevTools connection closed")
        return json.loads(message)

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.next_id += 1
        request_id = self.next_id
        self.socket.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
        while True:
            message = self._receive()
            if message.get("id") == request_id:
                if "error" in message:
                    raise CaptureError(f"CDP {method} failed: {message['error']}")
                return message.get("result", {})
            if "method" in message:
                self.events.append(message)

    def event(self, timeout: float = 1) -> dict[str, Any] | None:
        if self.events:
            return self.events.pop(0)
        old_timeout = self.socket.gettimeout()
        self.socket.settimeout(timeout)
        try:
            while True:
                message = self._receive()
                if "method" in message:
                    return message
        except websocket.WebSocketTimeoutException:
            return None
        finally:
            self.socket.settimeout(old_timeout)

    def evaluate(self, expression: str, await_promise: bool = False) -> Any:
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": await_promise,
                "returnByValue": True,
                "userGesture": True,
            },
        )
        remote = result.get("result", {})
        if remote.get("subtype") == "error" or result.get("exceptionDetails"):
            raise CaptureError(f"JavaScript evaluation failed: {remote.get('description', result)}")
        return remote.get("value")


def connect_discord(port: int) -> tuple[dict[str, Any], CDPClient]:
    target = select_discord_target(get_targets(port))
    return target, CDPClient(str(target["webSocketDebuggerUrl"]))


def _authorization_from_headers(headers: dict[str, Any]) -> str | None:
    for key, value in headers.items():
        if key.lower() == "authorization" and isinstance(value, str) and value.strip():
            lowered = value.strip().lower()
            if lowered not in {"undefined", "null"}:
                return value.strip()
    return None


def capture_authorization(client: CDPClient, timeout: int = 30, reload_page: bool = True) -> str:
    """Capture an Authorization request header in memory without displaying it."""
    client.call("Network.enable", {"maxTotalBufferSize": 0, "maxResourceBufferSize": 0})
    client.call("Page.enable")
    if reload_page:
        client.call("Page.reload", {"ignoreCache": False})
    deadline = time.monotonic() + timeout
    discord_api_request_ids: set[str] = set()
    pending_extra_headers: dict[str, dict[str, Any]] = {}
    while time.monotonic() < deadline:
        event = client.event(timeout=min(1, max(0.05, deadline - time.monotonic())))
        if not event:
            continue
        method = event.get("method")
        params = event.get("params", {})
        headers: dict[str, Any] = {}
        if method == "Network.requestWillBeSent":
            request = params.get("request", {})
            url = str(request.get("url", ""))
            if not re.search(r"https://(?:[^/]+\.)?(?:discord\.com|discordapp\.com)/api/", url):
                continue
            request_id = str(params.get("requestId", ""))
            discord_api_request_ids.add(request_id)
            headers = request.get("headers", {})
            authorization = _authorization_from_headers(headers)
            if not authorization and request_id in pending_extra_headers:
                authorization = _authorization_from_headers(pending_extra_headers.pop(request_id))
            if authorization:
                return authorization
        elif method == "Network.requestWillBeSentExtraInfo":
            request_id = str(params.get("requestId", ""))
            headers = params.get("headers", {})
            if request_id not in discord_api_request_ids:
                pending_extra_headers[request_id] = headers
                continue
            authorization = _authorization_from_headers(headers)
            if authorization:
                return authorization
    raise CaptureError(
        "No Discord Authorization header was observed. Keep Discord logged in, open a channel, "
        "and retry with page reload enabled."
    )


@dataclass
class DiscordRest:
    authorization: str
    api_base: str = DISCORD_API
    timeout: int = 30
    max_retries: int = 5

    def __post_init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": self.authorization,
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 DiscordChatCapture/1.0",
            }
        )

    def get(self, path: str, params: dict[str, Any] | None = None, allow_missing: bool = False) -> Any:
        url = path if path.startswith("http") else f"{self.api_base}{path}"
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt + 1 == self.max_retries:
                    raise CaptureError(f"Discord API request failed for {path}: {exc}") from exc
                time.sleep(min(2**attempt, 8))
                continue
            if response.status_code == 429:
                try:
                    delay = float(response.json().get("retry_after", 1))
                except (ValueError, TypeError):
                    delay = 1
                time.sleep(max(0.25, min(delay, 60)))
                continue
            if allow_missing and response.status_code in (403, 404):
                return None
            if not response.ok:
                detail = response.text[:300].replace(self.authorization, "[redacted]")
                raise CaptureError(f"Discord API {response.status_code} for {path}: {detail}")
            try:
                return response.json()
            except ValueError as exc:
                raise CaptureError(f"Discord API returned non-JSON data for {path}") from exc
        raise CaptureError(f"Discord API retry limit reached for {path}")


def infer_guild_and_channel(url: str) -> tuple[str | None, str | None]:
    thread_match = re.search(r"/channels/(\d+|@me)/(\d+)/threads/(\d+)", url)
    if thread_match:
        guild = None if thread_match.group(1) == "@me" else thread_match.group(1)
        return guild, thread_match.group(3)
    match = re.search(r"/channels/(\d+|@me)/(\d+)", url)
    if not match:
        return None, None
    guild = None if match.group(1) == "@me" else match.group(1)
    return guild, match.group(2)


def extract_discord_links(value: Any) -> list[str]:
    """Collect Discord deep links from nested message content without resolving them."""
    found: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, str):
            found.update(link.rstrip(".,;:") for link in DISCORD_LINK_PATTERN.findall(item))
        elif isinstance(item, dict):
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return sorted(found)


def message_to_record(message: dict[str, Any], thread: dict[str, Any]) -> dict[str, Any]:
    author = message.get("author") or {}
    timestamp = message.get("timestamp")
    referenced = message.get("referenced_message")
    referenced_summary = None
    if isinstance(referenced, dict):
        referenced_author = referenced.get("author") or {}
        referenced_summary = {
            "message_id": str(referenced.get("id", "")),
            "channel_id": str(referenced.get("channel_id", "")),
            "author": referenced_author.get("global_name") or referenced_author.get("username") or "",
            "author_id": str(referenced_author.get("id", "")),
            "timestamp": referenced.get("timestamp"),
            "content": referenced.get("content", ""),
            "attachments": referenced.get("attachments") or [],
            "embeds": referenced.get("embeds") or [],
        }
    mentions = []
    for mention in message.get("mentions") or []:
        if isinstance(mention, dict):
            mentions.append(
                {
                    "id": str(mention.get("id", "")),
                    "username": mention.get("username", ""),
                    "global_name": mention.get("global_name"),
                }
            )
    return {
        "record_type": "thread",
        "guild_id": thread.get("guild_id"),
        "parent_id": thread.get("parent_id"),
        "thread_id": str(thread.get("id", "")),
        "thread_title": thread.get("name", ""),
        "thread_created_local": local_iso((snowflake_time(thread.get("id")) or datetime.now(timezone.utc)).isoformat()),
        "message_id": str(message.get("id", "")),
        "timestamp": timestamp,
        "time_local": local_iso(timestamp),
        "author": author.get("global_name") or author.get("username") or "",
        "username": author.get("username", ""),
        "author_id": str(author.get("id", "")),
        "content": message.get("content", ""),
        "attachments": message.get("attachments") or [],
        "embeds": message.get("embeds") or [],
        "mentions": mentions,
        "mention_roles": message.get("mention_roles") or [],
        "message_reference": message.get("message_reference"),
        "referenced_message": referenced_summary,
        "message_snapshots": message.get("message_snapshots") or [],
        "components": message.get("components") or [],
        "position": message.get("position"),
        "discord_links": extract_discord_links(message),
        "edited_timestamp": message.get("edited_timestamp"),
        "type": message.get("type"),
        "captured_at": utc_now_iso(),
    }


def fetch_thread_messages(
    api: DiscordRest,
    thread: dict[str, Any],
    max_pages: int = 200,
    cutoff: datetime | None = None,
) -> list[dict[str, Any]]:
    thread_id = str(thread["id"])
    messages: dict[str, dict[str, Any]] = {}

    # In a Discord thread the starter message normally has the same snowflake as the thread.
    starter = api.get(f"/channels/{thread_id}/messages/{thread_id}", allow_missing=True)
    if not isinstance(starter, dict) and thread.get("parent_id"):
        starter = api.get(
            f"/channels/{thread['parent_id']}/messages/{thread_id}", allow_missing=True
        )
    if isinstance(starter, dict) and starter.get("id"):
        messages[str(starter["id"])] = starter

    before: str | None = None
    for _ in range(max_pages):
        params: dict[str, Any] = {"limit": 100}
        if before:
            params["before"] = before
        page = api.get(f"/channels/{thread_id}/messages", params=params, allow_missing=True)
        if not isinstance(page, list) or not page:
            break
        for message in page:
            if isinstance(message, dict) and message.get("id"):
                messages[str(message["id"])] = message
        oldest = min(page, key=lambda item: int(item.get("id", 0)))
        before = str(oldest.get("id"))
        oldest_time = parse_time(oldest.get("timestamp"))
        if cutoff and oldest_time and oldest_time < cutoff:
            break
        if len(page) < 100:
            break

    selected: list[dict[str, Any]] = []
    for message in messages.values():
        is_starter = str(message.get("id")) == thread_id
        timestamp = parse_time(message.get("timestamp"))
        if cutoff and timestamp and timestamp < cutoff and not is_starter:
            continue
        record = message_to_record(message, thread)
        record["starter_available"] = thread_id in messages
        record["thread_message_count_hint"] = thread.get("message_count")
        selected.append(record)
    selected.sort(key=lambda item: item.get("timestamp") or "")
    return selected
