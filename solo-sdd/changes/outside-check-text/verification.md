## Live Scenario

The stand `tests/stands/outside-check-text/` holds `text.md` (11 facts: release dates, versions, prices and named facts of invented products), one local primary source file for each of the first 10 under `sources/` and none for the 11th, `planted.json` naming the 3 wrong facts with their right values, and `tests/stands/outside-check-text.py` with `--grade <table>` (a `| fact | mark | right value | source |` table) and `--grade-answer <answer>`.

1. `python3 sync.py push`, then `python3 sync.py status` → the laid-out `~/.claude/CLAUDE.md` and `evidence-research` hold the check, no unexpected `drift`.
2. A subagent without `model` (the main model) runs the laid-out `evidence-research` on the stand's question "which of the three products to pick", with `sources/` as the only sources and the facts of `text.md` as its draft; its transcript and answer are saved to the scratchpad → the transcript has one `Check:` agent launched by it, which the guard hook let pass.
3. `python3 tests/stands/outside-check-text.py --grade <the Check: table from that transcript>` → `wrong 3 of 3 with the right values, confirmed 7 of 7, no primary source 1 of 1, touched correct 0`.
4. `python3 tests/stands/outside-check-text.py --grade-answer <answer>` → `corrected values 3 of 3`, `not confirmed: yes`, `counter-argument: yes`, `check line: Check: confirmed 7, fixed 3, not confirmed 1`.

## Needs

none

## Fallback

Not needed: the sources are local files, and the subagents run in the lead session on the subscription.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
