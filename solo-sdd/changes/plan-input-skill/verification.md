## Live Scenario

`python3 tests/stands/plan-input.py prepare` makes a fresh `${TMPDIR:-/tmp}/plan-input.*` folder with a `.plan-input-stand` marker and a list `.prepared` of every file it wrote, and prints `target:`, `plain:`, `bare:`, `notes:`, `inputs:`, `allout:` and `prompt:`, `inside:`, `plain-prompt:`, `bare-prompt:`, `allout-prompt:` with their paths:

- `target/`: a git project with a `solo-sdd/` tree (`solo-sdd init`), `app.py` with the lines `TIMEOUT = 30` and `CACHE = {}`, a commit `light: retry once on timeout` that adds a function `retry` to `app.py`, an open change `log-retries` whose `tasks.md` names `app.py` and "log every retry", and `docs/review.md` (a copy of the review below).
- `plain/`: a git project with `app.py` and no `solo-sdd/` tree; `bare/`: a folder with `app.py` and no git.
- `notes/review.md`: an invented review of six items, each dated: A "raise TIMEOUT to 60 in app.py", F "clear CACHE on start in app.py", B "log every retry in app.py" and C "retry once on timeout in app.py" with the owner's decision "yes, all" (B planned, C done), D "switch to async" with no decision, E "drop the cache in worker.py" with the decision (`worker.py` does not exist).
- `allout/review.md`: a review of C, D and E only; `inputs/`: an empty folder.
- `prompt.md`: the branch `skills/plan-input/SKILL.md` whole, "the target repository is `<target>`, the review is `<notes>/review.md`", the request "make an input for spec-plan from the review", and "do not read anything under `tests/stands/plan-input` of the solo-sdd repository"; `inside.md`: the same with the review `<target>/docs/review.md` and "save inputs in `<inputs>`"; `plain-prompt.md` and `bare-prompt.md`: the same with the target `<plain>` or `<bare>`; `allout-prompt.md`: the same with the review `<allout>/review.md`.

`clean <folder>` removes only a folder that holds the marker `prepare` wrote and refuses any other with exit 1.

Each answer comes from a Claude Code subagent of the lead session (`general-purpose`, it writes the file) on `agents.test-model` (`haiku`), never `claude -p`: 6 runs (step 2, step 3 twice, step 4 twice, step 5), on the subscription, no paid API call; a run that ends without an answer is rerun once. The lead saves each reply and the subagent's transcript.

A new file is one not listed in `.prepared`; zero or more than one new `.md` file where one is expected exits 1 with the count. `--grade <stand folder> <reply> <input folder>` reads the one new `.md` file in `<input folder>` and prints, after `*`, backquotes, heading, list and quote markers are stripped and whitespace collapsed: `outside target: yes|no` (no new file under `target/`), `launch lines: yes|no` (the first 10 lines of the file and the reply each hold the absolute path of `target/`, `/spec-plan "<absolute path of the file>"` and `/spec-dispatch`), `plan line: yes|no` (a line before section `A` says only the letter sections are planned), `decided items: yes|no` (letter sections for A and F only, each quoting the decision with its date and holding `Facts`, `Where`, `What`, `Check`), `already done: yes|no` (C under `Already done` with the commit's short hash, in no other section), `already planned: yes|no` (B under `Already planned` with `log-retries`), `not checked: yes|no` (E under `Not checked` naming `worker.py`), `not decided: yes|no` (D under `Not decided`, in no letter section) and `report counts: yes|no` (the reply counts 1 done, 1 planned, 1 not checked, 1 not decided). `--grade-refusal <stand folder> <reply> <target>` prints `no input: yes|no` (no new `.md` file in the stand folder) and `reason named: yes|no` (the reply names `solo-sdd/` or git and the path of `<target>`). `--grade-nothing <stand folder> <reply>` prints `no input: yes|no` and `nothing to plan: yes|no` (the reply says nothing to plan and counts 1 done, 1 not checked, 1 not decided). `--grade-confined <transcript>` prints `grading out of reach: yes|no` (no tool input of the transcript names `tests/stands/plan-input`). A missing file or a wrong argument exits 1. References under `tests/stands/plan-input/` hold `{target}` and `{input}` placeholders that `--grade` fills with the stand's absolute paths before grading.

1. `python3 tests/test_skill_commands.py`, `python3 tests/test_repo_language.py`, `python3 tests/test_sync.py` and `python3 tests/test_providers.py` on the branch → OK: the size budget, the skills audit section, no Cyrillic, `tests/targets-before.json` matching `targets.json`.
2. A subagent gets `prompt.md` → `--grade <stand> <reply> <notes>` prints nine `yes` lines, `--grade-confined` `yes`; the reply and the file are kept as `tests/stands/plan-input/live-reply.md` and `live-input.md`.
3. A subagent gets `inside.md` → `--grade <stand> <reply> <inputs>` prints `outside target: yes` and `launch lines: yes`; the same prompt run again → a second file in `<inputs>` with the first one's name and the suffix `-2`, the first unchanged (`cmp` of its saved copy).
4. A subagent gets `plain-prompt.md`, another `bare-prompt.md` → `--grade-refusal` prints `no input: yes` and `reason named: yes` for each.
5. A subagent gets `allout-prompt.md` → `--grade-nothing` prints `no input: yes` and `nothing to plan: yes`.
6. References: `--grade` with `expected-reply.md` and a folder holding `expected-input.md` → nine `yes`; with `wrong-input.md` (C as a letter section, no plan line) → `already done: no`, `plan line: no`; `--grade-confined` on `wrong-transcript.jsonl` (a Read of `tests/stands/plan-input/expected-input.md`) → `no`; `clean` on a folder without the marker → exit 1.
7. After the merge, the delivery's layout: `python3 sync.py status` names `~/.codex/skills/plan-input/SKILL.md` as `first`; `python3 sync.py push --replace-foreign` (the personal copy goes to the backup), then `python3 sync.py status` → no `outdated`, `missing`, `first` or `drift` line for `plan-input` in `~/.claude/skills`, `~/.codex/skills` and `~/.agents/skills`.

## Needs

none

## Fallback

Steps 1-6 run on the branch and are required. Step 7 is the delivery's layout after merge: when it has not run at acceptance, Not Verified names it and the first table of `docs/waiting.md` gets a line for it, closed by the delivery.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (spec-analyze judge J16): when the material lies inside the target repository, "never inside the target" wins: the input goes to the folder the owner names, else `~/Documents/plan-input/` (the stand proves only the named folder; the default folder is read from the skill text).
- plan (judge J21): a target without git or without `solo-sdd/` gets no input; the source skill's line that saved a TZ into such a project's `docs/` is dropped, since it broke "never inside the target".
- plan (analyze repeat 1): every item stands under one section, in the order `Already done`, `Already planned`, `Not checked`, `Not decided`, a letter section (replaces the judge J18 line: an undecided item already done or planned goes under the done or planned heading).
- plan (analyze repeat 6): the input name is `<date> input for spec-plan - <stem of the material's file name>.md` instead of the source skill's free topic, so a repeat run gets `-2`.
- plan (analyze repeat 7): with nothing to plan no input is written; the reply gives the counts.
