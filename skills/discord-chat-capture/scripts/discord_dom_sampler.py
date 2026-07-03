#!/usr/bin/env python3
"""Capture currently loadable Discord channel messages from the Desktop DOM."""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from discord_capture_lib import (
    CaptureError,
    connect_discord,
    infer_guild_and_channel,
    local_iso,
    parse_time,
    utc_now_iso,
    write_jsonl,
)


EXTRACT_JS = r"""
(() => {
  const channel = location.pathname.split('/').filter(Boolean).pop() || '';
  const channelText = (
    document.querySelector('h1')?.innerText ||
    document.querySelector('[class*="title"]')?.innerText ||
    document.title || ''
  ).trim();
  const nodes = [...document.querySelectorAll('[id^="message-content-"]')];
  return nodes.map(content => {
    const messageId = content.id.replace('message-content-', '');
    const root = content.closest('li[id^="chat-messages-"]') ||
                 content.closest('[data-list-item-id*="chat-messages"]') ||
                 content.closest('[class*="message"]') || content.parentElement;
    const authorNode = root?.querySelector('[id^="message-username-"], [class*="username"]');
    const timeNode = root?.querySelector('time');
    const links = [...(root?.querySelectorAll(
      'a[href*="cdn.discordapp.com"],a[href*="media.discordapp.net"],a[href*="attachments"]'
    ) || [])].map(a => a.href);
    const embeds = [...(root?.querySelectorAll('[class*="embed"]') || [])]
      .map(node => node.innerText?.trim()).filter(Boolean);
    return {
      message_id: messageId,
      text: content.innerText || content.textContent || '',
      author: authorNode?.innerText?.trim() || '',
      time: timeNode?.dateTime || timeNode?.getAttribute('datetime') || '',
      attachments: [...new Set(links)],
      embeds,
      channel_text: channelText,
      channel_id_hint: channel,
      url: `${location.origin}${location.pathname}`,
      title: document.title || ''
    };
  });
})()
"""


SCROLL_JS = r"""
(() => {
  const inner = document.querySelector('[data-list-id="chat-messages"]') ||
                document.querySelector('ol[role="list"]');
  let scroller = inner;
  while (scroller && scroller !== document.body && scroller.scrollHeight <= scroller.clientHeight) {
    scroller = scroller.parentElement;
  }
  if (!scroller) return {ok:false};
  const oldTop = scroller.scrollTop;
  scroller.scrollTop = 0;
  scroller.dispatchEvent(new Event('scroll', {bubbles:true}));
  return {ok:true, oldTop, scrollTop:scroller.scrollTop, scrollHeight:scroller.scrollHeight};
})()
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9333)
    parser.add_argument("--days", type=int, default=15)
    parser.add_argument("--scrolls", type=int, default=20)
    parser.add_argument("--wait", type=float, default=1.0, help="seconds to wait after each upward scroll")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    target, client = connect_discord(args.port)
    guild_id, channel_id = infer_guild_and_channel(str(target.get("url", "")))
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(args.days, 0)) if args.days else None
    captured: dict[str, dict[str, Any]] = {}
    try:
        client.call("Runtime.enable")
        for iteration in range(max(1, args.scrolls + 1)):
            values = client.evaluate(EXTRACT_JS)
            if isinstance(values, list):
                for row in values:
                    if not isinstance(row, dict) or not row.get("message_id"):
                        continue
                    timestamp = row.get("time") or None
                    row.update(
                        {
                            "record_type": "channel",
                            "guild_id": guild_id,
                            "channel_id_hint": row.get("channel_id_hint") or channel_id,
                            "time_local": local_iso(timestamp),
                            "captured_at": utc_now_iso(),
                        }
                    )
                    captured[str(row["message_id"])] = row
            known_times = [parse_time(row.get("time")) for row in captured.values()]
            known_times = [value for value in known_times if value]
            if cutoff and known_times and min(known_times) < cutoff:
                break
            if iteration >= args.scrolls:
                break
            state = client.evaluate(SCROLL_JS)
            if isinstance(state, dict) and not state.get("ok"):
                break
            time.sleep(max(0.1, args.wait))
    finally:
        client.close()

    rows = list(captured.values())
    if cutoff:
        rows = [row for row in rows if not parse_time(row.get("time")) or parse_time(row.get("time")) >= cutoff]
    rows.sort(key=lambda item: item.get("time") or "")
    count = write_jsonl(args.out, rows)
    print(f"captured={count} output={args.out} mode=DOM-limited")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureError as exc:
        raise SystemExit(f"error: {exc}")

