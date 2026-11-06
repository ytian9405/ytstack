---
name: unslop
description: Cut AI tells from any writing.
---

# Unslop

Edit text to remove AI patterns. Scan for the patterns below, then rewrite. Preserve meaning and match the intended tone.

## Patterns to detect and fix

Rule numbers are stable ids that other skills cite. A removed rule leaves a gap.

### Content

3. **Superficial -ing phrases.** "highlighting...", "ensuring...", "reflecting...", "showcasing...", "fostering...". Delete or expand with real sources.
5. **Vague attributions.** "Experts believe", "Industry reports suggest", "Some critics argue". Name the source or delete.

### Language

7. **AI vocabulary.** Additionally, crucial, delve, enduring, enhance, fostering, garner, interplay, intricate, landscape (abstract), pivotal, showcase, tapestry (abstract), testament, underscore, vibrant. Replace with plain words.
8. **Fancy ways to say "is".** "serves as", "stands as", "boasts", "features". Say "is" or "has".
9. **"Not just X, but Y."** State the point directly instead.
10. **Rule of three.** Don't force ideas into groups of three. Use the natural number.
11. **Synonym cycling.** Protagonist, main character, central figure, hero all in one paragraph. Pick one, repeat it.
12. **False ranges.** "from X to Y" where X and Y aren't on a meaningful scale. List topics directly.

### Style

13. **Em dash overuse.** Avoid em dashes entirely. Use periods or commas only (no parentheses, no en dashes, no hyphen-as-dash substitutes). If a thought needs separation, end the sentence or use a comma.
14. **Colon overuse.** Colons are fine before a list or example, not as mid-sentence connectors. "If you're coming from traditional automation: instead of registering event handlers, you describe conditions" adds nothing with the colon. Rewrite to let the point stand on its own without comparison framing. "Describing when the scheduler should fire works best as plain English." Same meaning, no crutch punctuation.
15. **Boldface overuse.** Don't bold every proper noun or acronym.
16. **Inline-header lists.** The tell is a bold label and colon that restates the line: "**Performance:** Performance improved...". Convert those to prose. A bold lead-in that ends in a period, names the item, and is followed by genuinely new detail ("**Schema in TypeScript.** Tables live in one file.") is fine, not a tell.
17. **Title case headings.** Use sentence case.
18. **Decorative emojis.** Remove from headings and bullets.
19. **Curly quotes.** Use straight quotes.

### Communication artifacts

20. **Chatbot phrases.** "I hope this helps!", "Let me know if...", "Of course!", "Certainly!", "Found the smoking gun!" Remove.
22. **Sycophantic tone.** "Great question! You're absolutely right!" Respond directly.

### Filler

23. **Filler phrases.** "In order to" becomes "To". "Due to the fact that" becomes "Because". Delete "It is important to note that".
24. **Excessive hedging.** "could potentially possibly be argued that it might" becomes "may".
25. **Generic conclusions.** "The future looks bright." State specific plans or facts.

### Jargon

