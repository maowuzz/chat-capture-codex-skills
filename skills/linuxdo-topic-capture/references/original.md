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

## Scope

Default site:

```text
https://linux.do/
```

Default output folder:

```text
<YOUR_CHAT_CAPTURE_WORKSPACE>\work\samples\linuxdo
```

Keep Linux.do data separate from QQ and Discord.

## Safety rules

- Default to list-only capture: topic title, topic id, URL, and visible row metadata.
- Do not open every topic by default.
- Do not post, reply, like, bookmark, edit settings, upload files, or access private messages.
- Use the Codex in-app browser login session; do not extract or print cookies/tokens.
- Use single-threaded, low-frequency page reads and gentle scrolling.
- Stop if the site shows errors, login problems, CAPTCHA, rate limit, or unusual account warnings.
- Do not use screenshot/OCR for normal capture.

## Browser setup

Use the `browser@openai-bundled` in-app browser skill path when available:

```text
<CODEX_HOME>\\plugins\\cache\\openai-bundled\\browser\\<BROWSER_VERSION>\skills\control-in-app-browser\SKILL.md
```

Connect via Node REPL and claim the existing user tab:

```js
const { setupBrowserRuntime } = await import("<CODEX_HOME>/plugins/cache/openai-bundled/browser/<BROWSER_VERSION>/scripts/browser-client.mjs");
await setupBrowserRuntime({ globals: globalThis });
globalThis.browser = await agent.browsers.get("iab");
const tabs = await browser.user.openTabs();
const linuxTabInfo = tabs.find(t => (t.url || "").startsWith("https://linux.do"));
globalThis.tab = await browser.user.claimTab(linuxTabInfo);
```

If no Linux.do tab exists, ask the user to open and log in first. Do not use system browser fallback for login-state capture.

## List-only capture workflow

1. Confirm the current tab is on `https://linux.do/`.
2. Extract visible topic links from DOM.
3. Gently scroll and repeat until the requested count is reached.
4. Save JSONL and Markdown under `work\samples\linuxdo`.
5. Optionally merge into a cumulative list file.

Use this extraction pattern:

```js
const rows = await tab.playwright.evaluate(() => {
  const out = [];
  const links = Array.from(document.querySelectorAll('a[href^="/t/"], a[href*="linux.do/t/"]'));
  for (const a of links) {
    const href = new URL(a.getAttribute("href"), location.origin).href;
    const m = href.match(/\/t\/[^/]+\/(\d+)(?:\/\d+)?$/) || href.match(/\/t\/topic\/(\d+)(?:\/\d+)?$/);
    const text = (a.textContent || "").trim().replace(/\s+/g, " ");
    if (!m || !text || /^\d+(\.\d+k|k)?$/i.test(text) || text.length < 4) continue;
    const topicId = m[1];
    let rowText = "";
    let p = a;
    for (let i = 0; i < 5 && p; i++, p = p.parentElement) {
      const t = (p.innerText || "").trim().replace(/\n{3,}/g, "\n\n");
      if (t.length > rowText.length && t.length < 1200) rowText = t;
    }
    out.push({ topicId, title: text.slice(0, 180), url: `https://linux.do/t/topic/${topicId}`, rowText: rowText.slice(0, 500) });
  }
  return out;
});
```

Deduplicate by `topicId`. Preserve per-run files like:

```text
linuxdo_topics_<count>_<YYYYMMDD_HHMMSS>.jsonl
linuxdo_topics_<count>_<YYYYMMDD_HHMMSS>.md
```

Cumulative files:

```text
linuxdo_topics_all_merged.jsonl
linuxdo_topics_all_merged.md
```

Merge rule: append new `topicId`s only, update existing rows if the new row has fresher visible metadata. Sort by capture order or latest capture time.

## Reporting

Report:

- requested count and captured count
- whether only topic list was captured
- first and last visible topics
- output paths
- whether cumulative files were updated

If the user asks for details of a specific topic later, open only that topic and extract its title/body/visible replies in a separate, explicit action.
