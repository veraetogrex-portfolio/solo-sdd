## Live Scenario

From the solo-sdd root:

0. Steps 1-2 as one stand: `python3 tests/stands/stop-background-shell.py` runs the repository hook `global/work_hooks.py` and prints `8 of 8 checks passed`; after `python3 sync.py push`, `python3 tests/stands/stop-background-shell.py --deployed` runs the same checks on the deployed hook `~/.claude/hooks/work_hooks.py`.
1. A scratch repository outside the project: `R="$(mktemp -d)/r"; mkdir -p "$R"; cd "$R"; git init -q; echo 'a{}' > app.css; git add -A; git -c user.email=t@t -c user.name=t commit -qm base; echo 'a{color:red}' > app.css`, and a transcript `t.jsonl` next to it with one `Edit` tool use of `$R/app.css`.
2. Run the deployed hook as Claude Code starts it, `python3 ~/.claude/hooks/work_hooks.py stop` with the Stop input on stdin under a temporary `HOME` (a new `session_id` per run), `background_tasks` as in the Claude Code hooks reference:
   - `[]`: stdout holds `"decision": "block"` and `uncommitted edits`;
   - `[{"id": "b1", "type": "shell", "status": "running", "description": "npm run dev", "command": "npm run dev"}]`: the same block (before the change: empty stdout);
   - `[{"id": "m1", "type": "monitor", "status": "running", "description": "watch log"}]`: the same block (before: empty);
   - the shell entry first, then `{"id": "a1", "type": "subagent", "status": "running", "agent_type": "general-purpose"}`: empty stdout;
   - `[{"id": "t1", "type": "teammate", "status": "running"}]` and `[{"id": "u1", "type": "x", "status": "running"}]`: empty stdout;
   - `[{"id": "x1", "status": "running"}]`: empty stdout;
   - the dispatcher waiting for delivery: one running `shell` entry with command `python3 ~/.local/bin/sdd-pr.py ship …`, a transcript of Bash calls only (no edit, no `bashEditDiff`), a clean repository and a last message in the reply language: empty stdout.
3. Only in a main interactive Claude Code session (a deliberate exception to "the turn does not end while your background command is running" of `spec-next`; under the dispatcher the acceptance agent is a subagent and fires SubagentStop, so this step goes to the Fallback): in a second scratch repository start `python3 -m http.server 8765` as a background Bash command, edit a tracked file there, end the turn: the Stop hook feedback names `uncommitted edits` of that repository; then stop the server by its task id (TaskStop).

## Needs

none

## Fallback

Step 3 needs a main interactive Claude Code session; under the dispatcher or a run without one it goes into `Not Verified` with the commands to repeat, steps 1-2 stay mandatory.

## Result

RESULT_PLACEHOLDER

## Not Verified

NV_PLACEHOLDER

## Decisions Without Owner

- plan: which running tasks keep the gate silent → every type except `shell` and `monitor`, and an entry without `type` → only those two are documented as plain commands and watchers; `workflow`, `teammate`, `cloud session` and `MCP task` are work whose result the session waits for, and an older Claude Code that sends no `type` keeps its behaviour.
- plan: a background `shell` the session does wait for (a test run, `sdd-pr.py ship` of `spec-dispatch` merge) now lets every gate run (uncommitted edits, including files a Bash call changed, unarchived change, open PR, `ui-check`, integrations, reply language) → each fires at most once per reason set while the session waits; the dispatcher's main session normally edits nothing itself, and Live Scenario step 2 proves its waiting shape stays silent.
- analyze: no CRITICAL or HIGH; MEDIUM fixed in the artifacts: the test task now says which rows fail on the current code, a scenario for other task types, the dispatcher row, step 3 limited to a main interactive session.
