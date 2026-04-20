<div align="center">
  <p>
    <a href="https://pypi.org/project/nanobot-ai/"><img src="https://img.shields.io/pypi/v/nanobot-ai" alt="PyPI"></a>
    <a href="https://pepy.tech/project/nanobot-ai"><img src="https://static.pepy.tech/badge/nanobot-ai" alt="Downloads"></a>
    <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <a href="https://github.com/HKUDS/nanobot/graphs/commit-activity" target="_blank">
        <img alt="Commits last month" src="https://img.shields.io/github/commit-activity/m/HKUDS/nanobot?labelColor=%20%2332b583&color=%20%2312b76a"></a>
    <a href="https://github.com/HKUDS/nanobot/issues?q=is%3Aissue%20is%3Aclosed" target="_blank">
        <img alt="Issues closed" src="https://img.shields.io/github/issues-search?query=repo%3AHKUDS%2Fnanobot%20is%3Aissue%20is%3Aclosed&label=issues%20closed&labelColor=%20%237d89b0&color=%20%235d6b98"></a>
    <a href="https://twitter.com/intent/follow?screen_name=nanobot_project" target="_blank">
        <img src="https://img.shields.io/twitter/follow/nanobot_project?logo=X&color=%20%23f5f5f5" alt="follow on X(Twitter)"></a>
    <a href="https://nanobot.wiki/docs/latest/getting-started/nanobot-overview"><img src="https://img.shields.io/badge/Docs-nanobot.wiki-blue?style=flat&logo=readthedocs&logoColor=white" alt="Docs"></a>
    <a href="./COMMUNICATION.md"><img src="https://img.shields.io/badge/Feishu-Group-E9DBFC?style=flat&logo=feishu&logoColor=white" alt="Feishu"></a>
    <a href="./COMMUNICATION.md"><img src="https://img.shields.io/badge/WeChat-Group-C5EAB4?style=flat&logo=wechat&logoColor=white" alt="WeChat"></a>
    <a href="https://discord.gg/MnCvHqpUGB"><img src="https://img.shields.io/badge/Discord-Community-5865F2?style=flat&logo=discord&logoColor=white" alt="Discord"></a>
  </p>
</div>

