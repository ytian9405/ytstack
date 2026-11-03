# Execution results

Current final-artifact run: `20261102T124105239011Z/` (Python 3.12.3).

Reproduce from project root:

```sh
python3 .agents/skills/test-ledger-lite/scripts/run_evidence.py
```

- LL01, LL02, LL03, LL04, LL05 and the preserved smoke case: PASS, six tests in both baseline and follow-up runs.
- All seven invalid-input subtests executed within LL05.
- Negative control: deliberately lost disk writes in an isolated copy; the unchanged LL02 command failed on list content (`[]` versus the required record), demonstrating persistence assertion sensitivity. This expected negative result is test-mechanism validation, not a defect in the live product.
- Live product SHA-256 and unchanged-byte check: see `receipt.txt`.
- Scratch copy removed; per-test temporary ledger state is cleaned on success and failure. No background processes started. Logs and patch survive cleanup.
- Doctor commands from the skill were run successfully: Python 3.12.3, required files and standard-library imports present, CLI help exit zero. No installation required.

The earlier directory `20261102T124002601124Z/` is an intermediate run retained as history. Its negative control stopped at the file-existence assertion; the final run improves the proof by reaching the persisted-content comparison.

Outside coverage: corrupt JSON, concurrent writes, filesystem permission failures (excluded by README); exhaustive numeric limits, Unicode combinations, and argparse diagnostics beyond selected invalid values are not tested. No product or README contract changes were made.
