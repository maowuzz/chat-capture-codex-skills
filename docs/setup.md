# 安装与配置

## 1. 复制 skill

把需要的文件夹复制到 Codex skills 目录：

```text
<CODEX_HOME>\skills\
```

例如只需要 QQ：

```text
skills\qq-chat-capture -> <CODEX_HOME>\skills\qq-chat-capture
```

## 2. 准备工作区

建议新建一个独立工作区，用来放脚本、状态和输出：

```text
<YOUR_CHAT_CAPTURE_WORKSPACE>
```

不同平台建议分目录：

```text
work\samples\qq\
work\samples\discord\
work\samples\linuxdo\
work\samples\telegram\
```

## 3. 按平台配置

### QQ

需要本机 QQNT、LiteLoaderQQNT、LLOneBot 或兼容 OneBot 服务。

默认示例端口：

```text
ws://127.0.0.1:<ONEBOT_WS_PORT>
```

### Discord

需要 Discord Desktop 以 remote debugging 模式启动。

默认示例接口：

```text
http://127.0.0.1:<DISCORD_DEBUG_PORT>/json/list
```

### Linux.do

需要 Codex 内置浏览器中已有登录态。默认只抓话题列表，不打开每个帖子正文。

### Telegram

需要本地 Telethon 配置和 session。不要提交配置文件或 session 文件。

## 4. 验证

安装后在 Codex 里指定 skill 做小范围测试，例如：

```text
用 qq-chat-capture 做一次只读连通性检查
用 discord-chat-capture 检查 debug endpoint
用 linuxdo-topic-capture 测试抓 10 条话题
用 telegram-chat-capture 列出 dialogs，不输出敏感信息
```

