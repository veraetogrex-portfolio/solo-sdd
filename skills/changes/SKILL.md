---
name: changes
description: Use only when the user explicitly invokes /changes - "what is in specs 16 to 47?", "what about 25, 37 and 73", "which specs are free", "which changes are ready for the archive", "show all changes".
disable-model-invocation: true
argument-hint: [a range 16-47 or numbers 25 37 73; without an argument, all open ones]
---

# changes: a table of change states

Argument (optional): a range (`16-47`), numbers (`25 37 73`) or a name. Without an argument, all open changes. Read only.

## Order

1. `solo-sdd list --json` and the folder names in `solo-sdd/changes/archive`: look for the numbers from the argument in both places.
2. For every change:
   - state: open | archived (date) | not found;
   - tasks: done of total (`- [x]` and `- [ ]` in `tasks.md`);
   - `CLAIM`: who and how many hours ago;
   - `WAITING`: the condition;
   - unarchived changes from `Depends On`;
   - the last change: `git log -1 --format=%cr -- <folder>`.
3. A table in number order.
4. Under the table, groups:
   - free: no `CLAIM` and `WAITING`, dependencies closed;
   - ready for the archive: all tasks checked;
   - stuck: `CLAIM` older than a day;
   - waiting: `WAITING`.

If the user in reply marks changes as ready ("16 is ready, 26 is ready"), close each through `/spec-next` with a check, not by a plain move into the archive.

In a project without a `solo-sdd/` tree show `docs/status.md` and say there are no changes; if it has `openspec/` instead, name the next step `solo-sdd import openspec`.
