---
name: plan-input
description: Use when a review, a research or a discussion has ended with the owner's decisions and the work goes to /spec-plan in another session or folder - "make an input for spec-plan", "write the decisions up for planning", "prepare the plan input", "hand the review to spec-plan", "the decisions of the weekly review", "write the TZ for Claude", "the final TZ", "the input for spec-plan" - and before telling the owner to run /spec-plan or /spec-dispatch from a folder that is not the target repository.
---

# plan-input: a self-contained input for /spec-plan, with the launch steps

The result is one Markdown file that `/spec-plan` reads without this chat, and three plain launch lines for the owner: which folder to open, which command to type, what happens next. No change, code or repository file is written here.

## Order

1. **Target.** Name the repository the items change: the files the items name, `solo-sdd status` (its `source:` line for shared rules and skills). One input file per target repository. An item that changes a deployed copy (`~/.claude/...`, `~/.codex/...`, `~/.agents/...`) is written against its source in the repository.
2. **Process tree.** The target is not a git repository (`git -C <target> rev-parse --show-toplevel` fails) or has no `solo-sdd/` tree: stop here, before any item check. Write no input; the reply says which of the two is missing and names the target's absolute path, with no section counts. `/spec-plan` and `/spec-dispatch` do nothing there.
3. **Sections.** Every item stands under exactly one section, the first that applies, in this order:
   1. `Already done`: a commit closes it (step 4), with its short hash.
   2. `Already planned`: an open change covers it (step 4), with the change id.
   3. `Not decided`: the owner gave no decision; one line each.
   4. `Not checked`: a decided item whose check failed (step 5), with the reason.
   5. A letter section (`A`, `B`, ...): a decided item that passed every check. Only these are planned.
4. **Done or planned.** Check every item, decided or not, against the target repository:
   - Done: a commit of `git -C <target> log` changes the item's named file and its subject or diff carries the item's edit (`git log --oneline -- <file>`, `git show <hash>`). A commit whose message only mentions the item's words does not close it. A file a commit deleted while closing the item counts as done, not as missing.
   - Planned: take the ids from `solo-sdd list --json` in the target (it prints ids and counts, no text), then read `solo-sdd/changes/<id>/proposal.md` and `tasks.md` of each; a change whose text names the item's file and edit covers it.
5. **Checks of a decided item.** Every named file exists in the target; a quoted line is still there as a fixed string (`grep -nF -- '<line>' <file>`). A failure puts the item under `Not checked` with its reason: `no file named`, the missing path, `line not found: <line>`, or `check could not run: <command>` when a `git` or `solo-sdd` call exits other than 0, `grep` exits 2 or more (1 is only no match), or a command is missing. A failed call is never taken for an empty answer: an item whose done or planned check could not run is not planned.
6. **Each letter section:**
   - `Decision`: the owner's words quoted verbatim, with the date.
   - `Facts`: date, session id (last 6 characters) or chat link, a quote of at most 15 words, counts. Only what was observed; a guess is marked as one.
   - `Where`: file and line in the target repository.
   - `What`: the ready text of the edit in the repository's language (solo-sdd: English only, the repository test rejects Cyrillic).
   - `Check`: the test row, stand or live scenario that proves it.
   - `Out of scope`: what the item does not touch, when the owner limited it.
7. **Slicing hint.** Which items go into one change, which are light path candidates (`light`), which depend on another. `/spec-plan` may refine it.
8. **Nothing to plan.** No item got a letter section (also with no items at all): write no input. The reply says there is nothing to plan, counts each section and lists every item in one line under its section with its reason (the hash, the change id, the missing path or line, the failed command).
9. **Save**, never inside the target repository (a material folder inside it does not count): in the folder the owner names; else next to the material's file (the review's folder, the research folder); else in `~/Documents/plan-input/`, created when missing. Name: `<YYYY-MM-DD> input for spec-plan - <stem>.md`, where the stem is the material file's name without its extension, or `chat` when the decisions came in the chat with no file. A taken name gets `-2`, `-3` before `.md`; an existing file is never overwritten. The text is in the owner's language, the `What` lines in the repository's.
10. **Launch lines** at the top of the file and at the top of the reply:
   1. Open a new Claude Code (or Codex) session in the folder `<absolute path of the target repository>`.
   2. Type `/spec-plan "<absolute path of the input file>"`.
   3. When the plan is committed: `/spec-dispatch` in the same session.

   Add one line: started from any other folder, `/spec-plan` and `/spec-dispatch` find no `solo-sdd/` tree and do nothing.

## File form

```markdown
# <target>: input for /spec-plan. <topic>, <date>

How to start: <the three launch lines>

Only the letter sections are planned; `Already done`, `Already planned`, `Not checked` and `Not decided` are for the owner.

The document is self-contained: the changes are planned from it. Source: <the review or research file>. Facts: <where the session ids come from>.

Suggested slicing: <A+B together, C, D (light), ...>

## A. <title> (decision: "<owner's words>", <date>)
- Decision: "<owner's words>", <date>
- Facts: ...
- Where: ...
- What: ...
- Check: ...

## Already done
## Already planned
## Not checked
## Not decided
```

## Red flags

| Thought | Reality |
|---|---|
| "The owner knows where to run it" | 2026-11-15: `/spec-dispatch`, `/spec-plan` and `/project-init` were started in the notes folder, then "where are the changes? why is the project empty?". Always write the folder and the command |
| "I will put the input into the repository so the planner sees it" | The repository gets only changes; the input stays outside it |
| "This item is obviously wanted" | No quoted decision: `Not decided` |
| "The line number is from the review, good enough" | Re-check with `grep -nF`; the source moves between the review and the plan |
| "`solo-sdd list` failed, so there are no open changes" | A failed call is not an empty answer: `check could not run: <command>` |
| "Same name as this morning's input, I will update it" | A new file with `-2`; the earlier input stays as it was |

## Report

The launch lines first (when an input was written), then 2-4 plain lines: the path of the input file, the target repository, how many items got a letter section and how many went under `Already done`, `Already planned`, `Not checked` and `Not decided`. With nothing to plan or a target without a process tree, the reply of step 8 or step 2 instead.
