# Telegram capture workflow reference

## Files produced

Per-dialog cumulative files:

```text
work\samples\telegram\messages\<dialog_safe_name>\telegram_all_merged.jsonl
```

Per-run combined files:

```text
work\samples\telegram\messages\runs\telegram_capture_probe_<YYYYMMDD_HHMMSS>.jsonl
```

Dialog list:

```text
work\samples\telegram\dialogs\telegram_dialogs_latest.jsonl
```

Local credential/session placeholder:\r\n
```text
work\samples\telegram\<LOCAL_TELEGRAM_SESSION_DIR>\<LOCAL_SESSION_FILE>
```

## Example capture report fields

- Dialogs processed
- New records
- Media metadata records
- Per-dialog cap
- Whether media files were downloaded
- Run JSONL path

## Known notes

- Telegram "已归档聊天" is captured because archive is only a client folder; Telethon dialogs still expose accessible chats.
- Unread count is not message count.
- Per-dialog caps protect against very large channels.
- Existing cumulative files enable deduplication by message ID and timestamp filtering.
