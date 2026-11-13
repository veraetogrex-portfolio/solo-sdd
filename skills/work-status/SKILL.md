---
name: work-status
description: Use when the user asks where the work stands or whether anything is still running - "status?", "what is the status", "are you there?", "what are we waiting for", "are you done?", "what is active now", "is the process running or stuck", "is it frozen?" - and before context compaction or a handoff to another session - "describe where we stopped", "I will press compact".
---

# work-status: five lines about the state

The answer is exactly the five lines below, in the user's language, without an introduction. It must show whether one can step away from the screen.

Before answering check the facts, not memory: the list of background processes and tasks, `git status`, `tasks.md` of the current change.

"Done" counts `light:` commits apart from changes: `light: <n> commits` from `git log --oneline --grep='^light:' --since=<the session's first message time>`, and names the archived changes by id.

```
Done: <what is finished and checked>
Running now: <process, how long so far and how much more, by what sign it ends> | nothing running
Left: <items until "done">
Blocking: <what we wait for, who can lift it, what cannot be checked yet, when to come back> | nothing
Needs from you: <a specific action> | nothing
```

## Conditions

- A process is stuck or dead: write it in "Running now", restart it and say that you restarted it.
- "Running now: nothing" while "Left" is not empty: right after the answer continue the work, do not wait for a command.
- The user mentioned a compaction, a move to another chat or another agent: write the same five lines and the list of decisions made into `handoff.md` in the current change's folder (no change: the project root) and name the path.
