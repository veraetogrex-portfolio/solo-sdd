# Proposal

## Why

The reply language check fights the owner when they ask for another language and does not reach the places where the wrong language hurts most.

- 2026-11-12 (one session) a Stop hook three times demanded "the final reply is not in Russian, rewrite it in Russian" after the owner asked for the reply in English and then "translate into English"; the agent each time answered that it keeps the translation and repeated the text. Two more sessions on 2026-11-10 and 2026-11-12 had the same turn: 5 wasted turns in the week. `wrong_language` in `global/work_hooks.py` counts every letter of the reply, a draft in a `:::writing` block and quoted `>` lines included, and does not look at what the user asked for.
- 2026-11-12 and 2026-11-13, three sessions with a Russian first message had 37 of 41, 10 of 11 and 21 of 37 agent messages in English, question windows among them; the owner answered by option clicks ("Yes, roll out") and then wrote "I do not understand where to click". Line 14 of `global/AGENTS.md` names only the final report and comments, and no hook looks at a question window.

The hook that ran in those Codex sessions is a stale copy that `sync.py push` does not lay out: that is `codex-hooks-layout`. This change fixes the check itself and adds the question window check.

## What Changes

- The reply language check leaves out `:::writing … :::` blocks and lines starting with `>`, as it already leaves out code, links and paths.
- The Stop hook does not check the language when the last message the user wrote asks for English or a translation: `translate`, `in English` or the Russian stems for "English" and "translate", ignoring case (the stems are `\u` escapes in the source, the repository has no Cyrillic letter).
- The `guard` hook checks an `AskUserQuestion` call: the questions, option labels and option descriptions together go through the same check with the project's reply language; a mismatch denies the call with a line to rewrite the window in that language. Fail-open as the other hooks. Messages between tool calls are not checked by a hook, on purpose.
- `solo-sdd install --hooks` adds `AskUserQuestion` to the `guard` matcher.
- Line 14 of `global/AGENTS.md` becomes: "Reply in the language the user writes in: every message the user sees — progress lines between tool calls, AskUserQuestion questions and option labels, the final report. A handoff, skill or repository written in English does not change it."
- Nothing changes while `reply.language` is `off` (the default) and `SOLO_SDD_REPLY_LANG` is unset.

## Capabilities

### New Capabilities

### Modified Capabilities
- `repo-language`: Reply language check is modified (quotes and writing blocks left out); Requested translation passes, Question window language and Question guard registration are added.

## Impact

- `global/work_hooks.py`, `solo_sdd/hooks.py`
- `global/AGENTS.md`, `docs/hooks.md`
- `tests/test_work_hooks.py`, `tests/stands/reply-language.py` (new)

## Out of Scope

- Laying out the current hook into the Codex hook folder: `codex-hooks-layout`.
- A hook check of progress messages between tool calls: the owner chose the rule only.
- Setting `reply.language` for the owner's projects: a setting, not code.
- The report form for the owner, the Telegram bot live rule and the `ship` CI wait: light path edits of the same plan.
- Run decisions of the dispatcher: `dispatch-run-decisions`; review rounds: `review-rounds-five`.

## Depends On

none

## Source

The owner, 2026-11-15, on the weekly review (translated from Russian): on the language hook after a requested translation, "Let's do it as proposed"; on the language of every visible message, "The rule and a hook on questions".
