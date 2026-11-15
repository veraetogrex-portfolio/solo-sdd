## Live Scenario

1. `python3 tests/stands/provider-probe.py codex` on this computer (Codex 0.159.2 or newer) → it prints the Codex version for `hooks`, or `hooks: unverified` with the reason; the printed line is copied into Result.
2. With `hooks` confirmed: `python3 tests/stands/codex-hooks.py` in a temporary home with a fake `~/.codex` folder runs `solo-sdd install --agents claude,codex --hooks` and prints one `ok` or `FAIL` line per step and `codex-hooks: <n> of <n> checks passed`:
   - `~/.codex/hooks/work_hooks.py` equals `global/work_hooks.py`, `~/.codex/hooks.json` has one `guard`, `context`, `stop` and `end` entry;
   - a second `install` changes no file;
   - an older hand copy of `work_hooks.py` is named `foreign` and kept, exit 1; `--replace-foreign` replaces it and the backup holds the old text;
   - a foreign `PreToolUse` entry of `hooks.json` stays;
   - a broken `hooks.json` → exit 1 naming it, no file under `~/.codex` written;
   - `install --agents claude --hooks` after it → the solo-sdd entries leave `hooks.json`, the foreign entry stays;
   - the laid-out hook fed a Codex `Stop` input with a Codex transcript ending in the Russian "translate into English" and an English reply under `reply.language: ru` → no block; the same transcript with a Russian question after it → a block.
3. `solo-sdd doctor` in that home → `ok agent codex` with hooks.
4. All tests from the `## Commands` table of `AGENTS.md` → code 0.

## Needs

- One `codex exec` run of the probe (step 1) on the cheapest Codex model of `global/model-policy.json`: 1 call on the owner's Codex subscription quota, no per-call charge expected (not checked); it needs the owner's consent before the run.
- The Codex transcript format and the hook trust record are read from a real run here, not assumed.

## Fallback

Without consent for the Codex run: steps 2 and 3 run with the capability set by hand in the stand only, Result says the capability is not confirmed, the registry keeps `unverified`, and `install --agents codex --hooks` keeps refusing; the change is not archived as done until step 1 passes.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: a task waited for the paid probe run → the run moved to Live Scenario step 1 and Needs, task 1.1 builds the probe only — pass 2.
- analyze: the Codex matcher tool names were to come from the paid run → the matcher copies the hand-made `hooks.json` Codex already runs here — the layout must not wait for consent.
- analyze: a broken `hooks.json` and Codex leaving the choice had no outcome → refused before any write; entries removed with the copies — lesson on refusing broken input before the first side effect.
- analyze: idempotence of the writer → a Hypothesis test in task 1.4 — pass 3a.
- analyze: `Depends On` `reply-language-requests` is not archived → the change waits for it; the dispatcher launches it after that merge.
