#!/usr/bin/env python3
"""
OpenClaw config helper for Home Assistant add-on.
Safely reads/writes openclaw.json without corrupting it.
"""

import json
import os
import re
import sys
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("OPENCLAW_CONFIG_PATH", "/config/.openclaw/openclaw.json"))



def read_config():
    """Read and parse openclaw.json."""
    if not CONFIG_PATH.exists():
        return None
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as e:
        print(f"ERROR: Failed to read config: {e}", file=sys.stderr)
        return None


def write_config(cfg):
    """Write config back to file with nice formatting."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        return True
    except IOError as e:
        print(f"ERROR: Failed to write config: {e}", file=sys.stderr)
        return False


def get_gateway_setting(key, default=None):
    """Get a gateway setting from config."""
    cfg = read_config()
    if cfg is None:
        return default
    return cfg.get("gateway", {}).get(key, default)


def set_gateway_setting(key, value):
    """Set a gateway setting, preserving other config."""
    cfg = read_config()
    if cfg is None:
        cfg = {}
    
    if "gateway" not in cfg:
        cfg["gateway"] = {}
    
    cfg["gateway"][key] = value
    return write_config(cfg)


def apply_gateway_settings(mode: str, bind_mode: str, port: int, enable_openai_api: bool, allow_insecure_auth: bool):
    """
    Apply gateway settings to OpenClaw config.
    
    Args:
        mode: "local" or "remote"
        bind_mode: "loopback" or "lan"
        port: Port number to listen on (must be 1-65535)
        enable_openai_api: Enable OpenAI-compatible Chat Completions endpoint
        allow_insecure_auth: Allow insecure HTTP authentication
    """
    # Validate gateway mode
    if mode not in ["local", "remote"]:
        print(f"ERROR: Invalid mode '{mode}'. Must be 'local' or 'remote'")
        return False
    
    # Validate bind mode
    if bind_mode not in ["loopback", "lan"]:
        print(f"ERROR: Invalid bind_mode '{bind_mode}'. Must be 'loopback' or 'lan'")
        return False
    
    # Validate port range
    if port < 1 or port > 65535:
        print(f"ERROR: Invalid port {port}. Must be between 1 and 65535")
        return False
    
    cfg = read_config()
    if cfg is None:
        cfg = {}
    
    if "gateway" not in cfg:
        cfg["gateway"] = {}
    
    gateway = cfg["gateway"]
    
    # controlUi should be nested inside gateway
    if "controlUi" not in gateway:
        gateway["controlUi"] = {}
    
    # http.endpoints.chatCompletions should be nested inside gateway
    if "http" not in gateway:
        gateway["http"] = {}
    if "endpoints" not in gateway["http"]:
        gateway["http"]["endpoints"] = {}
    if "chatCompletions" not in gateway["http"]["endpoints"]:
        gateway["http"]["endpoints"]["chatCompletions"] = {}
    
    control_ui = gateway["controlUi"]
    chat_completions = gateway["http"]["endpoints"]["chatCompletions"]
    
    current_mode = gateway.get("mode", "")
    current_bind = gateway.get("bind", "")
    current_port = gateway.get("port", 18789)
    current_openai_api = chat_completions.get("enabled", False)
    current_insecure = control_ui.get("allowInsecureAuth", False)
    
    changes = []
    
    if current_mode != mode:
        gateway["mode"] = mode
        changes.append(f"mode: {current_mode} -> {mode}")
    
    if current_bind != bind_mode:
        gateway["bind"] = bind_mode
        changes.append(f"bind: {current_bind} -> {bind_mode}")
    
    if current_port != port:
        gateway["port"] = port
        changes.append(f"port: {current_port} -> {port}")
    
    if current_openai_api != enable_openai_api:
        chat_completions["enabled"] = enable_openai_api
        changes.append(f"chatCompletions.enabled: {current_openai_api} -> {enable_openai_api}")
    
    if current_insecure != allow_insecure_auth:
        control_ui["allowInsecureAuth"] = allow_insecure_auth
        changes.append(f"allowInsecureAuth: {current_insecure} -> {allow_insecure_auth}")
    
    if changes:
        if write_config(cfg):
            print(f"INFO: Updated gateway settings: {', '.join(changes)}")
            return True
        else:
            print("ERROR: Failed to write config")
            return False
    else:
        print(f"INFO: Gateway settings already correct (mode={mode}, bind={bind_mode}, port={port}, chatCompletions={enable_openai_api}, allowInsecureAuth={allow_insecure_auth})")
        return True


def apply_memory_settings(
    enable_memory: bool,
    session_indexing: bool,
    mem0_api_key: str,
    mem0_base_url: str,
    mem0_user_id: str,
    cognee_api_key: str,
    cognee_base_url: str,
) -> bool:
    """
    Apply memory-related settings to OpenClaw config.

    Configures built-in SQLite hybrid search, Mem0 plugin, and Cognee plugin.
    Only writes to file when values actually change.
    """
    cfg = read_config()
    if cfg is None:
        cfg = {}

    # --- Built-in memory search ---
    agents = cfg.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})

    # Build desired memorySearch block (add-on-managed keys only)
    sources = ["memory", "sessions"] if session_indexing else ["memory"]
    desired_memory = {
        "enabled": enable_memory,
        "query": {
            "maxResults": 6,
            "minScore": 0.35,
            "hybrid": {"enabled": True, "vectorWeight": 0.7, "textWeight": 0.3},
        },
        "cache": {"enabled": True, "maxEntries": 50000},
        "sync": {"onSessionStart": True, "onSearch": True, "watch": True},
        "sources": sources,
        "experimental": {"sessionMemory": session_indexing},
    }

    # Preserve user/OpenClaw-owned keys the add-on should not manage
    current_memory = defaults.get("memorySearch", {})
    for key in ("provider", "model", "remote", "fallback"):
        if key in current_memory:
            desired_memory[key] = current_memory[key]
    desired_compaction = {
        "memoryFlush": {"enabled": True, "softThresholdTokens": 40000}
    }

    current_compaction = defaults.get("compaction", {})

    changes = []

    if current_memory != desired_memory:
        defaults["memorySearch"] = desired_memory
        changes.append("memorySearch")

    if current_compaction != desired_compaction:
        defaults["compaction"] = desired_compaction
        changes.append("compaction")

    # --- Mem0 plugin ---
    plugins = cfg.setdefault("plugins", {})
    entries = plugins.setdefault("entries", {})

    if mem0_api_key:
        desired_mem0 = {
            "enabled": True,
            "config": {
                "apiKey": mem0_api_key,
                "baseUrl": mem0_base_url or "https://api.mem0.ai",
                "userId": mem0_user_id or "ha-user",
                "autoRecall": True,
                "autoCapture": True,
                "topK": 5,
            },
        }
        if entries.get("openclaw-mem0") != desired_mem0:
            entries["openclaw-mem0"] = desired_mem0
            changes.append("plugins.openclaw-mem0")
    elif "openclaw-mem0" in entries:
        # API key cleared — disable but preserve entry
        if entries["openclaw-mem0"].get("enabled") is not False:
            entries["openclaw-mem0"]["enabled"] = False
            changes.append("plugins.openclaw-mem0 disabled")

    # --- Cognee plugin ---
    if cognee_api_key:
        desired_cognee = {
            "enabled": True,
            "config": {
                "baseUrl": cognee_base_url or "https://api.cognee.ai",
                "apiKey": cognee_api_key,
            },
        }
        if entries.get("memory-cognee") != desired_cognee:
            entries["memory-cognee"] = desired_cognee
            changes.append("plugins.memory-cognee")
    elif "memory-cognee" in entries:
        # API key cleared — disable but preserve entry
        if entries["memory-cognee"].get("enabled") is not False:
            entries["memory-cognee"]["enabled"] = False
            changes.append("plugins.memory-cognee disabled")

    # Clean up empty containers to avoid writing unnecessary structure
    if not entries:
        del plugins["entries"]
    if not plugins:
        del cfg["plugins"]

    if changes:
        if write_config(cfg):
            print(f"INFO: Updated memory settings: {', '.join(changes)}")
            return True
        else:
            print("ERROR: Failed to write config")
            return False
    else:
        print("INFO: Memory settings already correct")
        return True


def main():
    """CLI entry point for use by run.sh"""
    if len(sys.argv) < 2:
        print("Usage: oc_config_helper.py <command> [args...]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "apply-gateway-settings":
        if len(sys.argv) != 7:
            print("Usage: oc_config_helper.py apply-gateway-settings <local|remote> <loopback|lan> <port> <enable_openai_api:true|false> <allow_insecure:true|false>")
            sys.exit(1)
        mode = sys.argv[2]
        bind_mode = sys.argv[3]
        port = int(sys.argv[4])
        enable_openai_api = sys.argv[5].lower() == "true"
        allow_insecure_auth = sys.argv[6].lower() == "true"
        success = apply_gateway_settings(mode, bind_mode, port, enable_openai_api, allow_insecure_auth)
        sys.exit(0 if success else 1)
    
    elif cmd == "apply-memory-settings":
        if len(sys.argv) != 9:
            print("Usage: oc_config_helper.py apply-memory-settings <enable_memory:true|false> <session_indexing:true|false> <mem0_api_key> <mem0_base_url> <mem0_user_id> <cognee_api_key> <cognee_base_url>")
            sys.exit(1)
        # Decode __EMPTY__ sentinel (bash can't reliably pass empty positional args)
        def _decode(val):
            return "" if val == "__EMPTY__" else val
        enable_memory = sys.argv[2].lower() == "true"
        session_indexing = sys.argv[3].lower() == "true"
        mem0_api_key = _decode(sys.argv[4])
        mem0_base_url = _decode(sys.argv[5])
        mem0_user_id = _decode(sys.argv[6])
        cognee_api_key = _decode(sys.argv[7])
        cognee_base_url = _decode(sys.argv[8])
        success = apply_memory_settings(
            enable_memory, session_indexing,
            mem0_api_key, mem0_base_url, mem0_user_id,
            cognee_api_key, cognee_base_url,
        )
        sys.exit(0 if success else 1)

    elif cmd == "get":
        if len(sys.argv) != 3:
            print("Usage: oc_config_helper.py get <key>")
            sys.exit(1)
        key = sys.argv[2]
        value = get_gateway_setting(key)
        if value is not None:
            print(value)
        sys.exit(0)
    
    elif cmd == "set":
        if len(sys.argv) != 4:
            print("Usage: oc_config_helper.py set <key> <value>")
            sys.exit(1)
        key = sys.argv[2]
        value = sys.argv[3]
        # Try to convert to int if it looks like a number
        try:
            value = int(value)
        except ValueError:
            pass
        success = set_gateway_setting(key, value)
        sys.exit(0 if success else 1)
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
