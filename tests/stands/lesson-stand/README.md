# lesson-stand

Stand of change `lesson-routing`: two async handlers in `handlers.py` miss an `await`, and both tests in `test_handlers.py` fail. `AGENTS.md` has no `## Lessons`; `AGENTS.full.md` has 20 lessons, none about async calls. `openspec/` holds the one-task change `fix-second-handler`. `check.sh` prints the `## Lessons` section and the `sha256` of `~/AGENTS.md`, `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md`.

Stand readiness without models: `/usr/bin/python3 tests/stands/lesson-routing.py` from the solo-sdd root.

## Live Scenario

Run after `python3 sync.py push`, from the solo-sdd root, on the cheapest models (`cheap` in `global/model-policy.json`). Each step starts from a fresh copy unless it says otherwise.

```sh
S="$(mktemp -d)/stand"
cp -R tests/stands/lesson-stand "$S"
cd "$S"
git init -q
git add -A
git commit -qm stand
sh check.sh
```

1. `claude -p --model haiku "Make test_get_user pass."`, then `python3 -m unittest -v` (`test_get_user ... ok`) and `sh check.sh`: one line about awaiting async calls, no file name. Give only that line and `git diff` to a reviewer with a clean context: class of cause or symptom.
2. In the same copy, `claude -p --model haiku "Make test_get_order pass."`, then `sh check.sh`: the line count is unchanged.
3. In the same copy, `claude -p --model haiku "In get_user, rename the variable name to user_name."`: `## Lessons` unchanged.
4. `claude -p --model haiku "When you report a spec-next change, put the archive path first."`: `check.sh` shows the same three checksums as before, the reply has `Lesson for solo-sdd:`.
5. Steps 1 and 2 with `codex exec -s workspace-write -m gpt-6-luna "<same prompt>"` (the cheapest Codex model in `~/.codex/models_cache.json` at the time of the run).
6. `mv AGENTS.full.md AGENTS.md` in a fresh copy, then step 1: at most 20 lines, one about awaiting async calls.
7. After step 1, `claude -p --model haiku "/spec-next fix-second-handler"`: the report has `Lesson:` with the exact line and this `AGENTS.md`, or `Lesson: none`.
8. `rm AGENTS.md` in a fresh copy, then step 1: no `AGENTS.md` appears, the reply has `Lesson (no AGENTS.md):`.
