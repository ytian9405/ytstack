---
name: test-tiny-queue
description: Run Tiny Queue's persistent JSON CLI behavior tests, retain per-action evidence, and prove persistence failure detection in an isolated copy. Use for this repository's queue_cli.py contract, not generic Python testing.
---

# Test Tiny Queue

Run all commands from the repository root containing `queue_cli.py` and `README.md`. This Codex project skill is discoverable under `.agents/skills/`. It has no dependency on ytstack, a plugin cache, or the conversation that created it.

The public interface is `python3 queue_cli.py --state PATH {add TITLE,list,complete ID}`. README.md defines the behavioral expectations. There is no server, network, credential, package install, or build step. Use Python 3.8+ with its standard library and GNU `timeout` on this host. Each CLI invocation completes synchronously; valid JSON and the asserted task values establish readiness. A successful `--help` is only a prerequisite check.

## Doctor and launch

Choose a new evidence directory for each run; retain old receipts. The following directory name is an example for the first run only. On later runs substitute a new name consistently.

```sh
mkdir -p test-evidence/initial
timeout 15s python3 tests/test_queue_cli.py --doctor --evidence test-evidence/initial/doctor.json
```

Doctor reads and compiles the target without importing it, invokes `--help` with a five-second bound, and records Python, absolute target path, target SHA256 and startup output. It creates no queue state. A missing target, unusable interpreter, startup failure, or timeout is `BLOCKED`. No shared data, ports or processes require inspection. The runner creates a new owned system temporary directory per case, with a nonexistent nested state path. No preexisting queue file is used. Commands run in separate child processes, so reads prove persistence across invocations.

## Run and inspect

```sh
timeout 45s python3 tests/test_queue_cli.py --evidence test-evidence/initial/suite.json
timeout 30s python3 tests/test_queue_cli.py --case TQ02 --evidence test-evidence/initial/TQ02.json
```

See [the case index](cases/README.md) for the five stable case IDs, inputs, actions and literal expected results. The suite runs all five. Each child invocation has a five-second timeout. Runner exit 0 means all selected behavior assertions passed; 1 means a failed assertion or runner error; 2 means a prerequisite blocker. GNU timeout exit 124 means the outer run was interrupted, never a product regression. Inspect `runner_error` or traceback before interpreting exit 1 as a product defect. An unexecuted case is `SKIPPED`, never `PASS`. Keep failures intact; creating tests does not authorize product fixes or changing assertions to match bugs.

The JSON receipt records invocation, working directory, Python/target identity, each case's scratch path, actual CLI commands, stdout/stderr, exit status, assertion labels, actual and expected values, case result and cleanup. Evidence paths must be new; the runner rejects overwriting a historical receipt. Unexpected invalid JSON is an assertion failure recorded with the raw action output. The tests use public CLI subprocesses without mocks. Disk checks supplement fresh-process `list` checks. Setup responses are validated before testing an error path.

## Demonstrate failure detection

```sh
timeout 60s python3 .agents/skills/test-tiny-queue/scripts/prove_failure_detection.py --evidence-dir test-evidence/initial/failure-detection
```

The helper makes a disposable copy of `queue_cli.py` and removes only its write call. `add` still exits zero and prints the correct returned task. It runs TQ02 unchanged: the fresh-process list must return `[]` and fail the expected one-task assertion. It saves the variant, unified patch, output and receipt, restores the original bytes in that disposable copy, and reruns the exact same command and expectations. The helper moves each active receipt to `broken.json` or `restored.json` before the next run. `proof.json` checks intended failure, restored success, scratch removal and the live file's unchanged SHA256. Helper exit 0 validates this mechanism; it does not claim complete behavior coverage. If the write boundary changes, the helper reports a blocker requiring a reviewed variant update.

## Cleanup and maintenance

Normal runs, assertion failures and child timeouts clean their own `TemporaryDirectory` through unittest cleanup or context management. Every CLI child is waited for; subprocess timeouts kill and reap that owned child. No daemon or background process is started. Verify each case's `cleanup.scratch_removed` and the proof's cleanup fields; JSON/log/patch evidence remains under `test-evidence/`. Do not kill by process name or delete broad temporary-directory patterns. If an outer timeout or external kill prevents receipt completion, inspect the last recorded owned path, verify no owned child is running, then remove only that run's exact scratch directory. An incomplete receipt is not a pass.

For changed public behavior, update README.md's contract and the corresponding indexed expectations together, preserving case IDs, unrelated cases and old evidence. Rerun affected cases, the full suite and the isolated proof when persistence or test plumbing changes. Internal refactors should preserve these tests. Coverage excludes malformed/corrupt JSON, concurrent writers, filesystem permission failures, CLI parser permutations and performance; those behaviors have no documented product contract here.
