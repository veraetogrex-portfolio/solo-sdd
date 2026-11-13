---
name: project-init
description: Use when starting a new project or folder, or preparing an existing repository for agent work - "create agents md", "write agents md for the project", "connect the spec process", "initialise git", "start creating files in the folder", "create env" - and when a repository has no AGENTS.md, no `solo-sdd/` tree, or Claude does not pick up the project rules without being told to read them.
---

# project-init: a project ready for /spec-next

Done when you can say `/spec-next` in the folder to both agents right away and they get the same rules without reminders.

`/project-init map` runs only step 4a: it rewrites all four map files with new stamps, even if they exist, and changes nothing else (no commit, no other file); then the report by step 4a.

## Order

1. **Mode.** Decide by the task: `demo` (a demo, a defence, a prototype) or `prod`. The mode is not given and the task is not about a demo: choose `prod` and record the decision.
2. **Git.** `git init`, if there is none. An address is given: add a remote. `.gitignore`: `.env`, keys, certificates, working data. Do not put `solo-sdd/`, `AGENTS.md` and `CLAUDE.md` into `.gitignore`. Then `git check-ignore -q .claude/worktrees/x || { [ -n "$(tail -c1 .gitignore 2>/dev/null)" ] && echo >> .gitignore; echo '.claude/worktrees/' >> .gitignore; }` (the folder of built-in Claude Code worktrees must not get into commits). Do not change an existing `.gitignore` except for this line; if it does not hide `.env`, say so in the report.
3. **Process tree.** A project with `openspec/` and no `solo-sdd/`: do not create a second tree, name the next step `solo-sdd import openspec` in the report and go on with the other steps. Otherwise, no `solo-sdd/`: run `solo-sdd init` and do not repeat its steps (`solo-sdd/project.md`, `solo-sdd/analyze.md`, `solo-sdd/specs/`, `solo-sdd/changes/`, `docs/waiting.md`); after that edit only `solo-sdd/project.md`. In an existing `solo-sdd/project.md` keep the previous text, add only what is missing. For a new one:
   ```markdown
   # Project

   Language: en
   Mode: demo | prod

   Intent: <2-3 sentences: what this is and for whom; every new change is checked against it>
   Paid calls to the product model in tests and live acceptance use the cheapest models; review and acceptance use the main model.
   ```
   Templates of the project checks `solo-sdd/analyze.md` and of `docs/waiting.md` are in `~/.local/share/solo-sdd/templates/`. The whole workflow is `~/.local/share/solo-sdd/ALGORITHM.md`.
4. **`.env.example`** with empty fields and a comment on where to get the value. Keep existing `.env` and `.env.example`; add only the missing fields with empty values. If there is no `.env`, create it with empty fields. Do not ask for secret values in chat: name the field to fill in.
4a. **Codebase map.** Only in an existing project: `git -c core.quotePath=false ls-tree -r --name-only HEAD 2>/dev/null | grep -qv -e '^docs/' -e '^solo-sdd/' -e '^AGENTS\.md$' -e '^CLAUDE\.md$' -e '^\.gitignore$'` succeeds (`HEAD` has files besides docs, specs and what this skill commits itself). Otherwise no `docs/codebase/`. `docs/codebase/` already exists: keep it, skip to the report lines below (refresh only by `/project-init map`).

   The map is heavy reading, so four subagents on the cheapest model write it in parallel, one file each, in one message (Claude: `subagent_type: general-purpose`, `model: haiku`, description `Map: <file>`; Codex: its own subagents on the cheapest model). Each gets its scope and the common rules:
   - `STACK.md`: languages, frameworks, dependencies with versions from the manifests, external services and APIs, how it is built and run;
   - `ARCHITECTURE.md`: layers, data flow, entry points, folder structure;
   - `CONVENTIONS.md`: naming, error handling and logging, tests (where they live, how they run);
   - `CONCERNS.md`: debt, security, bottlenecks, risks; one item per concern;
   - common rules: write only `docs/codebase/<file>`, change no other file, do not commit; the first line is the output of `git log -1 --format='Commit: %H %cs'`; the file holds only the stamp, headings and list items; every statement is one list item (`- `) on one line that names in backticks at least one path existing in the repository; a statement you cannot tie to a path is not written; never quote the value of a secret (`.env`, a key in the code): name the file and the kind of secret; reply with one line only, `<path> <line count>`, no map text.
   The lead checks without reading the text: `for f in STACK ARCHITECTURE CONVENTIONS CONCERNS; do grep -qs '[^[:space:]]' docs/codebase/$f.md && wc -l < docs/codebase/$f.md || echo "$f missing or empty"; done`. A missing or empty file: its subagent runs once more; still missing or empty: the report names the file as not written, the other three stay. The map is not committed by this skill.
   Report lines: each map file with its line count (or "not written"); then each top-level list item of `CONCERNS.md` (`grep -E '^- ' docs/codebase/CONCERNS.md`; reading these items is the only map text the lead reads) as one line `Candidate for /spec-plan: <item>`. No change is created from them: the user runs `/spec-plan`.
