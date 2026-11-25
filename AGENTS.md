# Agent guide

A three-button Keybow Mini controller for PiKVM Switch ports, running on a
Raspberry Pi Zero W. `src/pikvm_keybow.py` imports `keybow` and touches GPIO
at import time, so tests never import it: `tests/test_tls.py` extracts the
HTTPS functions with `ast` and runs them against a local TLS server. Keep new
tests hardware-free the same way. See README.md.

Never commit `.env`, real PiKVM addresses, credentials or the rendered
`systemd/pikvm-keybow.service`.

Run before pushing:

```bash
python3 -m unittest discover -s tests -v   # needs requests and openssl
ruff check .
shellcheck --severity=warning scripts/install.sh
```

## Pull requests and review

Finish and test a coherent change locally, then run a local code and security
review before asking for remote review. The owner requests Codex review for
the exact pushed head (`@codex review <full head SHA>`), one request at a
time. Address every finding on the same pull request and resolve its thread;
after three rounds that still find substantive issues, stop and reconsider the
change. Merge only a qualified head.

Required checks are `quality` and `review-gate`. `review-gate` comes from
`.github/workflows/review-gate-trusted.yml` (`pull_request_target`): it runs
the default branch's copy with a read-only token and never runs pull request
code, so a pull request cannot rewrite it. Protection pins the check to the
GitHub Actions app, not that workflow, so a pull request could still add a
same-named job; merge only through the owner's qualification tooling, which
counts the trusted run alone. No AI attribution in commits, titles or
descriptions, and commits come from a person's identity, not an app or bot
account (Dependabot excepted); `review-gate` rejects both.

The files in `.github/scripts/` are vendored. Do not edit them here; change
them at their source and re-vendor. CI tools are
pinned with hashes in `.github/ci-requirements.txt`; edit
`.github/ci-requirements.in` and recompile with the command in its header.

### Review guidelines

Reviewers (Codex, Claude Code, humans) apply these to every pull request.

- Failure here means: TLS certificate or hostname verification weakened or
  bypassed; credentials logged, committed or sent anywhere but the configured
  PiKVM; a button press that switches to the wrong port or sends an ATX or
  power action; the service failing to start or recover on the Pi; tests or
  CI that import the hardware module or contact a real PiKVM; CI that runs
  pull request code with secrets or write tokens. Prioritize these.
- Report only issues the change introduces or makes worse; mark pre-existing
  problems as pre-existing.
- Every finding needs file:line evidence and a concrete failure scenario.
- At most three nitpicks per review; skip what ruff and shellcheck enforce.
- Skip vendored files in `.github/scripts/`. Always check tests and fixtures
  for real addresses, credentials or private content.
- Start the summary with the number of findings; say plainly when nothing
  needs fixing.
