# Proposal

## Why

The independent reviewer of `spec-next` gets `REVIEW.md` from the project root when there is one, but no skill writes that file and solo-sdd has none. The owner's review feedback is spread over PR comments, the owner's quotes and decisions in archived `verification.md` files, and `## Lessons`; the lessons are about classes of code defects, not about what the owner looks at in a review. So the reviewer checks by its own judgement, and nobody knows how often its verdict matches the owner's.

## What Changes

- A skill `review-principles` collects the owner's review remarks from the sources the project has (PR review comments and reviews by the login of the `Owner GitHub login:` line of `AGENTS.md` through `gh` when the project has a GitHub remote, archived `verification.md` lines that start with `owner, <date>` or quote the owner with a date; other authors' comments and the agent's decision lines do not count; an unread source is named, never taken for an empty one), and writes the project's `REVIEW.md`: at most 25 rules, each with one or two links to its sources. A rerun keeps the rules the owner moved or wrote.
- Patterns the remarks show but the owner never stated go into a separate `## Unconfirmed` section. The reviewer does not apply them until the owner moves a line into the main list.
- A parallel mode: an `agent-quality` set of K past changes with the owner's remarks as the golden answers (K = 3, the owner's number of 2026-11-20); `Review:` runs on the same diffs with and without `REVIEW.md`, where that `REVIEW.md` is written with the measured changes' remarks held out, and a table shows matched, missed and extra findings. The owner decides at what match they stop reviewing by hand.
- `spec-next` hands the reviewer `REVIEW.md` without its `## Unconfirmed` section.
- A `REVIEW.md` template, the form the skill writes; the file itself lives in the consumer project, not in solo-sdd.
- `/review-principles` is listed with the other manual commands (global rules, README, layout and skills audit docs), and a stand with a fixture project and a fake `gh` grades the skill's answers.

## Capabilities

### New Capabilities
- `review-principles`: the owner's review rules collected from past feedback, with the reviewer's match measured.

### Modified Capabilities
- `spec-next`: MODIFIED requirement Review rounds.

## Impact

- `skills/review-principles/SKILL.md`
- `skills/spec-next/acceptance.md`
- `templates/REVIEW.md`
- `targets.json`
- `global/AGENTS.md`
- `README.md`
- `docs/layout.md`
- `docs/skills-audit.md`
- `tests/test_skill_commands.py`
- `tests/stands/review-principles.py`
- `tests/stands/review-principles/`

## Out of Scope

- Writing `REVIEW.md` for solo-sdd itself: a run of the skill after the archive, on the owner's word.
- The owner's weekly review task outside the repository.
- `## Lessons` and chat histories as sources: lessons are written by the agent about classes of code defects, and a chat history has no place or format the project rules name; a later change can add them.
- Neighbouring changes of this plan: `subagent-check-roles`, `analyze-outside`, `outside-check-text`, `source-over-paste`, `goal-first`, `practitioner-techniques`, `eval-process-signals`, `skill-ablation`, `work-pull`.

## Depends On

- work-pull

## Source

The owner, 2026-11-20 (translated from Russian): "Turn into changes four techniques from the interview: attacking reviewers with a judge, a check of whether skills get in the way, a set of the owner's review rules, the agent choosing tasks." On the parallel mode, the number of past changes K: "3". Unit C: "Goal: the reviewer checks by the owner's rules, and it is known how far its verdict matches the owner's."
