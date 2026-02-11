# OpenClaw Assistant (Home Assistant Add-on)

This add-on runs **OpenClaw** inside **Home Assistant OS (HAOS)**.

It’s designed to be friendly to non-technical users:
- The add-on provides a simple Home Assistant page (Ingress) with a terminal.
- You complete setup using OpenClaw’s built-in onboarding commands.

---

## 0) What is what? (quick explanation)

- **Ingress page** (inside Home Assistant): a landing page + terminal.
- **Gateway**: the OpenClaw server running inside the add-on container.
- **Gateway Web UI (Control UI)**: the web interface you open in your browser.

The Gateway UI is opened in a **separate tab** (not embedded), because Home Assistant Ingress can have WebSocket issues.

---

## 1) Install the add-on

1) Home Assistant → **Settings → Add-ons → Add-on store**
2) Add repository URL:
- Add-on store → ⋮ → **Repositories** → paste:
  - `https://github.com/techartdev/OpenClawHomeAssistant`
3) Install **OpenClaw Assistant**
4) Start the add-on

---

## 2) First-time setup (step-by-step)

Open the add-on page (Ingress). You will see:
- **Open Gateway Web UI** button
- **Terminal** embedded on the page

### Step A — Run OpenClaw onboarding

In the terminal, run:

- **Recommended**:
  - `openclaw onboard`

If you prefer:
- `openclaw configure`

Follow the prompts.

### Step B — Get your Gateway token (needed for the Web UI)

In the terminal run:

```sh
openclaw config get gateway.auth.token
```

Copy the token somewhere safe.

### Step C — Make the Gateway reachable from your browser

You have two common setups:

#### Option 1: Use Home Assistant HTTPS (recommended)
If your Home Assistant is already exposed via HTTPS (Nabu Casa, reverse proxy, etc.), use that.
This avoids browser security issues.

#### Option 2: LAN access (http://192.168.x.x) — using add-on options (recommended)
The easiest way to enable LAN access is via the add-on configuration:

1. Go to Home Assistant → **Settings → Add-ons → OpenClaw Assistant → Configuration**
2. Set the following options:
   - `gateway_bind_mode`: **lan** (enables LAN binding; use **loopback** for local-only access)
   - `gateway_port`: **18789** (or your preferred port)
   - `allow_insecure_auth`: **true** (required for HTTP access; see section 4 below)
3. Restart the add-on

The add-on will automatically update OpenClaw's configuration on startup.

#### Option 3: LAN access — manual configuration (advanced)
If you prefer to configure manually via terminal:

```sh
openclaw config set gateway.bind lan
openclaw config set gateway.port 18789
openclaw config set gateway.mode local
```

Then restart the add-on.

---

## 3) Configure the “Open Gateway Web UI” button

The button uses the add-on option:
- `gateway_public_url`

Set it in Home Assistant → Add-on configuration.

Examples:
- LAN:
  - `http://192.168.1.119:18789`
- Public HTTPS:
  - `https://example.duckdns.org:12345`

The button will open:

`<gateway_public_url>/?token=<your_token>`

If the UI says **Unauthorized**, you likely used the wrong token. Re-check it with:

```sh
openclaw config get gateway.auth.token
```

---

## 4) Important: “requires HTTPS or localhost (secure context)”

Modern browsers sometimes refuse to run the Control UI on **plain HTTP** unless it is **localhost**.
If you open the Gateway UI over LAN HTTP and see:

> control ui requires HTTPS or localhost (secure context)

You have 3 options:

### Option A — Use HTTPS (best)
Put the gateway behind HTTPS (recommended long-term).

### Option B — Use localhost via port-forward
Access it as `http://localhost:18789` using SSH port forwarding from your computer.

### Option C — Allow insecure auth (quick workaround; less secure)

**Via add-on configuration (recommended)**:
1. Go to Home Assistant → **Settings → Add-ons → OpenClaw Assistant → Configuration**
2. Set `allow_insecure_auth`: **true**
3. Restart the add-on

**Via terminal (manual)**:
```sh
openclaw config set gateway.controlUi.allowInsecureAuth true
```

Then restart the add-on.

This allows using the Control UI over LAN HTTP.

---

## 5) Add-on options (custom / HA-specific)

This add-on keeps options minimal but practical. See `openclaw_assistant_dev/config.yaml` for the full schema.

### Gateway Network Settings
Control how the OpenClaw gateway operates and binds to the network:

- **`gateway_mode`** (string: **local** or **remote**, default **local**)
  - **local**: Run the gateway locally in this add-on (recommended for most users)
  - **remote**: Connect to a remote gateway running elsewhere
  - This setting determines whether OpenClaw runs its own gateway or connects to an existing one

- **`gateway_bind_mode`** (string: **loopback** or **lan**, default **loopback**)
  - **loopback**: Bind to 127.0.0.1 only — secure, local access only
  - **lan**: Bind to all interfaces — accessible from your local network
  - Only applies when `gateway_mode` is **local**

- **`gateway_port`** (int, default **18789**)
  - Port number for the gateway to listen on
  - Only applies when `gateway_mode` is **local**

