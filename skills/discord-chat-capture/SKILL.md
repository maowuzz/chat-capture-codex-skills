---
name: discord-chat-capture
description: "Capture, paginate, clean, index, summarize, and organize Discord server channel messages and thread replies from the local Discord Desktop remote debugging setup. Use when the user asks to 抓Discord聊天记录, 抓帖子底下回复, 抓<DISCORD_SERVER_NAME>服务器, 从暂停时间到现在拉取Discord, avoid screenshot/OCR capture, filter NSFW/adult channels, or organize Discord chat output files. Do not use for QQ/微信/飞书 routing, Codex Desktop Browser/iab repair, Cockpit/API, web research, or general thread orchestration; use the matching local skill."
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
3. For normal Discord thread/forum capture, prefer:
   `work\discord_sampler\discord_<DISCORD_SERVER_NAME>_api_all_threads_sampler.py`
4. For currently visible channel messages, use:
   `work\discord_sampler\discord_<DISCORD_SERVER_NAME>_dom_sampler.py`
5. Clean/merge with:
   `work\discord_sampler\discord_memory.py`
6. Keep outputs under:
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
