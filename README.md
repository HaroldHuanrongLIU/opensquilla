# OpenSquilla — Token-Efficient AI Agent

<p align="center">
  <img src="assets/opensquilla-long-logo.png" alt="OpenSquilla logo" width="500">
</p>

<p align="center">
  <a href="https://opensquilla.ai/"><img src="https://img.shields.io/badge/website-opensquilla.ai-blue?style=for-the-badge" alt="Website"></a>
  <a href="https://github.com/opensquilla/opensquilla/releases"><img src="https://img.shields.io/github/v/release/opensquilla/opensquilla?include_prereleases&style=for-the-badge" alt="GitHub release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=for-the-badge" alt="Apache 2.0 License"></a>
</p>

## Overview

OpenSquilla is a token-efficient, microkernel AI agent — same budget,
more capability, better results. It combines smart routing, persistent
memory, a secure sandbox, built-in web search, and local embeddings
under a single model loop.
Every entry point — Web UI, CLI, and chat channels — runs through a
shared `TurnRunner`, and a pluggable provider layer lets it speak to
OpenRouter, OpenAI, Anthropic, Ollama, DeepSeek, Gemini, Qwen/DashScope,
and roughly twenty other LLM providers without changes to your code or
config schema.

## Installation

OpenSquilla runs on Windows, macOS, and Linux. Pick the install path that
matches your use case; per-path prerequisites are summarized below.

