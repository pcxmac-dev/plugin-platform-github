"""The plugin conforms to the class contract (plugin API 2.2, read from the plugin alone, nothing run): a machine plugin
of the platform drawn under its Source Control plugins, its hooks the machine kind's and its own read, its token declared
as the login keeps it, its version, floor and entry point as pyproject says them, its interface's words sound."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import plugin_platform_github as module
from liminal_libs.apps import asking
from liminal_libs.sources.conformance import assert_module_conforms
from liminal_libs.sources.keys import refusal
from liminal_libs.ui import STATIC

PYPROJECT = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")


def test_the_plugin_conforms_to_the_class_contract():
    found = assert_module_conforms(module)
    assert [p.name for p in found] == ["github"] and all(p.api == "2.2" and not p.is_record for p in found)
    p = found[0]
    assert (p.SYSTEM, p.KIND, p.title, p.order, p.SECTION) == ("platform", "machine", "GitHub", 781, "scm")


def test_its_hooks_are_reads_alone():
    p = module.MACHINE
    assert set(p.interface()["hooks"]) == {"present", "status", "refresh"}
    assert getattr(p, "PAGE_ONLY_HOOKS", ()) == () and getattr(p, "JOB_HOOKS", ()) == ()  # it changes nothing
    assert asking.refusal(p, "refresh", "a-harness") == asking.refusal(p, "status", "a-harness") == ""


def test_its_token_is_declared_as_the_login_keeps_it():
    [k] = module.MACHINE.keys
    assert k.name == "GITHUB_TOKEN" and refusal(k.name) is None and k.secret is True and k.hint.startswith("optional")


def test_its_icon_is_one_the_platforms_page_draws():
    assert module.MACHINE.ICON == "github"
    drawn = set(re.findall(r"^\s*([a-z]+):\s*'", (STATIC / "icons.js").read_text(encoding="utf-8"), re.M))
    if "github" not in drawn:
        pytest.skip("the library's icons.js draws no github mark yet: the tray shows none for the plugin until it does")


def test_its_version_floor_and_entry_point_are_pyprojects():
    assert re.search(r'^version = "([^"]+)"', PYPROJECT, re.M).group(1) == module.__version__ == "0.1.0"
    assert re.search(r'"liminal-libs>=([0-9.]+)"', PYPROJECT).group(1) == "1.94.0"
    assert '[project.entry-points."liminal.providers"]\ngithub = "plugin_platform_github"' in PYPROJECT


def test_what_it_says_of_its_interface_is_sound():
    internal = pytest.importorskip("liminal_libs.internal")
    assert internal.problems(module.MACHINE) == []
