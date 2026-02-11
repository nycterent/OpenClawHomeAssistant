# AGENTS.md

This file provides guidance to agentic coding assistants working with the OpenClaw Home Assistant add-on repository.

## Project Overview

Home Assistant add-on that runs OpenClaw (AI assistant gateway) inside Home Assistant OS. This is a fork of techartdev/OpenClawHomeAssistant with custom features (scripts.d hooks, Java 21, Signal/Matrix deps).

Primary languages: **Bash**, **Python**, **Dockerfile**  
Architecture: Multi-arch Docker container (amd64, aarch64, armv7)  
Testing: pytest for Python, no tests for shell scripts

## Build Commands

```bash
# Python tests (local development - no Docker required)
pip install -r requirements-test.txt       # One-time setup
pytest tests/ -v                           # Run all tests
pytest tests/test_oc_config_helper.py      # Run single test file
pytest tests/test_oc_config_helper.py::TestApplyMemorySettings -v  # Run single test class
pytest tests/ -k "test_set_creates"        # Run tests matching keyword

# Docker build (for local testing)
docker build -t openclaw-addon openclaw_assistant/

# Home Assistant add-on build (preferred)
# Use HA's add-on builder: https://github.com/home-assistant/builder
```

## Code Style Guidelines

### Python (oc_config_helper.py)

**File Structure:**
- Shebang: `#!/usr/bin/env python3`
- Module docstring describing purpose
- Imports: stdlib first (grouped), then third-party
- Constants in UPPER_CASE at module level
- Functions before classes, classes grouped by functionality

**Import Style:**
```python
import json
import os
import re
import sys
from pathlib import Path
```

**Function Style:**
- Docstrings for all public functions (imperative mood)
- Type hints not used (compatibility with older Python)
- Early returns for error conditions
- Explicit error handling with try/except

**Naming Conventions:**
- Functions: `snake_case` (e.g., `read_config`, `apply_gateway_settings`)
- Constants: `UPPER_CASE` (e.g., `CONFIG_PATH`)
- Local variables: `snake_case`
- Abbreviations allowed: `cfg` for config, `gw` for gateway

**Error Handling:**
```python
try:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
except (json.JSONDecodeError, IOError) as e:
    print(f"ERROR: Failed to read config: {e}", file=sys.stderr)
    return None
```

### Shell Scripts (run.sh, brew-wrapper.sh)

**Script Header:**
```bash
#!/usr/bin/env bash
set -euo pipefail
```

**Variable Style:**
- Environment variables: `UPPER_CASE`
- Local variables: `UPPER_CASE` (consistent with env vars)
- Always quote variables: `"$VARIABLE"`
- Use `${VAR}` syntax in strings

**Command Style:**
- Use long options when available for clarity
- Pipe stderr to stdout for logging: `2>&1`
- Check command existence: `command -v cmd >/dev/null`

**Error Handling:**
```bash
if [ ! -f "$OPTIONS_FILE" ]; then
  echo "Missing $OPTIONS_FILE (add-on options)."
  exit 1
fi
```

**Signal Handling:**
```bash
trap 'cleanup_on_exit' EXIT
trap 'handle_shutdown' SIGTERM SIGINT
```

### Tests (pytest)

**Test Structure:**
- Class-based organization: `TestFeatureName`
- Method names: `test_specific_behavior`
- Fixtures in `conftest.py`
- Descriptive assertions

**Test Style Example:**
```python
class TestApplyGatewaySettings:
    def test_creates_minimal_config_on_first_run(self, oc_helper, tmp_config):
        """Test that apply-gateway-settings creates initial config."""
        result = oc_helper.apply_gateway_settings("local", "loopback", 18789, True, False)
        assert result is True
        cfg = json.loads(tmp_config.read_text())
        assert cfg["gateway"]["mode"] == "local"
```

### YAML Files (config.yaml, translations)

**Style:**
- 2-space indentation
- No trailing spaces
- Multi-line strings use `|` for readability
- Keys in snake_case

### Docker/Dockerfile

**Best Practices:**
- Multi-stage builds when beneficial
- Combine RUN commands to minimize layers
- Pin all versions explicitly
- Use ARG for version management
- Clean up package caches in same layer

## Common Patterns

### Config Manipulation
Always use `oc_config_helper.py` for config changes. Never directly modify openclaw.json.

### Process Management
- Track PIDs for graceful shutdown
- Use `wait` for synchronization
- Kill child processes before exit

### Path Handling
- Use `/config/` for persistent storage
- Create directories with `mkdir -p`
- Always use absolute paths in scripts

## Security Considerations

- Validate all user inputs (especially ports)
- Never log secrets (`set +x` after reading)
- Run services as non-root when possible
- Use file locks to prevent race conditions

## Testing Philosophy

- Test configuration logic thoroughly (Python)
- Shell scripts tested manually (no unit tests)
- Integration testing via Docker builds
- Focus on error conditions and edge cases

## When Adding Features

1. Update `config.yaml` schema if adding options
2. Add translations for all supported languages
3. Update `CLAUDE.md` documentation
4. Add Python tests for config logic
5. Test multi-arch builds locally
6. Bump version in `config.yaml`

## Debugging Tips

- Check logs: `docker logs <container>`
- OpenClaw logs: `/config/.openclaw/logs/`
- Test config helper: `python3 oc_config_helper.py get gateway.mode`
- Validate JSON: `jq . /config/.openclaw/openclaw.json`

## Pull Request Checklist

- [ ] Python tests pass (`pytest tests/`)
- [ ] Shell scripts validated (`shellcheck *.sh`)
- [ ] Translations updated for new options
- [ ] Version bumped if needed
- [ ] CLAUDE.md updated for significant changes
- [ ] Tested on at least one architecture
