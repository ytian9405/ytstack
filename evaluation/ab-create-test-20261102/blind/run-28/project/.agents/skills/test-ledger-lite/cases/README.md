# Case index

Working directory: repository root. Entry point for every case: `python3 expense_cli.py --state <isolated path> ...`, driven through subprocess by `tests/test_behavior.py`. Setup and teardown are automatic. Successful calls assert exit 0, empty stderr and exactly one parseable JSON value. Expected records and totals are literal contract examples.

| ID / unittest method | Input, action and independent assertions |
| --- | --- |
| LL01 / test_LL01_empty_reads | Missing nested ledger; `list` → `[]`, `summary` → zero count/total and empty categories; neither file nor parent created. |
| LL02 / test_LL02_add_persistence | Add ` 午餐 🍜 `, 1250, ` 餐饮 ` and `车票`, 300, travel; full records have IDs 1/2 and false void flags; new processes list exact original strings in order; nested file created. |
| LL03 / test_LL03_void_and_ids | Add lunch, void ID 1 twice, reopen between operations; exact full record preserved except true flag, repeated void leaves bytes unchanged; add dinner receives ID 2 and ordered list retains voided record. |
| LL04 / test_LL04_summary | Add food 1250/750, travel 300, void-only 999; void fourth; count 3, total 2300, food 2000/travel 300, no void-only key; void remainder yields empty summary. |
| LL05 / test_LL05_invalid_inputs_preserve_data | Seed lunch; reject cents 0/-1/1.5/abc, whitespace title/category, unknown void 999; each exits nonzero with stderr, preserves exact file bytes and reopened record. |

Exact selected-case commands:

```sh
python3 -m unittest discover -s tests -p test_behavior.py -k LL01 -v
python3 -m unittest discover -s tests -p test_behavior.py -k LL02 -v
python3 -m unittest discover -s tests -p test_behavior.py -k LL03 -v
python3 -m unittest discover -s tests -p test_behavior.py -k LL04 -v
python3 -m unittest discover -s tests -p test_behavior.py -k LL05 -v
```

Full suite: `python3 -m unittest discover -s tests -v`. Add `LEDGER_TRACE=1` before a command to print action/result JSON. For durable transcripts, target identity, baseline/restoration runs and negative-control evidence, run `python3 .agents/skills/test-ledger-lite/scripts/verify.py`. The existing `tests/test_smoke.py` remains unchanged and is included in the full suite.
