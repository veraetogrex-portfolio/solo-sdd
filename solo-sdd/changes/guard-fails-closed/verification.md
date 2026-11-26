## Live Scenario

The base is commit e262b7e (main when the change was planned).

1. In a temporary `HOME`, `python3 -m solo_sdd install --hooks` from the base commit and from the change's worktree, then read the `guard` entry of `$HOME/.claude/settings.json` → base: no `onFailure`; branch: `"onFailure": "block"`, `"timeout": 10`, and `G` holds the interpreter check.
2. In the same `HOME`, give `work_hooks.py` a syntax error and run the entry's command through `sh -c` with a PreToolUse JSON for a `Read` of `README.md` on stdin → a non-zero exit other than 2.
3. From the change's worktree, a driver script in a temporary folder imports `global/work_hooks.py` as a module, replaces `guard_secrets_bash` with a function that raises, sets `sys.argv` to `guard` and feeds a PreToolUse JSON for Bash `cat .env.local` to `main()` → `deny` naming `guard_secrets_bash`; the same with `guard_models_agent` raising on an `Agent` call → no answer. The base commit gives no answer in both.
4. On the owner's machine after `sync.py push` and `solo-sdd install --hooks` of the merged change: save a copy of `~/.claude/hooks/work_hooks.py`, put a syntax error into its first line, and in a new Claude Code session ask it to read `README.md` → the Read is refused by the hook; restore the copy (`sync.py status` shows no drift) → the same Read passes.

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
- analyze (repeat): the interpreter check in `G` starts `/usr/bin/python3` once more per guarded call (tens of milliseconds) so that the macOS stub without Command Line Tools passes instead of refusing every call.
- analyze (repeat): a timeout of the whole `guard` refuses even when the slow part is a check meant to fail open (worktree, merge, archive, handback): the hook cannot tell which check was running when Claude Code stopped it.
