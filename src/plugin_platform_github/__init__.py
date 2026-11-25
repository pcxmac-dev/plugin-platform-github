"""GitHub for Liminal, one of the platform's Source Control plugins (Monday list item 35; the user, 2026-11-22: "add
github, gitlab and Subversion, Mercurial"). GitHub is hosted, not installable: this plugin reads the account's
repositories, its open pull requests and its repositories' latest Actions runs. Its SECTION is "scm": a platform that
draws that section (0.39.0) shows it under Source Control plugins, an older one under Machine plugins.

How it asks, when the platform asks and never on its own (client.py):
- through the gh CLI where gh is signed in to github.com: gh signs each request itself, so no token is read, kept or
  stored by this plugin (the item's words: "reuse what the gh CLI can tell");
- else through GitHub's REST API with GITHUB_TOKEN, a fine-grained or classic personal access token through the login
  alone (never said, logged or returned: only whether it is set);
- else not at all: the page says how to sign gh in, or which token to set.
One read is a few GETs (the user, the repositories, the open pull requests, the latest runs of the most recently pushed
repositories), kept READ_S; Read again asks now. It changes nothing on GitHub."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import quote

from liminal_libs.machines.plugin import MachinePlugin
from liminal_libs.sources.keys import KeyVar

from . import apis as cards
from .client import GhSource, GitHubError, RestSource
from .tool import Runner

__version__ = "0.1.0"
READ_S = 60.0
REPOS = 30  # repositories read
PULLS = 30  # open pull requests read
RUNS_OF = 5  # repositories whose latest Actions runs are read
RUNS = 3  # runs read of each
TOKEN = "GITHUB_TOKEN"
KEYS = (KeyVar(TOKEN, label="GitHub token",
               hint=("optional where gh is signed in (gh auth login): a personal access token (fine-grained: read access "
                     "to metadata, pull requests and actions) used only when gh is not, sent to api.github.com alone")),)


def when(text) -> str:
    """GitHub's ISO time at this machine's local time ("" for none)."""
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OSError):
        return ""


@dataclass(frozen=True)
class Reading:
    at: float
    when: float
    how: str = ""  # gh, rest, or "" (not asked)
    gh: str = ""  # gh's version, "" when not on PATH
    account: str = ""
    trouble: str = ""
    repos: tuple = field(default=())
    pulls: tuple = field(default=())
    runs: tuple = field(default=())
    notes: tuple[str, ...] = ()

    @property
    def let_in(self) -> bool:
        return bool(self.account)


class GitHubPlugin(MachinePlugin):
    """GitHub's account as gh or a token lets the plugin read it: its repositories, pull requests and Actions runs."""

    name = "github"
    title = "GitHub"
    about = ("GitHub, hosted: the account's repositories, its open pull requests and the latest Actions runs, read "
             "through the gh CLI where it is signed in (no token kept), else with a token through the login")
    api = "2.2"
    apis = cards.APIS
    order = 781
    ICON = "github"
    SECTION = "scm"
    HOOKS = (*MachinePlugin.HOOKS, "refresh")
    READ_HOOKS = ("refresh",)
    INTERNAL_NOTES = (
        "GitHub is read through gh where gh is signed in (gh signs its own requests: no token is read or kept here), "
        f"else with {TOKEN} through the login, sent to api.github.com alone; it is never said, logged or returned.",
        f"One read is a few GETs, kept {READ_S:g} s; nothing is written to GitHub.",
    )
    keys = KEYS

    def __init__(self, runner: Runner | None = None, transport=None, clock=None, wall=None):
        self._runner = runner or Runner()
        self._transport = transport
        self._clock = clock or time.monotonic
        self._wall = wall or time.time
        self._lock = threading.Lock()
        self._reading: Reading | None = None
        self._asked = 0

    # -- reading -------------------------------------------------------------------------------------------------------
    def _token(self) -> str:
        try:
            value = str((self.login.variables([TOKEN]) or {}).get(TOKEN) or "") if self.login is not None else ""
        except Exception:  # noqa: BLE001 - a login that cannot be asked: none set
            return ""
        return value if value.isascii() and value.isprintable() and " " not in value else ""

    def _source(self):
        """(source, gh's version, why none)."""
        gh = GhSource(self._runner) if self._runner.find("gh") else None
        version = gh.version() if gh else ""
        if gh:
            ok, said = gh.signed_in()
            if ok:
                return gh, version, ""
        token = self._token()
        if token:
            return RestSource(token, self._transport), version, ""
        if gh:
            return None, version, f"gh is not signed in to github.com: run gh auth login, or set {TOKEN}"
        return None, version, f"gh is not on PATH here and {TOKEN} is not set: install gh (cli.github.com), or set it"

    def _get(self, source, path):
        self._asked += 1
        return source.get(path)

    def _read(self, fresh: bool = False) -> Reading:
        with self._lock:
            kept = self._reading
        if kept is not None and not fresh and self._clock() - kept.at < READ_S:
            return kept
        source, gh, why = self._source()
        base = {"at": self._clock(), "when": self._wall(), "gh": gh}
        if source is None:
            r = Reading(**base, trouble=why)
        else:
            r = self._ask(source, base)
        with self._lock:
            self._reading = r
        return r

    def _ask(self, source, base: dict) -> Reading:
        try:
            user = self._get(source, "/user")
        except GitHubError as e:
            words = (f"GitHub refused {'gh' if source.how == 'gh' else TOKEN}: {e}" if e.refused else str(e))
            return Reading(**base, how=source.how, trouble=words)
        account = str((user or {}).get("login") or "")
        notes = []
        repos = pulls = runs = ()
        try:
            repos = tuple(self._get(source, f"/user/repos?per_page={REPOS}&sort=pushed") or ())[:REPOS]
        except GitHubError as e:
            notes.append(f"its repositories: {e}")
        try:
            q = quote(f"is:pr is:open involves:{account}", safe="")
            found = self._get(source, f"/search/issues?q={q}&per_page={PULLS}&sort=updated") or {}
            pulls = tuple(found.get("items") or ())[:PULLS]
        except GitHubError as e:
            notes.append(f"its pull requests: {e}")
        got = []
        for repo in [x for x in repos if isinstance(x, dict) and x.get("full_name")][:RUNS_OF]:
            try:
                answer = self._get(source, f"/repos/{repo['full_name']}/actions/runs?per_page={RUNS}") or {}
                got += [(repo["full_name"], run) for run in (answer.get("workflow_runs") or ())[:RUNS]]
            except GitHubError as e:
                notes.append(f"{repo['full_name']}'s runs: {e}")
        runs = tuple(got)
        return Reading(**base, how=source.how, account=account, repos=repos, pulls=pulls, runs=runs, notes=tuple(notes))

    # -- the hooks -------------------------------------------------------------------------------------------------------
    def present(self) -> bool:
        """Whether gh is on PATH here or GITHUB_TOKEN is set: a way to read GitHub."""
        return bool(self._runner.find("gh")) or bool(self._token())

    def refresh(self) -> dict:
        """GitHub read again now."""
        r = self._read(fresh=True)
        return {"said": self._summary(r), "ok": True, "lines": list(r.notes) or ([r.trouble] if r.trouble else [])}

    def detach(self) -> None:
        with self._lock:
            self._reading = None
        super().detach()

    def api_facts(self) -> dict:
        """What it learned while it ran, asking nothing."""
        with self._lock:
            r = self._reading
        if r is None:
            return {}
        facts = {"Through": self._through(r), "Signed in": r.account or f"no: {r.trouble}",
                 "Requests": f"{self._asked:,} made since it was attached"}
        return {cards.REST: facts, cards.GH: {"gh": r.gh or "not on PATH here"}}

    # -- the page --------------------------------------------------------------------------------------------------------
    @staticmethod
    def _through(r: Reading) -> str:
        if r.how == "gh":
            return f"gh {r.gh}, signed in (no token kept by Liminal)"
        if r.how == "rest":
            return f"GitHub's REST API with {TOKEN}"
        return "nothing: not asked"

    @staticmethod
    def _summary(r: Reading) -> str:
        if not r.let_in:
            return f"GitHub is not read: {r.trouble}"
        return (f"GitHub as {r.account} · {len(r.repos)} repositories · {len(r.pulls)} open pull requests · through "
                f"{'gh' if r.how == 'gh' else TOKEN}")

    def status(self) -> dict:
        """The account, its repositories, open pull requests and latest Actions runs."""
        r = self._read()
        out = {"present": self.present(), "summary": self._summary(r), "valid": r.let_in,
               "why": "" if r.let_in else r.trouble, "through": self._through(r), "gh": r.gh or "not on PATH here",
               "account": r.account or "–", "readAt": f"kept {READ_S:g} s; Read again asks now"}
        if r.notes:
            out["problem"] = "; ".join(r.notes)
        out["tables"] = [self._repos_table(r), self._pulls_table(r), self._runs_table(r)]
        out["actions"] = [{"hook": "refresh", "args": [], "title": "Read again", "note": "asks GitHub again now"}]
        return out

    @staticmethod
    def _repos_table(r: Reading) -> dict:
        rows = []
        for x in r.repos:
            if not isinstance(x, dict):
                continue
            vis = "private" if x.get("private") else str(x.get("visibility") or "public")
            rows.append([{"text": str(x.get("full_name") or ""), "sub": str(x.get("description") or "")[:120] or None},
                         vis + (" · archived" if x.get("archived") else "") + (" · fork" if x.get("fork") else ""),
                         str(x.get("default_branch") or "–"), when(x.get("pushed_at")) or "–",
                         {"link": str(x.get("html_url") or ""), "text": "on GitHub"} if x.get("html_url") else "–"])
        return {"title": "Repositories", "rows": rows,
                "columns": [{"title": "Repository"}, {"title": "Kind"}, {"title": "Default branch"},
                            {"title": "Pushed"}, {"title": "Page"}],
                "note": f"the {REPOS} most recently pushed it can see",
                "empty": "Not read: " + (r.trouble or "none found") if not r.let_in else "None it can see."}

    @staticmethod
    def _pulls_table(r: Reading) -> dict:
        rows = []
        for x in r.pulls:
            if not isinstance(x, dict):
                continue
            repo = str(x.get("repository_url") or "").rsplit("/repos/", 1)[-1]
            rows.append([{"text": f"#{x.get('number')} {str(x.get('title') or '')[:120]}", "sub": repo or None},
                         str((x.get("user") or {}).get("login") or "–"),
                         "draft" if x.get("draft") else str(x.get("state") or ""), when(x.get("updated_at")) or "–"])
        return {"title": "Open pull requests", "rows": rows, "note": "those you wrote, were asked to review, or are named in",
                "columns": [{"title": "Pull request"}, {"title": "By"}, {"title": "State"}, {"title": "Updated"}],
                "empty": "None open." if r.let_in else "Not read."}

    @staticmethod
    def _runs_table(r: Reading) -> dict:
        rows = []
        for repo, run in r.runs:
            if not isinstance(run, dict):
                continue
            state = str(run.get("conclusion") or run.get("status") or "–")
            rows.append([repo, {"text": str(run.get("name") or "–"), "sub": str(run.get("event") or "") or None},
                         str(run.get("head_branch") or "–"), state, when(run.get("created_at")) or "–"])
        return {"title": "Latest Actions runs", "rows": rows,
                "note": f"the latest {RUNS} runs of the {RUNS_OF} most recently pushed repositories",
                "columns": [{"title": "Repository"}, {"title": "Workflow"}, {"title": "Branch"}, {"title": "Result"},
                            {"title": "Started"}],
                "empty": "No run." if r.let_in else "Not read."}


MACHINE = GitHubPlugin()
