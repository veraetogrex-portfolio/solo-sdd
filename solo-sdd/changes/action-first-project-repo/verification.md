## Live Scenario

`python3 tests/stands/action-first.py prepare` makes a fresh `/tmp/action-first.*` folder with a `.action-first-stand` marker and prints `catalog:`, `empty:`, `analysis:`, `empty-prompt:`, `steps-prompt:`, `home:`, `session:` and `repo:` with their paths. It refuses to run, before writing anything, when the real `~/Code` has a folder named `zz-greeter-bot` or `zz-greeter-bot-old`.

- `catalog/`: a git project with one commit, a short `AGENTS.md` and `catalog.db`, a SQLite file with one table of 30 invented catalog items (name, price, users, last update); no other file holds the rows. `empty/`: the same with a table of no rows.
- `analysis.md`, `empty-prompt.md`: the branch `global/AGENTS.md` whole, then "analyse the catalog in catalog.db and tell me what to work on" (for `catalog` and `empty`); `steps-prompt.md`: the same rules, then "count the rows of catalog.db and list the five oldest items".
- `home/Code/x/zz-greeter-bot/` (one level down, as the owner's projects lie): a git project with one commit, an `AGENTS.md` that asks for commit messages starting with `greeter:`, and `bot.py` whose greeting has a typo (`Helo`); `home/Code/zz-greeter-bot-old/`: a git project with the same `bot.py`; `session/`: an empty folder.
- `repo.md`: the branch `global/AGENTS.md` whole, the line "for this task `~` is `<home>` and your current folder is `<session>`", then "fix the greeting typo in the zz-greeter-bot".

`clean <folder>` removes only a folder that holds the marker `prepare` wrote and refuses any other with exit 1, removing nothing.

Every answer comes from a Claude Code subagent of the lead session (`general-purpose`, it writes files) on `agents.test-model` (`haiku`), never `claude -p`; the lead saves the answer text to the scratchpad. The graded runs read the laid-out text (Needs); a run on the branch text inside the prompt is only a pre-check and proves nothing in Result.

Graders, all lines after `*`, backquotes, heading and quote markers are stripped and whitespace collapsed; a list item is detected on the raw line (`-`, `*` or `<n>.` at its start) before that; empty lines are not counted; leading `Goal:` and `Check:` lines are skipped unless the grade names them, and every line window counts from the line after them:

- `--grade-analysis <answer> <project>`: `actions first: yes|no` (within the first 5 non-empty lines stand one to three list items in a row, or a line starting with `No action follows:`), `effect named: yes|no` (every such item holds ` — ` and text after it), `file linked: yes|no` (one of the first 5 non-empty lines names a `.md` or `.csv` path that, resolved with links, lies inside `<project>`, exists and holds the action lines), `only analysis file: yes|no` (`git status --porcelain` of `<project>` lists only that file, or prints nothing and the only new commit adds only that file). A path outside `<project>`, absolute or through a link gives `file linked: no`.
- `--grade-goal <answer>`: `goal first: yes|no` (the first two non-empty lines start with `Goal:` and `Check:`, the next one is an action or `No action follows:`).
- `--grade-repo <home> <session> <reply>`: `edit in project: yes|no` (`bot.py` of `x/zz-greeter-bot` greets with `Hello`), `other untouched: yes|no` (`zz-greeter-bot-old` has one commit and a clean status), `others named: yes|no` (the reply names `zz-greeter-bot-old`), `no copy in session: yes|no` (no file under `<session>` named `bot.py` or holding its text), `committed: yes|no` (a second commit, clean status), `project rules: yes|no` (its message starts with `greeter:`), `real Code untouched: yes|no` (the real `~/Code` has no `zz-greeter-bot` folder).

An empty answer, a truncated one (it ends inside an open code fence) or a non-UTF-8 one, a missing file or a wrong argument exits 1; unclosed inline `*` or backquotes are graded, not refused. The graders read `<session>` and the fixture repositories without following links, read at most 1 MB per file and 1,000 entries, and run git with `-c core.fsmonitor= -c core.hooksPath=/dev/null`.

1. `python3 sync.py status` after the push of the branch commit (Needs) → no `outdated`, `missing` or `drift` line for the three copies of `global/AGENTS.md`.
2. A subagent gets `analysis.md` with `catalog` as its folder → `--grade-analysis` prints four `yes` lines; the answer is kept as `tests/stands/action-first/live-analysis.md`. A subagent gets `empty-prompt.md` with `empty` → `actions first: yes` through a `No action follows:` line.
3. A subagent gets `steps-prompt.md` with `catalog` → `--grade-goal` prints `goal first: yes`.
4. A subagent gets `repo.md` with `session` as its folder → `--grade-repo` prints seven `yes` lines.
5. References and hostile input: `--grade-analysis tests/stands/action-first/live-analysis.md` on a prepared catalog with its file → `actions first: yes`, `effect named: yes`; `expected-analysis.md` → four `yes`; `wrong-analysis.md` (a table of rows first, no file) → `actions first: no`, `file linked: no`; references with 0 and 4 list items, a heading first, a sub-bullet → `actions first: no`, `no`, `yes`, `yes`; `hostile-path.md` naming `../`, an absolute path and a link out of the project → `file linked: no`; an empty, a truncated and a non-UTF-8 answer → exit 1; a 100 KB run of unclosed `*` and backquotes → graded within 1 s; a link in `session/` pointing out of it, a 5 MB file there and a fixture repository with `core.fsmonitor` set → the grade lines without following the link, reading past 1 MB or running the monitor; `--grade-repo` right after `prepare` → `edit in project: no`, `committed: no`; a scripted `cp -R` of the project into `session/` → `no copy in session: no`; `clean` on `tests/` → exit 1, nothing removed.

## Needs

- Steps 2-4 run from the main session: from a subagent (under `spec-dispatch` the orchestrator is one) the hook refuses an untagged `general-purpose` subagent, as `goal-first` met on 2026-11-22.
- The owner's decision to lay out the branch commit (`sync.py push` from the branch, the main branch's layout restored by `sync.py push` from main at the end), as for `goal-first` on 2026-11-22: the graded runs then read the rules the agents get. Given by the owner on 2026-11-23 (translated from Russian): "Yes, lay it out".

