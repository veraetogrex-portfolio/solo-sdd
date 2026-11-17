## Live Scenario

In a temporary git project with `solo-sdd/` and a `.gitignore` holding `node_modules`:
1. `python3 -m solo_sdd ignore` → lists `.claude/worktrees/`, `.env`, `.env.*`, `!.env.example`; `.gitignore` unchanged.
2. `python3 -m solo_sdd ignore --write` → `.gitignore` keeps `node_modules` as its first line and gains the block; `git check-ignore -q .env` exits 0 and `git check-ignore -q .env.example` exits 1; a second run prints `no change`.
3. `config set git.ignore ".claude/worktrees/, docs/waiting.md"` with `docs/waiting.md` tracked → the hint line; `ignore --write` names `git rm --cached -r -- docs/waiting.md`, the file stays in `git ls-files`, the block no longer has `.env`.
4. `config set git.ignore solo-sdd/` → exit 1; `config set git.ignore "*.md"` → exit 1 naming `AGENTS.md`; `solo-sdd/config` unchanged by both.
5. `git init` of a new folder, then `python3 -m solo_sdd init <folder> --yes` → its `.gitignore` has the block with the four default lines.

All in one call: `python3 tests/stands/settings-gitignore.py` → `5 of 5 checks passed`.

## Needs

none

## Fallback

not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: whether `.env.*` would hide the `.env.example` that `project-init` writes for the repository → the default gains `!.env.example` and an item starting with `!` re-includes a path (always written, never checked against outside rules) — a default that hides the example file breaks every new clone; dropping `.env.*` would let `.env.local` secrets in.
- analyze: the main requirements Process artifacts in git and Hidden process artifacts still allowed only the appended line `.claude/worktrees/` → both are MODIFIED to the solo-sdd block — the block also adds `.env` lines, which those requirements forbade.
- analyze: which rules count as "already hides" → only the repository's `.gitignore` files outside the block; `.git/info/exclude` and the global excludes file do not — `git check-ignore` reads both (probed), and they do not travel with the repository, so a clone would commit `.env`.
- analyze: refusing only the names `solo-sdd/`, `AGENTS.md`, `CLAUDE.md` let a glob such as `*.md` hide them → the refusal is by git's matching of each item, `#` items refused too — Process artifacts in git must hold for any value.
- analyze: a begin marker without an end, a lone end or two blocks → exit 1 naming the line, every file unchanged — rewriting up to the end of the file would delete the owner's lines.
- analyze: `project-init` step 2 runs before `solo-sdd/config` exists → the command runs after the process tree step (`init` runs it after writing the tree, a refusal gives exit 1 with the tree kept); without `solo-sdd/config` the defaults apply; outside git: exit 1.
- analyze: where the project's own secret and working-data paths of step 2 go → `solo-sdd config set git.ignore` before the command — one list the owner sees and edits.
- analyze: a path in the printed `git rm --cached` line comes from the config → it is shell-quoted — the owner pastes the line into a shell.
- analyze: `config unset git.ignore` changes the list too → it prints the same hint.