- **`enable_openai_api`** (bool, default **false**)
  - Enable the OpenAI-compatible Chat Completions endpoint (`/v1/chat/completions`)
  - Required for integrating with HA Assist pipeline via [Extended OpenAI Conversation](https://github.com/jekalmin/extended_openai_conversation)
  - See section 6 for full setup instructions

- **`allow_insecure_auth`** (bool, default **false**)
  - Allow HTTP authentication for gateway access on LAN
  - **WARNING**: Only enable if using HTTP (not HTTPS) for `gateway_public_url`
  - Required for browser access over HTTP (see section 4)

These settings are applied automatically on add-on startup. No need to run `openclaw config` commands manually.

### Terminal
- **`enable_terminal`** (bool, default **true**)
  - Enable or disable the web terminal button inside Home Assistant
  
- **`terminal_port`** (int, default **7681**)
  - Port number for the web terminal (ttyd) to listen on
  - Change this if port 7681 conflicts with another service on your system
  - Valid range: 1024-65535

Security note: the terminal gives shell access inside the add-on container.

### Home Assistant token
- `homeassistant_token` (optional)

If set, it is written to:
- `/config/secrets/homeassistant.token`

### Router SSH (generic)
For custom automations that need SSH access to a router/firewall or other LAN device:
- `router_ssh_host`
- `router_ssh_user`
- `router_ssh_key_path` (default `/data/keys/router_ssh`)

How to provide the key:
- Put the private key file under the add-on config directory so it appears in-container at `/data/keys/...`
- Recommended permissions: `chmod 600`

### Session cleanup
- `clean_session_locks_on_start` (bool, default **true**) — Remove stale lock files on startup
- `clean_session_locks_on_exit` (bool, default **true**) — Remove stale lock files on shutdown

---

## 6) Integrate with Home Assistant Assist Pipeline

OpenClaw's Gateway exposes an **OpenAI-compatible Chat Completions endpoint**. This means you can use OpenClaw as a **conversation agent** in Home Assistant's Assist pipeline — enabling voice control, automations, and smart home commands powered by OpenClaw.

### How it works

1. OpenClaw Gateway serves `POST /v1/chat/completions` (same port as the gateway)
2. [Extended OpenAI Conversation](https://github.com/jekalmin/extended_openai_conversation) (HACS integration) connects HA's Assist pipeline to any OpenAI-compatible endpoint
3. Both run on the same machine, so communication is via `127.0.0.1`

### Step 1 — Enable the OpenAI API endpoint

**Via add-on configuration (recommended)**:
1. Go to Home Assistant → **Settings → Add-ons → OpenClaw Assistant → Configuration**
2. Set `enable_openai_api`: **true**
3. Restart the add-on

**Via terminal (manual)**:
```sh
openclaw config set gateway.http.endpoints.chatCompletions.enabled true
```

### Step 2 — Install Extended OpenAI Conversation

1. Install [HACS](https://hacs.xyz/) if you haven't already
2. In HACS, add **Extended OpenAI Conversation** as a custom repository:
   - Repository: `https://github.com/jekalmin/extended_openai_conversation`
   - Category: **Integration**
3. Install it and restart Home Assistant

### Step 3 — Get your Gateway token

In the add-on terminal, run:

```sh
openclaw config get gateway.auth.token
```

Copy the token — you'll need it as the API key.

### Step 4 — Configure Extended OpenAI Conversation

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Extended OpenAI Conversation**
3. Configure:
   - **API Key**: Paste your gateway token
   - **Base URL**: `http://127.0.0.1:18789/v1` or a LAN url if you use `gateway_bind_mode: lan`
   - **API Version**: leave empty
   - **Organization**: leave empty
   - **Skip Authentication**: **true**

### Step 5 — Set as Conversation Agent

1. Go to **Settings → Voice Assistants**
2. Edit your assistant (default: "Home Assistant")
3. Under **Conversation agent**, select **Extended OpenAI Conversation**

### Step 6 — Expose entities

Expose the entities you want OpenClaw to control:
- Go to `http://{your-ha}/config/voice-assistants/expose`
- Toggle on the entities OpenClaw should be able to see and control

### Done!

You can now use Assist (voice or text) and OpenClaw will handle the conversation. It can:
- Control your smart home devices
- Answer questions using its skills
- Create automations
- Query entity history

**Tip**: If using LAN access (`gateway_bind_mode: lan`), other HA instances on your network can also connect to this endpoint.

---

## Troubleshooting

### Some skills fail to install (Homebrew errors)

If you see errors like:
- `Homebrew's x86_64 support on Linux requires a CPU with SSSE3 support!`
- `spawn brew ENOENT` or `brew: command not found`

**Cause**: Your CPU doesn't support SSSE3 instructions (required by Homebrew). This affects older CPUs like some Intel Atom, Celeron, or pre-2006 processors.

**Impact**: Skills that depend on CLI tools installed via Homebrew (e.g., `gemini`, `aider`) won't install. Core OpenClaw functionality still works.

**Solutions**:
1. **Use a newer CPU** with SSSE3 support (Intel Core 2 or newer, ~2006+)
2. **Install dependencies manually** if you know which tools are needed
3. **Use alternative skills** that don't require Homebrew dependencies

The add-on will still start and work - Homebrew is optional.

### I get ERR_CONNECTION_REFUSED
- The gateway is not reachable at that IP/port.
- Confirm bind/port in terminal:
  - `openclaw config get gateway.bind`
  - `openclaw config get gateway.port`

### The Gateway UI opens but shows Unauthorized
- Fetch the token:
  - `openclaw config get gateway.auth.token`

### Terminal isn’t visible
- Ensure `enable_terminal=true`
- Check logs for `Starting web terminal (ttyd)`
