# Sources and adaptations

ytstack is a small personal skill pack. It uses pstack's design of narrowly scoped skills with explicit evidence, reusable project instructions, and readable writing. It does not include the pstack coordinator, model routing, hooks, or runtime mapping system.

The copied or adapted upstream files come from `cursor/plugins/pstack`, copyright 2026 Lauren Tan, under the MIT License retained in `LICENSE`. The frozen source commit is `ae5650febf4320793844c12c4adaa937f417f8da`.

- `bro`: upstream instruction kept as the first line. Adds Chinese triggers and rules that keep conclusions, numbers, and alternatives.
- `technical-bro`: technical-writing instruction body retained. The name, heading, and invocation description are renamed; its `unslop` dependency is read through a package-relative link. Independent use exposed an unsolicited vocabulary-diff requirement, so proposals now require an explicit rule-maintenance request and an actual pattern in the input. A short language rule preserves the requested language, output format, and literal technical identifiers.
- `unslop`: upstream rules unchanged; appends Chinese rules 34-40. Bundled so technical-bro has no dependency on an external pstack installation.
- `acceptance-criteria`: new in v0.2. Upstream has no skill that writes criteria before implementation. The falsifiable-predicate idea comes from pstack's `figure-it-out`; no upstream text is copied. The skill directory carries the package license for uniformity.
- `voice/plain-talk.md`: new in v0.2. Its write-it-right-while-drafting approach comes from the "Writing the reply" section of pstack's `poteto-mode`; the rules themselves are new and target Codex's GPT models in Chinese.
- `create-test-skill`: adapted from create-verification-skill. Keeps repository-first investigation, real user paths, generated project skills, a maintained case index, evidence, owned cleanup, and an actual proving run. Adds explicit executable behavior assertions, demonstrated failure detection, incremental updates, distinct test-artifact/product results, and host-independent destinations. The required behavior principles are included directly rather than importing the full principles collection.

All five are ytstack skills with normal host discovery. The upstream `disable-model-invocation: true` field is intentionally omitted. Bro remains short; technical-bro retains technical-writing's scope and four writing layers. Its new name does not turn it into a general simplification command.

`michael-denyer/pstack-claude`, commit `8ecae6893912d2bbb3b841c09a8d76e61a4d708b`, informed the shared source layout and separation of host-specific discovery from skill instructions. No port-specific implementation or session hook is copied. That repository is also MIT-licensed; Michael Denyer is credited here for the design reference.

`provenance.json` records source URLs, commits, original hashes, adopted paths, and intended changes. `tools/validate.py` checks local copied-body hashes. Full host validation and behavioral test results are recorded separately; content hashes do not establish behavior.

Each skill directory also carries the full license so a standalone copied installation retains the copyright and permission notice.
