# Proposal

## Why

A person who wants to configure a project today reads `docs/settings.md` next to `solo-sdd config list`: the command prints only `<key> <value> <source>`, with no word about what a key does, which values it takes, its default or its team default. An interactive settings screen (`settings-tui`) needs the same facts from the package, not from a docs page, and `docs/settings.md` must not drift from them.

## What Changes

- Every registered key and every pattern key of `solo_sdd/settings.py` gets a group (`process`, `delivery`, `dispatch`, `agents`, `integrations`, `checklists`) and a one-sentence description of what it changes, kept in the package outside the `settings:begin`/`settings:end` block (the hook scripts do not need them).
- `solo-sdd config describe [<key>]`: per key the group, the description, the type with its allowed values, the default, the team default, the value in effect and its source; an unknown key is refused with exit 1 and the known keys.
- `solo-sdd config list --json`: the same fields for every key as a list of objects; plain `config list` keeps its output byte for byte.
- `docs/settings.md` names `config describe` and `config list --json`; its key table stays on the registry keys by the existing `Readme` test of `tests/test_settings.py`.
- Consumers: `config describe` and `config list --json` for a person and an agent, and the settings screen of `settings-tui`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `settings`: Key descriptions and Describe a setting are added.

## Impact

- `solo_sdd/settings.py`, `solo_sdd/cli.py` (the command list line of `config`)
- `docs/settings.md`, `docs/cli.md`
- `tests/test_settings.py`, `tests/affected.json`

## Out of Scope

- The interactive settings screen: `settings-tui`.
- Integrations and checklists on the screen: `settings-tui-lists`.
- Machine settings (agents, hooks, global rules) on the screen: `settings-tui-home`.
- What bare `solo-sdd` does on a terminal: `cli-menu`.
- Translating the descriptions into the reply language.

## Depends On

none

## Source

The owner, 2026-11-14 (translated from Russian): "I want a CLI in which I can configure solo-sdd for each project; everything that can be configured now must be in the CLI; the configuration must be detailed and convenient".
