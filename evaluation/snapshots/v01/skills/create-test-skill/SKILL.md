---
name: create-test-skill
description: "Generate or update a project-local testing skill with runnable behavior tests, reproducible evidence, and demonstrated failure detection. Use when asked to create a reusable test skill or test workflow for a repository. For an ordinary one-off test addition, use the existing project tests directly."
---

# Create a test skill

Create a project-local `test-<app>` skill and executable tests that another agent can run cold. A useful test drives real code through its public interface, checks an observable result against an independent expectation, and fails when that behavior breaks. A test plan alone is a draft.

## Establish the contract from the repository

Read the project's instructions, existing tests, and real entry points before choosing a runner. Respect the requested feature and scope. Work out:

- **Interface.** What does the user or caller use: UI, CLI, API, library, or several entry points?
- **Run and readiness.** What commands, dependencies, data, and credentials make the target usable? A healthy process or open port alone may not mean initialization is complete.
- **Behavior.** What concrete input, action, and observable result establish the requirement? Include relevant errors and externally visible effects such as persisted files or rows.
- **Drive and observe.** Which existing runner, browser driver, PTY, HTTP client, or public library API can exercise it? Reuse the project's harness and conventions. Add a small independent script only when there is no suitable runner.
- **Isolation.** Which ports, profiles, temporary data, files, or processes will this run own? Keep evidence separate from disposable state. Observe what a dry-run actually does before relying on its name.

Ask only for facts or product choices that the repository and an authorized local run cannot settle. Use the current host's actual tools. This skill requires no named model, subagent type, plugin, network service, or installed pstack.

If the unmodified target cannot start, distinguish an environment blocker from a reproducible product failure. Report the evidence. Creating tests does not authorize repairing product code, changing shared environments, or obtaining new external access.

## Write executable behavior tests

Choose the smallest useful coverage for the request. For a new project-wide skill, identify the main three to five behaviors when available; a narrow request can start with one. Enumerate distinct entry points instead of silently replacing an inaccessible one with a convenient path.

For each selected case, name its input, user action, independent expected result, and command. Prefer the real public path and literal expected values derived from the requirement. Verify the resulting state and relevant side effects, not just that a command ran, a file exists, or an internal helper was called. An exit status or file existence can itself be the contract, but it cannot stand in for a stronger behavior the test claims to cover.

Keep setup data separate from the actual result. Never compute the expected result by calling the implementation under test. A test must notice a missing write, wrong return value, or duplicated effect when that is the behavior it guards. Keep tests passing through an internal refactor that preserves the contract. Mocks belong at an existing external boundary, not in place of the behavior being verified.

Store tests in the repository's established test location. Keep owned driver helpers with the generated skill when that is the clearest local convention. Use stable selectors and real commands. Give executable helpers an invocation in the skill. Leave no placeholders in generated output.

## Generate the project skill and case index

Read [the output contract](references/output-contract.md) before writing the generated artifacts.

Honor an explicit destination and the repository's existing layout. Otherwise use the active host's project discovery directory: `.agents/skills/test-<app>/` for Codex, `.claude/skills/test-<app>/` for Claude Code. Infer the active host from the session, not merely from installed CLIs. If it is unknown and no convention exists, use `.agents/skills/` and state the choice. Use the same tests and instructions when both hosts are requested; preserve relative links and include dependencies in any installed copy.

If a matching test skill or equivalent tests already exist, extend them in place. Preserve established coverage, case IDs, evidence, and unrelated local changes. Describe intended changes to the behavioral contract rather than quietly changing assertions to fit current output.

Write `SKILL.md` with `name` and a discriminating `description`. From that file alone, a fresh agent must be able to launch a usable target, check the instance, run a named case or the suite, interpret results, retain evidence, and clean up. Include a case index and per-case driving instructions. Make counts, paths, selectors, and commands true of the actual repository. The generated skill must work without this generator, its chat history, or an installed ytstack.

## Prove the tests and the generated instructions

1. Follow the generated instructions from an isolated starting state. Launch, check readiness, run at least one mapped behavior, capture its assertions and outputs, and clean up. Use a bounded run or the project's timeout convention.
2. Demonstrate that at least one representative behavior assertion catches a meaningful break. Prefer an existing failing regression. Otherwise, in an isolated copy or reversible test-only variant, break one covered behavior and run the same test command. Confirm it fails for that behavior, not because of syntax, missing imports, an unavailable dependency, or a deliberately unconditional failure. Keep the expectation unchanged. Save the patch or variant and failure output, then restore and rerun. Do not alter the user's live target to manufacture this proof.
3. Clean up after success and failure. Stop only processes started by this run, using recorded identities; do not kill by process name. Remove only owned scratch state. Confirm the evidence still exists after cleanup.

Evaluate existing bugs honestly. A valid test can report `FAIL` on a real product defect; do not weaken it or patch the product to get green. A negative control demonstrates the tested assertion's sensitivity, not completeness of the suite. When failure detection or a real target cannot be exercised, deliver the files as a draft with the exact unverified item.

Record each case as `PASS`, `FAIL`, `BLOCKED`, or `SKIPPED`, with its command and evidence. A missing dependency is `BLOCKED`. An unexecuted case is never `PASS`. Keep test-artifact validation separate from the product's test results. If a stand-in was used, name the target-only setup and behavior still unverified.

## Hand off

Report the generated skill path, test command, cases actually run, observed results, failure-detection evidence, cleanup outcome, and remaining coverage. Link the evidence rather than claiming that generated files prove behavior. On later use, update the case index and rerun affected cases when code or prerequisites change. No separate maintenance skill is required for this release.
