# Ledger Lite behavior verification

Run from this project root using Python 3.9+ and its standard library. No installation or network is needed. The original tests/test_smoke.py is retained. The reusable agent skill is `.agents/skills/test-ledger/SKILL.md`.

```sh
unset LEDGER_TEST_CLI
mkdir -p test-results
python3 -m unittest discover -s tests -v > test-results/unittest.txt 2>&1
baseline_status=$?
cat test-results/unittest.txt
python3 scripts/check_test_detection.py > test-results/detection.txt 2>&1
detection_status=$?
cat test-results/detection.txt
printf 'baseline_exit=%s\ndetection_exit=%s\n' "$baseline_status" "$detection_status"
test "$baseline_status" -eq 0 && test "$detection_status" -eq 0
```

Every test owns a TemporaryDirectory and a nested ledger path; addCleanup removes state even on assertion failure. Every CLI command runs in a separate process with a timeout, so persistence checks cannot pass through shared Python memory. Successful stdout must parse as one complete JSON value. Error checks require a nonzero exit code, nonempty stderr, and unchanged existing state bytes.

| Case | User behavior |
| --- | --- |
| Existing smoke | Empty summary |
| C01 | Missing-state list/summary; reads create neither file nor parent directory |
| C02 | Exact record fields, positive one-cent boundary, Unicode and surrounding whitespace, nested parent creation, process persistence and insertion order |
| C03 | Void preserves fields, persists, remains idempotent, keeps records listed, and does not reuse the highest voided ID |
| C04 | Summary excludes voided records and categories; all-voided ledger yields zero totals |
| C05 | Repeated category aggregation and distinct raw category keys |
| C06 | Zero, negative, decimal, text amounts; empty/whitespace title/category; unknown/zero/negative void IDs; errors preserve data and next ID |
| C07 | Invalid writes against missing state do not create a state file |

The detection script copies source into a temporary directory, introduces one defect per copy, and executes the relevant behavior case through LEDGER_TEST_CLI. It requires assertion failures rather than accepting launch/import failures. It checks ID reuse, voided summary inclusion, title stripping, accepting zero, reversed listing, and overwritten category sums. It removes every temporary candidate and returns nonzero for any missed defect. These six probes demonstrate detection for specific regressions, not exhaustive mutation coverage. Product source is never modified.

Current exclusions follow README.md: malformed JSON, concurrent writes and filesystem permission failures. No guarantees are tested for atomic/crash-safe writes, performance, platform-specific encoding, huge datasets or undocumented parser error wording. Validation ran on the local Python/Linux environment; other supported Python versions and operating systems were not exercised.

Actual execution evidence is in test-results/unittest.txt, test-results/detection.txt and test-results/result.txt. Logs are snapshots; rerun commands to validate later changes.
