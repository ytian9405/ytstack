# ytstack v0.4 acceptance contract

The release contains four requested skills: `acceptance-criteria`, `create-test-skill`, `bro`, and `technical-bro`, plus always-on plain-talk rules in `voice/plain-talk.md`. `unslop` is a bundled dependency of `technical-bro`. One source tree serves Codex and Claude Code. There is no coordinator mode, session hook, model configuration, or dependency on an installed pstack.

## Scope and provenance

- `create-test-skill` generates a project-local `test-<app>` skill, runnable behavior tests, and a case index. It does not merely draft a test plan.
- `bro` keeps the upstream instruction first and adds Chinese rules.
- `technical-bro` preserves the upstream technical-writing body, with its name and relative dependency references adapted. Two trial-supported changes preserve the requested language and restrict vocabulary-rule proposals to explicit rule-maintenance tasks.
- `unslop` keeps every upstream rule and appends Chinese rules 34-44, a Chinese guiding principle, and a table that groups the upstream rules.
- Source commits, original file hashes, changes, and MIT attribution are recorded. Copied upstream text retains Lauren Tan's license. The Claude port is a design reference, not an unacknowledged source of copied implementation.
- New skills use normal discovery. The upstream explicit-only frontmatter is not carried into this new package.

## Structure and installation

- Each skill has valid `name` and `description` frontmatter. Every local resource link resolves inside the package.
- Core instructions use host capabilities rather than Cursor tool names, model slugs, cloud agents, transcript directories, or `/loop`.
- Claude plugin metadata names `ytstack`; its `skills/` directory is a sibling of `.claude-plugin/`.
- Project installation exposes each skill individually. Installing twice is harmless. An existing unrelated target is never overwritten. Selecting `technical-bro` includes `unslop`.
- The source package remains movable before installation. Installation and validation do not depend on this machine's absolute paths.

## Executable acceptance

| ID | Exercise | Pass condition |
| --- | --- | --- |
| S1 | Validate all five skills and the package | Names, descriptions, metadata, dependency links, and license records are valid. |
| S2 | Compare copied content with frozen upstream | Local body hashes match `provenance.json`; upstream `bro` and `unslop` text is still present; technical-writing differences are limited to the recorded adaptations. |
| S3 | Install into a temporary project | Individual entries resolve; repeated installation succeeds; a conflicting entry is preserved and reported. |
| B1 | Independent agent uses `create-test-skill` on a small CLI project | The agent reads the repository, generates a discoverable test skill and runnable tests, and verifies real public behavior, including persisted state. |
| B2 | Break one covered behavior in an isolated copy | The same test fails for the intended behavioral reason; restoring the copy makes it pass. No product source outside the isolated copy is altered. |
| B3 | Execute the generated skill after generation | A different agent can follow its instructions without the generator's conversation or ytstack installation. |
| B4 | Run a test where a prerequisite is unavailable | Report `BLOCKED`, not `PASS`; do not weaken assertions or silently substitute a different feature. |
| B5 | Inspect test artifacts and cleanup | Commands, outputs, exit statuses, covered case IDs, and evidence paths are preserved; temporary state and processes owned by the run are removed after success and failure. |
| W1 | Independent agent uses `bro` on a technical explanation | Meaning and numbers survive; language becomes understandable without new investigation or invented facts. |
| W0 | Sol and Astra answer ordinary project questions with `--voice` installed and no plain-language hint | Compared blind with the same question without it. **The user decides**: a model score cannot pass this row, because a model judge gave full marks to replies the user called jargon-heavy. |
| W3 | The user says “说人话” after a reply | `bro` loads; conclusions, numbers, conditions, and alternatives survive. |
| A1 | Ask for criteria in natural language before any code | `acceptance-criteria` loads and no code changes. Questions that merely explain code do not load it. |
| A2 | Compare criteria with a frozen list of open decisions | Decisions that change behavior are listed briefly at the end for the user to change. |
| A4 | The user compares criteria blind against the pre-skill baseline | **The user decides.** Model scores cannot pass this row. |
| A3 | Check criteria against frozen wrong and acceptable implementations | Wrong ones are rejected by a quoted criterion; acceptable ones are not. |
| W2 | Independent agent uses `technical-bro` on an operation guide | Commands, conditions, and technical facts survive. Steps are actionable, terminology is consistent, and the chosen document type remains clear. |

Behavioral results and structural validation are separate. A valid Markdown file does not demonstrate correct behavior. A test run that exposes a real product bug may report `FAIL` while its test artifact is valid; creating tests does not authorize repairing the product.

## Coverage limits

The current state of W0, W3, and A1-A3, including what is still failing, is in `evaluation/v04/REPORT.md`, with earlier rounds in `evaluation/v02/` and `evaluation/v03/`. The first behavioral exercise uses a real local CLI fixture. Other platforms are supported by the instructions, but UI, remote-service, and native-host discovery are not declared exercised unless a corresponding run is recorded. Missing capabilities are reported explicitly. No automatic publication, global installation, production modification, or unbounded test run is part of acceptance.
