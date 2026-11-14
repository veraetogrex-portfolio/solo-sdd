## Live Scenario

1. `wc -c README.md` → at most 12000 bytes (was 59511).
2. Text kept: for every paragraph, table row and list item of `git show HEAD~:README.md` from the sections that moved (Requirements to What is not here, except those rewritten into the showcase), `python3` finds it in a `docs/*.md` file after link rewriting → `missing: 0`.
3. Every link of `README.md`, `CONTRIBUTING.md` and the new `docs/*.md` resolves (`tests/test_readme.py`, `test_links_resolve`), and every absolute `blob/main/` link of README points to a file this branch tracks.
4. A clean temporary home: `pip install` of this tree into a fresh venv, then the Quick start commands as written (`solo-sdd install --hooks`, `cd` into a fresh git repository, `solo-sdd init --yes`) → each exits 0 and `solo-sdd doctor` prints `ok process guard: connected`.
5. The rendered page: the README rendered by `python3 -m markdown` (or GitHub's preview of the pushed branch) shows the badges, the change tree, the `<details>` sample and the Skills table; a reader names from it what a change is, which skills exist, how to update and how to remove.

## Needs

none

## Fallback

No package index access for step 4: install the working tree itself (`pip install .`), which is what step 4 does anyway. How PyPI and npm render `<details>` and badges is seen only after the next release; until then it goes to Not Verified.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
