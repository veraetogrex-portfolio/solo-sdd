## Live Scenario

The stand `tests/stands/analyze-outside/` holds a fixture project with one change, `add-export`, built with four planted holes. `tests/stands/analyze-outside/planted.json` gives each hole its passes and an identifying token: a requirement without a task (pass 1), a command that reads a user-given archive without a hostile input task (pass 2), two requirements true one by one that cannot hold together (pass 7a), a term that drifts between the proposal and the delta (pass 6, or 5, which names term drift too). A finding matches a hole when its Pass column names one of the hole's passes and its Where or Finding column holds the token; a row whose `Mark` starts with `drop` is not kept. `tests/stands/analyze-outside.py grade <findings> <transcript>` prints `<label>: found <x> of 4, unmatched keep <y>, tokens <t>` (the label is the findings file name without its extension, `tokens` the sum of `totalTokens` of the transcript's agent results) and the agents the transcript launched; the lead rereads every unmatched kept finding and records in `Result` whether the artifacts confirm it.

Every variant runs as a Claude Code subagent of the lead session, never as `claude -p` (the owner's decision of 2026-11-20). `python3 tests/stands/analyze-outside.py prepare <variant>` copies the fixture into a temporary git project and writes the subagent prompt: run `spec-next` on `add-export` there, stop after step 4a and print the step 4a report. `same-session` puts into the prompt the `spec-analyze` and `spec-next` texts of the base commit `8ce66d8` (read by `git show`, apart from the working folder), the other two the laid-out ones. The lead launches each prompt as an `Agent` subagent without `model` and saves its findings and transcript path. Under the dispatcher the lead is itself a subagent, and the hook refuses an untagged subagent from a subagent: the orchestrator then plays the variant lead of `analyze` and `attack` itself in the copy `prepare` made, launching only the `Analyze:`, `Attack:` and `Judge:` agents of the laid-out text, and its own transcript is the one `grade` reads; `same-session` runs only from a main session. `python3 tests/stands/analyze-outside.py clean <copy>` removes a copy.

1. `python3 sync.py push`, then `python3 sync.py status` → the laid-out `spec-analyze`, `spec-plan`, `spec-next` and `~/.claude/CLAUDE.md` match the repository, no unexpected `drift`.
2. `python3 -m solo_sdd config get process.analyze-attackers` in the fixture project → `3` with the source `default`.
3. Variant `same-session` → the subagent's transcript has no `Analyze:`, `Attack:` or `Judge:` agent; `grade` prints `same-session: found <x> of 4, unmatched keep <y>, tokens <t>`.
4. Variant `analyze` with `process.analyze-attackers: 0` in the copy's `solo-sdd/config` → the transcript has one `Analyze: add-export` agent and one `Analyze: add-export 1 2 7 7a` repeat, no pass run by the variant subagent itself; the report line starts with `Analyze: <n> findings, kept <n>, dropped 0`; `grade` prints the `analyze:` line.
5. Variant `attack` with the default → the transcript has `Attack: add-export 1 2 3 3a`, `Attack: add-export 4 4a` and `Attack: add-export 5 6 7 7a 7b` on `haiku`, one `Judge: add-export`, no agent launched by an attacker or the judge, and `git status` of the copy shows no edit before the variant subagent's own edits; the report line matches `Analyze: <n> findings, kept <k>, dropped <d>; CRITICAL <c> · HIGH <h>, fixed <f>`; `grade` prints the `attack:` line.
6. The three `grade` lines are the table of the three runs, and it goes into `Result` as is. Acceptance is the transcript structure and report lines of steps 3-5; an `attack` run that finds fewer planted holes than `same-session` is a `Not Verified` line and a new change, not a block.
7. `python3 tests/stands/analyze-outside.py grade tests/stands/analyze-outside/expected-all.md tests/stands/analyze-outside/reference.jsonl` → `expected-all: found 4 of 4, unmatched keep 0, tokens 54000`, every hole `found` and the five agents of the `attack` variant; on an empty findings file `found 0 of 4`.

## Needs

- Three variant subagents in the Claude Code session on the subscription, with their own `Analyze:`, `Attack:` and `Judge:` subagents (8 subagent sessions in all, 3 of them on `haiku`), allowed by the owner on 2026-11-20 only as Claude Code subagents; no `claude -p`, no paid API calls.

## Fallback

Not needed: every run is a subagent of the lead session. A variant subagent that fails or is stopped is named in `Not Verified`, and its row stays empty.

## Result

2026-11-21, worktree of branch `change/analyze-outside`, the orchestrator (a dispatched subagent on Opus) as the variant lead; the variant runs were 7 subagents of this session (3 on `haiku`), no `claude -p`, no paid API call.

- Step 1: `python3 sync.py status` shows `outdated` for exactly the edited deployed files (the `spec-analyze`, `spec-plan`, `spec-next` skills, `work_hooks.py`, `sdd-worktree.py`, `sdd-dispatch-plan.py`, `sdd-pr.py`, the three copies of `global/AGENTS.md`, `ALGORITHM.md`) and no `drift`; `sync.py push` is left to the delivery after merge (Decisions).
- Step 2: in the `attack` copy `config get process.analyze-attackers` printed `source: default` and `3`, `config list` the row `process.analyze-attackers 3 default`; in the `analyze` copy `0` from the file; `config set process.analyze-attackers -1` exit 1 with `process.analyze-attackers takes a whole number from 0, not '-1'`, the file unchanged.
- Step 4, `analyze` (`process.analyze-attackers: 0`): the transcript has `Analyze: add-export` (no `model`) and, after the lead's edits of the copy, `Analyze: add-export 1 2 7 7a`; the lead ran no pass itself, neither agent launched an agent or called Write or Edit. Report line `Analyze: 18 findings, kept 18, dropped 0; CRITICAL 3 · HIGH 5, fixed 8`. The table was saved with its Pass and Where columns verbatim and the Finding text shortened.
- Step 5, `attack` (the default): `Attack: add-export 1 2 3 3a`, `Attack: add-export 4 4a`, `Attack: add-export 5 6 7 7a 7b` on `haiku` in one message, then `Judge: add-export` (no `model`) with their three tables, then `Analyze: add-export 1 2 7 7a` after the lead's edits; no attacker or the judge launched an agent or called Write or Edit, and `git status` of both copies was empty before the lead's edits. The judge merged duplicates naming every attacker (for example J3 from A6, A10, A11 and 1, 6) and dropped 6 with reasons. Report line `Analyze: 19 findings, kept 13, dropped 6; CRITICAL 4 · HIGH 7, fixed 11`.
- Both repeats found holes the lead's own fixes opened (hostile-input limits in a task that no requirement names, the store format assumed and never defined, a failed write without a scenario): the case the repeat exists for.
- Step 6, the `grade` lines on the orchestrator's transcript (it holds both variants, so `tokens` is the sum of all seven agents; per variant from the `agent:` lines, `analyze` 203225, `attack` 501691):

  `analyze: found 4 of 4, unmatched keep 14, tokens 704916`
  `attack: found 3 of 4, unmatched keep 9, tokens 704916` (the term drift `snapshot` missed by all three attackers)
  `same-session`: not run (Not Verified)

  The unmatched kept findings were reread against the fixture: they hold (Full history against `--since`, `--merge` against the 1 MB cap, merged notes' versions, undecided error cases), holes of the fixture beyond the four planted ones.
- Step 7: `python3 tests/stands/analyze-outside.py grade tests/stands/analyze-outside/expected-all.md tests/stands/analyze-outside/reference.jsonl` printed `expected-all: found 4 of 4, unmatched keep 0, tokens 54000`, the four holes `found` and the five agents; on an empty findings file `empty: found 0 of 4, unmatched keep 0, tokens 54000`. `clean` removed both copies and refused a folder `prepare` did not make (exit 1).

## Not Verified

- Step 3, the `same-session` variant: it needs an untagged variant subagent, which the hook refuses from a dispatched orchestrator (a subagent); it runs only from a main session. Its row of the table stays empty, and the comparison with the in-session baseline is open (`docs/waiting.md`).
- `attack` found fewer planted holes than `analyze` (3 against 4: the term drift, pass 5 and 6 of the third group, was missed by its `haiku` attacker). The rule of step 6 compares with `same-session`, which did not run, so no new change was made; one run is no measure of the gain.
- Step 1 `sync.py push`: left to the delivery after merge.

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: a direct `/spec-analyze` call by the user → passes in place — the user asked for the analysis in that session; only `spec-plan` 7a and `spec-next` 4a, where the author checks its own work, go outside.
- analyze: the `same-session` baseline of the stand → the `spec-analyze` and `spec-next` texts of base commit `8ce66d8` read by `git show` — after this change the laid-out text no longer runs in session.
- analyze: overlap with the open change `lesson-merge-by-cause` (section 15 of `global/AGENTS.md`, `tests/test_skill_commands.py`) → it goes into Depends On, which orders it before the whole chain of this plan.
- analyze: Live Scenario steps 3-5 had the lead launch an untagged variant subagent, which the hook refuses when the lead is a dispatched orchestrator (HIGH, pass 7a, a hidden assumption) → under the dispatcher the orchestrator plays the variant lead of `analyze` and `attack` and `same-session` needs a main session — no other way runs the variants without bypassing the hook.
- analyze: task 1.3 widens "the existing tests" of Lead writes code and Orchestrator writes code, and none exists (MEDIUM) → one new test in `tests/test_skill_commands.py` checks the five tags in the three texts.
- analyze: the status field `LIVE` needs one command with a fixed output → step 7 grades the stand's reference findings and transcript.
- analyze: term drift is named by pass 5 ("one term named differently") as well as pass 6, and a hole of two requirements by 7 as well as 7a → `planted.json` gives each hole a list of passes, and the token may stand in Where or Finding — an attacker that finds the hole under the neighbouring pass or names the token only in its finding still found it.
- Live step 1: `sync.py push` is a prod action on the agent folders and the dispatcher delivers after merge → this run checks `sync.py status` only, as `subagent-check-roles` did.
- grade: the tokens of an agent result are read from `toolUseResult.totalTokens` or from the `<usage>` block of the result text (`subagent_tokens:` or `total_tokens:`), the form this Claude Code writes → both forms, `n/a` when neither.
- spec-plan size: the step 7a and report line edits put `skills/spec-plan/SKILL.md` over 16,000 bytes → the Mistakes row on the requirement length goes, since `creation.md` holds the same rule with its key.
- spec-analyze: the outside run fits in `SKILL.md` (15,338 bytes) → no step file, no `targets.json` or `tests/affected.json` entry.
- spec-analyze: n in the report line counts the findings after the judge's merge (k + d), as the scenario's 9 = 4 + 5.
- review round 1, Important F1 (subagent limits that still named only acceptance and search: `ALGORITHM.md` dispatcher paragraph, the Codex sentence and the WORKTREE and foreground lines of `spec-next`, the `codex-orchestration` description) → fixed; the depth check of `spec-dispatch` step 1 stays, since it is about whether an orchestrator can launch any subagent at all.
- review round 1, Important F2 (the dispatched scenario A small change said "launches only the reviewer") → the MODIFIED delta restates it with the outside run's subagents.
- review round 1, Important F3-F5 (`grade` took an escaped `\|` or a pipe in a code span as a column break, took a table without Pass and Where for no findings, printed a partial token sum as whole) → cells split by GFM rules, a row with another cell count and a non-empty file with no findings table are refused, a partial sum prints `(<k> of <n> agents)`.
- review round 1, Important F6 (the `same-session` subagent could call the newer installed skill) → its prompt bans the Skill tool and installed skills.
- review round 1, Important F7 (rows of the text test that the stand proves) → the group split string, the attack model default and the N = 0 row removed; the rows task 1.1 names stay.
- review round 1: the shape-only text tests stay (the repository's form for skill text requirements); Nits fixed: a non-object JSON line is refused, the BASE comment, the reused name `n`; Nits kept: 3 bytes of spec-plan headroom, the repeat of the no-edit rule in What to do with findings (read on its own), the description wording, the repeat subagent's model (the Analyze model rule two lines above covers it). The proposal Impact lost `targets.json` and `tests/affected.json` and gained `skills/codex-orchestration/SKILL.md`; the spec-next delta keeps its shorter wording of the lookup role, since the main wording puts the requirement at 514 of 500 characters.
