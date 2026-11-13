"""Agents solo-sdd deploys for: detection, skill root, rules files, capabilities.

A capability maps to the agent version it was checked on (tests/stands/provider-probe.py) or "unverified";
`hooks` counts only where a no-op hook ran in the probe.
"""
import os, shutil

PROVIDERS = {
    "claude": {
        "detect": ("claude", "~/.claude"),
        "skills": "~/.claude/skills",
        "rules": "~/.claude/CLAUDE.md",
        "project_rules": "CLAUDE.md",
        "owns": ("~/.claude/",),
        "caps": {"hooks": "2.1.312", "subagents": "2.1.312"},
    },
    "codex": {
        "detect": ("codex", "~/.codex"),
        "skills": "~/.codex/skills",
        "rules": "~/.codex/AGENTS.md",
        "project_rules": "AGENTS.md",
        "owns": ("~/.codex/",),
        # 0.159.2 lists the `hooks` feature, but a no-op hook in a temporary CODEX_HOME did not run
        "caps": {"hooks": "unverified", "subagents": "0.159.2"},
    },
    "cursor": {
        # not probed: no Cursor was available (2026-11-09); skills, rules and capabilities wait for
        # `tests/stands/provider-probe.py cursor` on an installed version. Until then it gets only the `other` files.
        "detect": ("cursor-agent", "~/.cursor"),
        "skills": None,
        "rules": None,
        "project_rules": None,
        "owns": ("~/.cursor/",),
        "caps": {"hooks": "unverified", "subagents": "unverified"},
    },
    "other": {
        "detect": None,  # any agent that reads ~/.agents/skills and AGENTS.md: always chosen
        "skills": "~/.agents/skills",
        "rules": "~/AGENTS.md",
        "project_rules": "AGENTS.md",
        "owns": ("~/.agents/", "~/AGENTS.md"),
        "caps": {"hooks": "unverified", "subagents": "unverified"},
    },
}
ALL = tuple(PROVIDERS)
LEGACY = ("claude", "codex", "other")  # the choice of a state written before the choice was stored
GAPS = {"hooks": "CLAIM guard, secret guard and stop check not enforced",
        "subagents": "spec-dispatch and independent review subagents not available"}


def has(name, cap):
    return PROVIDERS[name]["caps"].get(cap, "unverified") != "unverified"


def found(name, home=None):
    """Why the provider counts as installed (`claude in PATH`, `~/.claude`, `always`), None when it is not found."""
    det = PROVIDERS[name]["detect"]
    if det is None:
        return "always"
    if shutil.which(det[0]):
        return "%s in PATH" % det[0]
    return det[1] if os.path.isdir(os.path.join(home or os.path.expanduser("~"), det[1][2:])) else None


def detected(home=None):
    """Providers found by a command in PATH or their folder in home, plus `other`; registry order."""
    return [name for name in PROVIDERS if found(name, home)]


def parse(text):
    """Chosen names from `a,b` plus `other`, registry order; ValueError naming the known ones."""
    names = [n.strip() for n in text.split(",") if n.strip()]
    bad = [n for n in names if n not in PROVIDERS]
    if bad or not names:
        raise ValueError("unknown agent %s; known: %s" % (", ".join(bad) or repr(text), ", ".join(ALL)))
    return [n for n in ALL if n in names or PROVIDERS[n]["detect"] is None]


def owner(key):
    """The provider whose folder holds the copy at key (a path from ~), None for a shared copy."""
    for name, p in PROVIDERS.items():
        if any(key == o or key.startswith(o) for o in p["owns"]):
            return name
    return None


def probed(name):
    """False for a provider whose skill root no probe has recorded yet: it gets only the `other` files."""
    return PROVIDERS[name]["skills"] is not None


def unprobed():
    """What a provider without a recorded skill root gets instead (doctor and install say the same)."""
    return "unverified: skills, project rules: skills go to %s, project rules come from solo-sdd init" % PROVIDERS["other"]["skills"]


def row(name):
    """Doctor line (level, detail) for one chosen agent."""
    caps = PROVIDERS[name]["caps"]
    missing = [c for c in GAPS if not has(name, c)]
    seen = probed(name)
    if not missing and seen:
        return "ok", ", ".join("%s (%s)" % (c, caps[c]) for c in GAPS)
    return "warn", "; ".join(([] if seen else [unprobed()]) + ["no %s: %s" % (c, GAPS[c]) for c in missing])


def table():
    """The "Supported agents" table of README.md."""
    lines = ["| Agent | Detected by | Skills | Global rules | Project rules | Hooks | Subagents |", "|---|---|---|---|---|---|---|"]
    for name, p in PROVIDERS.items():
        det = "always" if p["detect"] is None else "`%s` in PATH or `%s`" % p["detect"]
        cap = lambda c: p["caps"].get(c, "no")
        val = lambda k: "`%s`" % p[k] if p[k] else "unverified"
        lines.append("| `%s` | %s | %s | %s | %s | %s | %s |" % (
            name, det, val("skills"), val("rules"), val("project_rules"), cap("hooks"), cap("subagents")))
    return "\n".join(lines) + "\n"
