---
name: test-ledger-lite
description: Run Ledger Lite public CLI contract tests with isolated ledger data, retained command transcripts, and an isolated lost-write negative control.
---

# Ledger Lite tests

Run all commands from this repository root (the directory containing `expense_cli.py`). Requires Python 3.9+ standard library only. No install, network, credentials, server, port, or background process is needed. Expectations derive from README.md. Do not modify product code or weaken assertions on failure.

## Doctor and launch

Read README.md and tests/test_smoke.py when updating coverage. Check prerequisites without writing ledger data:

```sh
python3 --version
python3 expense_cli.py --help
python3 -c "from pathlib import Path; assert Path('expense_cli.py').is_file(); assert Path('tests/test_behavior.py').is_file()"
```

A missing interpreter, target, or test file is BLOCKED. A successful help command checks CLI readiness; it does not prove ledger behavior. Each test launches the real CLI with `sys.executable` and an absolute `--state` path in its own TemporaryDirectory. Every command is a fresh process, bounded to 10 seconds. The CLI exits after each action; no manual target startup is needed.

## Run and retain evidence

```sh
python3 -m unittest discover -s tests -v
python3 .agents/skills/test-ledger-lite/scripts/verify.py
```

The first command runs the original smoke test plus five behavior cases. To select a case, use the exact command in [cases/README.md](cases/README.md). unittest exit 0 means all selected assertions passed; assertion failures return nonzero. Inspect errors: missing prerequisites and timeouts require diagnosis rather than calling them product regressions.

The verification helper uses the same suite, enables JSON action transcripts, and writes a unique UTC directory under `evidence/`. Each log includes case identifiers, actual command arguments, JSON stdout, stderr and exit code, plus unittest assertion results. `commands.json` records working directories and runner exit codes. `receipt.json` identifies Python, target SHA-256, case status, failure detection and cleanup. The helper prints the evidence directory and returns nonzero when validation fails. It bounds each suite subprocess to 120 seconds. Keep all logs, even if assertions fail. On a blocked or interrupted helper run, preserve partial logs and record the reason; absent receipts do not mean PASS.

## Failure detection and cleanup

The helper copies tests and the target into an owned TemporaryDirectory under the new evidence directory. Only that copy changes: saving writes an empty array while commands still return normal success values. The unchanged LL02 test must fail at its reopened `list` content assertion. `negative-expense_cli.py` and `negative-control.log` preserve the exact variant and failure. This is evidence of assertion sensitivity, separate from product test results. The helper removes the disposable copy on success or failure, then reruns the original full suite and checks that live source is unchanged. Test state directories are removed by unittest cleanup even after assertion failure; subprocesses are synchronous and bounded. Never delete historical evidence or kill processes by name.

## Interpretation and maintenance

PASS: a case ran and all assertions passed. FAIL: the target ran and violated a contract assertion. BLOCKED: a prerequisite prevented a meaningful run. SKIPPED: explicitly deferred or out of scope; never label an unrun case PASS. Receipt case statuses apply to successful full suite runs; if a suite fails, use individual unittest lines to distinguish actual passed/failed/blocked cases.

Update the case index, literal expected values and tests together only when the documented contract changes. Rerun affected cases and the full verification helper after changes to CLI parsing, persistence, IDs, voiding or summaries. Preserve smoke coverage and previous evidence. If the save boundary changes, review the isolated negative variant instead of modifying the live target.

Not covered: corrupt JSON, concurrent writers and filesystem permission failures (outside README contract); performance, other Python/OS versions, signals and arbitrary fuzz inputs. These are SKIPPED, not verified behavior.
