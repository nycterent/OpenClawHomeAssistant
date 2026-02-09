# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant add-on that runs **OpenClaw** (an AI assistant gateway) inside Home Assistant OS. Provides an always-on gateway, an embedded web terminal (ttyd), and an Ingress landing page with links to the Gateway Web UI.

Current version: **0.5.39** with OpenClaw **2026.2.6-3**.

This is a **fork** of [techartdev/OpenClawHomeAssistant](https://github.com/techartdev/OpenClawHomeAssistant). The fork adds custom features (scripts.d hooks, Java 21 fix, Signal/Matrix deps). When syncing with upstream, merge or rebase against `techartdev/main` — the fork may be several versions ahead with local customizations.

## Repository Structure

All add-on code lives in `openclaw_assistant/`. The root contains only repo-level files (README.md, DOCS.md, repository.yaml).

Key files in `openclaw_assistant/`:
- **run.sh** — Container entrypoint (PID 1). Orchestrates startup: reads HA options, bootstraps config, starts gateway + ttyd + nginx, handles graceful shutdown via signal traps.
- **oc_config_helper.py** — Python utility for safe read-modify-write of `openclaw.json`. Called by run.sh to apply add-on settings without clobbering user config.
- **config.yaml** — HA add-on manifest. Defines the option schema, architecture support, Ingress settings, and default values.
- **Dockerfile** — Multi-arch container build. Installs Node.js 22, ttyd, Java 21 (Temurin), signal-cli, Chromium, Homebrew (as linuxbrew user), and OpenClaw via npm.
- **nginx.conf.tpl** / **landing.html.tpl** — Templates rendered at runtime with gateway token, public URL, and terminal port.
- **brew-wrapper.sh** — Allows root to delegate brew commands to the linuxbrew user via sudo.
- **scripts.d.examples/** — Example custom startup scripts (e.g., `10-signal-cli.sh` for Signal daemon).
- **translations/** — Multi-language YAML files for HA UI option labels.

## Architecture

```
run.sh (PID 1)
  ├── scripts.d/*.sh start  (custom startup hooks, alphabetical order)
  ├── openclaw gateway run  (port 18789, loopback or LAN)
  ├── ttyd                  (port 7681, localhost only)
  └── nginx                 (port 8099, HA Ingress)
        ├── /terminal/ → proxy to ttyd (WebSocket)
        └── /          → landing.html (rendered from template)
```

- **Three background services** managed by run.sh with PID tracking and SIGTERM propagation.
- **Custom scripts**: `/config/.openclaw/scripts.d/*.sh` executed on startup (alphabetical order, before gateway) and shutdown (reverse order). Scripts receive `start` or `stop` as $1.
- **Container exits** when the gateway process exits (`wait $GW_PID`).
- **Persistent storage** at `/config` (mapped to HA addon_config). Config lives at `/config/.openclaw/openclaw.json`, workspace at `/config/clawd`.
- **Config ownership**: The add-on only bootstraps a minimal config on first boot (gateway mode + auth token). All other config is owned by OpenClaw's onboarding tools. `oc_config_helper.py` surgically updates only gateway bind/port/mode/allowInsecureAuth without touching other keys.

## Build & Deployment

This is a **Home Assistant add-on** — there is no local build/test/lint workflow. The build system is HA's Docker-based add-on builder.

- **Base images** defined in `build.yaml`: Debian Bookworm for amd64, aarch64, armv7.
- **Dockerfile** is the single build artifact. To test changes, build with the HA add-on builder or `docker build`.
- **No CI/CD, no tests, no linter config** exists in this repo.
- Debian chosen over Alpine for glibc compatibility (native modules like clipboard, node-llama-cpp).

## Versioning

Two versions to track when updating:
1. **Add-on version** in `config.yaml` (`version: "0.5.39"`) — bump for any add-on change.
2. **OpenClaw version** in `Dockerfile` (`npm install -g openclaw@2026.2.6-3`) — update when upgrading upstream OpenClaw.

## Pinned Dependency Versions (Dockerfile)

| Dependency | Version | Location / Notes |
|---|---|---|
| Node.js | 22 LTS | NodeSource `setup_22.x` |
| OpenClaw | 2026.2.6-3 | `npm install -g openclaw@VERSION` |
| ttyd | 1.7.7 | Binary download from GitHub releases |
| Java (Temurin JRE) | 21 | Adoptium API; amd64/aarch64 only |
| signal-cli | 0.13.24 | `ARG SIGNAL_CLI_VERSION` |
| libsignal | 0.87.1 | `ARG LIBSIGNAL_VERSION` (non-amd64 patching) |

When bumping any of these, update the corresponding `ARG` or URL in the Dockerfile.

## Key Design Decisions

- **Gateway Web UI is NOT embedded in Ingress** — WebSockets are unreliable through HA's Ingress proxy. The landing page opens it in a new tab instead.
- **host_network: true** — Required for gateway network flexibility (LAN binding).
- **Single-instance guard** — File lock at `/config/.openclaw/gateway.start.lock` prevents concurrent starts.
- **Session lock cleanup** — Stale `.jsonl.lock` files from crashes are cleaned on start/exit (configurable). Cleanup is skipped if gateway is still running.
- **Terminal port validation** — Regex-validated in run.sh to prevent nginx config injection.
- **Homebrew runs as linuxbrew user** — Never as root. `brew-wrapper.sh` intercepts root calls and delegates via sudo. Homebrew install is non-fatal (graceful fallback for CPUs without SSSE3).
- **pnpm** — Installed globally; required by some OpenClaw skills (e.g., clawhub).
- **Java 21 (Temurin JRE)** — Required by signal-cli 0.13.x. Available for amd64 and aarch64 only; armv7 skipped (no builds exist).
- **signal-cli native library patching** — For non-amd64 arches, the Dockerfile downloads a compatible `libsignal_jni.so` from exquo/signal-libs-build and injects it into the libsignal-client jar.
- **Matrix plugin** — Extension deps installed post-`npm install -g` because global installs skip extension `node_modules`. The monorepo `workspace:*` devDependency must be stripped first.

## oc_config_helper.py CLI

Called by run.sh to safely modify `openclaw.json` without clobbering user settings:

```bash
# Apply all gateway settings at once (called during startup)
python3 /oc_config_helper.py apply-gateway-settings <local|remote> <loopback|lan> <port> <true|false>

# Get/set individual gateway keys
python3 /oc_config_helper.py get <key>
python3 /oc_config_helper.py set <key> <value>
```

Config path is read from `$OPENCLAW_CONFIG_PATH` (default: `/config/.openclaw/openclaw.json`).

## Configuration Flow

1. User sets options in HA UI → saved to `/data/options.json`
2. `run.sh` reads options with `jq`
3. `oc_config_helper.py apply-gateway-settings` updates `openclaw.json` (read-modify-write)
4. Custom startup scripts from `scripts.d/` run (before gateway)
5. Gateway, ttyd, and nginx start with applied settings
6. Landing page is rendered with token (queried via `openclaw config get`) and public URL

## Template Placeholder System

Templates (`nginx.conf.tpl`, `landing.html.tpl`) use `__PLACEHOLDER__` strings replaced by Python at runtime in run.sh:
- `__TERMINAL_PORT__` → nginx config (proxy target port)
- `__GATEWAY_TOKEN__` → landing page (auth token for UI button)
- `__GATEWAY_PUBLIC_URL__` → landing page (external URL)
- `__GW_PUBLIC_URL_PATH__` → landing page (trailing slash logic)

To add a new placeholder: define it in the template file, then add the replacement in the Python block in run.sh (~line 351).

## When Modifying Code

- **run.sh**: Keep `set +x` after reading secrets to avoid log leakage. Maintain the startup order (config → scripts.d → gateway → ttyd → nginx). Signal handler must kill all three services.
- **oc_config_helper.py**: Must preserve existing config keys — only update what the add-on manages. The nested path `gateway.controlUi.allowInsecureAuth` requires creating intermediate objects.
- **config.yaml**: The `schema` section must match the `options` section. Option types use HA add-on schema syntax (e.g., `int(1024,65535)?`, `list(local|remote)?`).
- **Dockerfile**: OpenClaw version is pinned (`npm install -g openclaw@VERSION`). ttyd architecture detection maps Docker TARGETARCH to ttyd release filenames. signal-cli and Java installs are arch-conditional (armv7 gets no Java).
- **Templates**: `__PLACEHOLDER__` strings are replaced by Python at runtime in run.sh. Add new placeholders there.
- **Translations**: Every option in config.yaml should have entries in all translation files under `translations/`.

## Upstream Sync

```bash
git remote add upstream https://github.com/techartdev/OpenClawHomeAssistant.git  # if not set
git fetch upstream
git merge upstream/main  # or rebase
```

After merging, check for OpenClaw version bumps in the Dockerfile and config.yaml version conflicts. The fork's version should always be >= upstream.