🐈 **nanobot** is an open-source and ultra-lightweight AI agent in the spirit of [OpenClaw](https://github.com/openclaw/openclaw), [Claude Code](https://www.anthropic.com/claude-code), and [Codex](https://www.openai.com/codex/). It keeps the core agent loop small and readable while still supporting chat channels, memory, MCP and practical deployment paths, so you can go from local setup to a long-running personal agent with minimal overhead.

## 📢 News

- **2026-04-14** 🚀 Released **v0.1.5.post1** — Dream skill discovery, mid-turn follow-up injection, WebSocket channel, and deeper channel integrations. Please see [release notes](https://github.com/HKUDS/nanobot/releases/tag/v0.1.5.post1) for details.
- **2026-04-13** 🛡️ Agent turn hardened — user messages persisted early, auto-compact skips active tasks.
- **2026-04-12** 🔒 Lark global domain support, Dream learns discovered skills, shell sandbox tightened.
- **2026-04-11** ⚡ Context compact shrinks sessions on the fly; Kagi web search; QQ & WeCom full media.
- **2026-04-10** 📓 Notebook editing tool, multiple MCP servers, Feishu streaming & done-emoji.
- **2026-04-09** 🔌 WebSocket channel, unified cross-channel session, `disabled_skills` config.
- **2026-04-08** 📤 API file uploads, OpenAI reasoning auto-routing with Responses fallback.
- **2026-04-07** 🧠 Anthropic adaptive thinking, MCP resources & prompts exposed as tools.
- **2026-04-06** 🛰️ Langfuse observability, unified Whisper transcription, email attachments.
- **2026-04-05** 🚀 Released **v0.1.5** — sturdier long-running tasks, Dream two-stage memory, production-ready sandboxing and programming Agent SDK. Please see [release notes](https://github.com/HKUDS/nanobot/releases/tag/v0.1.5) for details.


## 💡 Key Features of nanobot

- **Ultra-lightweight**: stable long-running agent behavior with a small, readable core.
- **Research-ready**: the codebase is intentionally simple enough to study, modify, and extend.
- **Practical**: chat channels, memory, MCP, and deployment paths are already built in.
- **Hackable**: you can start fast, then go deeper through repo docs instead of a monolithic landing page.

## 📦 Install

> [!IMPORTANT]
> If you want the newest features and experiments, install from source. 
> 
> If you want the most stable day-to-day experience, install from PyPI or with `uv`.

**Install from source**

```bash
git clone https://github.com/HKUDS/nanobot.git
cd nanobot
pip install -e .
```

**Install with `uv`**

```bash
uv tool install nanobot-ai
```

**Install from PyPI**

```bash
pip install nanobot-ai
```

## 🚀 Quick Start

**1. Initialize**

```bash
nanobot onboard
```

**2. Configure** (`~/.nanobot/config.json`)

Configure these **two parts** in your config (other options have defaults). Add or merge the following blocks into your existing config instead of replacing the whole file.

*Set your API key*:

```json
{
  "providers": {
    "openaiCompat": {
      "apiKey": "sk-xxx"
    }
  }
}
```

*Set your model* (optionally pin a provider — defaults to auto-detection):

```json
{
  "agents": {
    "defaults": {
      "provider": "openai_compat",
      "model": "anthropic/claude-opus-4-6"
    }
  }
}
```

- Want different config options? Please refer to the stable docs at https://nanobot.wiki.

## 🏗️ Architecture

<p align="center">
  <img src="images/nanobot_arch.png" alt="nanobot architecture" width="800">
</p>

🐈 nanobot stays lightweight by centering everything around a small agent loop: messages come in from chat apps, the LLM decides when tools are needed, and memory or skills are pulled in only as context instead of becoming a heavy orchestration layer. That keeps the core path readable and easy to extend, while still letting you add channels, tools, memory, and deployment options without turning the system into a monolith.

## ✨ Features

<table align="center">
  <tr align="center">
    <th><p align="center">📈 24/7 Real-Time Market Analysis</p></th>
    <th><p align="center">🚀 Full-Stack Software Engineer</p></th>
    <th><p align="center">📅 Smart Daily Routine Manager</p></th>
    <th><p align="center">📚 Personal Knowledge Assistant</p></th>
  </tr>
  <tr>
    <td align="center"><p align="center"><img src="case/search.gif" width="180" height="400"></p></td>
    <td align="center"><p align="center"><img src="case/code.gif" width="180" height="400"></p></td>
    <td align="center"><p align="center"><img src="case/schedule.gif" width="180" height="400"></p></td>
    <td align="center"><p align="center"><img src="case/memory.gif" width="180" height="400"></p></td>
  </tr>
  <tr>
    <td align="center">Discovery • Insights • Trends</td>
    <td align="center">Develop • Deploy • Scale</td>
    <td align="center">Schedule • Automate • Organize</td>
    <td align="center">Learn • Memory • Reasoning</td>
  </tr>
</table>

## 📚 Docs

Browse the [repo docs](./docs/README.md) for the latest features and GitHub development version, or visit [nanobot.wiki](https://nanobot.wiki/docs/latest/getting-started/nanobot-overview) for the stable release documentation.

- For stable release documentation, visit [nanobot.wiki](https://nanobot.wiki/docs/latest/getting-started/nanobot-overview).

## 🤝 Contribute & Roadmap

PRs welcome! The codebase is intentionally small and readable. 🤗

### Branching Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases — bug fixes and minor improvements |
| `nightly` | Experimental features — new features and breaking changes |

**Unsure which branch to target?** See [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

**Roadmap** — Pick an item and [open a PR](https://github.com/HKUDS/nanobot/pulls)!

- **Multi-modal** — See and hear (images, voice, video)
- **Long-term memory** — Never forget important context
- **Better reasoning** — Multi-step planning and reflection
- **More integrations** — Calendar and more
- **Self-improvement** — Learn from feedback and mistakes

### Contributors

<a href="https://github.com/HKUDS/nanobot/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=HKUDS/nanobot&max=100&columns=12&updated=20260210" alt="Contributors" />
</a>


## ⭐ Star History

<div align="center">
  <a href="https://star-history.com/#HKUDS/nanobot&Date">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=HKUDS/nanobot&type=Date&theme=dark" />
      <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=HKUDS/nanobot&type=Date" />
      <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=HKUDS/nanobot&type=Date" style="border-radius: 15px; box-shadow: 0 0 30px rgba(0, 217, 255, 0.3);" />
    </picture>
  </a>
</div>

<p align="center">
  <em> Thanks for visiting ✨ nanobot!</em><br><br>
  <img src="https://visitor-badge.laobi.icu/badge?page_id=HKUDS.nanobot&style=for-the-badge&color=00d4ff" alt="Views">
</p>