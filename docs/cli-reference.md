# CLI Reference

| Command | Description |
|---------|-------------|
| `nanobot onboard` | Initialize config & workspace at `~/.nanobot/` |
| `nanobot onboard --wizard` | Launch the interactive onboarding wizard |
| `nanobot onboard -c <config> -w <workspace>` | Initialize or refresh a specific instance config and workspace |
| `nanobot serve` | Start the OpenAI-compatible API (`/v1/chat/completions`) |
| `nanobot serve -c <config>` | Use a specific config file |
| `nanobot serve -w <workspace>` | Override workspace directory |
| `nanobot serve -p <port> -H <host>` | Bind address and port |
| `nanobot serve --verbose` | Show nanobot runtime logs |
| `nanobot gateway` | Start the gateway |
| `nanobot status` | Show status |
| `nanobot provider login openai-codex` | OAuth login for providers |
| `nanobot channels login <channel>` | Authenticate a channel interactively |
| `nanobot channels status` | Show channel status |

Programmatic use: `from nanobot.nanobot import Nanobot` then `await Nanobot.from_config().run("...")` (see [Python SDK](./python-sdk.md)).
