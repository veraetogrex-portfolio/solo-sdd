## Live Scenario

The lead session runs every prepared prompt as an `Agent` subagent without `model` (the main model, the one measured), under the description the prompt names (`Ablation: <skill> <variant> <task> <run>`), then `grade <run> --from <its subagents folder>`.

1. `python3 tests/test_skill_commands.py` → the audit table test passes: every skill of `targets.json` has a section in `docs/skills-audit.md`, every step its row with one of the three marks, every `hook: yes` row in `Gates a hook could hold`.
2. `python3 tests/stands/skill-ablation.py prepare debug-profile --budget 6` → 6 prompts (2 tasks by 3 variants), exit 0; the lead runs them as 6 subagents; `python3 tests/stands/skill-ablation.py grade <run> --from <subagents folder>` → a table of 6 rows with the outcome, the path and the tokens, no `not run` row. The table goes into `docs/skills-audit.md` under `### Run <date> <model>`.
3. The same for `evidence-research`.
4. `python3 tests/stands/skill-ablation.py prepare evidence-research --budget 4` → 4 prompts and `budget reached: 2 of 6 calls not made`, exit 3; no subagent runs it.
5. `python3 tests/stands/skill-ablation/stand.py` → steps 2-4 end to end with each task's `reference.jsonl` as the transcript of every prompt (every row `pass`), and `skill-ablation stand: <n> of <n> checks passed`.

## Needs

- 12 subagent runs in the Claude Code session on the subscription (6 per skill), allowed by the owner on 2026-11-20 only as Claude Code subagents; no `claude -p`, no paid API calls.

## Fallback

A subagent that fails or is stopped leaves a `not run` row, named in `Not Verified`. A session that cannot launch the `Ablation:` subagents (an orchestrator under the dispatcher, where the hook allows only role-tagged subagents) runs steps 1, 4 and 5, and steps 2-3 wait in `docs/waiting.md` for a main session.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: order → after `eval-process-signals`: the audit table test reads every skill step, so it lands after the plan's skill edits; `tests/test_skill_commands.py` and `tests/affected.json` are shared with them.
- analyze: the runner's budget → 12 subagent runs (6 per skill); the owner allowed runs only as Claude Code subagents (2026-11-20), so the runner prepares prompts and grades answers, and `claude -p` is not used.
- analyze (outside run): 22 findings, kept 18, dropped 4; CRITICAL 1, HIGH 7, all fixed in the artifacts.
- analyze: a test row reading a format a later task defines (J1) → the two-lost-runs row moved to task 1.7 with the release rule and the run format.
- analyze: the hook value of a text gate untested (J2) → a scenario and a test row for an empty hook column.
- analyze: the ban in the prompts untested (J3) and invariants without a property test (J5) → rows in task 1.2 and the Hypothesis test of task 1.3.
- analyze: hostile input of `grade` (J4) → requirements Grade outcomes (`unreadable`) and Runner input refused, task 1.5; the check gets the answer as a file path and never runs it.
- analyze: no measure for "did not beat" (J6) → `compare:` counts passes over the tasks whose every prepared row is `pass` or `fail`; a lost run is full passes no more than none passes; a run of `of 0` counts neither way; the last two runs with a compared task decide; rejected: counting leaked or not run rows as losses.
- analyze: where `prepare` writes (J7) → a new folder each call (`--out` must be empty or absent), its path printed; rejected: one fixed folder per skill.
- analyze: shared context of the subagents (J8) → the three variants share the lead's context, every prompt carries the ban, a leak is a `Skill` call or any tool input naming `skills/<skill>/` (the repository and every laid-out copy).
- analyze: the full variant reaches its subagent (J18) → inline in the prompt like the cut variant, with the same ban, so the three arms differ only in the text.
- analyze: the main model in the Live Scenario (J11) → the subagents run without `model` on the main model because the main model is what is measured; the owner allowed these runs as Claude Code subagents on 2026-11-20, so no cheap-model rule applies.
- analyze: the model of a run (J15) → the `model` field of the transcripts' assistant lines, printed by `grade`.
- analyze: the answer of a subagent → taken from its transcript (the last `SubagentHandback` message, else the last assistant text), so the lead copies or points to transcripts and writes no answer files; tokens are the last assistant turn's input, cache and output tokens, the number the `Agent` tool reports as `subagent_tokens`.
- analyze: required commands → regular expressions over `<tool> <input JSON>` of every tool call, so a read through the Read tool and through `cat` both count.
- analyze (repeat run, passes 1 2 7 7a): 15 findings, CRITICAL 2, HIGH 3, MEDIUM 9, LOW 1; all fixed in the artifacts: `grade` reads the run folder and the `--from` folder only, `prepare` copies each task's check and required calls; one outcome order (`unreadable`, `not run`, `leaked`, `pass`, `fail`); prompts go task by task and `compare:` takes only tasks with every variant prepared; a folder with no task is refused (the property test generates 1-4 tasks); a read of `tests/stands/skill-ablation/` is a leak; the audit test reads only the step table and skips fenced code; the `candidate to cut` line stays until the owner removes it; `cut - of <n>` without a cut variant; a reference transcript `reference.jsonl` per task instead of `reference.md`, so the stand needs no generated tool calls.
