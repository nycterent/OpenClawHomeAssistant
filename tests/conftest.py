"""Shared fixtures for OpenClawHomeAssistant tests."""

import json
import sys
from pathlib import Path

import pytest

# Add the openclaw_assistant directory to sys.path so we can import oc_config_helper
ADDON_DIR = Path(__file__).resolve().parent.parent / "openclaw_assistant"

# Project root for accessing templates, config.yaml, translations, run.sh
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Provide a temporary config path and patch oc_config_helper.CONFIG_PATH."""
    config_file = tmp_path / "openclaw.json"

    # oc_config_helper reads CONFIG_PATH at module level; patch it per test
    sys.path.insert(0, str(ADDON_DIR))
    import oc_config_helper

    monkeypatch.setattr(oc_config_helper, "CONFIG_PATH", config_file)
    sys.path.pop(0)

    return config_file


@pytest.fixture
def oc_helper(tmp_config):
    """Return the oc_config_helper module with CONFIG_PATH already patched."""
    sys.path.insert(0, str(ADDON_DIR))
    import oc_config_helper

    sys.path.pop(0)
    return oc_config_helper


def write_fixture_config(path: Path, data: dict) -> Path:
    """Write a JSON config to the given path and return it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path
