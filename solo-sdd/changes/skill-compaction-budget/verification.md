## Live Scenario

1. `python3 tests/test_skill_commands.py` → passes; `wc -c skills/*/SKILL.md` → no file above 16,000 bytes.
2. `python3 tests/stands/skill-compaction-budget.py` checks a copy of the base commit `2cf3a49` (pinned by hash, read apart from the working folder) before the split → prints `over budget: skills/spec-dispatch/SKILL.md 35699 bytes` (and the lines of `spec-next` 20525 and `spec-plan` 21332) and that the check fails; on the change branch → prints `ok: 20 skills within 16000 bytes, step files named and present`; the stand exits 0 only when both hold.
3. The stand deploys the change into a temporary home (`sync.py push` with `HOME` set to a temporary folder) → every step file of `spec-dispatch`, `spec-next` and `spec-plan` lies next to its deployed `SKILL.md` in each agent root with the same text; prints `ok: step files deployed`.
4. Rule kept: the stand joins each split skill's `SKILL.md` with its step files and compares the set of non-empty lines of the base `SKILL.md` with it → every base line is present word for word (whitespace collapsed); prints `ok: no rule lost`.
5. After compaction, in a real session: `claude -p --model haiku` in a temporary clone invokes `/spec-dispatch` with the instruction to stop before step 0, then `/compact` in the same session (`--resume <id>`), then asks to quote the line of step 7 and the name of the file it says to read → the answer quotes step 7 and names its step file.

## Needs

- Step 5: three paid Claude Code calls on the cheapest model (haiku), about USD 0.05 in all; the owner's approval.

## Fallback

- Step 5 without approval, or when `claude -p` does not accept `/compact` in a resumed session: steps 1-4 prove that every `SKILL.md` fits the re-attached 5,000 tokens at 3.2 bytes per token and that every moved rule is in a deployed step file; step 5 goes into `Not Verified` and `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- plan: the budget is 16,000 bytes, not the 20,000 of Superpowers → 5,000 tokens at 3.2 bytes per token — the skills are dense with paths and commands; at 4 bytes per token `spec-next` (19,791 bytes) would sit at the edge with no margin.
- plan: step files lie next to `SKILL.md` (`skills/<name>/<step>.md`), not in `references/` → one folder level, the same relative name in every agent root.
- analyze: a step whose whole body is one line → the line moves whole into the step file and `SKILL.md` gets a new short line naming the file; every base line stays unchanged in the joined text, which is what Live Scenario step 4 compares.
- analyze: moved text left the Line length check, which reads only `SKILL.md` → Line length is MODIFIED to cover `skills/*/*.md`.
- analyze: the sizes of 16.11.2026 grew before the start (`spec-dispatch` 35,699 bytes at base `2cf3a49`) → Live Scenario step 2 names the base hash and its sizes; the split still moves whole lines.
- analyze: what "named" means was open → a step file is named by a `SKILL.md` line that holds it in backquotes followed by `each time` (the read instruction); other backquoted `.md` names (`tasks.md`, `AGENTS.md`) are not step files; the joined text replaces that line with the file's text, which gives back the base text word for word.
- analyze: no property test → the budget and the step files are checks of fixed repository files with boundary rows (16,000 and 16,001 bytes), not functions of generated input.