| Path | Audience | When to use |
| --- | --- | --- |
| [Windows portable](#windows-portable-no-python) | Windows users | No Python toolchain; one-zip launch |
| [Install with uv](#install-with-uv) **(recommended)** | End users on any OS | Stable release wheel from a terminal |
| [Install from source](#install-from-source) | Users tracking `main` | Run from a checkout, not edit it |
| [Develop from source](#develop-from-source) | Contributors | Edit, test, or debug the source |

### Prerequisites

| Requirement | Windows portable | Install with uv | Install from source | Develop from source |
| --- | :---: | :---: | :---: | :---: |
| Python 3.12+ | bundled | via `uv` | via `uv` or system | via `uv` |
| Git + Git LFS | — | — | required | required |
| `uv` | — | required | recommended | required |
| Windows VC++ runtime | auto-installed | recommended | auto-installed | recommended |

`SquillaRouter` is included by default in every path. Set
`OPENSQUILLA_INSTALL_PROFILE=core` (or pass `--router disabled` at onboard)
only when you intentionally want to skip it. On Windows, see
[Troubleshooting → Visual C++ runtime](#windows-visual-c-runtime) if
startup prints `DLL load failed`.

Install links: [Git](https://git-scm.com/downloads) ·
[Git LFS](https://git-lfs.com/) ·
[uv](https://docs.astral.sh/uv/getting-started/installation/).

### Windows portable (no Python)

The fastest path on Windows. The zip ships a bundled CPython runtime, so
no separate Python install is required.

1. Download `OpenSquilla-windows-x64-portable.zip` from
   [GitHub Releases](https://github.com/opensquilla/opensquilla/releases/latest).
2. Extract it to Downloads, Documents, or another writable folder.
3. Right-click `Start OpenSquilla.cmd` → **Run as administrator**.
4. Complete onboarding, then open <http://127.0.0.1:18791/control/>.

> [!NOTE]
> OpenSquilla 0.1.0 preview builds are unsigned. Administrator launch is
> the supported path. If SmartScreen appears, choose **More info** →
> **Run anyway**. If Smart App Control or enterprise policy blocks the
> unsigned app, use [Install with uv](#install-with-uv) instead.
> References: [SmartScreen][ms-smartscreen] · [Smart App Control][ms-sac].

<details>
<summary>Advanced portable usage</summary>

Provide an OpenRouter key before first start:

```powershell
$env:OPENROUTER_API_KEY="sk-..."
Set-ExecutionPolicy -Scope Process Bypass
.\start.ps1
```

If `OPENROUTER_API_KEY` is set and no local config exists, the launcher
writes an env-reference config and starts the gateway without prompting.
If unset, the onboarding wizard lets you pick any supported provider.

The portable zip does not install a global `opensquilla` command. For a
terminal where `opensquilla …` works, run `OpenSquilla Shell.cmd`, or
call the bundled launcher directly:

```powershell
.\opensquilla.cmd onboard --provider openrouter --api-key-env OPENROUTER_API_KEY
```

</details>

[ms-smartscreen]: https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/
[ms-sac]: https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview

### Install with uv

Terminal install on Windows, macOS, or Linux. `uv` manages Python
automatically — no system Python required.

**Linux / macOS**

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
. "$HOME/.local/bin/env"
uv tool install "opensquilla[recommended] @ https://github.com/opensquilla/opensquilla/releases/latest/download/opensquilla-latest-py3-none-any.whl"
opensquilla onboard
opensquilla gateway run
```

**Windows PowerShell**

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
$env:Path = "$env:USERPROFILE\.local\bin;" + $env:Path
uv tool install "opensquilla[recommended] @ https://github.com/opensquilla/opensquilla/releases/latest/download/opensquilla-latest-py3-none-any.whl"
opensquilla onboard
opensquilla gateway run
```

> [!NOTE]
> Keep the quotes around `"opensquilla[recommended] @ …"` exactly as
> shown — the quotes prevent shells from interpreting the `[`, and the
> `@` form lets `uv` apply `[recommended]` to a URL install. Local
> wheel paths can use the simpler `path/to/wheel.whl[recommended]` form
> directly.

After install, see [Configuration](#configuration) for provider setup
and runtime options.

### Install from source

Use this path to run OpenSquilla from a checkout without editing it.
The clone is only the package source for the installer; after install,
use the `opensquilla` command — do not run `uv run`. Choose
[Develop from source](#develop-from-source) instead if you intend to
modify the code.

1. **Clone with LFS assets**

   ```sh
   git lfs install
   git clone https://github.com/opensquilla/opensquilla.git
   cd opensquilla
   git lfs pull --include="src/opensquilla/squilla_router/models/**"
   ```

   `git lfs install` and the LFS pull are both idempotent — safe to
   re-run.

2. **Run the installer**

   **macOS / Linux**

   ```sh
   bash install.sh
   ```

   **Windows PowerShell**

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\install.ps1
   ```

   PowerShell 7 users can substitute `pwsh` for `powershell`. The
   script installs `.[recommended]` (SquillaRouter + memory + local
   models) into a dedicated user environment via `uv tool install`,
   falling back to `python -m pip install --user` when `uv` is
   unavailable. Open a new terminal if `opensquilla` is not on `PATH`
   after install.

3. **(optional) Install advanced extras** into the same command. Most
   channel adapters work directly from the base install — Feishu,
   Telegram, DingTalk, QQ, WeCom, Slack, and Discord need no extra
   step. The available opt-in extras are:

   - `matrix` — Matrix channel (pulls in `matrix-nio`)
   - `matrix-e2e` — Matrix channel with end-to-end encryption (pulls in `matrix-nio[e2e]`; requires libolm)
   - `document-extras` — PDF generation via WeasyPrint

   ```sh
   OPENSQUILLA_INSTALL_EXTRAS=matrix bash install.sh                       # macOS / Linux
   ```

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Extras matrix   # Windows
   ```

4. **Configure and run** — see [Configuration](#configuration).

<details>
<summary>Installer environment variables and PATH checks</summary>

```sh
OPENSQUILLA_INSTALL_PROFILE=core   bash install.sh   # minimal runtime, no SquillaRouter
OPENSQUILLA_INSTALL_DRY_RUN=1      bash install.sh   # print the plan only
```

```powershell
$env:OPENSQUILLA_INSTALL_PROFILE="core"
$env:OPENSQUILLA_INSTALL_DRY_RUN="1"
```

To verify which `opensquilla` your shell will run:

```sh
command -v opensquilla    # macOS / Linux
where.exe opensquilla     # Windows
```

If `opensquilla` is not on `PATH`, run `uv tool update-shell` (uv
install) or add the Python user-scripts directory to `PATH` (pip
fallback). After reinstalling from a local checkout, restart the
gateway so it loads the updated package.

</details>

<details>
<summary>Install prerequisites from a terminal</summary>

Windows PowerShell:

```powershell
winget install --id Git.Git -e
winget install --id GitHub.GitLFS -e
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
git lfs install
```

macOS (Homebrew, optional — see <https://brew.sh/>):

```sh
brew install git git-lfs uv
git lfs install
```

Debian / Ubuntu:

```sh
sudo apt update && sudo apt install -y git git-lfs
curl -LsSf https://astral.sh/uv/install.sh | sh
git lfs install
```

Fedora:

```sh
sudo dnf install -y git git-lfs
curl -LsSf https://astral.sh/uv/install.sh | sh
git lfs install
```

Arch:

```sh
sudo pacman -S --needed git git-lfs
curl -LsSf https://astral.sh/uv/install.sh | sh
git lfs install
```

PATH changes from these installers apply to new terminal sessions.

</details>

### Develop from source

Use this path only to modify, test, or debug the current checkout.
Unlike [Install from source](#install-from-source), this path requires
`uv`: `uv sync` creates a checkout-local `.venv` and `uv run` executes
against the live source tree.

```sh
uv sync --extra recommended
uv run opensquilla --help
```

The `recommended` extra includes SquillaRouter for development too.
Use `uv sync` without `--extra recommended` only when intentionally
testing a minimal environment. Install additional extras into the same
environment you run:

```sh
uv sync --extra recommended --extra matrix
uv run opensquilla channels status matrix --json
```

In this mode, prefix every `opensquilla` command in
[Configuration](#configuration) with `uv run`. Do not debug a
development checkout through a user-local `opensquilla` command — that
command runs in a different Python environment.

## Configuration

### First-run config

`opensquilla onboard` is the human first-run setup command. It writes
the active config file and keeps provider secrets in environment
variables when you pass `--api-key-env`. `opensquilla onboard
--if-needed` is the idempotent entrypoint for repeatable scripts and
already-configured users; it skips only when a real config file exists
and the required provider setup is complete. Environment variables are
treated as candidate inputs until the config references them. The
router defaults to `recommended`, which enables SquillaRouter on
supported providers; pass `--router disabled` for direct single-model
routing, or `--router openrouter-mix` to keep the built-in OpenRouter
mixed-model routes.

Useful invocations:

```sh
opensquilla onboard                # full interactive wizard
opensquilla onboard --if-needed    # idempotent: script and repeat-install guard
opensquilla onboard --minimal      # provider only, skip channels and search
```

In SSH, CI, or any environment without a TTY, the interactive flow
exits with code 2. Use the non-interactive form — keep the secret in
the environment and pass its **name**, not its value:

**macOS / Linux**

```sh
export OPENROUTER_API_KEY="sk-..."
opensquilla onboard --provider openrouter --api-key-env OPENROUTER_API_KEY
```

**Windows PowerShell**

```powershell
$env:OPENROUTER_API_KEY="sk-..."
opensquilla onboard --provider openrouter --api-key-env OPENROUTER_API_KEY
```

To persist the key on macOS or Linux, add the same `export` line to
your shell profile. On Windows, use `setx OPENROUTER_API_KEY "sk-..."`
and reopen PowerShell. OpenRouter is only an example; substitute any
supported provider and its API-key variable.

> [!NOTE]
> On Windows, if the bundled router cannot initialize `onnxruntime`,
> OpenSquilla keeps running with a safe direct-route fallback. See
> [Troubleshooting → Visual C++ runtime](#windows-visual-c-runtime) to
> restore the bundled router.

**(optional)** Re-configure one section later without redoing the
whole wizard:

```sh
opensquilla configure provider --provider openai --model gpt-4o
opensquilla configure router --router recommended
opensquilla configure search   --search-provider brave
opensquilla configure image-generation --image-provider openrouter --api-key-env OPENROUTER_API_KEY
opensquilla configure channels                # interactive section
opensquilla configure channels --channel-type feishu --name feishu-main \
  --field app_id=cli_... --field app_secret=...
```

Sections: `provider`, `router`, `channels`, `search`,
`image-generation`, `memory-embedding`. The Web UI also exposes a
setup flow at `/control/setup` for provider, router tiers, optional
channels, and extras. Prefer `opensquilla configure <section>` over
provider-specific aliases for later edits.

Messaging-channel saves are config changes, not runtime-connectivity
proof. Restart the gateway after channel edits, then verify the live
adapter state:

```sh
opensquilla gateway restart
opensquilla channels status <name> --json
```

Treat a channel as connected only when the status payload reports
`enabled=true`, `configured=true`, and `connected=true`. Feishu
defaults to websocket mode and does not need a public URL in that
mode; Feishu webhook mode, Slack, and WeCom require a public,
provider-reachable URL.

The same JSON status payload also includes two support surfaces.
`capability_profile` covers transport-level facts such as group chat,
mentions, native file upload, replies, threads, cards, and reactions.
`platform_manifest` covers provider-level boundaries such as files,
attachments, docs, drive, wiki, permissions, and scope diagnostics.
Unsupported or config-required rows are intentional: they prevent the
product from claiming Feishu-style doc/wiki/drive behavior on
providers whose adapter or platform does not expose that surface yet.
Real tenant smoke tests remain opt-in and credential-gated.

**Config load order:** `OPENSQUILLA_GATEWAY_CONFIG_PATH` →
`./opensquilla.toml` → `~/.opensquilla/config.toml` → built-in
defaults. Onboarding writes the file at the path the runtime will
read; environment values for individual secrets always win over file
values.

### Run

```sh
opensquilla gateway run                # foreground, 127.0.0.1:18791
opensquilla gateway start --json       # background + health wait
opensquilla chat                       # interactive REPL
opensquilla agent -m "your prompt"     # one-shot, automation-friendly
```

Open the Web UI at <http://127.0.0.1:18791/control/> and check health
with `curl http://127.0.0.1:18791/health`. Press `Ctrl+C` to stop the
foreground gateway.

### Public network binding (optional)

To make the Web UI reachable from another machine, bind the gateway to
all interfaces and use the host's public IP address:

```sh
opensquilla gateway run --listen 0.0.0.0 --port 18791
# or, for a background process:
opensquilla gateway start --listen 0.0.0.0 --port 18791 --json
```

Then open `http://<public-ip>:18791/control/` and verify the public
health endpoint:

```sh
curl http://<public-ip>:18791/health
```

If another gateway is already bound to `18791`, stop it first or
choose a different `--port`. Public access also requires the host
firewall or cloud security group to allow inbound TCP on that port.
Do not expose the gateway publicly with `[auth] mode = "none"`;
configure token auth before binding to `0.0.0.0`.

### Docker and portable paths (optional)

`./start.sh` (or `start.ps1` on Windows) wraps `docker compose up -d`
and tails the gateway logs — convenient if you do not want a Python
toolchain on the host. Windows release zips that bundle a CPython
runtime are produced by the **Windows Release Assets** workflow;
portable users extract the zip and run its bundled launcher without a
system Python install.

### Further tuning

Provider-specific config, tier profiles, sandbox tuning, image
generation, and concurrency settings are managed through
`opensquilla onboard`, `opensquilla configure`, and
`opensquilla.toml.example`.

## Troubleshooting

### Windows: Visual C++ runtime

If startup logs `DLL load failed while importing
onnxruntime_pybind11_state`, OpenSquilla keeps running with a safe
router fallback, but the bundled SquillaRouter runtime is inactive
until the Visual C++ Redistributable for Visual Studio 2015–2022
(x64) is installed.

`install.ps1` attempts to install the redistributable via `winget`.
If that fails or `winget` is not present, install it manually and
restart PowerShell: <https://aka.ms/vs/17/release/vc_redist.x64.exe>.

To keep a first install quiet and direct while the runtime is being
fixed:

```powershell
$env:OPENROUTER_API_KEY="sk-..."
opensquilla onboard --provider openrouter --api-key-env OPENROUTER_API_KEY --router disabled --minimal
opensquilla gateway run
```

After installing the redistributable and reopening PowerShell, restore
the recommended router (re-set `OPENROUTER_API_KEY` in the new session
if you only used `$env:`):

```powershell
opensquilla onboard --provider openrouter --api-key-env OPENROUTER_API_KEY --router recommended
opensquilla gateway restart
```

## Benchmark Results

PinchBench 1.2.1 average results across 25 tasks:

| Agent | Base Model | Avg. score | Total input tokens | Total output tokens | Total cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| OpenSquilla | Model router (Opus4.7, GLM5.1, DS4 Flash) | 0.9251 | 1,721,328 | 61,475 | $0.688 |
| OpenClaw | Claude Opus 4.7 | 0.9255 | 3,066,243 | 50,890 | $6.233 |

## Key Features

- **Token-efficient routing** — local `SquillaRouter` (LightGBM + ONNX
  BGE classifier, `recommended` extra) routes each turn across four
  tiers (T0–T3). Hybrid features (length, language, code blocks,
  keywords + semantic embeddings) pick the cheapest model that can
  handle the turn; classification runs on-device, so your prompt never
  leaves the machine to make the decision.
- **Adaptive reasoning and prompts** — reasoning-token billing only
  kicks in when the turn needs deep thought, and the system prompt
  scales with task complexity (lightweight for trivial turns, full
  instructions for complex ones). No paying reasoning tokens for "hello".
- **On-demand skills** — built-in MCP client plus 15
  bundled skills (coding agents, GitHub, cron,
  pptx/docx/xlsx/pdf toolkits, summarization, tmux, weather, and more);
  only the skills needed for the current task are loaded into context,
  avoiding steady-state token waste.
- **Four-tier cognitive memory** — working (current task) → episodic
  (experience and causality) → semantic (facts and rules) → raw (audit
  and retraining base), mirroring human cognition.
- **Hybrid memory search + local embeddings** — Markdown source-of-truth
  memory with FTS keyword search alongside `sqlite-vec` semantic recall.
  Bundled ONNX inference runs on CPU so embeddings stay on your machine;
  optionally swap to OpenAI- or Ollama-hosted embeddings.
- **Adaptive recall and consolidation** — frequently used memories
  auto-promote and dated ones decay exponentially (with an "evergreen"
  opt-out); periodic Dream consolidation merges scattered episodic
  traces into structured knowledge, mirroring sleep consolidation, with
  bounded prompt-injection budgets throughout.
- **Layered security sandbox** — three policy tiers (Standard / Strict
  / Locked) on a permission-tier matrix, with Bubblewrap on Linux
  executing code in isolated environments (the macOS Seatbelt backend
  currently renders SBPL profiles only; process execution is pending).
  A denial ledger auto-pauses autonomous execution after repeated
  sandbox denials, rejected outputs are purged via intent + stale-output
  caches so the agent can't recover them through a side channel, and
  all skill metadata and tool results are XML-escaped to close common
  prompt-injection vectors.
- **Unified gateway across all entry points** — Starlette ASGI server on
  `127.0.0.1:18791` with WebSocket RPC and an embedded control console
  (`/control/`). Web UI, CLI, and first-class adapters for Terminal,
  WebSocket, Slack, Telegram, Discord, Feishu, DingTalk, WeCom,
  Matrix, and QQ all converge on a shared `TurnRunner` for
  consistent tool dispatch, retry, and decision logging.
- **20+ LLM providers** — OpenRouter, OpenAI, Anthropic, Ollama,
  DeepSeek, Gemini, DashScope/Qwen, Moonshot, Mistral, Groq, Zhipu,
  SiliconFlow, Volcengine, BytePlus, MiniMax, vLLM, LM Studio, OVMS, and
  more, with a primary-plus-fallback selector.
- **Durable sessions, agents, and scheduling** — SQLite-backed session,
  transcript, and replay storage with per-agent workspaces and a
  `reset`/flush contract that proves persistence before destructive
  rewrites; `SchedulerEngine` with an in-tree `CronExpression` parser
  plus stagger, reaper, and heartbeat services exposed via the
  `opensquilla cron` CLI.

## Credits

OpenSquilla is a token-efficient AI Agent inspired by
[OpenClaw](https://github.com/openclaw/openclaw). Bundled third-party content is fully attributed
in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Contributing

OpenSquilla is an open-source project and we welcome contributions of
every kind — bug reports, feature ideas, documentation, new provider or
channel adapters, skills, and core runtime work. Open an issue or a
pull request on [GitHub](https://github.com/opensquilla/opensquilla)
to get involved.
