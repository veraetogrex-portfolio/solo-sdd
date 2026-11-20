# Proposal

## Why

The rule "one more line means merging or generalising the closest lines" names a method, and the only check of it (`Section full`) counts lines. Agents met the cap by gluing rules together: on 20.11.2026 five of seven projects under `~/Code` held 20 lines in `## Lessons`, and in two consumer projects single lines reached about 1,800 and 950 characters with five or six separate rules in one line. Such a line no longer reads as one rule, while the details in it are still the material its cause is found from.

## What Changes

- A merge at the cap writes one new line naming the cause the merged lines share, never their concatenation.
- Every `## Lessons` line is one sentence of at most 300 characters; its details live in the project's `LESSONS.md` under an id the line links to (`([full text](LESSONS.md#<id>))`), the form this repository already uses.
- Any edit of `## Lessons` leaves no line over the bound: a longer line found there is shortened in the same edit, its old text moved verbatim under its id.
- The four lines of this repository's own `## Lessons` over 300 characters are shortened; their full text in `LESSONS.md` stays.
- The lesson stand gets a full section with a glued line, and `check.sh` reports lines over the bound and links to missing ids.

## Capabilities

### New Capabilities

### Modified Capabilities
- `lesson-routing`: `Lessons without duplicates` merges by the shared cause; new requirement `Short line with full text`.

## Impact

- `global/AGENTS.md`
- `AGENTS.md`
- `LESSONS.md`
- `tests/test_skill_commands.py`
- `tests/stands/lesson-stand/`
- `tests/stands/lesson-routing.py`

## Out of Scope

- Rewriting the `## Lessons` sections of consumer projects (mylnitsa, ref): their own repositories, after `sync.py push`; the rule also shortens them at their next lesson.
- A setting for the 300-character bound: no project asked for another value.
- Moving lessons shared by several projects into `global/AGENTS.md`: the owner adds those by hand.
- The language of lessons: each project's own choice.

## Depends On

none

## Source

The owner, 2026-11-20 (translated from Russian): "Is that really bad? We can get the root cause out and rewrite it short" (on lessons lines that grew to paragraphs at the 20-line cap); then "Yes, create it".
