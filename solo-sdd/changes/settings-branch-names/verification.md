## Live Scenario

In a temporary git project with `solo-sdd/` and two ready changes `a` and `b`:
1. `python3 -m solo_sdd config set delivery.branch-prefix feat/` → code 0; create branch `change/a`; `python3 global/sdd_dispatch_plan.py <root>` → `launch: a b`: the old-prefix branch no longer holds `a`.
2. Create branch `feat/a`; the plan again → `launch: b`, and `a` waits with `not merged: branch feat/a`.
3. `config set delivery.branch-prefix change/` while `feat/a` exists → exit 1 naming `feat/a`, the value stays `feat/`.
4. `python3 -m solo_sdd config set commit.light-prefix quick:` → code 0, `config get commit.light-prefix` prints `quick:`; `HOME=<temporary home> python3 sync.py push` → the laid-out `work-status`, `report` and `spec-plan` texts read `commit.light-prefix` through `solo-sdd config get`.

Steps 1-3 in one call: `python3 tests/stands/settings-branch-names.py` → `3 of 3 checks passed`.

## Needs

none

## Fallback

not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: the launch line of `sdd-dispatch-plan.py` prints ids, never a branch, so "the launch line names `feat/a`" needed new output → the scenarios prove the prefix by which branch holds a change (`not merged: branch feat/a`) and which no longer does — no new output line for one check.
- analyze: thirteen main requirements in `spec-dispatch`, `dispatch-tool`, `pr-tool`, `spec-plan` and `work-size` name `change/<id>`, `plan/<first id>` or `light:` literally in their text, which a set prefix contradicts → one sentence in Branch and commit prefixes reads those names as the defaults; thirteen `MODIFIED` copies were rejected: they change no behaviour beyond the name, and two of them (Local land command, Land after green) are modified by `settings-local-merge` and `settings-ci-wait`.
- analyze: the guard covered only `config set` → `config unset` changes the prefix in effect too and is guarded the same way.
- analyze: with `delivery.delete-branch: off` (`settings-ci-wait`) merged branches stay, and a guard on every branch under the prefix would block any change of it → only branches of open changes count: the dispatcher drops other ids anyway.
- analyze: a plan prefix equal to the branch prefix makes the plan branch `change/<first id>`, which the dispatcher reads as a leftover change branch → equal prefixes are refused; a prefix with which `<prefix>a` is no valid branch name is refused too.
- analyze: the guard had no outcome for a folder outside git or a failed `git branch` → outside git it passes, a failed listing refuses with git's message: "could not read" never reads as "no branches".
- analyze: "a prefix git refuses is refused" holds for any value, and two examples do not reach the edge forms of a ref name → a Hypothesis property in task 1.1 with a mutant without the ref check.
- analyze: a light prefix with `[`, `.` or `*` would break the `git log --grep='^light:'` pattern of `work-status` and `report` → the prefix is matched as plain text at the subject start.
- analyze: `config set` lives in `run` of `solo_sdd/settings.py`, not in `solo_sdd/cli.py` → task 1.2 names `run`, `solo_sdd/cli.py` left `Impact`; the settings screen refusal got a row in `tests/test_settings_ui.py` and `sdd-eval.py` a row in `tests/test_sdd_eval.py`.
- analyze: Live Scenario step 4 asked a static skill text to print a `git log` command with `quick:` in it → the step checks that the laid-out texts read `commit.light-prefix` and that the project prints `quick:`.
- analyze: `Depends On` names `settings-delivery-items` (the `text` kind) and `settings-local-merge` (the same `land-local` and `merge.md` lines), both open → recorded as the intended queue order: this change starts after both are archived.
- analyze (plan cross-check): `settings-ci-wait` modifies "Land after green", which still names `change/<id>` → `settings-ci-wait` added to Depends On — the prefix change lands after every change that rewrites branch-naming text, so the defaults sentence covers the final wording.
