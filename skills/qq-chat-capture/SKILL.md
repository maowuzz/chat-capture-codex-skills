---
name: qq-chat-capture
description: "Capture, index, summarize, pause, and organize QQ group chat records from the local QQNT + LiteLoaderQQNT + LLOneBot OneBot setup. Use when the user asks to 抓取QQ聊天记录, 恢复/停止QQ监控, 从暂停时间到现在拉取QQ群消息, 汇总QQ群新消息, 检查OneBot连接, or organize QQ chat output files under the chat-record robot workspace. Do not use for Discord capture, Hermes route-only forwarding, Codex Desktop repair, Cockpit/API, or web research; use the matching local skill."
---

# QQ Chat Capture

## Routing boundaries

Use this skill for:

- QQ group chat capture from QQNT + LiteLoaderQQNT + LLOneBot.
- Manual or incremental pull since pause time.
- QQ output indexing, summarizing, and organization.

Do not use this skill for:

- Discord capture -> use `discord-chat-capture`.
- Route-only QQ/微信/飞书 forwarding -> use `hermes-message-router`.
- Codex Desktop/Cockpit/API repair -> use the relevant local repair skill.

## Default workflow

1. Use workspace:
   `<YOUR_CHAT_CAPTURE_WORKSPACE>`
2. Check pause state:
   `work\samples\manual_pause_state.json`
3. Check OneBot:
   `ws://127.0.0.1:<ONEBOT_WS_PORT>`
4. For normal manual capture, run from workspace:
   `python work\qq_tech_sampler\onebot_sampler.py --config work\qq_tech_sampler\config.increment.tmp.yaml sample`
5. Re-index:
   `python work\qq_tech_sampler\qq_memory.py index`
6. Keep outputs under:
   `work\samples\qq\`

## Reference map

Read `references/original.md` when you need:

- exact health checks;
- known groups;
- pause/stop JSON shape;
- per-group and merged output paths;
- deduplication and SQLite rules;
- reporting format.

## Safety rules

- Do not uninstall QQ, LiteLoaderQQNT, or LLOneBot.
- Do not restore recurring automation unless the user explicitly asks.
- Do not start duplicate long-running samplers.
- Keep QQ outputs separate from Discord/other platforms.