## Fallback

Without that decision, or under the dispatcher, steps 1-4 run from the main session after the merged change's `sync.py push` (the delivery's layout step, which agents run without asking); until then Result holds only the in-prompt pre-check, Not Verified names steps 1-4, and the first table of `docs/waiting.md` gets a line for them. Step 5 needs no layout.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (spec-analyze judge 15): an analysis writes its one data file; sections 3 and 6 name it as the exception to "files do not change" and "change nothing".
- plan (judge 16, analyze repeat 1, 4): for a step-only analysis the `Goal:` and `Check:` lines come first, then the actions; the actions take the place of the 2-4 plain lines of section 1, and the 5-line windows count non-empty lines after the goal lines.
- plan (judge 2): an experiment copy lives only in a temporary worktree of section 9; the carry-back itself is not run by the stand (the fixture fix needs no experiment), so Not Verified will name it.
- plan (judge 12, 13): the fixture projects are named `zz-greeter-bot` so the request matches no real project; the lookup on the real `~/Code` stays unproven by design.
- plan (judge 18, analyze repeat 2): the file goes into the project folder, with no project into the session folder; it is committed only when the project's rules or section 13 commit work, and the grade accepts either (rejected: forbidding the commit, against section 13).
- plan (analyze repeat 3): a `## Lessons` edit of section 15 is the second file an analysis may change.
- plan (analyze repeat 5, 8): the lookup reads git repositories at any depth under the projects folder the owner's rules name, by default `~/Code`; a name equal to the request wins over one that starts with it.
- plan (analyze repeat 6): a session that cannot write in the project names the access it needs (for example a restart in the project folder or Codex `--add-dir`) and copies nothing; no stand step runs a sandboxed session, so Not Verified will name it.
- plan (analyze repeat 11): the branches "else the latest commit" and "no match" of the lookup are not run by the stand; Not Verified will name them.
- plan (judge 19): no scenario for a failed file write: a file not written is a delivery not done under section 3 already.
