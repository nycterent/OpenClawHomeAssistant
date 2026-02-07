# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant add-on that runs **OpenClaw** (an AI assistant gateway) inside Home Assistant OS. Provides an always-on gateway, an embedded web terminal (ttyd), and an Ingress landing page with links to the Gateway Web UI.

Current version: **0.5.35** with OpenClaw **2026.2.3-1**.

## Repository Structure

All add-on code lives in `openclaw_assistant/`. The root contains only repo-level files (README.md, DOCS.md, repository.yaml).

Key files in `openclaw_assistant/`:
- **run.sh** — Container entrypoint (PID 1). Orchestrates startup: reads HA options, bootstraps config, starts gateway + ttyd + nginx, handles graceful shutdown via signal traps.
- **oc_config_helper.py** — Python utility for safe read-modify-write of `openclaw.json`. Called by run.sh to apply add-on settings without clobbering user config.
- **config.yaml** — HA add-on manifest. Defines the option schema, architecture support, Ingress settings, and default values.
- **Dockerfile** — Multi-arch container build. Installs Node.js 22, ttyd, Chromium, Homebrew (as linuxbrew user), and OpenClaw via npm.
- **nginx.conf.tpl** / **landing.html.tpl** — Templates rendered at runtime with gateway token, public URL, and terminal port.
- **brew-wrapper.sh** — Allows root to delegate brew commands to the linuxbrew user via sudo.
- **translations/** — Multi-language YAML files for HA UI option labels.

## Architecture

```
run.sh (PID 1)
  ├── openclaw gateway run    (port 18789, loopback or LAN)
  ├── ttyd                    (port 7681, localhost only)
  └── nginx                   (port 8099, HA Ingress)
        ├── /terminal/ → proxy to ttyd (WebSocket)
        └── /          → landing.html (rendered from template)
```

- **Three background services** managed by run.sh with PID tracking and SIGTERM propagation.
- **Container exits** when the gateway process exits (`wait $GW_PID`).
- **Persistent storage** at `/config` (mapped to HA addon_config). Config lives at `/config/.openclaw/openclaw.json`, workspace at `/config/clawd`.
- **Config ownership**: The add-on only bootstraps a minimal config on first boot (gateway mode + auth token). All other config is owned by OpenClaw's onboarding tools. `oc_config_helper.py` surgically updates only gateway bind/port/mode/allowInsecureAuth without touching other keys.

## Build & Deployment

This is a **Home Assistant add-on** — there is no local build/test/lint workflow. The build system is HA's Docker-based add-on builder.

- **Base images** defined in `build.yaml`: Debian Bookworm for amd64, aarch64, armv7.
- **Dockerfile** is the single build artifact. To test changes, build with the HA add-on builder or `docker build`.
- **No CI/CD, no tests, no linter config** exists in this repo.
- Debian chosen over Alpine for glibc compatibility (native modules like clipboard, node-llama-cpp).

## Key Design Decisions

- **Gateway Web UI is NOT embedded in Ingress** — WebSockets are unreliable through HA's Ingress proxy. The landing page opens it in a new tab instead.
- **host_network: true** — Required for gateway network flexibility (LAN binding).
- **Single-instance guard** — File lock at `/config/.openclaw/gateway.start.lock` prevents concurrent starts.
- **Session lock cleanup** — Stale `.jsonl.lock` files from crashes are cleaned on start/exit (configurable). Cleanup is skipped if gateway is still running.
- **Terminal port validation** — Regex-validated in run.sh to prevent nginx config injection.
- **Homebrew runs as linuxbrew user** — Never as root. `brew-wrapper.sh` intercepts root calls and delegates via sudo.

## Configuration Flow

1. User sets options in HA UI → saved to `/data/options.json`
2. `run.sh` reads options with `jq`
3. `oc_config_helper.py apply-gateway-settings` updates `openclaw.json` (read-modify-write)
4. Gateway, ttyd, and nginx start with applied settings
5. Landing page is rendered with token (queried via `openclaw config get`) and public URL

## When Modifying Code

- **run.sh**: Keep `set +x` after reading secrets to avoid log leakage. Maintain the startup order (config → gateway → ttyd → nginx). Signal handler must kill all three services.
- **oc_config_helper.py**: Must preserve existing config keys — only update what the add-on manages. The nested path `gateway.controlUi.allowInsecureAuth` requires creating intermediate objects.
- **config.yaml**: The `schema` section must match the `options` section. Option types use HA add-on schema syntax (e.g., `int(1024,65535)?`, `list(local|remote)?`).
- **Dockerfile**: OpenClaw version is pinned (`npm install -g openclaw@VERSION`). ttyd architecture detection maps Docker TARGETARCH to ttyd release filenames.
- **Templates**: `__PLACEHOLDER__` strings are replaced by Python at runtime in run.sh. Add new placeholders there.
- **Translations**: Every option in config.yaml should have entries in all translation files under `translations/`.
