# Proposal

## Why

The readiness gate of the Stop hook goes silent while any background task runs, not only a background agent. Reproduction on 2026-11-21: a repository with an uncommitted edit of the session, the real entry point `global/work_hooks.py stop` with `background_tasks` in the documented form. With no task it returns `decision: block` with the uncommitted edits reason; with one running `{"type": "shell", "command": "npm run dev"}` entry, or one running `monitor` entry, it prints nothing, exactly as with a running `subagent`.

Cause: `global/work_hooks.py:2747` (`cmd_stop`) returns on any entry with `status == "running"` and never reads `type`. The requirement `Stop waits for background agents` was written for the dispatcher waiting for its orchestrators, but its text covers every task. Claude Code documents `type` on each entry (`shell`, `subagent`, `monitor`, `workflow`, `teammate`, `cloud session`, `MCP task`; hooks reference), and 2.1.329 (2026-11-19) moved Monitor scripts from `shell` to `monitor`. `global/AGENTS.md` section on processes tells agents to run servers as managed background tasks, so a dev server or `tail -f` left running for a live check, the usual state of a web project at the end of a turn, switches off every gate: uncommitted edits, unarchived change, open PR, `ui-check` and reply language.

## What Changes

- A running `shell` or `monitor` entry alone no longer silences the Stop readiness gate; the gates run as if no task ran.
- A running `subagent` entry, or any running entry of another or missing `type`, still silences it, so the dispatcher waiting for its orchestrators is unchanged and older Claude Code input without `type` keeps the old behaviour.
- `docs/hooks.md` names which background tasks keep the gate silent.

## Capabilities

### New Capabilities

### Modified Capabilities
- `work-hooks-subagents`: `Stop waits for background agents` skips the checks only for running tasks that are not `shell` or `monitor`.

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `docs/hooks.md`

## Out of Scope

- Telling a background test run (the session waits for it) from a dev server (it never ends) among `shell` tasks: the input has no field for it; a gate that fires once while a test run is in flight is the accepted cost (the same reason set does not fire twice).
- The `session_crons` array of the Stop input: a scheduled wakeup is not running work, and the gate does not read it today.
- SubagentStop and the status handback: they do not read `background_tasks`.
- The Codex copy of the hook: Codex sends no `background_tasks`.

## Depends On

none

## Source

The owner, in the weekly competitor review task (translated from Russian): "Whatever is better than what we have now, add that into changes, or what you consider better from the point of view of functionality". The bug was found by the agent in that task while checking the Stop input of the Claude Code hooks reference against `cmd_stop`.
