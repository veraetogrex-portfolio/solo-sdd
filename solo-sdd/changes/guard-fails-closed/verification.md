## Live Scenario

The base is commit e262b7e (main when the change was planned). Steps 1 to 3 run as one stand: `python3 tests/stands/guard-fails-closed.py`; it makes and removes its temporary folder and prints one line per step and a summary.

1. In a temporary `HOME`, `python3 -m solo_sdd install --hooks` from the base commit and from the change's worktree, then read the `guard` entry of `$HOME/.claude/settings.json` → base: no `onFailure`; branch: `"onFailure": "block"`, `"timeout": 10`, and `G` holds the interpreter check.
2. In the same `HOME`, give `work_hooks.py` a syntax error and run the entry's command through `sh -c` with a PreToolUse JSON for a `Read` of `README.md` on stdin → a non-zero exit other than 2.
3. From the change's worktree, a driver script in a temporary folder imports `global/work_hooks.py` as a module, replaces `guard_secrets_bash` with a function that raises, sets `sys.argv` to `guard` and feeds a PreToolUse JSON for Bash `cat .env.local` to `main()` → `deny` naming `guard_secrets_bash`; the same with `guard_models_agent` raising on an `Agent` call → no answer; the installed hook given `[1]` on stdin → `deny` naming `guard input`. The base commit gives no answer in all three.
4. On the owner's machine after `sync.py push` and `solo-sdd install --hooks` of the merged change: save a copy of `~/.claude/hooks/work_hooks.py`, append a line `)(` at the end of the file (a syntax error the whole file fails to compile on), and in one new Claude Code session ask it once to read `README.md` (one prompt on the owner's subscription, no paid API call) → the Read is refused by the hook; restore the copy (`sync.py status` shows no drift) → the same Read passes.

## Needs

- Step 4: the owner's yes in the chat to break the installed guard for one Read in one session, restored right after.

## Fallback

Without that yes, step 4 is replaced by steps 1 to 3; Not Verified names step 4 with a line in the first table of `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (spec-analyze judge J1, J2): the project rule "Hooks are fail-open" is narrowed, not dropped: only the three secret checks and a crash or timeout of the whole `guard` refuse, by the owner's words in Source; the merge, model, worktree, archive, handback and question checks keep failing open. A crash before the checks run also refuses a `SubagentHandback`; the requirement Status check on handback covers an error inside its own check, which still passes.
- analyze: J5 (a refusal on timeout is checked by no scenario) kept by the judge, not fixed → a timeout and a crash reach Claude Code as the same hook failure under `onFailure: "block"`; the crash rows prove it, and a row that waits 10 seconds per run would only slow the suite.
- analyze (repeat): the interpreter check in `G` starts `/usr/bin/python3` once more on every call of every `work_hooks.py` entry and the status line, not only `guard` (the cost is not measured), so that the macOS stub without Command Line Tools passes instead of refusing every call.
- analyze (repeat): a timeout of the whole `guard` refuses even when the slow part is a check meant to fail open (worktree, merge, archive, handback): the hook cannot tell which check was running when Claude Code stopped it.
- analyze (spec-next, judge J1): the Guard entry fails closed requirement was 514 characters, over 500 → the sentence on the other entries keeping no `onFailure` moved out of the requirement; the scenario A fresh home still asserts it.
- analyze (spec-next, judge J2): "a crash before the checks run" was undecided against `main()`, which swallows every exception → the cli requirement now means a hook process that cannot start or times out; input `guard` cannot read (stdin not a JSON object, a `tool_input` not an object, a non-string `cwd`, `command`, `file_path` or `notebook_path`) denies, by the new requirement Unreadable guard input refused; the rejected option was to let such input pass as before, since Claude Code never sends it and a pass is the gap the owner closed.
- analyze (spec-next, judge J3): no task tested hostile command text through the new deny path → task 1.2 and the scenario Hostile command text: unbalanced quotes, an unterminated heredoc, nested `$(` and backquotes and a 100,000-character run give no answer, no `errors.log` line and return within 5 seconds.
- analyze (spec-next, judge J4): that Claude Code refuses a non-0/2 exit and a timeout under `onFailure: "block"` is shown only by step 4; the earlier record in the working-copy file `docs/process-safety-verification.md` (2026-10-14) says a hook launch error and its timeout block, on an older Claude Code than today's.
- analyze (spec-next, judge J12): Codex runs the same `cmd_guard`, so the in-process deny of the secret checks and of unreadable input applies to Codex too; Codex's own failure field stays out of scope.
- analyze (spec-next repeat, A1): `guard_secrets_bash` is quadratic on long runs of `$(` or of raw backslashes (measured here: 5,000 `$(` 0.7 s, 10,000 2.9 s, 50,000 about 75 s) → the scenario Hostile command text names the runs that stay fast; a slower run is refused after the 10-second timeout under `onFailure: "block"`, the fail-closed side the owner chose; bounding that check's time is a separate change, not done here.
- analyze (spec-next repeat, A2): falsy values of the wrong type (`0`, `[]`, `false`) raised nothing and passed → `guard_input` and `text_field` check the types explicitly; an absent or null field keeps passing, and the input of tools no secret check reads (Agent, AskUserQuestion, SubagentHandback) keeps failing open, so the existing Question window row with a string `tool_input` stays as it is.
- analyze (spec-next repeat, A5): the rewording of `AGENTS.md`, `docs/hooks.md`, the docstring and the `DENY` comment gets no requirement of its own → it documents the three requirements, and task 1.6 asserts it.
- review round 1, Important 1 (a Read `file_path` that is not a string passed) → fixed: `cmd_guard` reads it with `text_field` under `guard_env_read`, and the scenario A field of the wrong type and its test row name it.
- review round 1, Nit 1 (the interpreter check runs for every `work_hooks.py` entry and the status line) → kept as task 1.5 asks: one `G` for every entry; a non-guard entry with a broken interpreter now exits 0 silently, and `doctor` still checks `/usr/bin/python3`.
- review round 1, Nit 2 (a test that checks the words of the rules) → kept: task 1.6 asks for it, and the `tests/affected.json` rows for `AGENTS.md` and `docs/hooks.md` route edits of those files to it.
- review round 1, Nit 3 (the fresh-home row asserts the probe text) → kept: Live Scenario step 1 names that `G` holds the interpreter check, and the row is its unit form.
