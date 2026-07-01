---
name: telegram-chat-capture
description: "Capture, incrementally merge, summarize, and organize Telegram/飞机 chat records using the user's local Telethon setup. Use when the user asks to 抓飞机, 抓Telegram聊天记录, 抓归档聊天, 抓频道/群组/个人, 从上次抓取后拉取飞机消息, or add Telegram to the QQ/Discord/L站 chat-record workflow. Do not use for QQ, Discord, Linux.do, Browser/iab repair, or Telegram account setup unless the request explicitly involves Telegram capture."
---

# Telegram Chat Capture

## Scope

Use this skill for:

- Telegram/飞机 messages from the local Telethon session.
- Groups, channels, private chats, and Telegram "已归档聊天".
- Incremental capture and cumulative JSONL organization.

Do not use this skill for:

- QQ -> use `qq-chat-capture`.
- Discord -> use `discord-chat-capture`.
- Linux.do -> use `linuxdo-topic-capture`.
- Screenshot/OCR extraction.
- Reading Telegram Desktop `tdata`.

## Workspace

Default workspace:

```text
<YOUR_CHAT_CAPTURE_WORKSPACE>
```

Core scripts:

```text
work\telegram_sampler\telegram_login_probe.py
work\telegram_sampler\telegram_list_dialogs.py
work\telegram_sampler\telegram_fetch_recent.py
work\telegram_sampler\telegram_capture_incremental.py
work\telegram_sampler\run_login_from_config.ps1
work\telegram_sampler\run_list_dialogs_from_config.ps1
work\telegram_sampler\run_fetch_recent_from_config.ps1
work\telegram_sampler\run_capture_incremental_from_config.ps1
```

Important state:

```text
work\samples\telegram\<LOCAL_TELEGRAM_CONFIG_FILE>
work\samples\telegram\<LOCAL_TELEGRAM_SESSION_DIR>\
work\samples\telegram\dialogs\telegram_dialogs_latest.jsonl
work\samples\telegram\messages\
work\samples\telegram\messages\runs\
```

`<LOCAL_TELEGRAM_CONFIG_FILE>` stores local login configuration through Windows CurrentUser DPAPI. Do not print or copy secret values.

## Expected verified state

- Telethon session should be created and verified with `LOGIN_OK`.
- Background capture can run without opening a visible PowerShell window if the wrapper script is configured that way.
- Telegram Desktop does not need to be open for capture if network/proxy works and the Telethon session remains valid.

## Standard capture

When the user says "抓一下飞机" or asks for Telegram capture without extra constraints, run:

```powershell
cd <YOUR_CHAT_CAPTURE_WORKSPACE>
powershell -ExecutionPolicy Bypass -NoProfile -File .\work\telegram_sampler\run_capture_incremental_from_config.ps1 -MaxDialogs 0 -LimitPerDialog 500 -IncludeUsers
```

Meaning:

- `-MaxDialogs 0`: capture all currently accessible dialogs.
- `-LimitPerDialog 500`: cap each group/channel/private chat at 500 fetched messages for that run.
- `-IncludeUsers`: include private chats.
- Existing per-dialog `telegram_all_merged.jsonl` files are used for dedup/incremental append.
- Media is recorded as metadata summary only; media files are not downloaded by default.

## Smaller tests

List dialogs:

```powershell
cd <YOUR_CHAT_CAPTURE_WORKSPACE>
powershell -ExecutionPolicy Bypass -NoProfile -File .\work\telegram_sampler\run_list_dialogs_from_config.ps1
```

Fetch one dialog:

```powershell
cd <YOUR_CHAT_CAPTURE_WORKSPACE>
powershell -ExecutionPolicy Bypass -NoProfile -File .\work\telegram_sampler\run_fetch_recent_from_config.ps1 -Entity "<TELEGRAM_DIALOG_NAME>" -Limit 100
```

## Reporting

Report:

- Total dialogs captured.
- Total new messages.
- Media summary count.
- Run JSONL path.
- Root per-dialog messages path.
- Whether this was capped per dialog.
- Whether media files were downloaded or only metadata was stored.

Use full absolute Windows paths in final replies.

## Safety

- Never output `api_hash`, Telegram login code, 2FA password, session content, or tokens.
- If the user shares a screenshot with a 2FA password or code, tell them to rotate the password after setup.
- Do not read Telegram Desktop `tdata` unless explicitly asked and risks are explained.
- Do not repeatedly retry login after auth failures; avoid account risk.
- If Telethon shows `TimeoutError`, check TUN/global proxy or configure a local proxy before retrying.

## Storage expectations

JSONL text records are small compared with media. Storage grows mainly if media download is enabled later.