26. **Abstract metaphor nouns.** Substrate (base), wedge, wedge in (add), vector (way, method), locus, vantage, nexus, primitive as a noun, harness as a metaphor, surface as in "API surface", bedrock, scaffolding as a metaphor, modality, paradigm, gold-plating (more than the job needs), ratchet as a metaphor (the mechanism's real name, or a limit that only tightens), evacuate for moving code (move out), endgame (the last phase), north star, flywheel. These read as technical but usually have a plainer concrete word. Pick the concrete word.

### Plain speech

27. **Say what it does, not how it feels.** "the database stays close at hand", "SQL you can read", "types that follow your schema" name a feeling. The fix names the mechanism or a number: "`.toSQL()` returns the exact string sent to the database", "a column rename fails the build". Ask what the sentence tells the reader to do or know, then write that. If you can't restate it as a concrete instruction, fact, or number, cut it. One more check: if the sentence could appear unchanged in another project's docs, it says nothing about this one. Cut it.
28. **Shorten or split dense sentences.** If the reader has to backtrack to parse a sentence, break it in two or drop clauses. One idea per sentence.
29. **Active voice.** Prefer it. Catch "is/are/was/were + past participle" and name the actor: "queries are validated" becomes "the compiler validates queries", "the file is parsed by the loader" becomes "the loader parses the file". Passive is fine only when the actor is unknown or genuinely doesn't matter.
30. **Cut adverbs, or use a stronger verb.** "runs quickly" becomes "is fast" or the number, and "significantly improves" becomes the measured delta. An adverb propping up a weak verb means the verb is wrong.
31. **Prefer the plain word.** "utilize" and "leverage" become "use", "facilitate" becomes "help", "numerous" becomes "many", "in the event that" becomes "if". The fancier synonym is rarely clearer.
32. **Mannered prose.** Metaphor or flourish where a literal phrase exists: aphorisms ("wire it or delete it"), rhetorical fragments for effect, personified code ("the plan holds it"), figurative verbs ("rides along", "stands on"), stock framing phrases. "A dial worth turning" becomes "a parameter worth varying". Say what you mean. Rule 26 covers the metaphor nouns.
33. **Over-compression.** Dropped articles, verbless fragments, symbol-speak, and abbreviations that make the reader decode instead of read. "Parser rejects bad date → exit 2, no write" becomes "The parser rejects a bad date, exits with code 2, and writes nothing." Write whole sentences with their articles and verbs, and spell out arrows and abbreviations.

### 中文

下面的规则用于中文文本。上面针对英文语法的规则（比如 -ing 短语、弯引号）只在正文确实是英文时才用。

34. **机制名代替后果。** 读者要查资料才懂的词，换成它造成的后果或具体做法。“写入不是原子的”改成“保存到一半程序挂了，原来的内容也可能坏掉”。命令、文件名、字段名照抄。读者是工程师、这个词又是日常用语时，可以保留。
35. **黑话和互联网腔。** 兜底、链路、收敛、落盘、拉通、赋能、沉淀、打通、心智，换成具体动作或结果。同类的新词按同样方式处理，这份名单没有列全。
36. **翻译腔和名词堆叠。** “进行修改”写成“改”，“对其进行处理”写成具体动作。“基于……的……机制”拆成一句主谓完整的话。
37. **共同条件放在前面。** 几条内容共用的前提写进引导句，比如“同一账户 24 小时内重试时：”。
38. **独立信息分开。** 彼此独立的事实各占一个列表项，限制和应对办法分开写。原本就是一句话的内容不要强行拆开。
39. **不重复解释。** 前文已经说过的意思，不要换个说法再说一遍。比如已经写了“计划”“尚未验证”，就不再补一句“这是计划时间，尚不能确认”。
40. **不写交代性声明。** 删掉读者没问的“以上仅为分析”“未修改代码”“希望对你有帮助”。结论没经过实际运行时，在结论那句里写清楚，这是事实，不算声明。

**照抄的内容。** 命令、代码块、文件路径、报错原文和引用的原话一律照抄，下面第 41 条不适用于这些内容。

41. **生词第一次出现：能换就换，换不掉再解释。** 叙述里的英文词、代号、自造词（含自造四字词），能换成日常说法的直接换掉，不保留原词。读者之后要亲手用到、或要拿去搜索排查的原词（比如要去改的配置项名、要运行的命令），才保留原词，照第 34 条原样写出，并在第一次出现时补一句是什么。
    反例「主库挂了会走 fallback，缓存靠 warmup 提前拉满，过期时间由 cache_ttl 控制」→ 改后「主库挂掉时会改用备用数据源，缓存会提前装满。要改缓存的过期时间，改 `cache_ttl`（缓存过期时间的设置）」。
    不用改：读者都是工程师、词又是日常用语时，可以保留。
42. **一句话只说一层转折。** 不用“不是 A，而是 B”“既不是……也尚未……”把判断垫在排除后面；先说判断，再说依据。
    反例「登录页打不开不是服务器挂了，而是浏览器在用旧缓存」→ 改后「登录页打不开，是因为浏览器在用旧缓存；服务器没有挂」。
    不用改：对方确实猜错时，直接说“不是 A，是 B”就是正确的纠正，保留。
