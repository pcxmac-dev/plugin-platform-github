"""gh and GitHub as stand-ins. `FakeGh` is the runner's spawn (subprocess.run's shape): gh's version, its auth status
(signed in or not, as gh prints it, its masked token line among them) and `gh api` answered from `DATA`, each call kept
with its keywords. `FakeGitHub` is the Endpoint's transport for the REST path: it answers the same data to a request
carrying `TOKEN` as a bearer, 401 otherwise, and keeps each request. Nothing runs, nothing is sent."""
from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from liminal_libs.machines.endpoint import Reply

from plugin_platform_github.tool import Runner

GH = "C:\\Program Files\\GitHub CLI\\gh.exe"
TOKEN = "github_pat_11ABCDEFG0123456789_abcdefghijklmnopqrstuvwxyz"
DATA = {
    "/user": {"login": "pcxmac-dev", "id": 300025796},
    "/user/repos": [
        {"full_name": "pcxmac-dev/liminal-libs", "private": False, "visibility": "public", "default_branch": "main",
         "pushed_at": "2026-11-25T10:00:00Z", "html_url": "https://github.com/pcxmac-dev/liminal-libs",
         "description": "the library"},
        {"full_name": "pcxmac-dev/liminal-platform", "private": True, "default_branch": "main",
         "pushed_at": "2026-11-24T09:00:00Z", "html_url": "https://github.com/pcxmac-dev/liminal-platform"},
    ],
    "/search/issues": {"total_count": 1, "items": [
        {"number": 12, "title": "Source control section", "state": "open", "draft": False,
         "repository_url": "https://api.github.com/repos/pcxmac-dev/liminal-platform", "user": {"login": "pcxmac-dev"},
         "updated_at": "2026-11-25T11:00:00Z"}]},
    "/repos/pcxmac-dev/liminal-libs/actions/runs": {"workflow_runs": [
        {"name": "CI", "event": "push", "head_branch": "main", "status": "completed", "conclusion": "success",
         "created_at": "2026-11-25T10:01:00Z"}]},
    "/repos/pcxmac-dev/liminal-platform/actions/runs": {"workflow_runs": []},
}
SIGNED_IN = ("github.com\n  \u2713 Logged in to github.com account pcxmac-dev (keyring)\n  - Active account: true\n"
             "  - Git operations protocol: https\n  - Token: gho_************************************\n")
SIGNED_OUT = "You are not logged into any GitHub hosts. To log in, run: gh auth login\n"


@dataclass
class Done:
    returncode: int
    stdout: str
    stderr: str = ""


class FakeGh:
    def __init__(self, signed_in=True, answers=None):
        self.signed_in = signed_in
        self.answers = dict(answers or {})
        self.calls: list[tuple[list, dict]] = []

    @property
    def argvs(self):
        return [a[1:] for a, _ in self.calls]

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), dict(kw)))
        args = tuple(argv[1:])
        if args in self.answers:
            got = self.answers[args]
            if isinstance(got, BaseException):
                raise got
            return got
        if args == ("--version",):
            return Done(0, "gh version 2.63.2 (2024-12-05)\nhttps://github.com/cli/cli/releases/tag/v2.63.2\n")
        if args[:2] == ("auth", "status"):
            return Done(0, SIGNED_IN) if self.signed_in else Done(1, "", SIGNED_OUT)
        if args[:3] == ("api", "--method", "GET"):
            path = args[-1].split("?")[0]
            if path in DATA:
                return Done(0, json.dumps(DATA[path]))
            return Done(1, "", "gh: Not Found (HTTP 404)")
        return Done(1, "", f"unknown command {args}")


def runner(found=("gh",), spawn=None):
    s = spawn if spawn is not None else FakeGh()
    return Runner(which=lambda name: GH if name in found else None, spawn=s), s


class FakeGitHub:
    def __init__(self, token=TOKEN):
        self.token = token
        self.asked: list[tuple[str, str, dict]] = []

    def __call__(self, method, url, headers, body, timeout, stream):
        h = {str(k).lower(): str(v) for k, v in headers.items()}
        self.asked.append((method, url, h))
        parts = urlsplit(url)
        if h.get("authorization") != f"Bearer {self.token}":
            status, data = 401, {"message": "Bad credentials", "documentation_url": "https://docs.github.com/rest"}
        elif parts.path in DATA:
            status, data = 200, DATA[parts.path]
        else:
            status, data = 404, {"message": "Not Found"}
        return Reply(status, {"Content-Type": "application/json; charset=utf-8"}, [json.dumps(data).encode()],
                     lambda: None)

    def query(self, i):
        return parse_qs(urlsplit(self.asked[i][1]).query)
