---
name: qq-chat-capture
description: Capture, index, summarize, pause, and organize QQ group chat records from the local QQNT + LiteLoaderQQNT + LLOneBot OneBot setup. Use when the user asks to 抓取QQ聊天记录, 恢复/停止QQ监控, 从暂停时间到现在拉取QQ群消息, 汇总QQ群新消息, 检查OneBot连接, or organize QQ chat output files under the chat-record robot workspace.
---

# QQ Chat Capture

## Fixed workspace and runtime

Default workspace:

```text
<YOUR_CHAT_CAPTURE_WORKSPACE>
```

Current QQ stack:

```text
QQNT + LiteLoaderQQNT + LLOneBot
OneBot WebSocket: ws://127.0.0.1:<ONEBOT_WS_PORT>
```

Core scripts:

```text
work\qq_tech_sampler\onebot_sampler.py
work\qq_tech_sampler\qq_memory.py
```

Known groups:

```text
<QQ_GROUP_ID_1>  <QQ_GROUP_NAME_1>
<QQ_GROUP_ID_2>  <QQ_GROUP_NAME_2>
<QQ_GROUP_ID_3>  <QQ_GROUP_NAME_3>
```

Pause state:

```text
work\samples\manual_pause_state.json
```

Organized QQ outputs:

```text
work\samples\qq\groups
work\samples\qq\jsonl
work\samples\qq\live
work\samples\qq\db
work\samples\qq\state
work\samples\qq\backups
```

Canonical cumulative QQ outputs:

```text
work\samples\qq\jsonl\qq_group_<group_id>_merged.jsonl
work\samples\qq\jsonl\qq_all_groups_merged.jsonl
work\samples\qq\db\qq_messages.sqlite3
```

## Rules

- Do not restore recurring automation unless the user explicitly asks.
- Manual capture is allowed when the user asks to 抓一下/拉取/抓记录.
- Prefer read-only checks before restarting QQ or touching processes.
- Do not delete user-installed QQ, LiteLoaderQQNT, or LLOneBot unless the user explicitly asks.
- If OneBot is occupied or unreachable, diagnose the port/process instead of repeatedly restarting.
- Keep QQ and other platforms in separate folders; do not mix Discord or Telegram output into QQ folders.
- After every successful manual or incremental capture, keep the increment files and also merge the new records into the canonical cumulative QQ files above.

## Health check

Run from the workspace:

```powershell
cd <YOUR_CHAT_CAPTURE_WORKSPACE>
Get-Content -Raw work\samples\manual_pause_state.json
python work\qq_tech_sampler\qq_memory.py index
```

Check OneBot port:

```powershell
Test-NetConnection 127.0.0.1 -Port 3001
Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue
```

If QQ was closed, ask the user to reopen QQ first. After QQ is open, sample using the normal script instead of modifying the plugin chain.

## Manual capture workflow

Use the three-group config when the user wants all current QQ groups:

```powershell
cd <YOUR_CHAT_CAPTURE_WORKSPACE>
python work\qq_tech_sampler\onebot_sampler.py --config work\qq_tech_sampler\config.increment.tmp.yaml sample
python work\qq_tech_sampler\qq_memory.py index
```

If a command times out, check whether files were updated before rerunning:

```powershell
Get-Process python -ErrorAction SilentlyContinue
Get-ChildItem work\samples -File | Sort-Object LastWriteTime -Descending | Select-Object -First 20 Name,Length,LastWriteTime
```

Do not start duplicate long-running samplers if one is already writing JSONL files.

## Capture since pause time

Read pause time from:

```text
work\samples\manual_pause_state.json
```

Filter source JSONL files:

```text
work\samples\qq_group_<QQ_GROUP_ID_1>.jsonl
work\samples\qq_group_<QQ_GROUP_ID_2>.jsonl
work\samples\qq_group_<QQ_GROUP_ID_3>.jsonl
```

Write per-group increment files like:

```text
work\samples\qq\groups\qq_group_<group_id>_since_<YYYYMMDD_HHMMSS>.jsonl
```

Write merged increment file:

```text
work\samples\qq\jsonl\qq_all_groups_since_<YYYYMMDD_HHMMSS>.jsonl
```

After writing increment files, also update cumulative files:

```text
work\samples\qq\jsonl\qq_group_<group_id>_merged.jsonl
work\samples\qq\jsonl\qq_all_groups_merged.jsonl
```

Merge rule: append only records not already present, deduplicate by `(group_id, message_id, message_seq)` when available; otherwise use `(group_id, time_text, user_id, text)`. Sort by message time after merging.

Copy or refresh latest SQLite index to:

```text
work\samples\qq\db\qq_messages.sqlite3
```

## Reporting format

For each group, report:

- group id and name
- new message count
- first and last message time
- top active speakers
- concise content summary
- technical/important points
- output paths
- cumulative files updated

If there are no new messages, say so explicitly for each group.

## Stop/pause workflow

When the user asks to stop fetching or pause automation:

1. Stop only capture processes started for this task.
2. Do not uninstall QQ or plugins.
3. Record local time in `work\samples\manual_pause_state.json`.
4. State that automation was not restored.

Pause JSON shape:

```json
{
  "paused_at_local": "YYYY-MM-DD HH:mm:ss +08:00",
  "paused_at_iso": "YYYY-MM-DDTHH:mm:ss.sss+08:00",
  "reason": "User requested stop fetching; pull later",
  "automation_id": "qq-5"
}
```
