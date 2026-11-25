"""What the GitHub plugin attaches to (plugin API 2.2): GitHub's REST API, which it reads the account's repositories,
pull requests and Actions runs through, and the gh CLI, which signs those requests where it is signed in.

These cards were written on 2026-11-25 from GitHub's documentation as known to their writer; no page was fetched for this
build. `LIMINAL_VENDOR_PAGES=1 pytest tests/test_apis.py` asks every address on them once."""
from __future__ import annotations

from liminal_libs.sources.apis import Api, Area, Call, Link

from .client import VERSION

VERIFIED = "2026-11-25"
REST, GH = "GitHub REST API", "GitHub CLI (gh)"
_DOCS = "https://docs.github.com/en/rest/"

GITHUB_REST = Api(
    name=REST, maker="GitHub (Microsoft)", kind="rest",
    about=("GitHub's REST API: repositories, issues and pull requests, Actions, users and organizations, search, and "
           "much more. The plugin reads the signed-in user, the repositories it can see (most recently pushed first), "
           "the open pull requests it is involved in, and the latest Actions runs of a few repositories. It writes "
           "nothing."),
    base="https://api.github.com (through gh where it is signed in)",
    version=f"X-GitHub-Api-Version: {VERSION}, Accept: application/vnd.github+json",
    auth=("gh's own sign-in, where gh is signed in (no token read by the plugin); else GITHUB_TOKEN, a personal access "
          "token, as a bearer token"),
    limits="5,000 requests an hour for a signed-in user; the search API 30 a minute; a read here is about eight",
    costs="nothing for these reads",
    links=(Link("GitHub REST API", _DOCS, "reference"),
           Link("Authenticating to the REST API", _DOCS + "authentication/authenticating-to-the-rest-api", "auth"),
           Link("Rate limits", _DOCS + "using-the-rest-api/rate-limits-for-the-rest-api", "limits"),
           Link("API versions", "https://docs.github.com/en/rest/about-the-rest-api/api-versions", "changelog"),
           Link("GitHub status", "https://www.githubstatus.com/", "status")),
    areas=(Area("Users", "the signed-in user and others", _DOCS + "users/users", covered="who is signed in"),
           Area("Repositories", "repositories listed, read, made, changed", _DOCS + "repos/repos",
                covered="the Repositories table"),
           Area("Search", "issues and pull requests, code, repositories found by a query", _DOCS + "search/search",
                covered="the Open pull requests table"),
           Area("Actions", "workflows, their runs, jobs, artifacts and runners", _DOCS + "actions/workflow-runs",
                covered="the Latest Actions runs table"),
           Area("Pulls", "pull requests read, made, reviewed, merged", _DOCS + "pulls/pulls"),
           Area("Issues", "issues read, made, commented"), Area("Organizations", "organizations and their members"),
           Area("Git database", "blobs, trees, commits and refs"), Area("Checks", "check runs and suites"),
           Area("Releases", "releases and their assets")),
    calls=(Call("GET /user", "the signed-in user", "Users", used="who is signed in, and whether it is let in",
                docs=_DOCS + "users/users#get-the-authenticated-user"),
           Call("GET /user/repos", "the repositories the user can see", "Repositories",
                used="the Repositories table (per_page 30, sort pushed)",
                docs=_DOCS + "repos/repos#list-repositories-for-the-authenticated-user"),
           Call("GET /search/issues", "issues and pull requests found by a query", "Search",
                used="the Open pull requests table (is:pr is:open involves:<user>)",
                docs=_DOCS + "search/search#search-issues-and-pull-requests"),
           Call("GET /repos/{owner}/{repo}/actions/runs", "a repository's workflow runs, newest first", "Actions",
                used="the Latest Actions runs table (per_page 3, five repositories)",
                docs=_DOCS + "actions/workflow-runs#list-workflow-runs-for-a-repository"),
           Call("POST /repos/{owner}/{repo}/pulls", "a pull request made", "Pulls", writes=True),
           Call("PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge", "a pull request merged", "Pulls", writes=True),
           Call("POST /repos/{owner}/{repo}/actions/runs/{run_id}/rerun", "a run started again", "Actions", writes=True)),
    verified=VERIFIED)

GH_CLI = Api(
    name=GH, maker="GitHub (Microsoft; open source, MIT)", kind="command",
    about=("gh, GitHub's command line: signs in once (gh auth login) and keeps its token in the system's keyring, then "
           "signs every request. The plugin asks gh for its version and whether it is signed in to github.com (the "
           "account's name alone is kept: never its token line), and reads through gh api, without a window, its "
           "prompts, pager and update checks off."),
    base="gh on PATH", version="gh 2: auth status's lines as it prints them",
    auth="gh's own: the plugin never asks gh for its token (gh auth token is never run)", limits="GitHub's own",
    costs="nothing",
    links=(Link("GitHub CLI manual", "https://cli.github.com/manual/", "reference"),
           Link("gh auth status", "https://cli.github.com/manual/gh_auth_status", "auth"),
           Link("gh api", "https://cli.github.com/manual/gh_api", "docs"),
           Link("cli/cli", "https://github.com/cli/cli", "source"),
           Link("Releases", "https://github.com/cli/cli/releases", "changelog")),
    areas=(Area("Version", "gh's own version", covered="gh's version on the page"),
           Area("Authentication", "gh auth login, status, token, logout", covered="whether gh is signed in, and as whom"),
           Area("API", "gh api: any REST or GraphQL request, signed by gh", covered="every read of GitHub through gh"),
           Area("Repositories", "gh repo clone, create, view"), Area("Pull requests", "gh pr list, create, merge"),
           Area("Actions", "gh run list, view, rerun")),
    calls=(Call("gh --version", "gh's version", "Version", used="gh's version"),
           Call("gh auth status --hostname github.com", "whether gh is signed in, and as whom", "Authentication",
                used="whether gh can be read through"),
           Call("gh api --method GET <path>", "a REST read, signed by gh", "API", used="every read through gh"),
           Call("gh auth token", "the token gh keeps, printed", "Authentication"),
           Call("gh pr merge", "a pull request merged", "Pull requests", writes=True)),
    verified=VERIFIED)

APIS = (GITHUB_REST, GH_CLI)
