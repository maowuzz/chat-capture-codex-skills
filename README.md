# Chat Capture Codex Skills

一组用于 Codex 的聊天/帖子采集工作流 skills，适合把不同平台的可访问消息整理为本地 JSONL/SQLite/Markdown 资料，方便后续搜索、摘要和归档。

## 包含的 Skills

| Skill | 用途 |
| --- | --- |
| `qq-chat-capture` | 通过本地 QQNT + LiteLoaderQQNT + LLOneBot / OneBot 链路抓取 QQ 群消息、索引和增量整理 |
| `discord-chat-capture` | 通过 Discord Desktop remote debugging 抓取频道消息、论坛帖/Thread 正文和回复，并清洗合并 |
| `linuxdo-topic-capture` | 通过 Codex 内置浏览器登录态抓取 Linux.do / L站话题列表标题、链接和可见元数据 |
| `telegram-chat-capture` | 通过本地 Telethon session 增量抓取 Telegram/飞机群组、频道、私聊和归档聊天 |

## 适合场景

- 把自己有权限访问的聊天记录做本地备份。
- 定期增量抓取新消息。
- 把不同平台的数据分目录保存，避免 QQ/Discord/Telegram/Linux.do 混在一起。
- 后续用 Codex 做模糊搜索、主题摘要、技术线索整理。

## 不包含什么

本仓库只包含 Codex skill 工作流说明，不包含：

- 聊天记录
- 数据库
- cookie
- token
- Telegram session
- Telegram api_id / api_hash
- Discord Authorization
- QQ 群号/服务器 ID/个人账号信息

## 安装

把 `skills/` 目录下需要的 skill 文件夹复制到你的 Codex skills 目录，例如：

```text
<CODEX_HOME>\skills\
```

或个人用户目录：

```text
C:\Users\<YOUR_WINDOWS_USER>\.codex\skills\
```

然后重启 Codex Desktop。

## 使用方式

在 Codex 对话里可以这样说：

```text
使用 qq-chat-capture 抓取 QQ 聊天记录
使用 discord-chat-capture 抓取 Discord 帖子和回复
使用 linuxdo-topic-capture 抓取 L站最近话题
使用 telegram-chat-capture 抓取飞机增量聊天记录
```

每个 skill 的具体命令、路径和安全边界在对应的 `SKILL.md` 和 `references/` 里。

## 配置占位符

仓库中的示例全部使用占位符。使用前需要按你的机器环境替换：

```text
<YOUR_CHAT_CAPTURE_WORKSPACE>
<CODEX_HOME>
<BROWSER_VERSION>
<ONEBOT_WS_PORT>
<DISCORD_DEBUG_PORT>
<QQ_GROUP_ID_*>
<QQ_GROUP_NAME_*>
<DISCORD_SERVER_NAME>
<DISCORD_GUILD_ID>
<TELEGRAM_DIALOG_NAME>
<LOCAL_TELEGRAM_CONFIG_FILE>
<LOCAL_TELEGRAM_SESSION_DIR>
<LOCAL_SESSION_FILE>
```

## 安全边界

- 只抓取你自己有权限访问的聊天、群组、频道和帖子。
- 不要把 token、cookie、session、api_hash、验证码、密码提交到仓库。
- 不建议默认下载媒体文件；媒体会显著增加硬盘占用和隐私风险。
- 遇到平台验证码、限流、登录异常或账号警告时停止自动化。
- Discord/Telegram/QQ 的具体登录和授权需要用户自己在本机完成。

## 目录结构

```text
chat-capture-codex-skills/
  README.md
  LICENSE
  .gitignore
  docs/
    setup.md
    privacy.md
  skills/
    qq-chat-capture/
    discord-chat-capture/
    linuxdo-topic-capture/
    telegram-chat-capture/
```

