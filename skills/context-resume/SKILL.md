---
name: context-resume
description: Use when returning to a project or task after a pause, a compaction or a switch between Claude and Codex, before doing any work - "continue", "let's continue", "back to the project", "check the chats", "look in the notes", "what did we decide", "where did we stop", "pick up the context", "are you up to date?", "read the history" - and when about to ask the user something they may have already said.
---

# context-resume: a task map before the first action

The user must not carry context between sessions and agents. Everything they already said, decided or put into `.env`, you find yourself. The result is a short task map that shows what to do next.

## Order

1. **Project rules.** `AGENTS.md`, `CLAUDE.md`, `solo-sdd/project.md`, `docs/status.md`, `docs/waiting.md`. This is the source of truth about the process.
2. **Handoff.** `handoff.md` in the active change's folder or at the project root, `verification.md` of unclosed changes, `solo-sdd list --json`.
3. **Current state.** `git status`, `git log -10 --oneline`, the branch, open PRs, keys in `.env` (names only, do not print values), running processes. For a service: what is actually deployed: the commit, the container, the tables.
4. **History.** Search by the task's keywords instead of reading everything. Sources by availability:
   - the user gave a live link to a chat: first read every such chat; the link title does not replace the content;
   - chat search, if the agent has it; if not, the local history files below;
   - Claude Code: `~/.claude/projects/<project-folder>/*.jsonl`;
   - Codex: `~/.codex/memories/MEMORY.md`, `~/.codex/sessions/<year>/<month>/`;
   - a notes vault, if the project names one: start with its index note.
   No tool: go to the next source. Do not invent what "was in the chats".
5. **Check.** Check every fact from history against files and the service. If they diverge, trust the current state and record the divergence.
6. **Map** in the form below, then straight to work. If the user asked only to restore the context, stop at the map.

## Map (in the user's language, without an introduction)

```
Goal: <what must come out, in one sentence>
Source of truth: <files, service, table I rely on>
Last confirmed state: <what was checked and where, with a date>
Decisions and constraints: <what the user already decided or forbade>
Blockers: <what we wait for and from whom> | none
Next step: <one action>
History versus fact divergences: <what is outdated> | none
```

## Finishing work

If the project rules keep `handoff.md` or `docs/status.md`, update them with the same map. Change global memory (a notes vault, agent memory) only on a direct request.

## Mistakes

| Thought | What to do |
|---|---|
| "I will ask the user where the key is" | First `.env`, history, neighbouring services |
| "The chat said it was done" | Check in the code and on the service |
| "I will read the whole history so as not to miss anything" | Search by the task's words, history is expensive |
| "I will create a working copy next to it" | The project has one folder, work in it |
| "The old note in the vault is right" | A note is a hypothesis until checked |
| "An independent new task, but I will search the history" | Do not drag foreign context into a new task |
