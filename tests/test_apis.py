"""What the plugin attaches to (plugin API 2.2): its cards are sound; the REST card names every call the plugin makes,
through gh and through the REST API alike, and claims none it does not; the gh card names every gh command it runs, and
never gh auth token; and, with LIMINAL_VENDOR_PAGES=1 alone, every address on them answers."""
from __future__ import annotations

import os
import re
from urllib.parse import urlsplit

import pytest

from liminal_libs.machines import standins
from liminal_libs.sources import apis as A
from liminal_libs.sources.conformance import problems
from plugin_platform_github import MACHINE, GitHubPlugin
from plugin_platform_github import apis as cards
from stand_ins import TOKEN, FakeGh, FakeGitHub, runner


def card(name):
    return next(a for a in MACHINE.apis if a.name == name)


def named(api, method, path):
    for c in api.calls:
        m, _, template = c.name.partition(" ")
        rx = re.sub(r"\\\{[^}]*\\\}", "[^/]+", re.escape(template))
        if m == method and re.fullmatch(rx, path):
            return c
    return None


def test_its_cards_are_sound():
    assert MACHINE.api == "2.2" and problems(MACHINE) == [] and A.problems(MACHINE.apis) == []
    for a in MACHINE.apis:
        assert a.verified == cards.VERIFIED and a.used and a.covered and len(a.calls) > len(a.used)


def test_the_rest_card_names_every_call_made_and_no_other():
    r, gh = runner()
    p = GitHubPlugin(runner=r)
    p.login = standins.login({})
    p.status()
    through_gh = {a[-1].split("?")[0] for a in gh.argvs if a[:1] == ["api"]}
    r2, _ = runner(spawn=FakeGh(signed_in=False))
    web = FakeGitHub()
    q = GitHubPlugin(runner=r2, transport=web)
    q.login = standins.login({"GITHUB_TOKEN": TOKEN})
    q.status()
    through_rest = {urlsplit(url).path for _, url, _ in web.asked}
    assert through_gh == through_rest
    rest = card(cards.REST)
    made = {named(rest, "GET", path).name for path in through_gh}
    assert made == {c.name for c in rest.used} and not any(c.writes for c in rest.used)


def test_the_gh_card_names_every_command_it_runs():
    r, gh = runner()
    p = GitHubPlugin(runner=r)
    p.login = standins.login({})
    p.status()
    ran = {" ".join(a[:3]) if a[:1] == ["api"] else " ".join(a) for a in gh.argvs}
    assert ran == {"--version", "auth status --hostname github.com", "api --method GET"}
    used = {c.name for c in card(cards.GH).used}
    assert used == {"gh --version", "gh auth status --hostname github.com", "gh api --method GET <path>"}
    assert "gh auth token" in {c.name for c in card(cards.GH).calls} - used


@pytest.mark.skipif(os.environ.get("LIMINAL_VENDOR_PAGES") != "1",
                    reason="reaches the makers' pages: LIMINAL_VENDOR_PAGES=1")
def test_every_address_on_its_cards_answers(monkeypatch):
    monkeypatch.undo()
    assert A.dead_links(MACHINE.apis) == []
