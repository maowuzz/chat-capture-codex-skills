---
name: discord-chat-capture
description: "Capture, paginate, clean, index, summarize, and organize Discord server channel messages and thread replies from the local Discord Desktop remote debugging setup. Use when the user asks to 抓Discord聊天记录, 抓帖子底下回复, 抓指定Discord服务器, 从暂停时间到现在拉取Discord, avoid screenshot/OCR capture, filter NSFW/adult channels, or organize Discord chat output files. Do not use for QQ/微信/飞书 routing, Codex Desktop Browser/iab repair, Cockpit/API, web research, or general thread orchestration; use the matching local skill."
---

# Discord Chat Capture

## Routing boundaries

Use this skill for:

- Discord Desktop remote-debug capture.
- Discord channel/thread pagination, cleanup, indexing, and summaries.
- <DISCORD_SERVER_NAME> server capture workflows.

Do not use this skill for:

- QQ chat capture -> use `qq-chat-capture`.
- General web/platform research -> use `agent-reach`.
- Codex Desktop Browser/iab or Cockpit/API repair -> use the relevant local repair skill.

## Fixed workspace and runtime

Default workspace:

```text
<YOUR_CHAT_CAPTURE_WORKSPACE>
```

Discord Desktop debug endpoint:

```text
http://127.0.0.1:<DISCORD_DEBUG_PORT>/json/list
```

Known server:

```text
<DISCORD_SERVER_NAME>
guild id: <DISCORD_GUILD_ID>
```

Bundled scripts (resolve `<SKILL_DIR>` to this skill folder):

```text
<SKILL_DIR>\scripts\discord_dom_sampler.py
<SKILL_DIR>\scripts\discord_api_thread_sampler.py
<SKILL_DIR>\scripts\discord_api_all_threads_sampler.py
<SKILL_DIR>\scripts\discord_memory.py
<SKILL_DIR>\scripts\discord_desktop_probe.py
```

Pause state shared with the chat-record robot:

```text
work\samples\manual_pause_state.json
```

Organized Discord outputs:

```text
work\samples\discord\channels\raw
work\samples\discord\channels\clean
work\samples\discord\threads\raw
work\samples\discord\threads\clean
work\samples\discord\db
work\samples\discord\probe
```

Canonical cumulative Discord outputs:

```text
work\samples\discord\channels\clean\discord_<DISCORD_SERVER_NAME>_channels_all_merged.clean.jsonl
work\samples\discord\threads\clean\discord_<DISCORD_SERVER_NAME>_threads_all_merged.clean.jsonl
work\samples\discord\db\discord_all_merged.sqlite3
```

## Rules

- Do not use screenshot or OCR for Discord message extraction.
- Do not print, save, or expose Discord Authorization tokens.
- Use API pagination for thread/forum posts. Discord "帖子/Thread" capture must include the post body/main message and all fetchable replies, not just the title or surrounding chat mention.
- Prefer `discord_<DISCORD_SERVER_NAME>_api_all_threads_sampler.py` over `discord_<DISCORD_SERVER_NAME>_api_thread_sampler.py` for normal manual/incremental thread capture because it discovers archived public threads/forum posts and keeps old threads that have recent activity.
- DOM capture alone is incomplete for large channels/threads and should not be treated as full thread-body capture.
- Exclude adult/NSFW-related channels or content when the user requests no色情/no adult. Default filter keywords: `成人|色情|r18|nsfw|喝茶吹水`.
- Keep Discord files separate from QQ files.
- Do not restore any recurring automation unless the user explicitly asks.
- After every successful manual or incremental capture, keep the increment files and also merge the new records into the canonical cumulative Discord files above.

## Runtime setup and health check

Install dependencies once:

```powershell
python -m pip install -r <SKILL_DIR>\scripts\requirements.txt
```

Run:

```powershell
cd <YOUR_CHAT_CAPTURE_WORKSPACE>
Invoke-RestMethod http://127.0.0.1:<DISCORD_DEBUG_PORT>/json/list
python <SKILL_DIR>\scripts\discord_desktop_probe.py --port <DISCORD_DEBUG_PORT>
```

If the endpoint is down and the user wants capture now, restart only Discord Desktop with the debug port:

```powershell
Get-Process Discord -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Start-Process "$env:LOCALAPPDATA\Discord\app-<YOUR_DISCORD_VERSION>\Discord.exe" -ArgumentList "--remote-debugging-port=9333" -WindowStyle Hidden
```

If the installed Discord version path differs, locate it under:

```text
C:\Users\<YOUR_WINDOWS_USER>\AppData\Local\Discord
```

## Channel capture

DOM channel capture is useful for currently loadable channel messages:

```powershell
cd <YOUR_CHAT_CAPTURE_WORKSPACE>
python <SKILL_DIR>\scripts\discord_dom_sampler.py --port 9333 --days 15 --scrolls 20 --out work\samples\discord\channels\raw\discord_<DISCORD_SERVER_NAME>_channels_raw.jsonl
python <SKILL_DIR>\scripts\discord_memory.py clean --input work\samples\discord\channels\raw\discord_<DISCORD_SERVER_NAME>_channels_raw.jsonl --output work\samples\discord\channels\clean\discord_<DISCORD_SERVER_NAME>_channels.clean.jsonl
```

