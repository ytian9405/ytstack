---
name: test-ledger-lite
description: Run Ledger Lite CLI contract tests, retain reproducible unittest evidence, and demonstrate detection of a lost persistence write in an isolated copy.
---

# Ledger Lite contract checks

Run all commands from the Ledger Lite project root (the directory containing `expense_cli.py` and `README.md`). Use Python 3.9+ and its standard library only. No dependencies, network, account, server, ports, or credentials are needed. The public entry point is `python3 expense_cli.py --state PATH COMMAND`; every successful call returns one JSON value.

## Doctor and initialization

Read `README.md` for the contract and `tests/test_smoke.py` for the original convention. Read-only prerequisite check:

```sh
python3 --version
python3 -c "from pathlib import Path; import json, subprocess, tempfile, unittest; assert Path('expense_cli.py').is_file(); assert Path('tests/test_behaviors.py').is_file()"
python3 expense_cli.py --help
```

Python below 3.9, a missing file, inability to create a temporary directory, or a subprocess timeout is BLOCKED pending diagnosis, not proof of a product defect. A CLI which runs but violates a README expectation is FAIL. Preserve errors without changing assertions or product code.

Each test initializes its own `TemporaryDirectory`, with a previously absent nested state path. Each action starts a fresh CLI process with a 10 second timeout. LL01 establishes readiness by verifying empty `list` and `summary` responses and absent disk state; no persistent service needs launch. No live user ledger is used.

## Run and retain evidence

Full suite, including preserved smoke test:

```sh
python3 -m unittest discover -s tests -v
```

Named case example (replace LL02 with any indexed ID):

```sh
python3 -m unittest discover -s tests -p test_behaviors.py -k LL02 -v
```

[Case index](cases/README.md) maps commands and literal expectations. `ok` means the case ran and its assertions passed; unittest's nonzero exit requires inspecting the traceback to distinguish FAIL from BLOCKED. Never label unrun cases PASS; use SKIPPED with a reason. The seven invalid actions in LL05 run as subtests.

For a bounded suite, negative control, follow-up suite, and durable evidence:

```sh
python3 .agents/skills/test-ledger-lite/scripts/run_evidence.py
```

The script resolves the project from its own location and gives each suite at most 120 seconds. It creates a unique UTC directory under `evidence/`, prints that path, and stores commands, working directories, stdout/stderr, exit statuses, target SHA-256, and cleanup checks. `baseline.log` and `restored.log` contain individual unittest case outcomes. `receipt.txt` summarizes observed results. Inspect logs when the wrapper exits nonzero; a traceback or prerequisite problem is not a successful sensitivity proof. Exceptions propagate as nonzero.

## Failure detection

The script copies the test tree and CLI into an owned temporary directory. It replaces only the disk write with `pass`; the CLI still prints the successful add result. It runs the exact named LL02 command above with unchanged tests. The expected failure is the independent `list` response assertion: `[]` differs from the literal persisted record. `negative-control.patch` records the change, and `negative-control.log` records the failing assertion. This establishes lost-write detection, not completeness. The live product is never edited. The disposable copy is deleted and the original suite reruns; the receipt verifies unchanged product bytes.

## Cleanup and maintenance

Test state is removed by `addCleanup` even when assertions fail. The negative copy uses a context manager and is removed on success and assertion failure. CLI subprocesses finish synchronously; subprocess timeouts terminate and wait for the owned child. No background process is launched. Evidence remains outside scratch data. Python may create `__pycache__` under tests; these are harmless runner caches, not ledger state. Keep evidence directories when cleaning caches.

When changing CLI parsing, storage, ID allocation, void behavior, or aggregation, rerun the corresponding indexed cases and full suite. Update literal expectations only when the README contract intentionally changes. Preserve the original smoke test, stable case IDs, and previous evidence. Add cases for new contract requirements. Corrupt JSON, concurrent writes, and filesystem permission errors are outside this contract; no claim is made for them. This suite also does not exhaust huge amounts, arbitrary Unicode combinations, or all argparse errors.
