---
name: linuxdo-topic-capture
description: "Capture Linux.do / L站 topic list titles, links, ids, categories/tags, reply/view/update snippets from the Codex in-app browser login session. Use when the user asks to 抓L站, linux.do帖子名, L站话题列表, 最近话题, or wants only titles to decide what to read. Default is list-only capture; do not open every topic or collect full replies unless explicitly requested. Do not use for Browser/iab repair, generic web research, Douyin/QQ/Discord capture, Cockpit/API, or full forum scraping; use the matching local skill."
---

# Linux.do Topic Capture

## Routing boundaries

Use this skill for:

- Linux.do/L站 topic list capture from an existing in-app browser login session.
- List-only title/link/id/category/reply-view-update snippets.

Do not use this skill for:

- Browser/iab unavailable or login/control repair -> use `codex-desktop-permission-browser-repair`.
- General internet research -> use `agent-reach`.
- Douyin/QQ/Discord capture -> use the matching capture skill.

## Default workflow

1. Use the Codex in-app Browser login session.
2. Confirm current tab is on `https://linux.do/`.
3. Capture list rows only by default: topic title, id, URL, and visible metadata.
4. Scroll gently, single-threaded, until the requested count is reached.
5. Save outputs under:
   `<YOUR_CHAT_CAPTURE_WORKSPACE>\work\samples\linuxdo`
6. Merge cumulative files only when requested or when continuing an existing capture set.

## Reference map

Read `references/original.md` when you need:

- exact Browser setup JavaScript;
- DOM extraction pattern;
- output filenames and merge rules;
- detailed safety/reporting rules;
- specific-topic follow-up behavior.

## Safety rules

- Do not post, reply, like, bookmark, edit settings, upload files, or access private messages.
- Do not extract or print cookies/tokens.
- Stop on CAPTCHA, rate limit, login errors, or unusual account warnings.
- Do not use screenshot/OCR for normal capture.
