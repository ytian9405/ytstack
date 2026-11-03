# Generated test skill contract

Write instructions for an agent that has not seen the generation conversation. Adapt the structure to the actual project; the capabilities below must remain discoverable.

## Required artifacts

1. A discoverable `test-<app>/SKILL.md` with valid name and description frontmatter.
2. Executable tests in the existing test tree, or an owned driver when no runner fits. A checklist, mock-only demonstration, or prose exercise is insufficient.
3. `cases/README.md` indexing stable case IDs, the real entry points, what each case proves, its test location, and the exact command. Add per-case instructions when the journey needs more than a short index row.
4. An evidence location outside disposable state. Reuse a native runner's output where it already captures the necessary facts. Machine-readable receipts are useful, but a second report format is unnecessary when existing output suffices.

Use project-relative commands and document their working directory. Resolve bundled scripts relative to the generated skill directory, not to ytstack or a plugin cache. Generated artifacts contain concrete project values, not this contract's naming placeholders.

## Capabilities the skill must describe

- **Launch.** Actual setup/build/start commands, isolated data, initialization, readiness condition, and teardown. For a library, explain the environment and public invocation; it needs no invented server.
- **Doctor.** A read-only check that the target, version, data, authentication, and owned process or port are suitable. Explain how environment failure differs from behavior failure.
- **Run.** Exact commands for a selected case and the supported suite. State time bounds and how the runner signals failed assertions and setup blockers. Use stable handles for UI tests.
- **Assertions.** Observable input/action/result for each case, including relevant persistence or external effects. Expectations come from requirements. An expected value copied from the code under test proves nothing.
- **Evidence.** Capture the action and result, not only a final screenshot. Record the command, working directory, relevant non-secret parameters, output, exit status, case IDs, failed/passed assertions, artifact paths, and target identity or revision when known. Never log credentials. A suite-level receipt may reference native case-level reports.
- **Failure detection.** Explain the representative regression or isolated bad variant, the exact unchanged test command, intended assertion failure, restoration, and follow-up result. Keep product test results distinct from whether the test mechanism has been validated.
- **Cleanup.** Identify scratch state and processes the run owns. Execute cleanup after failure as well as success. Evidence survives cleanup. Never delete by a broad pattern or kill by process name.
- **Maintenance.** What code or behavior each case covers, and what to update and rerun when that contract changes. Preserve unrelated cases and historical evidence.

## Result meanings

| Result | Meaning |
| --- | --- |
| `PASS` | The case actually ran on the named target and its behavior assertions passed. |
| `FAIL` | The target ran and violated a behavior assertion. Preserve the failing expectation and evidence. |
| `BLOCKED` | A prerequisite or capability prevented a meaningful behavior check. Include the failed command or reason. |
| `SKIPPED` | An explicitly out-of-scope or deferred case was not run. State why. |

Raw runner exit codes keep their actual meaning. For example, a missing executable that exits nonzero is a blocker, not a demonstrated product regression. A wrapper must propagate a failed assertion as failure; do not swallow exceptions or return success after a failed subprocess.

## Example of a meaningful case

For a notes CLI, a persistence case can run the public `add` command with a concrete title in an isolated data directory. Then run the public `list` command in a new process and compare the returned titles with the literal expected title. Reopening the data matters: checking only the object constructed during setup would miss a dropped disk write.

To check sensitivity, make an isolated variant whose `add` command still prints a success message and exits zero but does not persist the note. The same persistence test must fail at the content assertion. Keep the captured failure and variant as evidence, restore the code, rerun, and verify cleanup left those artifacts intact.

This example explains the proof standard; use the target project's real interface and requirement rather than copying this case into unrelated projects.
