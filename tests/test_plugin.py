"""GitHub read through gh where it is signed in (no token read or kept), else with GITHUB_TOKEN through the REST API,
else not at all; every word without a token; nothing written."""
from __future__ import annotations

import subprocess

from liminal_libs.machines import standins

from plugin_platform_github import GitHubPlugin
from plugin_platform_github.client import scrub
from stand_ins import TOKEN, Done, FakeGh, FakeGitHub, runner


def plugin(found=("gh",), gh=None, pairs=None, web=None):
    r, s = runner(found, gh)
    w = web or FakeGitHub()
    p = GitHubPlugin(runner=r, transport=w)
    p.login = standins.login(dict(pairs or {}))
    return p, s, w


def test_through_gh_signed_in_no_token_is_read_or_sent():
    p, gh, web = plugin(pairs={"GITHUB_TOKEN": TOKEN})
    st = p.status()
    assert st["valid"] and st["account"] == "pcxmac-dev" and st["through"].startswith("gh 2.63.2, signed in")
    assert web.asked == []  # the token went nowhere: gh signed its own requests
    argvs = gh.argvs
    assert argvs[:2] == [["--version"], ["auth", "status", "--hostname", "github.com"]]
    reads = [a for a in argvs if a[:1] == ["api"]]
    assert all(a[:3] == ["api", "--method", "GET"] for a in reads)
    assert [a[-1].split("?")[0] for a in reads] == ["/user", "/user/repos", "/search/issues",
                                                    "/repos/pcxmac-dev/liminal-libs/actions/runs",
                                                    "/repos/pcxmac-dev/liminal-platform/actions/runs"]
    assert ["auth", "token"] not in argvs and TOKEN not in str(gh.calls)
    assert "gho_" not in str(st)  # its masked token line is never kept
    tables = {t["title"]: t for t in st["tables"]}
    assert [r[0]["text"] for r in tables["Repositories"]["rows"]] == ["pcxmac-dev/liminal-libs", "pcxmac-dev/liminal-platform"]
    assert tables["Repositories"]["rows"][1][1] == "private"
    assert tables["Open pull requests"]["rows"][0][0]["text"] == "#12 Source control section"
    assert tables["Latest Actions runs"]["rows"] == [["pcxmac-dev/liminal-libs", {"text": "CI", "sub": "push"}, "main",
                                                      "success", tables["Latest Actions runs"]["rows"][0][4]]]


def test_gh_is_run_without_a_window_its_prompts_and_pager_off():
    p, gh, _ = plugin()
    p.status()
    for _, kw in gh.calls:
        assert kw["stdin"] is subprocess.DEVNULL and kw["env"]["GH_PROMPT_DISABLED"] == "1"
        assert kw["env"]["GH_NO_UPDATE_NOTIFIER"] == "1" and kw["env"]["GH_PAGER"] == "" and kw["cwd"]
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            assert kw["creationflags"] & 0x08000000


def test_gh_signed_out_and_a_token_set_reads_the_rest_api_with_it():
    p, gh, web = plugin(gh=FakeGh(signed_in=False), pairs={"GITHUB_TOKEN": TOKEN})
    st = p.status()
    assert st["valid"] and st["through"] == "GitHub's REST API with GITHUB_TOKEN"
    assert [a for a in gh.argvs if a[:1] == ["api"]] == []
    assert all(url.startswith("https://api.github.com/") for _, url, _ in web.asked)
    assert web.asked[0][2]["x-github-api-version"] == "2022-11-28"
    assert TOKEN not in str(st) and TOKEN not in str(p.api_facts())


def test_no_gh_and_no_token_asks_nothing_and_says_how():
    p, gh, web = plugin(found=())
    st = p.status()
    assert not st["valid"] and "gh is not on PATH here and GITHUB_TOKEN is not set" in st["why"]
    assert gh.calls == [] and web.asked == [] and p.present() is False


def test_gh_signed_out_and_no_token_says_to_sign_it_in():
    p, gh, web = plugin(gh=FakeGh(signed_in=False))
    st = p.status()
    assert "gh auth login" in st["why"] and web.asked == []


def test_a_refused_token_is_said_without_it():
    p, _, web = plugin(found=(), pairs={"GITHUB_TOKEN": TOKEN}, web=FakeGitHub(token="another"))
    st = p.status()
    assert not st["valid"] and "GitHub refused GITHUB_TOKEN" in st["why"] and TOKEN not in st["why"]


def test_a_token_in_gh_s_words_is_taken_out():
    leaky = FakeGh(answers={("api", "--method", "GET", "-H", "Accept: application/vnd.github+json", "-H",
                             "X-GitHub-Api-Version: 2022-11-28", "/user"):
                            Done(1, "", "error: token ghp_abcdefghijklmnop1234567890 is expired (HTTP 401)")})
    p, _, _ = plugin(gh=leaky)
    st = p.status()
    assert "ghp_abcdefghijklmnop1234567890" not in str(st) and "<a token>" in st["why"] and "refused" in st["why"]
    assert scrub("github_pat_11AAAAAAAAAA_bbbbbbbb") == "<a token>"


def test_what_was_read_is_kept_and_read_again_asks_now():
    p, gh, _ = plugin()
    p.status()
    n = len(gh.calls)
    p.status()
    assert len(gh.calls) == n
    p.refresh()
    assert len(gh.calls) == 2 * n


def test_its_facts_ask_nothing():
    p, gh, _ = plugin()
    assert p.api_facts() == {}
    p.status()
    n = len(gh.calls)
    facts = p.api_facts()
    assert len(gh.calls) == n and facts["GitHub REST API"]["Signed in"] == "pcxmac-dev"


def test_gh_s_sign_in_is_kept_as_its_account_alone():
    from plugin_platform_github.client import GhSource

    ok, said = GhSource(runner()[0]).signed_in()
    assert ok and said == "pcxmac-dev"


def test_a_token_pasted_with_a_space_or_a_line_break_is_never_sent():
    for bad in (TOKEN + " x", TOKEN + "\n"):
        p, _, web = plugin(found=(), pairs={"GITHUB_TOKEN": bad})
        assert not p.status()["valid"] and web.asked == []
