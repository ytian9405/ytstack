# Tiny Queue case index

Working directory: repository root. All cases drive the real `queue_cli.py` entry point via a new subprocess per action, with a unique nonexistent nested state path. Tests are in `tests/test_queue_cli.py`, class `QueueCases`. Expectations below derive from README.md; no implementation helper supplies expected output. Use a new evidence filename each time.

| ID / test method | Input and action | Observable contract | Exact command |
| --- | --- | --- | --- |
| TQ01 / `test_TQ01_empty_queue` | `list` on missing state | JSON `[]`; no file is written | `timeout 30s python3 tests/test_queue_cli.py --case TQ01 --evidence test-evidence/TQ01.json` |
| TQ02 / `test_TQ02_add_persistence_order` | Add `  Prepare slides 雪  `, read in new process, add `Send notes`, read again | IDs 1 and 2; exact titles including whitespace/Unicode; `done: false`; parent created; both tasks persist in insertion order on disk and through `list` | `timeout 30s python3 tests/test_queue_cli.py --case TQ02 --evidence test-evidence/TQ02.json` |
| TQ03 / `test_TQ03_complete_idempotence` | Add two tasks, complete ID 1 twice, list after each, add `Archive` | Original title retained; ID 1 done true; ID 2 unchanged; no duplicate task; later addition ID 3 | `timeout 30s python3 tests/test_queue_cli.py --case TQ03 --evidence test-evidence/TQ03.json` |
| TQ04 / `test_TQ04_blank_title_rejected` | Add whitespace-only titles to missing and populated state | Nonzero exit and a nonempty error on stderr; missing state remains absent; existing tasks remain unchanged on disk and in a new process | `timeout 30s python3 tests/test_queue_cli.py --case TQ04 --evidence test-evidence/TQ04.json` |
| TQ05 / `test_TQ05_unknown_id_rejected` | Complete ID 42 with missing and populated state | Nonzero exit and a nonempty error on stderr; missing state remains absent; original task remains unchanged on disk and in a new process | `timeout 30s python3 tests/test_queue_cli.py --case TQ05 --evidence test-evidence/TQ05.json` |

Full suite: `timeout 45s python3 tests/test_queue_cli.py --evidence test-evidence/suite.json`.

Every setup task is created through `add` and its exact response is checked. All task expectations use literal IDs/titles/booleans rather than reading the implementation. Error tests additionally snapshot the established disk state before the rejected action and compare it afterward. Each case starts independently and always registers scratch cleanup before driving the CLI. The machine-readable receipt includes per-action outputs, each assertion and the final case status.
