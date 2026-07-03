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

## Default workflow

1. Use workspace:
   `<YOUR_CHAT_CAPTURE_WORKSPACE>`
2. Check Discord debug endpoint:
   `http://127.0.0.1:<DISCORD_DEBUG_PORT>/json/list`
3. On Windows, launch or restart Discord in debug mode with:
   `powershell -ExecutionPolicy Bypass -File <SKILL_DIR>\scripts\start_discord_debug.ps1 -Port <DISCORD_DEBUG_PORT> -Restart`
4. Install runtime requirements once:
   `python -m pip install -r <SKILL_DIR>\scripts\requirements.txt`
5. For normal Discord thread/forum capture, prefer:
   `<SKILL_DIR>\scripts\discord_api_all_threads_sampler.py`
6. For a specific current thread, use:
   `<SKILL_DIR>\scripts\discord_api_thread_sampler.py`
   Parse both `/channels/<guild>/<thread>` and `/channels/<guild>/<parent>/threads/<thread>` routes; prefer the open URL's thread id over title-only matching.
7. For currently visible channel messages, use:
   `<SKILL_DIR>\scripts\discord_dom_sampler.py`
8. Resolve internal Discord jump links with:
   `<SKILL_DIR>\scripts\discord_jump_resolver.py`
9. Clean/merge/index with:
   `<SKILL_DIR>\scripts\discord_memory.py`
10. Keep outputs under:
   `work\samples\discord\`

## Reference map

Read `references/original.md` when you need:

- exact commands;
- known paths and canonical cumulative files;
- direct thread-id fallback;
- pause-time filtering;
- SQLite schema/output rules;
- reporting format.

## Safety rules

- Never print or persist Discord Authorization tokens.
- Do not use screenshot/OCR for normal capture.
- Do not restore recurring automation unless the user explicitly asks.
- Keep Discord outputs separate from QQ outputs.
