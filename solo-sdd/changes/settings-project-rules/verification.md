## Live Scenario

1. In a temporary project whose `solo-sdd/project.md` has `Language: en` and `Mode: demo`: `python3 -m solo_sdd config get project.stage` → `demo`, `source: project.md`; `config list` → `project.stage demo project.md`.
2. `config set project.stage prod` → `config get project.stage` → `prod`, `source: file`; `project.md` keeps its bytes.
3. `config set artifacts.language "Russian language"` → exit 1; `config set artifacts.language ru` → code 0.
4. `HOME=<temporary home> python3 sync.py push` → the laid-out `~/.claude/CLAUDE.md` names `project.stage`, `lessons.write` and `lessons.max-lines`, and `spec-plan` names `artifacts.language`.

Steps 1-3 in one call: `python3 tests/stands/settings-project-rules.py` → `3 of 3 checks passed`.

## Needs

none

## Fallback

not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: `project.stage` had no default → empty, read as "not set": the global rules keep deciding by the task, as section 11 says today.
- analyze: "any lowercase language code" had no form, and the `choice` kind with any value checks branch names → 2 or 3 lowercase ASCII letters (ISO 639); a longer tag such as `pt-br` was rejected as not asked for.
- analyze: which parts of an artifact go into `artifacts.language` was open, and translated headings or `SHALL`/`WHEN`/`THEN` would fail `validate` → only the prose; headings, keywords, keys and paths stay English.
- analyze: a file value and a different `Mode:` line in `project.md` would give an agent two answers → the file value wins and the global rules say so; `config set` does not edit `project.md`, and the Live Scenario checks its bytes.
- analyze: a `Mode:` or `Language:` line outside the allowed values had no outcome → it is left out (the default holds) and `config get`, `list` and `describe` name it on stderr, never a silent skip.
- analyze: a new source `project.md` contradicted the closed source list of the main Config command, and the main Defaults by mode names only the `## Delivery` items as old sources → `MODIFIED` Config command adds `project.md`; Defaults by mode is left to `settings-delivery-items`, whose `MODIFIED` block reads every key's old source "named after that file", and that change is added to `Depends On` so the two never modify the same block.
- analyze: `lessons.write: off` contradicts the main Lesson from a correction or a fix ("write, without asking") → `MODIFIED` there; `lessons.max-lines` only changes the number 20 of Lessons without duplicates, so Project rules in config reads that number as the default instead of a second `MODIFIED` copy.
- analyze: an agent could switch `lessons.write` off or `project.stage` to `demo` and skip the duties they carry → the global rules let an agent change the four keys only on the owner's words in the chat.
- analyze: the stand claimed "all in one call, 4 of 4" while step 4 needs a layout into a temporary home → the stand runs steps 1-3 (`3 of 3 checks passed`), step 4 runs on its own.
