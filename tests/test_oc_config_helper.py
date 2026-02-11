"""Tests for oc_config_helper.py — config read/write/apply logic."""

import json

from conftest import write_fixture_config


# ---------------------------------------------------------------------------
# read_config
# ---------------------------------------------------------------------------


class TestReadConfig:
    def test_returns_none_for_missing_file(self, oc_helper, tmp_config):
        assert not tmp_config.exists()
        assert oc_helper.read_config() is None

    def test_returns_none_for_corrupted_json(self, oc_helper, tmp_config):
        tmp_config.write_text("{invalid json!!!", encoding="utf-8")
        assert oc_helper.read_config() is None

    def test_parses_valid_json(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {"gateway": {"mode": "local"}})
        cfg = oc_helper.read_config()
        assert cfg == {"gateway": {"mode": "local"}}

    def test_parses_empty_object(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        assert oc_helper.read_config() == {}


# ---------------------------------------------------------------------------
# write_config
# ---------------------------------------------------------------------------


class TestWriteConfig:
    def test_creates_parent_dirs(self, oc_helper, tmp_config, monkeypatch):
        nested = tmp_config.parent / "sub" / "dir" / "openclaw.json"
        monkeypatch.setattr(oc_helper, "CONFIG_PATH", nested)
        assert oc_helper.write_config({"a": 1})
        assert nested.exists()

    def test_writes_formatted_json(self, oc_helper, tmp_config):
        oc_helper.write_config({"x": 1, "y": [2, 3]})
        raw = tmp_config.read_text(encoding="utf-8")
        # indent=2 formatting
        assert '"x": 1' in raw
        # trailing newline
        assert raw.endswith("\n")
        # verify roundtrip
        assert json.loads(raw) == {"x": 1, "y": [2, 3]}


# ---------------------------------------------------------------------------
# get_gateway_setting
# ---------------------------------------------------------------------------


class TestGetGatewaySetting:
    def test_returns_default_when_no_config(self, oc_helper, tmp_config):
        assert oc_helper.get_gateway_setting("mode", default="fallback") == "fallback"

    def test_returns_default_when_no_gateway_key(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {"agents": {}})
        assert oc_helper.get_gateway_setting("mode", default="none") == "none"

    def test_reads_nested_gateway_key(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {"gateway": {"mode": "remote", "port": 9999}})
        assert oc_helper.get_gateway_setting("mode") == "remote"
        assert oc_helper.get_gateway_setting("port") == 9999

    def test_returns_none_default(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {"gateway": {}})
        assert oc_helper.get_gateway_setting("nonexistent") is None


# ---------------------------------------------------------------------------
# set_gateway_setting
# ---------------------------------------------------------------------------


class TestSetGatewaySetting:
    def test_creates_gateway_object_if_missing(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        oc_helper.set_gateway_setting("mode", "local")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["gateway"]["mode"] == "local"

    def test_creates_config_from_scratch(self, oc_helper, tmp_config):
        # No config file at all
        assert not tmp_config.exists()
        oc_helper.set_gateway_setting("port", 8080)
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["gateway"]["port"] == 8080

    def test_preserves_non_gateway_keys(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {"agents": {"workspace": "/tmp"}, "gateway": {"mode": "local"}})
        oc_helper.set_gateway_setting("port", 5555)
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["agents"]["workspace"] == "/tmp"
        assert cfg["gateway"]["mode"] == "local"
        assert cfg["gateway"]["port"] == 5555


# ---------------------------------------------------------------------------
# apply_gateway_settings — validation
# ---------------------------------------------------------------------------


class TestApplyGatewaySettingsValidation:
    def test_rejects_invalid_mode(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        assert oc_helper.apply_gateway_settings("invalid", "loopback", 18789, False, False) is False

    def test_rejects_invalid_bind_mode(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        assert oc_helper.apply_gateway_settings("local", "invalid", 18789, False, False) is False

    def test_rejects_port_zero(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        assert oc_helper.apply_gateway_settings("local", "loopback", 0, False, False) is False

    def test_rejects_port_negative(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        assert oc_helper.apply_gateway_settings("local", "loopback", -1, False, False) is False

    def test_rejects_port_over_65535(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        assert oc_helper.apply_gateway_settings("local", "loopback", 65536, False, False) is False

    def test_accepts_port_1(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        assert oc_helper.apply_gateway_settings("local", "loopback", 1, False, False) is True

    def test_accepts_port_65535(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        assert oc_helper.apply_gateway_settings("local", "loopback", 65535, False, False) is True


# ---------------------------------------------------------------------------
# apply_gateway_settings — read-modify-write
# ---------------------------------------------------------------------------


class TestApplyGatewaySettingsReadModifyWrite:
    def test_creates_structure_from_empty_config(self, oc_helper, tmp_config):
        # Use non-default values so change detection writes all fields.
        # Defaults (not written if unchanged): port=18789, enabled=False, allowInsecureAuth=False
        write_fixture_config(tmp_config, {})
        assert oc_helper.apply_gateway_settings("local", "loopback", 9999, True, True) is True
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["gateway"]["mode"] == "local"
        assert cfg["gateway"]["bind"] == "loopback"
        assert cfg["gateway"]["port"] == 9999
        assert cfg["gateway"]["http"]["endpoints"]["chatCompletions"]["enabled"] is True
        assert cfg["gateway"]["controlUi"]["allowInsecureAuth"] is True

    def test_creates_config_from_missing_file(self, oc_helper, tmp_config):
        assert not tmp_config.exists()
        assert oc_helper.apply_gateway_settings("remote", "lan", 9000, False, True) is True
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["gateway"]["mode"] == "remote"
        assert cfg["gateway"]["bind"] == "lan"
        assert cfg["gateway"]["port"] == 9000
        assert cfg["gateway"]["controlUi"]["allowInsecureAuth"] is True

    def test_preserves_existing_non_gateway_keys(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {
            "agents": {"defaults": {"workspace": "/config/clawd"}},
            "customKey": "customValue",
        })
        oc_helper.apply_gateway_settings("local", "loopback", 18789, False, False)
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["agents"]["defaults"]["workspace"] == "/config/clawd"
        assert cfg["customKey"] == "customValue"

    def test_preserves_nested_gateway_keys_not_managed(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {
            "gateway": {
                "mode": "local",
                "bind": "loopback",
                "port": 18789,
                "auth": {"mode": "token", "token": "abc123"},
            }
        })
        oc_helper.apply_gateway_settings("local", "loopback", 18789, False, False)
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["gateway"]["auth"]["mode"] == "token"
        assert cfg["gateway"]["auth"]["token"] == "abc123"

    def test_idempotent_same_args_twice(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        oc_helper.apply_gateway_settings("local", "lan", 8080, True, True)
        content_after_first = tmp_config.read_text(encoding="utf-8")
        oc_helper.apply_gateway_settings("local", "lan", 8080, True, True)
        content_after_second = tmp_config.read_text(encoding="utf-8")
        assert content_after_first == content_after_second

    def test_change_detection_no_write_when_same(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {
            "gateway": {
                "mode": "local",
                "bind": "loopback",
                "port": 18789,
                "controlUi": {"allowInsecureAuth": False},
                "http": {"endpoints": {"chatCompletions": {"enabled": False}}},
            }
        })
        mtime_before = tmp_config.stat().st_mtime_ns
        # apply with same values — should not rewrite
        oc_helper.apply_gateway_settings("local", "loopback", 18789, False, False)
        mtime_after = tmp_config.stat().st_mtime_ns
        assert mtime_before == mtime_after

    def test_correctly_sets_all_five_fields(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        oc_helper.apply_gateway_settings("remote", "lan", 12345, True, True)
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["gateway"]["mode"] == "remote"
        assert cfg["gateway"]["bind"] == "lan"
        assert cfg["gateway"]["port"] == 12345
        assert cfg["gateway"]["http"]["endpoints"]["chatCompletions"]["enabled"] is True
        assert cfg["gateway"]["controlUi"]["allowInsecureAuth"] is True

    def test_updates_only_changed_fields(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {
            "gateway": {
                "mode": "local",
                "bind": "loopback",
                "port": 18789,
                "controlUi": {"allowInsecureAuth": False},
                "http": {"endpoints": {"chatCompletions": {"enabled": False}}},
            }
        })
        # Only change mode and port
        oc_helper.apply_gateway_settings("remote", "loopback", 9999, False, False)
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["gateway"]["mode"] == "remote"
        assert cfg["gateway"]["port"] == 9999
        # Unchanged
        assert cfg["gateway"]["bind"] == "loopback"
        assert cfg["gateway"]["controlUi"]["allowInsecureAuth"] is False
        assert cfg["gateway"]["http"]["endpoints"]["chatCompletions"]["enabled"] is False


# ---------------------------------------------------------------------------
# CLI entry point (main)
# ---------------------------------------------------------------------------


class TestMainCLI:
    def test_apply_gateway_settings_cli(self, oc_helper, tmp_config, monkeypatch):
        write_fixture_config(tmp_config, {})
        monkeypatch.setattr(
            "sys.argv",
            ["oc_config_helper.py", "apply-gateway-settings", "local", "lan", "8080", "true", "false"],
        )
        # main() calls sys.exit — catch it
        with __import__("pytest").raises(SystemExit) as exc_info:
            oc_helper.main()
        assert exc_info.value.code == 0
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["gateway"]["mode"] == "local"
        assert cfg["gateway"]["bind"] == "lan"

    def test_get_cli(self, oc_helper, tmp_config, monkeypatch, capsys):
        write_fixture_config(tmp_config, {"gateway": {"mode": "remote"}})
        monkeypatch.setattr("sys.argv", ["oc_config_helper.py", "get", "mode"])
        with __import__("pytest").raises(SystemExit) as exc_info:
            oc_helper.main()
        assert exc_info.value.code == 0
        assert "remote" in capsys.readouterr().out

    def test_set_cli(self, oc_helper, tmp_config, monkeypatch):
        write_fixture_config(tmp_config, {})
        monkeypatch.setattr("sys.argv", ["oc_config_helper.py", "set", "port", "9999"])
        with __import__("pytest").raises(SystemExit) as exc_info:
            oc_helper.main()
        assert exc_info.value.code == 0
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["gateway"]["port"] == 9999

    def test_unknown_command_exits_1(self, oc_helper, tmp_config, monkeypatch):
        monkeypatch.setattr("sys.argv", ["oc_config_helper.py", "bogus"])
        with __import__("pytest").raises(SystemExit) as exc_info:
            oc_helper.main()
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# apply_memory_settings
# ---------------------------------------------------------------------------


class TestApplyMemorySettings:
    def test_creates_full_memory_structure_from_empty(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        assert oc_helper.apply_memory_settings(True, True, "", "", "", "", "") is True
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        ms = cfg["agents"]["defaults"]["memorySearch"]
        assert ms["enabled"] is True
        assert "provider" not in ms  # provider is user-owned, not set by add-on
        assert ms["query"]["hybrid"]["enabled"] is True
        assert ms["sources"] == ["memory", "sessions"]
        assert ms["experimental"]["sessionMemory"] is True
        comp = cfg["agents"]["defaults"]["compaction"]
        assert comp["memoryFlush"]["enabled"] is True
        assert comp["memoryFlush"]["softThresholdTokens"] == 40000

    def test_session_indexing_false_excludes_sessions(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        oc_helper.apply_memory_settings(True, False, "", "", "", "", "")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        ms = cfg["agents"]["defaults"]["memorySearch"]
        assert ms["sources"] == ["memory"]
        assert ms["experimental"]["sessionMemory"] is False

    def test_enable_memory_false_sets_disabled(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        oc_helper.apply_memory_settings(False, True, "", "", "", "", "")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["agents"]["defaults"]["memorySearch"]["enabled"] is False

    def test_preserves_existing_gateway_config(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {
            "gateway": {"mode": "local", "port": 18789, "auth": {"token": "secret"}}
        })
        oc_helper.apply_memory_settings(True, True, "", "", "", "", "")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["gateway"]["mode"] == "local"
        assert cfg["gateway"]["auth"]["token"] == "secret"

    def test_preserves_existing_agent_defaults(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {
            "agents": {"defaults": {"workspace": "/config/clawd", "customKey": 42}}
        })
        oc_helper.apply_memory_settings(True, True, "", "", "", "", "")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["agents"]["defaults"]["workspace"] == "/config/clawd"
        assert cfg["agents"]["defaults"]["customKey"] == 42
        assert "memorySearch" in cfg["agents"]["defaults"]

    def test_preserves_existing_provider(self, oc_helper, tmp_config):
        """Provider is user-owned; add-on must not overwrite it."""
        write_fixture_config(tmp_config, {
            "agents": {"defaults": {"memorySearch": {
                "enabled": True, "provider": "openai",
                "model": "text-embedding-3-small",
                "remote": {"apiKey": "sk-test"},
                "fallback": "none",
            }}}
        })
        oc_helper.apply_memory_settings(True, True, "", "", "", "", "")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        ms = cfg["agents"]["defaults"]["memorySearch"]
        assert ms["provider"] == "openai"
        assert ms["model"] == "text-embedding-3-small"
        assert ms["remote"] == {"apiKey": "sk-test"}
        assert ms["fallback"] == "none"

    def test_idempotent_no_rewrite(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        oc_helper.apply_memory_settings(True, True, "", "", "", "", "")
        mtime_first = tmp_config.stat().st_mtime_ns
        oc_helper.apply_memory_settings(True, True, "", "", "", "", "")
        mtime_second = tmp_config.stat().st_mtime_ns
        assert mtime_first == mtime_second

    def test_creates_config_from_missing_file(self, oc_helper, tmp_config):
        assert not tmp_config.exists()
        assert oc_helper.apply_memory_settings(True, True, "", "", "", "", "") is True
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["agents"]["defaults"]["memorySearch"]["enabled"] is True

    def test_mem0_config_written_when_key_set(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        oc_helper.apply_memory_settings(True, True, "m0-key-123", "", "ha-user", "", "")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        mem0 = cfg["plugins"]["entries"]["openclaw-mem0"]
        assert mem0["enabled"] is True
        assert mem0["config"]["apiKey"] == "m0-key-123"
        assert mem0["config"]["baseUrl"] == "https://api.mem0.ai"
        assert mem0["config"]["userId"] == "ha-user"
        assert mem0["config"]["autoRecall"] is True
        assert mem0["config"]["topK"] == 5

    def test_mem0_custom_base_url(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        oc_helper.apply_memory_settings(True, True, "key", "https://my-mem0.local", "admin", "", "")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["plugins"]["entries"]["openclaw-mem0"]["config"]["baseUrl"] == "https://my-mem0.local"
        assert cfg["plugins"]["entries"]["openclaw-mem0"]["config"]["userId"] == "admin"

    def test_mem0_disabled_when_key_empty_existing_entry(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {
            "plugins": {"entries": {"openclaw-mem0": {"enabled": True, "config": {"apiKey": "old"}}}}
        })
        oc_helper.apply_memory_settings(True, True, "", "", "", "", "")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["plugins"]["entries"]["openclaw-mem0"]["enabled"] is False

    def test_mem0_not_created_when_key_empty_no_prior(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        oc_helper.apply_memory_settings(True, True, "", "", "", "", "")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert "plugins" not in cfg

    def test_cognee_config_written_when_key_set(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        oc_helper.apply_memory_settings(True, True, "", "", "", "cog-key-456", "")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        cognee = cfg["plugins"]["entries"]["memory-cognee"]
        assert cognee["enabled"] is True
        assert cognee["config"]["apiKey"] == "cog-key-456"
        assert cognee["config"]["baseUrl"] == "https://api.cognee.ai"

    def test_cognee_custom_base_url(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {})
        oc_helper.apply_memory_settings(True, True, "", "", "", "key", "https://my-cognee.local")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["plugins"]["entries"]["memory-cognee"]["config"]["baseUrl"] == "https://my-cognee.local"

    def test_cognee_disabled_when_key_empty_existing_entry(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {
            "plugins": {"entries": {"memory-cognee": {"enabled": True, "config": {"apiKey": "old"}}}}
        })
        oc_helper.apply_memory_settings(True, True, "", "", "", "", "")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["plugins"]["entries"]["memory-cognee"]["enabled"] is False

    def test_preserves_other_plugins(self, oc_helper, tmp_config):
        write_fixture_config(tmp_config, {
            "plugins": {"entries": {"some-other-plugin": {"enabled": True, "config": {"foo": "bar"}}}}
        })
        oc_helper.apply_memory_settings(True, True, "m0-key", "", "", "", "")
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["plugins"]["entries"]["some-other-plugin"]["config"]["foo"] == "bar"
        assert cfg["plugins"]["entries"]["openclaw-mem0"]["enabled"] is True


# ---------------------------------------------------------------------------
# apply_memory_settings CLI
# ---------------------------------------------------------------------------


class TestApplyMemorySettingsCLI:
    def test_basic_cli(self, oc_helper, tmp_config, monkeypatch):
        write_fixture_config(tmp_config, {})
        monkeypatch.setattr(
            "sys.argv",
            ["oc_config_helper.py", "apply-memory-settings",
             "true", "true", "__EMPTY__", "__EMPTY__", "__EMPTY__", "__EMPTY__", "__EMPTY__"],
        )
        with __import__("pytest").raises(SystemExit) as exc_info:
            oc_helper.main()
        assert exc_info.value.code == 0
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["agents"]["defaults"]["memorySearch"]["enabled"] is True

    def test_cli_with_mem0_and_cognee(self, oc_helper, tmp_config, monkeypatch):
        write_fixture_config(tmp_config, {})
        monkeypatch.setattr(
            "sys.argv",
            ["oc_config_helper.py", "apply-memory-settings",
             "true", "true", "m0key", "__EMPTY__", "myuser", "cogkey", "__EMPTY__"],
        )
        with __import__("pytest").raises(SystemExit) as exc_info:
            oc_helper.main()
        assert exc_info.value.code == 0
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert cfg["plugins"]["entries"]["openclaw-mem0"]["config"]["apiKey"] == "m0key"
        assert cfg["plugins"]["entries"]["openclaw-mem0"]["config"]["userId"] == "myuser"
        assert cfg["plugins"]["entries"]["memory-cognee"]["config"]["apiKey"] == "cogkey"

    def test_wrong_arg_count_exits_1(self, oc_helper, tmp_config, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            ["oc_config_helper.py", "apply-memory-settings", "true"],
        )
        with __import__("pytest").raises(SystemExit) as exc_info:
            oc_helper.main()
        assert exc_info.value.code == 1