Warn the user if they need true full channel history: DOM capture may miss virtualized/off-screen history. A dedicated channel API paginator is needed for full channel backfill.

## Thread reply capture

Use API pagination for post/thread bodies and replies. Default to the all-threads sampler:

```powershell
cd <YOUR_CHAT_CAPTURE_WORKSPACE>
python <SKILL_DIR>\scripts\discord_api_all_threads_sampler.py --port 9333 --guild-id <DISCORD_GUILD_ID> --days 15 --max-pages 200 --out work\samples\discord\threads\raw\discord_<DISCORD_SERVER_NAME>_threads_recent_15d_body_api.raw.jsonl
```

Older fallback, only when the all-threads sampler fails:

```powershell
cd <YOUR_CHAT_CAPTURE_WORKSPACE>
python <SKILL_DIR>\scripts\discord_api_thread_sampler.py --port 9333 --days 15 --max-pages 80 --out work\samples\discord\threads\raw\discord_<DISCORD_SERVER_NAME>_threads_recent_15d_api.jsonl
```

This script captures Authorization only in memory through DevTools/network state. Never log or persist it.

Thread-body completeness expectations:

- `thread_title` is only the title.
- `content` is the message body/reply text.
- The first message in a thread usually represents the post body/main content.
- Include `attachments` and `embeds`; do not rely only on `content`.
- A thread can be old but still active. Treat `last_message_id`, archive timestamp, and fetched message timestamps as activity signals; do not filter solely by thread creation time.
- If the user says "正文", "帖子内容", "全部回复", or shows a forum/thread screenshot, run the all-threads sampler and merge results into the threads cumulative file.
- If the current Discord page URL is `/channels/<guild_id>/<thread_id>` or the page title is a specific thread title, directly fetch that `<thread_id>` first with:
  - `GET /api/v9/channels/<thread_id>` to confirm title, parent channel, last_message_id, and message_count.
  - `GET /api/v9/channels/<thread_id>/messages?limit=100&before=...` until no more pages.
  Do this even if the all-threads discovery output did not include the thread. Direct thread URL capture is the required fallback for active/unarchived forum posts that user-token discovery APIs may miss.
- After a user points at a specific thread/title, verify capture by searching the cumulative threads file for the title or thread id. If not found, run direct thread-id capture before reporting completion.

For incremental capture since pause, write raw and clean files like:

```text
work\samples\discord\threads\raw\discord_<DISCORD_SERVER_NAME>_threads_since_<YYYYMMDD_HHMMSS>.raw.jsonl
work\samples\discord\threads\clean\discord_<DISCORD_SERVER_NAME>_threads_since_<YYYYMMDD_HHMMSS>.clean.jsonl
```

After writing the clean increment, also merge it into:

```text
work\samples\discord\threads\clean\discord_<DISCORD_SERVER_NAME>_threads_all_merged.clean.jsonl
```

## Filter since pause time

Read:

```text
work\samples\manual_pause_state.json
```

Use `paused_at_iso` as the cutoff. Keep only records whose local or UTC timestamp is after the cutoff. Deduplicate by message id.

When the user asks for "after last capture", use each Discord stream's own cumulative max timestamp as the cutoff:

```text
channels: max time in work\samples\discord\channels\clean\discord_<DISCORD_SERVER_NAME>_channels_all_merged.clean.jsonl
threads: max time in work\samples\discord\threads\clean\discord_<DISCORD_SERVER_NAME>_threads_all_merged.clean.jsonl
```

For Discord records, typical timestamp fields:

```text
time_local
timestamp
time
```

For thread records, typical fields:

```text
thread_id
thread_title
thread_created_local
message_id
time_local
author
username
content
attachments
embeds
```

For channel records, typical fields:

```text
message_id
title
url
text
time
time_local
author
channel_text
channel_id_hint
captured_at
```

## SQLite outputs

For incremental Discord output, create or refresh:

```text
work\samples\discord\db\discord_since_<YYYYMMDD_HHMMSS>.sqlite3
```

Use tables:

```text
discord_channels(message_id, time_local, channel, author, text, raw_json)
discord_threads(message_id, time_local, thread_title, author, content, raw_json)
```

For full recent thread history, known output:

```text
work\samples\discord\db\discord_threads.sqlite3
```

After each capture, refresh the cumulative SQLite DB:

```text
work\samples\discord\db\discord_all_merged.sqlite3
```

Merge rule: append only records not already present, deduplicate by `message_id` plus stream type (`channel` or `thread`). Sort JSONL by `time_local`/`timestamp` after merging. Keep per-run `since...to...` files for audit, but use the cumulative files as the default search source.

## Reporting format

Report separately:

- normal channel message count, time range, top channels, top authors
- thread reply count, time range, top threads, top authors
- whether adult/NSFW filtering was applied
- raw, clean, and SQLite paths
- cumulative files updated

Explicitly state if channel capture is DOM-limited or API-paginated.
