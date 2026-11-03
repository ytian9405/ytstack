# Case index

Working directory: project root. All cases drive `expense_cli.py` using independent subprocesses and per-test temporary state. Expectations derive from README, never implementation helpers. Tests live in `tests/test_behaviors.py`, class `LedgerBehaviorTests`.

| ID | Action and independent observable expectation | Method |
| --- | --- | --- |
| LL01 | Missing nested state: list is `[]`, summary is zero with `{}` categories; neither file nor parent is created. | `test_LL01_empty_reads_do_not_write` |
| LL02 | Add ` 午餐 🍜 ` / 1250 / ` 餐饮 ` and `车票` / 300 / travel: exact full records with IDs 1, 2, untrimmed strings, false void flags; fresh lists preserve order and content; nested file created. | `test_LL02_add_preserves_strings_and_persists` |
| LL03 | Add lunch, void ID 1 twice, add tea: exact returned and persisted void record, byte-identical repeated void, next ID 2, original record retained. | `test_LL03_void_is_persistent_idempotent_and_ids_increase` |
| LL04 | Add food 1250 + 200 and travel 300: count 3, total 1750, food 1450/travel 300. Void first: count 2, total 500, food 200/travel 300. Void all: zero summary. | `test_LL04_summary_groups_only_active_entries` |
| LL05 | Reject amounts 0, -1, 1.5, abc, whitespace title/category and void 999: each nonzero with stderr, unchanged disk bytes and exact original list. | `test_LL05_rejected_changes_preserve_data` |
| SMOKE | Original `tests/test_smoke.py`, `SmokeTests.test_empty_summary`: missing state summary equals literal zero summary. | preserved existing test |

Exact commands:

```sh
python3 -m unittest discover -s tests -p test_behaviors.py -k LL01 -v
python3 -m unittest discover -s tests -p test_behaviors.py -k LL02 -v
python3 -m unittest discover -s tests -p test_behaviors.py -k LL03 -v
python3 -m unittest discover -s tests -p test_behaviors.py -k LL04 -v
python3 -m unittest discover -s tests -p test_behaviors.py -k LL05 -v
python3 -m unittest discover -s tests -p test_smoke.py -v
```

Each method contains its complete setup and drives its own isolated journey; no case depends on another case's execution. Use the evidence runner in the parent skill for captured results and the isolated lost-write demonstration.
