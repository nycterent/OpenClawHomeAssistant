"""Static analysis tests for run.sh environment variable exports.

These tests read run.sh as text and verify env var patterns — no shell execution.
"""

import re
from pathlib import Path

from conftest import PROJECT_ROOT

RUN_SH = PROJECT_ROOT / "openclaw_assistant" / "run.sh"


def _run_sh_text() -> str:
    return RUN_SH.read_text(encoding="utf-8")


class TestRunShEnvVars:
    def test_exports_openclaw_state_dir(self):
        text = _run_sh_text()
        assert re.search(r"^export OPENCLAW_STATE_DIR=", text, re.MULTILINE), (
            "run.sh must export OPENCLAW_STATE_DIR"
        )

    def test_exports_openclaw_config_path(self):
        text = _run_sh_text()
        assert re.search(r"^export OPENCLAW_CONFIG_PATH=", text, re.MULTILINE), (
            "run.sh must export OPENCLAW_CONFIG_PATH"
        )

    def test_exports_xdg_data_home(self):
        text = _run_sh_text()
        assert re.search(r"^export XDG_DATA_HOME=", text, re.MULTILINE), (
            "run.sh must export XDG_DATA_HOME"
        )

    def test_exports_xdg_cache_home(self):
        text = _run_sh_text()
        assert re.search(r"^export XDG_CACHE_HOME=", text, re.MULTILINE), (
            "run.sh must export XDG_CACHE_HOME"
        )

    def test_no_removed_env_vars(self):
        """Ensure the old fake env vars are not exported."""
        text = _run_sh_text()
        assert not re.search(r"^export OPENCLAW_CONFIG_DIR=", text, re.MULTILINE), (
            "run.sh must NOT export removed OPENCLAW_CONFIG_DIR"
        )
        assert not re.search(r"^export OPENCLAW_WORKSPACE_DIR=", text, re.MULTILINE), (
            "run.sh must NOT export removed OPENCLAW_WORKSPACE_DIR"
        )
