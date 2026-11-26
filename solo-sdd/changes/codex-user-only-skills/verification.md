## Live Scenario

The base is commit e262b7e (main when the change was planned).

1. In a temporary `HOME` holding an empty `.codex` folder (Codex is chosen by detection), `python3 sync.py push` from the change's worktree → `$HOME/.codex/skills/<name>/agents/openai.yaml` and `$HOME/.agents/skills/<name>/agents/openai.yaml` (the folder the Codex documentation names for user skills) exist for the seven skills and hold `allow_implicit_invocation: false`; neither folder has `spec-next/agents/`. The same run from the base commit lays no `agents/` folder.
2. After the layout on the owner's machine (`sync.py push` of the merged change), a Codex session in a project with a `solo-sdd/` tree gets the prompt "what is next in this project?" without `$next-up` → the session does not load the `next-up` skill (its transcript under `~/.codex/sessions/` holds no read of `skills/next-up/SKILL.md`).
3. In the same session, `$next-up` → the skill loads and answers by its report form.

If step 2 loads `next-up` on its own, the change is not archived: Not Verified names the Codex version (`codex --version`) and the folder it read the skill from, and the fix goes into a new bug fix change.

## Needs

- Step 2 and 3: one Codex session on the owner's ChatGPT subscription, two prompts, after the layout of the merged change; within the subscription, no charge beyond it.

## Fallback

Before the layout, steps 2 and 3 are replaced by step 1 and a quote of the Codex documentation line on `allow_implicit_invocation`; Not Verified names steps 2 and 3 with a line in the first table of `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: the first run's judge kept J1 (docs proof), J5 (quoted values) and J6 (the `~/.agents/skills` copy) as HIGH; all three fixed: the test of 1.1 asserts the doc, the file form is fixed as text lines, the layout scenario and step 1 check both folders. Kept MEDIUM J2, J3 and J11 fixed too (the wrong-policy row, detection by an empty `~/.codex`, the outcome when step 2 fails).
- analyze (repeat): the `docs/layout.md` assertion has no requirement of its own; it proves What Changes item 3 and stays in the test of 1.1.
