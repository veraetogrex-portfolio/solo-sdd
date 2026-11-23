# Proposal

## Why

Two failures of the week 16-22.11.2026 (the owner's weekly review of 2026-11-23, facts from `~/.codex/sessions`) come from rules the global rules do not hold.

An analysis was delivered as data the owner could not open. On 19.11 (session …5ca035) the analysis of the Apify catalog lay only in the database of an MCP server, and the owner asked how they were supposed to look at it and what result it gave. On 17.11 (…ebbc13) the owner asked for clear actions that give a bigger result and said they did not see what would give it. `goal-first` (archived 22.11) covers only a request made of steps without a goal; nothing asks an analysis to open with what to do and what it gives.

A project was worked in a copy. On 18.11 (…09dca2) a Codex session started in `~/Documents/Codex/2026-11-18/new-chat` copied the sources of the invoice bot from its repository under `~/Code` into the session folder and ran 31 commands there; the edits were carried back (checked 23.11) but not committed, and the owner was told the work was done. Section 0 of the global rules finds the rules of the current folder only; it does not say where to work when the request names another project.

## What Changes

- Section 1 (Communication) of `global/AGENTS.md`, after the line on a request of steps without a goal: the result of an analysis, a research or a data pull opens with one to three actions, each with its expected effect for the owner (a number when there is one), or the line `No action follows:` with the reason; the data and the full analysis go into a file the owner can open, linked in the first lines; data kept only inside a tool, a database or an MCP server is not delivered.
- Section 0 (Rule order), the end of item 1: a request that names a project on this computer is worked in that project's repository, found under `~/Code`; its rules are read there and it is edited and run from there; its sources are not copied into the session folder, and a copy made for an experiment is carried back and its edits committed before the report.
- The actions are written `<action> — <expected effect>` within the first 5 lines; for a request of steps without a goal they come right after the `Goal:` and `Check:` lines. Sections 3 and 6 name the analysis file as the one file an analysis writes.
- The named project is the git repository at any depth under the projects folder the owner's rules name, by default `~/Code`, whose name equals or starts with the one in the request (the exact name wins over a longer one, the report names the others; no match: the current folder, said in the report), and it takes the place of the current folder for the rule search of section 0. An experiment copy lives only in a temporary worktree of section 9.
- Where the rules meet others: a skill's or the request's report form and file rules win; an unreadable source is named as a failure, never `No action follows:`, which stays in English in any reply language; a new analysis file each time, never overwriting one, and committed only when it holds no personal data (section 8). The lookup compares names case-folded with spaces, `-` and `_` taken as one, an equal name before a prefix and the latest commit among several; a current folder already in a worktree or clone of the project stays; a session that cannot write in the project names the access it needs.
- A stand `tests/stands/action-first.py` grades both rules on answers of Claude Code subagents on the laid-out `global/AGENTS.md`, with references for the graders' boundaries and hostile answers.

## Capabilities

### New Capabilities
- `action-first`: the result of an analysis opens with the actions it leads to and their effect, and its data reaches the owner as a file.
- `project-repo`: a request that names a project on this computer is worked in that project's repository, not in a copy.

### Modified Capabilities

## Impact

- `global/AGENTS.md`
- `tests/stands/action-first.py`
- `tests/stands/action-first/`

## Out of Scope

- A hook that refuses `cp -R` of a repository's sources into a session folder: the rule is text first; a hook is a separate change if the stand or the next weekly review shows the text is not enough.
- A check that the expected effect of an action came true: the line steers the report, acceptance stays the Live Scenario.
- Neighbouring changes of this plan: `worktree-add-quiet`, `fix-env-dump-text-words`, `plan-input-skill`.
- The skill `mac-proxy-launch`: the owner declined it on 2026-11-23.

## Depends On

none

## Source

The owner, 2026-11-23, on the decisions of the weekly review of 16-22.11 (translated from Russian): "all except the proxy, yes", then "do it". Items A ("an analysis opens with the action and the effect") and B ("work in the project's repository, not in a copy") of the owner's input file "2026-11-23 input for spec-plan" (name translated).
