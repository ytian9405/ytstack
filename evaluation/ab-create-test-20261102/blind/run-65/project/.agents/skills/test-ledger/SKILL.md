---
name: test-ledger
description: Verify Ledger Lite CLI user behavior with standard-library unittest and demonstrate regression detection using temporary defective copies.
---

Use this skill when validating Ledger Lite behavior or changes to its CLI. Run from the project root with Python 3.9+. No dependencies, network, account or service are required.

1. Read README.md and tests/test_smoke.py plus tests/test_behavior.py. Treat README.md as the product contract. Preserve the original smoke test and do not alter the product or contract merely to make tests pass.
2. Run `python3 -m unittest discover -s tests -v`. Ensure LEDGER_TEST_CLI is unset for the baseline; that variable is only a test seam for temporary candidate programs.
3. Run `python3 scripts/check_test_detection.py`. Require all six mutations to report DETECTED and temporary-directory cleanup to report True. A missed mutation or changed mutation anchor requires investigation, not weakening an assertion.
4. For durable evidence, run the commands in TESTING.md and retain exit codes and full output. On failure, report the case ID, exact command, expected behavior and observed output. Fix authorized product changes separately; rerun affected checks and then the full suite.
5. Report counts, detection results, artifact locations and scope limits. Test data and mutated source must remain temporary; never use a real ledger.

Case mapping and exclusions are in TESTING.md. Each behavior test creates an independent temporary state path and invokes real CLI subprocesses with a 10-second timeout. Tests do not import implementation helpers. To extend coverage, assert observable JSON, exit status, stderr or persisted state against the documented contract, and demonstrate the test detects a representative isolated defect where practical.
