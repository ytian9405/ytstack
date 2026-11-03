# Execution results

Final authoritative run: `20261102T123809463314Z/receipt.json` and associated native logs.
Working directory: this project root. Python 3.12.3, standard library only.

Command: `python3 .agents/skills/test-ledger-lite/scripts/verify.py` → exit 0.
Baseline and restored full suites: 6 tests each, OK (original smoke plus LL01–LL05).
LL01, LL02, LL03, LL04, LL05: PASS. Each case's command/result transcript is in baseline.log and restored.log.
The isolated negative-control suite: 1 test, expected failure, exit 1. LL02's reopened list returned [] instead of the literal expected record after an add returned success. Failure detection: PASS. The variant is retained as negative-expense_cli.py.
The live expense_cli.py hash is recorded in receipt.json and source equality was confirmed. README.md and the original smoke test were not edited. Scratch copies and per-test ledgers were removed, with no owned ledger directories found after the final run; evidence remains. Doctor checks (Python version, CLI --help, file prerequisites) succeeded.

Earlier evidence is retained: 20261102T123737392342Z detected the lost-write variant at the second add's ID assertion, but its stricter log matcher expected a list assertion, so helper validation was FAIL despite product tests passing. LL02 was strengthened to reopen immediately after the first add. 20261102T123752432375Z then passed helper validation. Final run also locates test scratch directories inside the project.

Artifact review: skill frontmatter, case index, selected case commands, trace output and relative helper root were checked against actual files and executed helper commands. No separate dependency installation or generated artifacts are needed to rerun.

SKIPPED/out of scope: corrupt JSON, concurrent writes, filesystem permission failures (README exclusions), performance, additional Python/OS environments, signals and fuzzing. A negative control shows sensitivity for lost writes, not complete mutation coverage.
