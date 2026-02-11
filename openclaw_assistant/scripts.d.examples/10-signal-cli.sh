#!/bin/bash
# Signal-CLI daemon startup script for OpenClaw Home Assistant addon
#
# Installation:
#   1. Copy this file to /config/.openclaw/scripts.d/10-signal-cli.sh
#   2. Make it executable: chmod +x /config/.openclaw/scripts.d/10-signal-cli.sh
#   3. Restart the addon
#
# Prerequisites:
#   - signal-cli must be installed (OpenClaw installs it during Signal channel setup)
#   - Signal account must be registered: signal-cli -a +PHONENUMBER register
#   - Signal channel must be configured in openclaw.json
#
# This script:
#   - Creates persistent storage for signal-cli data (survives container recreation)
#   - Starts signal-cli as an HTTP daemon on the port configured in openclaw.json
#   - Stops the daemon gracefully on container shutdown

set -euo pipefail

SIGNAL_DATA_DIR="/config/.openclaw/signal-cli-data"
SIGNAL_SYSTEM_DIR="/root/.local/share/signal-cli"
SIGNAL_PID_FILE="/var/run/signal-cli.pid"

CONFIG_FILE="/config/.openclaw/openclaw.json"

# Read Signal configuration from openclaw.json
get_config() {
  local key="$1"
  local default="${2:-}"
  jq -r "$key // empty" "$CONFIG_FILE" 2>/dev/null || echo "$default"
}

SIGNAL_ACCOUNT=$(get_config '.channels.signal.account')
SIGNAL_CLI_PATH=$(get_config '.channels.signal.cliPath')
SIGNAL_HTTP_URL=$(get_config '.channels.signal.httpUrl')

setup_persistence() {
  # Create persistent data directory
  mkdir -p "$SIGNAL_DATA_DIR"
  mkdir -p "$(dirname "$SIGNAL_SYSTEM_DIR")"

  # Link ephemeral system directory to persistent location
  if [ -L "$SIGNAL_SYSTEM_DIR" ]; then
    # Already a symlink - verify it points to correct location
    if [ "$(readlink "$SIGNAL_SYSTEM_DIR")" != "$SIGNAL_DATA_DIR" ]; then
      rm -f "$SIGNAL_SYSTEM_DIR"
      ln -s "$SIGNAL_DATA_DIR" "$SIGNAL_SYSTEM_DIR"
      echo "INFO: Updated signal-cli symlink to persistent storage"
    fi
  elif [ -d "$SIGNAL_SYSTEM_DIR" ]; then
    # Existing directory with data - migrate then symlink
    if [ "$(ls -A "$SIGNAL_SYSTEM_DIR" 2>/dev/null)" ]; then
      echo "INFO: Migrating existing signal-cli data to persistent storage..."
      cp -a "$SIGNAL_SYSTEM_DIR"/* "$SIGNAL_DATA_DIR"/ 2>/dev/null || true
    fi
    rm -rf "$SIGNAL_SYSTEM_DIR"
    ln -s "$SIGNAL_DATA_DIR" "$SIGNAL_SYSTEM_DIR"
    echo "INFO: Linked signal-cli data to persistent storage"
  else
    # No directory exists - create symlink
    ln -s "$SIGNAL_DATA_DIR" "$SIGNAL_SYSTEM_DIR"
    echo "INFO: Created signal-cli symlink to persistent storage"
  fi
}

start_daemon() {
  # Check if Signal channel is configured
  if [ -z "$SIGNAL_ACCOUNT" ] || [ -z "$SIGNAL_CLI_PATH" ]; then
    echo "INFO: Signal channel not configured in openclaw.json, skipping daemon"
    return 0
  fi

  # Check if signal-cli binary exists
  if [ ! -f "$SIGNAL_CLI_PATH" ]; then
    echo "WARN: signal-cli not found at $SIGNAL_CLI_PATH"
    echo "WARN: Install signal-cli or update channels.signal.cliPath in openclaw.json"
    return 0
  fi

  # Extract port from httpUrl (e.g., http://127.0.0.1:8080 -> 8080)
  local port
  port=$(echo "$SIGNAL_HTTP_URL" | sed -n 's/.*:\([0-9]*\)$/\1/p')
  port="${port:-8080}"

  # Check if account is registered (has data files)
  if [ ! -d "$SIGNAL_DATA_DIR/data" ] || [ -z "$(ls -A "$SIGNAL_DATA_DIR/data" 2>/dev/null)" ]; then
    echo "WARN: Signal account $SIGNAL_ACCOUNT is not registered"
    echo "WARN: To register, run inside the container:"
    echo "WARN:   $SIGNAL_CLI_PATH -a $SIGNAL_ACCOUNT register"
    echo "WARN: Then verify with the SMS code:"
    echo "WARN:   $SIGNAL_CLI_PATH -a $SIGNAL_ACCOUNT verify CODE"
    return 0
  fi

  # Check if daemon is already running
  if [ -f "$SIGNAL_PID_FILE" ]; then
    local old_pid
    old_pid=$(cat "$SIGNAL_PID_FILE" 2>/dev/null || echo "")
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
      echo "INFO: signal-cli daemon already running (PID $old_pid)"
      return 0
    fi
    rm -f "$SIGNAL_PID_FILE"
  fi

  echo "Starting signal-cli daemon for $SIGNAL_ACCOUNT on 127.0.0.1:$port..."
  # Force IPv4 to avoid Java binding to IPv6-mapped localhost
  export SIGNAL_CLI_OPTS="${SIGNAL_CLI_OPTS:-} -Djava.net.preferIPv4Stack=true"
  "$SIGNAL_CLI_PATH" -a "$SIGNAL_ACCOUNT" daemon --http "127.0.0.1:$port" &
  local pid=$!
  echo "$pid" > "$SIGNAL_PID_FILE"
  echo "INFO: signal-cli daemon started with PID $pid"

  # Give it a longer moment to start (Java JVM startup is slow)
  sleep 4
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "ERROR: signal-cli daemon failed to start or exited immediately"
    rm -f "$SIGNAL_PID_FILE"
    return 1
  fi
}

stop_daemon() {
  if [ -f "$SIGNAL_PID_FILE" ]; then
    local pid
    pid=$(cat "$SIGNAL_PID_FILE" 2>/dev/null || echo "")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "INFO: Stopping signal-cli daemon (PID $pid)..."
      kill -TERM "$pid" 2>/dev/null || true
      # Wait up to 5 seconds for graceful shutdown
      local count=0
      while kill -0 "$pid" 2>/dev/null && [ $count -lt 5 ]; do
        sleep 1
        count=$((count + 1))
      done
      # Force kill if still running
      if kill -0 "$pid" 2>/dev/null; then
        echo "WARN: signal-cli did not stop gracefully, forcing..."
        kill -9 "$pid" 2>/dev/null || true
      fi
      echo "INFO: signal-cli daemon stopped"
    fi
    rm -f "$SIGNAL_PID_FILE"
  fi
}

case "${1:-start}" in
  start)
    setup_persistence
    start_daemon
    ;;
  stop)
    stop_daemon
    ;;
  restart)
    stop_daemon
    sleep 1
    setup_persistence
    start_daemon
    ;;
  status)
    if [ -f "$SIGNAL_PID_FILE" ]; then
      pid=$(cat "$SIGNAL_PID_FILE" 2>/dev/null || echo "")
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        echo "signal-cli daemon is running (PID $pid)"
        exit 0
      fi
    fi
    echo "signal-cli daemon is not running"
    exit 1
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
