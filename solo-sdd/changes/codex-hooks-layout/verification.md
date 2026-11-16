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

- One `codex exec` run of the probe (step 1). Its model endpoint is a closed local port (`http://127.0.0.1:9`), as in the existing probe, so no request reaches a model and no quota is spent; no consent needed (decision below).
- The Codex transcript format and the hook trust record are read from a real run here, not assumed.

## Fallback

Without consent for the Codex run: steps 2 and 3 run with the capability set by hand in the stand only, Result says the capability is not confirmed, the registry keeps `unverified`, and `install --agents codex --hooks` keeps refusing; the change is not archived as done until step 1 passes.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

- Trusting the laid-out hooks in the owner's real `~/.codex/config.toml` and replacing the hand copy `~/.codex/hooks/work_hooks.py` there (Out of Scope, the owner's step): after merge, `python3 sync.py push` names it `foreign`; `solo-sdd install --replace-foreign` (or `sync.py push --replace-foreign`) replaces it with a backup. The `hooks.json` entries solo-sdd writes have the hand file's exact text, so the trust Codex recorded for them is expected to hold (not checked in the owner's Codex: the hash inputs were not read).
- A real Codex session on the owner's computer running the laid-out `stop` hook: the stand feeds the hook the Codex `Stop` input fields read from the 0.159.2 binary and a rollout in the format of a real one; no live Codex turn reached a model.

## Decisions Without Owner

- analyze: a task waited for the paid probe run → the run moved to Live Scenario step 1 and Needs, task 1.1 builds the probe only — pass 2.
- analyze: the Codex matcher tool names were to come from the paid run → the matcher copies the hand-made `hooks.json` Codex already runs here — the layout must not wait for consent.
- analyze: a broken `hooks.json` and Codex leaving the choice had no outcome → refused before any write; entries removed with the copies — lesson on refusing broken input before the first side effect.
- analyze: idempotence of the writer → a Hypothesis test in task 1.4 — pass 3a.
- analyze: `Depends On` `reply-language-requests` is not archived → the change waits for it; the dispatcher launches it after that merge.
- apply: the paid run of Needs → the probe keeps the existing closed local endpoint (`http://127.0.0.1:9`), so `codex exec` sends no request to a model and the run needed no consent; the SessionStart hook fires before the first model request.
- apply: how Codex records a trusted hook → read from Codex itself, not assumed: the app server's `hooks/list` gives each hook a `key` and `currentHash`, and `[hooks.state."<key>"] trusted_hash = <currentHash>` in `config.toml` is the form the owner's real `config.toml` holds; untrusted, the no-op hook did not run, trusted it ran.
- apply: the registry entry is updated in `solo_sdd/providers.py` by hand from the probe line, as for every earlier capability; the probe prints and compares, it does not rewrite the source.
- apply: the hook copies go into `~/.codex/hooks/` with the agent choice (like `~/.claude/hooks/`, also by `sync.py push`), gated by the Codex `hooks` capability through `needs` in `targets.json`; only the `hooks.json` entries wait for `--hooks` (or hooks already connected).
- apply: every `hooks.json` entry that runs `~/.codex/hooks/work_hooks.py` counts as solo-sdd's, so the hand-made entries are taken over, not doubled; the commands keep the hand file's exact text (absolute path in single quotes, same matcher and timeouts).
- apply: the Codex Stop reader takes only `event_msg` user entries (`user_message`, `item_completed` of a `UserMessage`); `response_item` user messages also carry the AGENTS.md and environment text Codex injects, so they are not the user.
- apply: `uninstall` and `uninstall --hooks` remove the Codex entries too, and `uninstall --purge` refuses while they are recorded, as for the Claude hooks; `solo-sdd settings` takes its refusal from the same `cli.hooks_refusal`.
- apply: a choice without `claude` while the Claude hooks are connected stays refused even with a confirmed codex (the Claude settings would point at removed copies).
- apply: `tests/test_cli.py` `test_hooks_without_claude` removed: its scenario (MODIFIED) is checked with an unverified codex in `tests/test_providers.py` `InstallForChosenAgents`; with a confirmed codex the old command now succeeds.