5. **`AGENTS.md`** by the sections below. Keep an existing `AGENTS.md` and add only the missing rules; do not replace it with an import line. The block between `<!-- solo-sdd:begin -->` and `<!-- solo-sdd:end -->` is written by `solo-sdd init`: write the project sections outside it and do not edit inside it. Take facts from the code and `package.json` / `pyproject.toml`, do not invent commands.
5a. **`DESIGN.md`.** Only in a project with an interface: outside `node_modules/`, `tests/`, `solo-sdd/` and hidden folders there is a `.html .htm .css .scss .sass .less .tsx .jsx .vue .svelte` file (this is `UI_EXT` of the hook `global/work_hooks.py`) or the user explicitly named an interface in the request (a site, a landing page, an app with screens). Otherwise `DESIGN.md` is not created and `AGENTS.md` has no "Interface" section.

   Create it by the template `~/.local/share/solo-sdd/templates/DESIGN.md`. Carry over only the user's words from the request or the chat: each word into the field it is about; guess nothing, do not copy into neighbouring fields and do not add notes of your own. Words about the style as a whole ("style: calm", "strict") go into "Character", into "Mood" only what the user called a mood.

   A field that got at least one answer from the user counts as filled, even if the answer is incomplete. Dials are not derived from words: the `Dial` line stays with `n` until the user names numbers; a `Dial` line with `n` counts as an empty field.

   If there are empty fields, one line in the `docs/waiting.md` table (no file: create it by `~/.local/share/solo-sdd/templates/docs/waiting.md`): Change `—`, Items `—`, Waiting for "DESIGN.md: fill in the fields <list of empty fields>", From whom: the user, Since: the date. There is no `WAITING` file. No empty fields, no line.

   A repeated run: keep the existing `DESIGN.md`, do not change filled fields, add missing ones empty, fill empty ones only with the user's answers from this request; update the line in `docs/waiting.md` instead of duplicating it, delete it if no empty fields are left.
6. **`CLAUDE.md`**: if there is no file, create it with one line `@AGENTS.md`, so Claude reads the same rules itself. If the file exists, add `@AGENTS.md` when the link is not there yet; keep the previous instructions.
7. **Check.** `solo-sdd validate --all`, the commands from the AGENTS.md table actually run.
7a. **Artifact commit.** `git check-ignore -v -- solo-sdd/ AGENTS.md CLAUDE.md`, then by case:
   - `.gitignore` was created by this run: `git add -- .gitignore AGENTS.md CLAUDE.md solo-sdd && git commit -m "project-init: rules and specs" -- .gitignore AGENTS.md CLAUDE.md solo-sdd`;
   - `.gitignore` already existed, the output is empty: the same two commands, with `.gitignore` among the paths only if this run appended `.claude/worktrees/` to it; otherwise without it (all three already committed without changes: the step is skipped);
   - `.gitignore` already existed, the output is not empty: do not change `.gitignore` except the line `.claude/worktrees/` (if this run appended it, a separate commit of `.gitignore` alone), and do not commit the artifacts. The report gets: the path, the `.gitignore` line that hides it, and the cost: such artifacts reach a worktree only through `sdd-worktree.py`; in a public repository specs with the user's quotes would be visible to everyone, so the decision is theirs.
   Only the named paths go into the commit: other edits stay uncommitted.
