# Proposal

## Why

Codex sessions on this computer run a hook copy that solo-sdd neither lays out nor knows about. `~/.codex/hooks.json` calls `~/.codex/hooks/work_hooks.py`, a hand copy from 2026-10-15 that `targets.json` does not name: it checks every final reply for Russian whatever `reply.language` says. That copy made the 5 wasted turns of 2026-11-10 to 2026-11-12, when the owner asked for an English text in Codex, and no fix in `global/work_hooks.py` reaches it after `sync.py push`. The provider registry keeps Codex `hooks` as `unverified` (on 0.159.2 a no-op hook in a temporary `CODEX_HOME` did not run), and `install --agents codex --hooks` is refused; yet the real Codex runs these hooks, so the probe misses a step Codex needs (expected: the hook trust Codex records in `config.toml`; not confirmed until the probe runs here).

## What Changes

- The provider probe for Codex trusts its no-op hook the way Codex records trusted hooks and records the Codex version as the `hooks` capability when the hook ran; when it did not, the capability stays `unverified` and the probe prints why.
- With the Codex `hooks` capability confirmed, `solo-sdd install --hooks` for a choice with `codex` lays out `global/work_hooks.py` and `global/model-policy.json` into `~/.codex/hooks/` and writes the `guard`, `context`, `stop` and `end` entries into `~/.codex/hooks.json` once, keeping foreign entries and backing the file up first.
- A hand copy in `~/.codex/hooks/` that differs from the source is a foreign copy: kept and named until `install --replace-foreign`, as for any other target.
- The Stop hook reads the last user message from a Codex transcript too, so a requested translation passes in Codex as in Claude Code.
- `solo-sdd doctor` prints `ok agent codex` with hooks once they are laid out.

## Capabilities

### New Capabilities

### Modified Capabilities
- `agent-providers`: Install for chosen agents is modified (Codex hooks allowed once confirmed); Codex hook probe and Codex hook layout are added.

## Impact

- `solo_sdd/providers.py`, `solo_sdd/hooks.py`, `solo_sdd/layout.py`, `solo_sdd/doctor.py`, `targets.json`
- `global/work_hooks.py`
- `docs/agents.md`, `docs/hooks.md`
- `tests/stands/provider-probe.py`, `tests/stands/codex-hooks.py` (new), `tests/test_providers.py`, `tests/test_work_hooks.py`

## Out of Scope

- The language check itself and the question window guard: `reply-language-requests`.
- Trusting the laid-out hooks in the owner's real `~/.codex/config.toml` and replacing the hand copy there: the owner's step, named in the report.
- Codex subagent or worktree guards beyond the four entries the hand copy already has.

## Depends On

reply-language-requests

## Source

The owner, 2026-11-15, on the weekly review (translated from Russian), on the language hook: "Let's do it as proposed"; the proposal included "check that Codex hooks.json calls the same code, and that the edit reaches Codex after sync.py push".
