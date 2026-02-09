"""Tests for config.yaml schema/options/translations consistency."""

import yaml
from pathlib import Path

from conftest import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "openclaw_assistant" / "config.yaml"
TRANSLATIONS_DIR = PROJECT_ROOT / "openclaw_assistant" / "translations"
EXPECTED_LANGUAGES = ["en", "bg", "de", "es", "pl"]


def _load_config():
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _load_translation(lang: str):
    path = TRANSLATIONS_DIR / f"{lang}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class TestConfigSchemaConsistency:
    def test_every_option_has_schema_entry(self):
        cfg = _load_config()
        option_keys = set(cfg["options"].keys())
        schema_keys = set(cfg["schema"].keys())
        missing = option_keys - schema_keys
        assert not missing, f"Options without schema entries: {missing}"

    def test_every_schema_has_option_entry(self):
        cfg = _load_config()
        option_keys = set(cfg["options"].keys())
        schema_keys = set(cfg["schema"].keys())
        orphans = schema_keys - option_keys
        assert not orphans, f"Schema entries without options: {orphans}"

    def test_every_option_in_all_translations(self):
        cfg = _load_config()
        option_keys = set(cfg["options"].keys())

        for lang in EXPECTED_LANGUAGES:
            trans = _load_translation(lang)
            trans_keys = set(trans.get("configuration", {}).keys())
            missing = option_keys - trans_keys
            assert not missing, f"Missing from {lang}.yaml translations: {missing}"

    def test_translation_entries_have_name_and_description(self):
        for lang in EXPECTED_LANGUAGES:
            trans = _load_translation(lang)
            for key, entry in trans.get("configuration", {}).items():
                assert "name" in entry, f"{lang}.yaml: '{key}' missing 'name'"
                assert "description" in entry, f"{lang}.yaml: '{key}' missing 'description'"
