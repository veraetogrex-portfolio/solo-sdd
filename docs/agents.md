# Supported agents

<!-- generated from solo_sdd/providers.py; tests/test_providers.py compares -->
| Agent | Detected by | Skills | Global rules | Project rules | Hooks | Subagents |
|---|---|---|---|---|---|---|
| `claude` | `claude` in PATH or `~/.claude` | `~/.claude/skills` | `~/.claude/CLAUDE.md` | `CLAUDE.md` | 2.1.312 | 2.1.312 |
| `codex` | `codex` in PATH or `~/.codex` | `~/.codex/skills` | `~/.codex/AGENTS.md` | `AGENTS.md` | unverified | 0.159.2 |
| `cursor` | `cursor-agent` in PATH or `~/.cursor` | unverified | unverified | unverified | unverified | unverified |
| `other` | always | `~/.agents/skills` | `~/AGENTS.md` | `AGENTS.md` | unverified | unverified |

`install --agents claude,codex` deploys for the named agents plus `other`; without `--agents` it keeps the choice of the last install, and a first install takes the detected agents plus `other`. A deployment from a version without the choice counts as `claude`, `codex`, `other`. The choice is kept in `~/.local/share/solo-sdd/state.json`; `status`, `update`, `sync.py push` and `doctor` follow it, `uninstall` removes the copies of every agent.

Dropping an agent from the choice removes its unchanged copies; an edited copy is kept and named. An unknown name exits with code 1 and the known names, no file changes; so does a choice without `claude` with `--hooks` or while the hooks are connected (`uninstall` removes them). A skill that needs capabilities gets deployed only where they are present: `spec-dispatch` needs subagents and hooks (`needs` in `targets.json`).

`doctor` prints `ok agent <name>` when hooks and subagents are both present, else `warn agent <name>: no <capability>: <what is not enforced>`. The versions are those `tests/stands/provider-probe.py` ran: subagents from `claude --help` and `codex features list`, hooks from a no-op hook in a temporary home; `unverified` means the probe did not see it work.

`cursor` has not been probed: no Cursor was available, so `install --agents cursor` deploys only the `other` files, says that project rules come from `solo-sdd init`, `doctor` prints `warn agent cursor: unverified: skills, project rules: …` before the `no hooks` and `no subagents` gaps, and `tests/stands/provider-probe.py cursor` prints `not run` for each capability, installing nothing.

A file laid out into skill folders (the bundled copies under `integrations/`) is added to `targets.json["files"]` as one line naming each skill and the path inside its folder, never an agent folder: `"integrations/antislop/antislop.md": {"skills": {"ui-check": "antislop/core.md", "copy-check": "antislop/core.md"}}`. It goes to every agent that skill's `SKILL.md` goes to and to no other, so a new agent needs no edit there. A line naming a skill absent from `skills` stops `install`, `status` and `sync.py push` with code 1 and the line named, nothing written.
