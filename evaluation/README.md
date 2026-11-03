# v0.1 evaluation evidence

Start with [summary.json](summary.json). Package checks, native Claude plugin validation, independent agent behavior, and coverage limits are recorded separately.

- `cli/`: an independent agent used `create-test-skill` on a small real CLI fixture. It generated a project-local skill, runnable tests, a case index, evidence, and a failure-detection helper. Five public behaviors passed with 49 assertions. Removing persistence in an isolated copy caused the intended assertion to fail; restoring the copy made it pass.
- `cold-use/`: a fresh agent received only the generated project and its test skill. It independently ran the suite and failure-detection proof, checked cleanup, and preserved evidence. It did not read ytstack or the first agent's report.
- `cli/test-evidence/parent-review/`: the parent independently confirmed that a missing target is `BLOCKED`. A different mutation, leaving completed tasks incomplete, caused the expected completion assertion to fail; restoring the code made it pass.
- `writing/`: independent `bro` and `technical-bro` outputs. The first writing trial exposed an unsolicited rule-diff requirement inherited from upstream. The skill received the documented correction; `technical-bro-v2.txt` and `report-v2.json` are the follow-up result.
- `skill-validation.json`: skill-creator frontmatter checks.
- `package-integrity.log`, `installer-tests.log`, and `claude-plugin.log`: actual package checks and the seven installation regressions. Native Claude validation passed with a non-blocking marketplace icon warning; no marketplace submission was requested.

Original receipts retain the exact temporary paths at which the recorded runs occurred. Those observations are not rewritten after archiving. To rerun an archived project, enter `cli/` or `cold-use/`, read its `.agents/skills/test-tiny-queue/SKILL.md`, and choose a new evidence directory. The generated instructions and tests resolve their project paths locally and do not require ytstack.

The exercised target is a local Python CLI. UI, remote-service, native application, actual Claude model invocation, and cross-host automatic selection are not claimed tested. One successful fixture cannot establish universal behavior for a prompt-based generator.
