"""How GitHub is asked: through the gh CLI where it is signed in (`GhSource`: no token is read, kept or stored by the
plugin; gh signs its own requests), else through GitHub's REST API with GITHUB_TOKEN from the login (`RestSource`, the
library's Endpoint: https alone, no redirect followed, every answer bounded, the token taken out of every word). Both
answer `get(path)` with the JSON GitHub sends, and say a failure as a GitHubError in words that never hold a token."""
from __future__ import annotations

import json
import re
from typing import Callable

from liminal_libs.machines.endpoint import Endpoint, EndpointError

from .tool import Runner, ToolError

API = "https://api.github.com"
HOST = "github.com"
VERSION = "2022-11-28"  # the REST API version asked (X-GitHub-Api-Version)
ACCEPT = "application/vnd.github+json"
TOKENS = re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,})")


def scrub(text: str, secrets=()) -> str:
    """Words with every token taken out (GitHub's token shapes, and the ones given)."""
    out = TOKENS.sub("<a token>", str(text or ""))
    for s in secrets:
        if s:
            out = out.replace(s, "<a token>")
    return out


class GitHubError(Exception):
    """A read that failed, in words; `status` GitHub's HTTP status when one came (0: none), `refused` for 401 and 403."""

    def __init__(self, message: str, status: int = 0):
        super().__init__(scrub(message)[:400])
        self.status = status

    @property
    def refused(self) -> bool:
        return self.status in (401, 403)


class GhSource:
    """GitHub through gh: `gh auth status` says who is signed in (its account's name alone is kept: never its token line),
    `gh api --method GET <path>` reads."""

    how = "gh"

    def __init__(self, runner: Runner):
        self._runner = runner
        self.account = ""

    def version(self) -> str:
        from .tool import version_of

        try:
            ran = self._runner.run("gh", "--version")
        except ToolError:
            return ""
        return version_of(ran.out) if ran.code == 0 else ""

    def signed_in(self) -> tuple[bool, str]:
        """(whether gh is signed in to github.com, its account or why not)."""
        try:
            ran = self._runner.run("gh", "auth", "status", "--hostname", HOST)
        except ToolError as e:
            return False, str(e)
        said = f"{ran.out}\n{ran.err}"
        found = re.search(r"Logged in to github\.com (?:account|as) ([A-Za-z0-9-]+)", said)
        if ran.code == 0 and found:
            self.account = found.group(1)
            return True, self.account
        return False, "gh is not signed in to github.com (gh auth login signs it in)"

    def get(self, path: str):
        try:
            ran = self._runner.run("gh", "api", "--method", "GET", "-H", f"Accept: {ACCEPT}", "-H",
                                   f"X-GitHub-Api-Version: {VERSION}", path)
        except ToolError as e:
            raise GitHubError(str(e)) from None
        if ran.code != 0:
            status = re.search(r"HTTP (\d{3})", ran.err or "")
            raise GitHubError(f"gh api {path.split('?')[0]}: {(ran.err or ran.out).strip()[:300]}",
                              int(status.group(1)) if status else 0)
        try:
            return json.loads(ran.out or "null")
        except ValueError:
            raise GitHubError(f"gh api {path.split('?')[0]} answered no JSON") from None


class RestSource:
    """GitHub's REST API with a token (GITHUB_TOKEN), sent as a bearer by the library's Endpoint."""

    how = "rest"

    def __init__(self, token: str, transport: Callable | None = None):
        self._token = token
        self._at = Endpoint(API, key=token, headers={"Accept": ACCEPT, "X-GitHub-Api-Version": VERSION},
                            transport=transport)
        self.account = ""

    def get(self, path: str):
        try:
            return self._at.get(path)
        except EndpointError as e:
            raise GitHubError(scrub(str(e), (self._token,)), e.status) from None
