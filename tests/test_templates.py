"""Tests for template placeholder coverage.

Ensures every __PLACEHOLDER__ in templates has a corresponding .replace() call
in the Python block inside run.sh.
"""

import re
from pathlib import Path

from conftest import PROJECT_ROOT

NGINX_TPL = PROJECT_ROOT / "openclaw_assistant" / "nginx.conf.tpl"
LANDING_TPL = PROJECT_ROOT / "openclaw_assistant" / "landing.html.tpl"
RUN_SH = PROJECT_ROOT / "openclaw_assistant" / "run.sh"

# Match __WORD_PARTS__ but not greedily across adjacent placeholders.
# E.g., __FOO____BAR__ should match as __FOO__ and __BAR__, not one token.
PLACEHOLDER_RE = re.compile(r"__[A-Z]+(?:_[A-Z]+)*__")


def _extract_placeholders(path: Path) -> set[str]:
    """Return all __PLACEHOLDER__ strings found in a file."""
    return set(PLACEHOLDER_RE.findall(path.read_text(encoding="utf-8")))


def _extract_replace_targets(run_sh_text: str) -> set[str]:
    """Return all placeholder strings used in .replace('__X__', ...) calls in run.sh."""
    # Matches both .replace('__X__', ...) and .replace("__X__", ...)
    return set(re.findall(r"\.replace\(['\"](__[A-Z]+(?:_[A-Z]+)*__)['\"]", run_sh_text))


class TestTemplatePlaceholders:
    def test_nginx_placeholders_are_replaced(self):
        placeholders = _extract_placeholders(NGINX_TPL)
        assert placeholders, "nginx.conf.tpl should have at least one placeholder"
        replacements = _extract_replace_targets(RUN_SH.read_text(encoding="utf-8"))
        unreplaced = placeholders - replacements
        assert not unreplaced, f"nginx.conf.tpl placeholders not replaced in run.sh: {unreplaced}"

    def test_landing_placeholders_are_replaced(self):
        placeholders = _extract_placeholders(LANDING_TPL)
        assert placeholders, "landing.html.tpl should have at least one placeholder"
        replacements = _extract_replace_targets(RUN_SH.read_text(encoding="utf-8"))
        unreplaced = placeholders - replacements
        assert not unreplaced, f"landing.html.tpl placeholders not replaced in run.sh: {unreplaced}"

    def test_no_unknown_placeholders(self):
        """Every placeholder across all templates should have a .replace() in run.sh."""
        all_placeholders = _extract_placeholders(NGINX_TPL) | _extract_placeholders(LANDING_TPL)
        replacements = _extract_replace_targets(RUN_SH.read_text(encoding="utf-8"))
        unknown = all_placeholders - replacements
        assert not unknown, f"Template placeholders without .replace() calls: {unknown}"
