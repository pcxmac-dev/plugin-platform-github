# plugin-platform-github

GitHub for Liminal, one of the platform's Source Control plugins (Monday list item 35). GitHub is hosted, not
installable: this plugin reads the account's repositories, open pull requests and latest Actions runs. `SECTION` "scm",
icon `github`. It changes nothing on GitHub.

## How it asks

- **Through gh, where gh is signed in to github.com** (`gh auth status --hostname github.com`): every read is
  `gh api --method GET <path>`, signed by gh, so no token is read, kept or stored by this plugin; `gh auth token` is
  never run, and only the account's name is kept of what `auth status` prints. gh runs without a window, its prompts,
  pager, colours and update checks off.
- **Else with `GITHUB_TOKEN`** (through the login alone; a fine-grained token with read access to metadata, pull
  requests and actions), sent as a bearer to `https://api.github.com` alone by the library's Endpoint.
- **Else not at all**: the page says to run `gh auth login` or to set the token.

A read is the user, the 30 most recently pushed repositories, the open pull requests you are involved in, and the
latest three Actions runs of the five most recently pushed repositories (about eight GETs), kept 60 s; Read again
asks now. A token is taken out of every word said (GitHub's token shapes and the one set).

## Tests

Stand-ins alone: no gh, docker or network is run or reached (`tests/conftest.py` refuses every process and
connection while a test runs). Run them with the library on the path:

    PYTHONPATH="src;<liminal-libs>/src" python -m pytest -q -p no:cacheprovider

`LIMINAL_VENDOR_PAGES=1` lets `tests/test_apis.py` ask every address on its API cards once (the only test that reaches
the network). Each gate was taken out once and a test seen to fail.