8. **README.** The project starts from scratch by the README, without knowledge from the chat: installation, `.env` from `.env.example`, the run command, how to tell it works. Go through these steps yourself in a clean shell. If it did not start, fix the README or the project; this is part of the task.

## AGENTS.md sections

| Section | Content |
|---|---|
| Purpose and mode | One or two sentences about the project. `Mode: demo` or `prod` |
| Sources of truth | What counts as the contract, what as historical context |
| Working with specs | The four rules below, verbatim |
| Commands | A table: install, build, tests (the `Tests` row, the whole suite, and the `Tests (one)` row, one file or one test with a placeholder for its name), run, live run. The test commands follow the rules below |
| Project map | A short list of folders and their role; when `docs/codebase/` exists, a link to it (stack, architecture, conventions, concerns) |
| Boundaries and invariants | What must not be broken |
| Checks | What to run before "done" |
| Security | Secrets, paid requests, prod |
| Interface (only in a project with an interface) | A link to `DESIGN.md`: the interface direction, filled in by the user |
| Delivery | For `spec-dispatch` and `ship`: the item "Mode:" is `local` (merge into the local main branch, then `ship`) or `pr` (every change is its own PR), "Merge:" is `squash`, `merge` or `rebase`, "PR title:" is the rule, "Deploy:" says whether a merge into the main branch triggers a rollout and where, "Owner only:" holds path patterns in backquotes (`*` within a name, `**` across folders, a trailing `/` means the whole directory) that the agent does not merge itself; `.github/workflows/**` is always added, the list is read from the main folder's `AGENTS.md` |
| Working copy (optional) | For `spec-dispatch`, if some artifacts are ignored by git: the items under the table |

The items of "Working copy":

- the item "Paths:" says what else to copy into a worktree,
- the item "Prepare:" is the command for it (installing dependencies),
- the item "After refresh:" is the command `sdd-worktree.py refresh` runs in the worktree after a transfer without conflicts (rebuilding files that git ignores and that are built from sources, for example `npm run build:ocr`; limit 600 s, a failure gives code 4),
- the item "Orchestrators:" is the number of simultaneous `spec-dispatch` orchestrators (default 2),
- the item "Shared:" holds paths in backquotes that changes edit often and that do not hinder parallel work; a path ending in `/` makes all files under the directory shared: `docs/` for documents, the directory of live check stands

The `Tests (one)` row by runner: unittest `python3 -m unittest <module>` (one test: `<module>.<Class>.<test>`), pytest `pytest -q <file>` (one test: `<file>::<test>`), vitest `npx vitest run <file> --reporter=dot` and jest `npx jest <file> --silent` (one test in both: `-t "<name>"`). Every reader of the suite command (a script, the `TESTS` field of a status, the `Checks` section, the thread limit below) takes the `Tests` row only.

The test command with a "Working copy" section (the `Tests` row; `Tests (one)` gets no flag): compute `max(1, ⌊cores / N⌋)`, where cores is the output of `sysctl -n hw.ncpu` (on Linux, `nproc`), N is the item "Orchestrators:" (default 2), and write into the table the ready command with this number, without the formula and conditions: vitest and jest get `--maxWorkers=<number>` (through npm: `npm test -- --maxWorkers=<number>`), pytest with pytest-xdist installed gets `-n <number>`.

No section, or the test runner cannot limit threads: the command without a flag. Add the flag to an existing command without one, do not recompute a flag already there.

Rules for the "Working with specs" section:

- One change per session, up to the archive.
- No clarifying questions: a reasoned decision, recorded in the report.
- Work outside the current spec becomes a new change.
- After `tasks.md` is closed, an independent live test before reporting readiness.

## demo mode

No docker and no deploy. Data is invented or emulated, except the user's business numbers, reviews and customers: they stay placeholders `[data needed: <what>]`. One reproducible demo script: data seed → scenario → output. The first line of the README is the run command.
