#!/usr/bin/env python3
"""Dispatcher queue: which open changes to launch now.

Run: sdd_dispatch_plan.py <MAIN> [--running id1,id2,...] [--waiting id1,id2,...] [--ignore-dep id:name]...
        [--shared path]...

--running: orchestrators at work; --waiting: waiting for merge (status accepted, the branch went to CI).
An id in both lists is running; an id that is not an open change is dropped.

Ready: no CLAIM or WAITING, no branch <delivery.branch-prefix><id> (default change/<id>), every Depends On archived, the change folder committed
(otherwise the reason «not committed»: a worktree made from a commit would not see it).
Reasons in order: branch («not merged»), CLAIM, WAITING, «not committed», dependencies.
Dependencies: a name that is neither an open change nor archived is «unknown dependency: <name>»
(«(a spec, not a change)» if <root>/specs/<name> exists), then after «; » «depends on <open ones>».
The value none, -, — (any case, with .,:; after it) first in the Depends On item means no dependencies.
--ignore-dep id:name does not count the name as a dependency of that change; --shared path adds a shared path (like «Shared:»).
CLAIM abandoned: session=<id> and the session files in ~/.claude/hook-state have not changed for 60 minutes or are missing;
a label without an id is 12 hours old or more. The script does not remove the label: the owner decides.
Process root: solo-sdd/ if it holds project.md, specs/ or changes/, else openspec/ (then the last line is the import hint).
Artifacts outside git: if the process root, AGENTS.md or CLAUDE.md is ignored, the line «Artifacts outside git: <paths>» is printed.
A hard conflict of two changes: a shared requirement (capability, name) or a shared file from Impact.
Conflicts are checked against running, waiting-for-merge and already granted changes.
Shared paths give no conflict: COMMON and the «Shared:» item of the AGENTS.md section «Working copy»;
a path ending in / makes every file under it shared. Pairs launched over a shared path are «together:» lines.
Limit: dispatch.limit of solo-sdd/config, else the «Orchestrators: <number>» item of the AGENTS.md section «Working copy»,
else the settings default (2). A broken solo-sdd/config: exit 1 with the file, the line and the reason.
Places are taken by running changes and only by those waiting for merge beyond the limit: free =
limit - running - max(0, waiting for merge - limit). First line: «limit: N, running: K, waiting for merge: W».
Order: by the number of open changes that depend on this one (directly or through a chain), then by id.
Second line: «loopback: ok» or «loopback: blocked: <error>»: a listen and a connect on 127.0.0.1, once per call,
the timeout LOOPBACK_TIMEOUT; a sandbox may deny them. The item «Loopback: needed» of the AGENTS.md section
«Commands» or «Working copy» (the project's tests need local sockets) makes it «loopback: blocked (needed by the project): <error>».
Third line: «delivery: <local|pr> (<source>), merge: <squash|merge|rebase> (<source>)»: each from solo-sdd/config (file),
else the «Mode:» and «Merge:» items of the AGENTS.md section «Delivery» with an allowed value (AGENTS.md), else the team
default under mode: team (mode), else the settings default (default: nothing names it).
"""
import os
import re
import socket
import subprocess
import sys
import time

COMMON = {"AGENTS.md", "CLAUDE.md", "docs/waiting.md", "CHANGELOG.md"}
NO_DEPS = {"none", "-", "—"}
STATE = os.path.join(os.path.expanduser("~"), ".claude", "hook-state")
SESSION_SILENCE = 3600
IMPORT_HINT = "process in openspec/: run solo-sdd import openspec"
LABEL_AGE = 12 * 3600
LOOPBACK_TIMEOUT = 1.0


# settings:begin
# solo-sdd/config: one `key: value` per line, lines starting with # are comments, list values are separated by commas.
SETTINGS_FILE = "solo-sdd/config"
# key -> (type: choice | exts | int | ints | lang | list | model | names | paths | text, allowed values (None: any), default, default under `mode: team` (None: the same));
# a key with the default "" takes an empty value, read as "not set"
REGISTRY = {
    "mode": ("choice", ("solo", "team"), "solo", None),
    "delivery.mode": ("choice", ("local", "pr"), "local", "pr"),
    "delivery.merge": ("choice", ("squash", "merge", "rebase"), "squash", None),  # a pull request
    "delivery.local-merge": ("choice", ("merge", "squash", "rebase"), "merge", None),  # sdd-dispatch.py land-local
    "delivery.merge-by": ("choice", ("agent", "human"), "agent", "human"),  # who merges into the base
    "delivery.base": ("choice", None, "", None),  # "": the remote's default branch
    "delivery.promote": ("list", None, "", None),  # branches after the base in order; `release/*`: the newest by version
    "delivery.pr-title": ("text", None, "the change name", None),  # the PR title rule ship and spec-dispatch follow
    "delivery.deploy": ("text", None, "no", None),  # what a push or merge deploys, and where
    "delivery.owner-only": ("paths", None, "", None),  # globs a merge waits for the owner on, besides .github/workflows/**
    "delivery.ci-timeout": ("int", None, "1200", None),  # seconds sdd-pr.py wait gives CI as a whole
    "delivery.ci-stuck": ("int", None, "300", None),  # seconds a required check may stay missing or not started
    "delivery.ci-no-checks": ("int", None, "180", None),  # seconds a PR may show no checks at all
    "delivery.require-ci": ("choice", ("on", "off"), "on", None),  # off: a PR without checks merges (CI: none)
    "delivery.code-scanning": ("choice", ("gate", "warn", "off"), "gate", None),  # open alerts: code 8, a warning, not asked
    "delivery.delete-branch": ("choice", ("on", "off"), "on", None),  # off: a merged PR keeps its branch
    "delivery.draft": ("choice", ("on", "off"), "off", None),  # on: a PR opens as a draft, marked ready before the merge
    "delivery.branch-prefix": ("choice", None, "change/", None),  # a change branch is <prefix><id>
    "delivery.plan-prefix": ("choice", None, "plan/", None),  # the spec-plan branch is <prefix><first id>
    "dispatch.limit": ("int", None, "2", None),
    "process.review-rounds": ("int", None, "5", None),
    "process.light-path": ("choice", ("on", "off"), "on", None),  # off: every code edit goes through a change
    "process.light-path.max-files": ("int", None, "3", None),
    "process.max-tasks": ("int", None, "10", None),  # solo-sdd validate: tasks of one change
    "process.bugfix-max-tasks": ("int", None, "5", None),  # spec-plan, spec-analyze: a bug fix takes the smaller limit
    "process.requirement-max-chars": ("int", None, "500", None),  # solo-sdd validate: one requirement text
    "process.audit-every": ("int", None, "5", None),  # spec-next proposes spec-audit at a multiple of the archive count
    "process.analyze": ("choice", ("on", "off"), "on", None),  # off: spec-plan and spec-next skip spec-analyze
    "commit.light-prefix": ("text", None, "light:", None),  # a light commit subject starts with it, as plain text
    "project.stage": ("choice", ("demo", "prod"), "", None),  # "": the global rules decide by the task
    "artifacts.language": ("lang", None, "en", None),  # the prose of the change artifacts
    "lessons.write": ("choice", ("on", "off"), "on", None),  # off: a lesson goes to the report, not into AGENTS.md
    "lessons.max-lines": ("int", None, "20", None),  # the most lines of ## Lessons
    "reply.language": ("choice", ("ru", "en", "off"), "off", None),
    "agents": ("list", ("claude", "codex", "cursor", "other"), "claude, codex, other", None),
    "rules.scope": ("choice", ("project", "global"), "project", None),  # project: init writes the rules block into AGENTS.md
    "agents.orchestrator-model": ("model", None, "opus", None),  # spec-dispatch; work_hooks.py keeps it in the main list
    "agents.review-model": ("model", None, "", None),  # "": the session's main model; work_hooks.py: the main list
    "agents.lookup-model": ("model", None, "haiku", None),  # work_hooks.py: the cheap list
    "agents.test-model": ("model", None, "haiku", None),  # paid product calls in tests; the Test model allowlist bounds it
    "agents.dispatcher-effort": ("choice", ("low", "medium", "high"), "low", None),
    "agents.executor": ("choice", ("self", "codex"), "self", None),  # codex: as if the owner named codex-orchestration
    "integrations": ("names", None, "", None),  # the enabled integrations, by folder name (solo_sdd/integrations.py)
    "integrations.off": ("names", None, "", None),  # the bundled integrations switched off, by folder name
    "git.ignore": ("paths", None, ".claude/worktrees/, .env, .env.*, !.env.example", None),  # solo-sdd ignore --write
    "hooks.stop.uncommitted": ("choice", ("on", "off"), "on", None),  # work_hooks.py stop: uncommitted session edits
    "hooks.stop.unarchived": ("choice", ("on", "off"), "on", None),  # stop: every task checked, not archived
    "hooks.stop.open-pr": ("choice", ("on", "off"), "on", None),  # stop: an open PR; merge-by human keeps it off
    "hooks.stop.ui-check": ("choice", ("on", "off"), "on", None),  # stop: an interface edit without a browser check
    "hooks.auto-claim": ("choice", ("on", "off"), "on", None),  # guard: a tasks.md tick creates CLAIM
    "ui.extensions": ("exts", None, ".html, .htm, .css, .scss, .sass, .less, .tsx, .jsx, .vue, .svelte", None),
    "ui.widths": ("ints", None, "1280, 390", None),  # ui-check and spec-plan
}
LIST_KINDS = ("exts", "ints", "list", "paths", "names")
# the lowest value of an int key, 1 when not named: a task limit under 3 fits no change (Acceptance holds two tasks)
INT_MIN = {"process.max-tasks": 3, "process.bugfix-max-tasks": 3, "process.requirement-max-chars": 100}
# pattern keys: <name> is lowercase letters, digits and -, not starting with -; set keys show in `config list` as `file`
PATTERNS = {
    "checklist.<name>.paths": ("paths", None, "", None),  # globs of the files a person checks by the list
    "checklist.<name>.file": ("path", None, "", None),  # a markdown file of `- [ ]` items, from the repository root
}
NAME_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789-"
MODEL_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_[]"
TEXT_MAX = 200
# the Delivery items of AGENTS.md read as the old source of a text or paths key: item -> key
DELIVERY_ITEMS = (("PR title:", "delivery.pr-title"), ("Deploy:", "delivery.deploy"), ("Owner only:", "delivery.owner-only"))
# the lines of solo-sdd/project.md read as the old source of a key, source `project.md`: line start -> key
PROJECT_FILE = "solo-sdd/project.md"
PROJECT_LINES = (("Mode:", "project.stage"), ("Language:", "artifacts.language"))
OLD_SOURCE = dict((key, "project.md") for _, key in PROJECT_LINES)  # any other old source key: AGENTS.md


class SettingsError(ValueError):
    pass


IGNORE_KEY = "git.ignore"
# the process paths no git.ignore item may hide (a trailing / marks a folder, or a path that may be either); placeholders:
# <capability> any folder name, <change> any but archive (the change archive may stay out of git), <top> any but changes,
# <...> one or more names of any kind
KEPT = ("AGENTS.md", "CLAUDE.md", "solo-sdd/", "solo-sdd/project.md", "solo-sdd/analyze.md", "solo-sdd/config",
        "solo-sdd/rules-block", "solo-sdd/integrations/", "solo-sdd/specs/", "solo-sdd/specs/<capability>/",
        "solo-sdd/specs/<capability>/spec.md", "solo-sdd/changes/", "solo-sdd/changes/<change>/",
        "solo-sdd/<top>/", "solo-sdd/<top>/<...>/", "solo-sdd/changes/<change>/<...>/") + tuple(
    "solo-sdd/changes/<change>/" + f for f in ("proposal.md", "design.md", "tasks.md", "verification.md", "CLAIM",
                                               "WAITING", "specs/", "specs/<capability>/", "specs/<capability>/spec.md"))
NOT_NAMED = {"<change>": "archive", "<top>": "changes"}


def ignore_part_re(part):
    """A regular expression of one gitignore pattern part: * and ? within a name; a [...] class counts as any one
    character. Matched without case, as git does on a case-insensitive file system: a superset of git's match, so
    the check below never misses what git hides."""
    out, i = "", 0
    while i < len(part):
        c = part[i]
        if c == "[":
            j = i + (2 if part[i + 1:i + 2] in ("!", "^") else 1) + 1
            j = part.find("]", j)
            out, i = out + "[^/]", (j + 1 if j > 0 else i + 1)
            continue
        out, i = out + ("[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c)), i + 1
    return out


def ignore_hits(parts, names, named):
    """Whether the parts of an anchored pattern match the path names as git's wildmatch does; named: a placeholder
    (<...>) matches a part, except the literal name NOT_NAMED gives it, and <...> any rest of the parts."""
    if not parts:
        return not names
    if parts[0] == "**":
        return bool(names) if len(parts) == 1 else any(ignore_hits(parts[1:], names[k:], named) for k in range(len(names) + 1))
    if not names:
        return False
    name = names[0]
    if name == "<...>":
        return named
    if name.startswith("<"):
        ok = named and parts[0].lower() != NOT_NAMED.get(name, "/")
    else:
        ok = re.fullmatch(ignore_part_re(parts[0]), name, re.I) is not None
    return ok and ignore_hits(parts[1:], names[1:], named)


def ignore_hides(item, paths=KEPT):
    """The first of paths a git.ignore item hides by git's matching (a matched folder hides what is under it), or
    None; a ! item re-includes and hides none. A placeholder counts only for a pattern of two or more names."""
    if item.startswith("!"):
        return None
    folder = item.endswith("/")
    body = item[:-1] if folder else item
    parts = ["**" if p and set(p) == {"*"} and len(p) > 1 else p for p in body.split("/")]
    anchored = "/" in body
    named = anchored and sum(p != "**" for p in parts) > 1
    for path in paths:
        names = path.rstrip("/").split("/")
        if folder and not path.endswith("/"):
            continue
        if anchored and ignore_hits(parts, names, named) or not anchored and not names[-1].startswith("<") and \
                re.fullmatch(ignore_part_re(body), names[-1], re.I):
            return path
    return None


def ignore_refusal(key, item, hides):
    return "%s item %s %s; solo-sdd/ (but solo-sdd/changes/archive/), AGENTS.md and CLAUDE.md stay in git" % (
        key, item, hides if hides.startswith("starts") else "hides " + hides)


def bad_name(name):
    """A value of a key without a fixed list git would refuse or read as an option (`*` stays: release/*)."""
    return name.startswith(("-", "+")) or ".." in name or any(c in name for c in " \t~^:?[\\")


def bad_path(path):
    """A path value outside the repository or one the lists would split: absolute, `..`, spaces, backslashes."""
    return path.startswith(("/", "-")) or ".." in path.split("/") or any(c in path for c in " \t\\")


def good_name(name):
    """A <name>: lowercase ASCII letters, digits and -, not starting with -."""
    return bool(name) and name[0] != "-" and all(c in NAME_CHARS for c in name)


def entry(key, registry=REGISTRY):
    """The registry tuple of a fixed or a pattern key; None when the key is unknown."""
    if key in registry:
        return registry[key]
    for pattern, value in PATTERNS.items():
        head, tail = pattern.split("<name>")
        name = key[len(head):len(key) - len(tail)] if key.startswith(head) and key.endswith(tail) else ""
        if good_name(name):
            return value
    return None


def check_value(key, value, registry=REGISTRY):
    """The normalized value, or SettingsError naming the allowed values."""
    kind, allowed, default = entry(key, registry)[:3]
    v = value.strip()
    if kind == "text":
        if not v or not v.isprintable() or len(v) > TEXT_MAX:
            raise SettingsError("%s takes one line of printable characters, at most %d characters, not %r"
                                % (key, TEXT_MAX, v if len(v) <= 60 else v[:60] + "..."))
        return v
    if kind == "model":
        if v and all(c in MODEL_CHARS for c in v) or not v and default == "":
            return v
        raise SettingsError("%s takes one model name of ASCII letters, digits, ., -, _, [ and ], not %r" % (key, v))
    if kind == "lang":
        if 2 <= len(v) <= 3 and v.isascii() and v.isalpha() and v.islower():
            return v
        raise SettingsError("%s takes a language code of 2 or 3 lowercase letters (ISO 639), not %r" % (key, v))
    if kind == "int":
        low = INT_MIN.get(key, 1)
        if not (v.isascii() and v.isdigit()) or int(v) < low:
            raise SettingsError("%s takes a whole number from %d, not %r" % (key, low, v))
        return str(int(v))
    items = [i.strip() for i in v.split(",")] if kind in LIST_KINDS else [v]
    items = [i for i in items if i]
    if not items and (default == "" or key == IGNORE_KEY):  # an empty git.ignore removes the block
        return ""
    paths = kind in ("path", "paths")
    for i in items if key == IGNORE_KEY else ():
        hides = "starts with #: git reads it as a comment" if i.startswith("#") else ignore_hides(i)
        if hides:
            raise SettingsError(ignore_refusal(key, i, hides))
    bad = [i for i in items if (bad_path(i) if paths else not good_name(i) if kind == "names" else
                                not re.fullmatch(r"\.[A-Za-z0-9]+", i) if kind == "exts" else
                                not (i.isascii() and i.isdigit() and int(i) >= 1) if kind == "ints" else
                                i not in allowed if allowed else bad_name(i))]
    if kind == "names" and len(set(items)) < len(items):
        raise SettingsError("%s takes each name once, not %r" % (key, v))
    if bad or not items:
        what = ", ".join(allowed) if allowed else (
            "relative paths (no spaces, \\ or .., not starting with / or -)" if paths else
            "names (lowercase letters, digits and -, not starting with -)" if kind == "names" else
            "file extensions (. and ASCII letters or digits)" if kind == "exts" else
            "whole numbers from 1" if kind == "ints" else
            "branch names (no spaces, ~^:?[\\ or .., not starting with - or +)") + (
            ", separated by commas" if kind in LIST_KINDS else "")
        raise SettingsError("%s takes %s, not %r" % (key, what, v))
    return ", ".join(str(int(i)) if kind == "ints" else i for i in items)


def parse_settings(text, registry=REGISTRY, name=SETTINGS_FILE):
    """{key: value} of the file text; SettingsError names <name>:<line> and the reason."""
    found = {}
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        key, colon, value = s.partition(":")
        key, where = key.strip(), "%s:%d" % (name, n)
        if not colon or not key:
            raise SettingsError("%s: not \"key: value\": %s" % (where, s))
        if entry(key, registry) is None:
            raise SettingsError("%s: unknown key %s; known: %s" % (where, key, ", ".join(list(registry) + list(PATTERNS))))
        if key in found:
            raise SettingsError("%s: %s is set twice" % (where, key))
        try:
            found[key] = check_value(key, value, registry)
        except SettingsError as e:
            raise SettingsError("%s: %s" % (where, e))
    return found


def effective(found, registry=REGISTRY, agents=None):
    """{key: (value, source)}: source `file`, else `AGENTS.md` or `project.md` (agents: agents_delivery, OLD_SOURCE),
    else `mode` (the team default under `mode: team`), else `default`."""
    team = found.get("mode") == "team"
    agents = agents or {}
    out = {}
    for key, (_, _, default, team_default) in registry.items():
        if key in found:
            out[key] = (found[key], "file")
        elif key in agents:
            out[key] = (agents[key], OLD_SOURCE.get(key, "AGENTS.md"))
        elif team and team_default is not None:
            out[key] = (team_default, "mode")
        else:
            out[key] = (default, "default")
    out.update((key, (value, "file")) for key, value in found.items() if key not in registry)  # pattern keys
    return out


def read_settings_text(root):
    """The file text of the project at root, "" when there is no file."""
    try:
        with open(os.path.join(root, SETTINGS_FILE), encoding="utf-8", newline="") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def project_lines(root, registry=REGISTRY):
    """({key: value}, [line left out]) of solo-sdd/project.md at root, the old source of the PROJECT_LINES keys: the
    first line starting with each item, trimmed, a final dot dropped; an empty one counts as none, a value check_value
    refuses is left out and its line named with the reason; a file that cannot be opened: ({}, [])."""
    try:
        with open(os.path.join(root, PROJECT_FILE), encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return {}, []
    out, bad, seen = {}, [], set()
    for ln in lines:
        for item, key in PROJECT_LINES:
            v = ln[len(item):].strip() if ln.startswith(item) and key not in seen and key in registry else ""
            v = v[:-1].rstrip() if v.endswith(".") else v
            if not v:
                continue
            seen.add(key)
            try:
                out[key] = check_value(key, v, registry)
            except SettingsError as e:
                bad.append("%s is left out: %s" % (ln.strip(), e))
    return out, bad


def agents_delivery(root, registry=REGISTRY):
    """{key: value} of the old sources at root: the project_lines values, and the «## Delivery» section of AGENTS.md:
    the first allowed «Mode:» and «Merge:» items, the first non-empty «PR title:» and «Deploy:» texts trimmed and as
    written, and the backquoted patterns of every «Owner only:» item; a file that cannot be opened adds nothing."""
    out, inside = dict(project_lines(root, registry)[0]), False
    try:
        with open(os.path.join(root, "AGENTS.md"), encoding="utf-8", errors="replace") as f:  # other readers own the encoding
            lines = f.read().splitlines()
    except OSError:
        return out
    for ln in lines:
        if ln.startswith("## "):
            inside = ln.strip() == "## Delivery"
            continue
        s = ln.strip().lstrip("-* ").strip()
        for key, item in (("delivery.mode", "Mode:"), ("delivery.merge", "Merge:")):
            words = s[len(item):].split() if inside and s.startswith(item) else []
            v = words[0].strip("`.,;").lower() if words else ""
            if v in registry[key][1]:
                out.setdefault(key, v)
        for item, key in DELIVERY_ITEMS if inside else ():
            if s.startswith(item) and key == "delivery.owner-only":
                found = [p for p in re.findall(r"`([^`]*)`", s) if p.strip()]
                if found:
                    out[key] = ", ".join(([out[key]] if key in out else []) + found)
            elif s.startswith(item) and s[len(item):].strip():
                out.setdefault(key, s[len(item):].strip())
    return out


def read_settings(root, registry=REGISTRY):
    """Settings in effect of the project at root; no file means all defaults; a broken file raises SettingsError."""
    return effective(parse_settings(read_settings_text(root), registry), registry, agents_delivery(root, registry))
# settings:end


# keywords:begin
# Pre-English AGENTS.md headings and items -> English. The old names live only here, as \u escapes,
# so the repository holds no Cyrillic letter. Scripts read only the English names.
OLD_SECTIONS = {
    "\u0420\u0430\u0431\u043e\u0447\u0430\u044f \u043a\u043e\u043f\u0438\u044f": "Working copy",
    "\u041f\u043e\u0441\u0442\u0430\u0432\u043a\u0430": "Delivery",
    "\u041a\u043e\u043c\u0430\u043d\u0434\u044b": "Commands",
}
OLD_ITEMS = {  # English section -> ((old item, English item), ...)
    "Working copy": (
        ("\u041f\u0443\u0442\u0438:", "Paths:"),
        ("\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430:", "Prepare:"),
        ("\u041f\u043e\u0441\u043b\u0435 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f:", "After refresh:"),
        ("\u041e\u0431\u0449\u0438\u0435:", "Shared:"),
        ("\u041e\u0440\u043a\u0435\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u043e\u0432:", "Orchestrators:"),
        ("\u041e\u0440\u043a\u0435\u0441\u0442\u0440\u0430\u0442\u043e\u0440: \u0441\u0430\u043c", "Orchestrator: solo"),
    ),
    "Delivery": (
        ("\u0420\u0435\u0436\u0438\u043c:", "Mode:"),
        ("\u0417\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a PR:", "PR title:"),
        ("\u0414\u0435\u043f\u043b\u043e\u0439:", "Deploy:"),
        ("\u0422\u043e\u043b\u044c\u043a\u043e \u0432\u043b\u0430\u0434\u0435\u043b\u0435\u0446:", "Owner only:"),
    ),
    "Commands": (("\u0422\u0435\u0441\u0442\u044b", "Tests"),),  # row of the commands table
}


def migrate_agents(text):
    """(text with the old headings and items renamed to English, English names found in order).

    Items are renamed only inside their section, at the start of a list item or a table row;
    every other byte stays as it was."""
    out, found, section = [], [], None
    for line in re.split(r"(?<=\n)", text):  # lines end only at \n, as in the file
        if line.startswith("## "):
            title = line[3:].strip()
            if title in OLD_SECTIONS:
                line = line.replace(title, OLD_SECTIONS[title], 1)
                title = OLD_SECTIONS[title]
                found.append(title)
            section = title
        else:
            for old, new in OLD_ITEMS.get(section, ()):
                m = re.match(r"(\s*(?:[-*]\s+|\|\s*))" + re.escape(old) + r"(?!\w)", line)
                if m:
                    line = m.group(1) + new + line[m.end():]
                    found.append(new)
                    break
        out.append(line)
    return "".join(out), list(dict.fromkeys(found))


def migrate_hint(path, found):
    """One line for a reader of an AGENTS.md with old keywords: the file, what was found, the command."""
    return "%s: pre-English keywords (%s) are ignored; run: solo-sdd migrate-agents %s" % (
        path, ", ".join(found), os.path.dirname(os.path.abspath(path)))
# keywords:end


def text(p):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def sections(src, title):
    """Lines of the "## title" section up to the next "## "."""
    out, inside = [], False
    for ln in src.splitlines():
        if ln.startswith("## "):
            inside = ln.strip() == "## " + title
        elif inside:
            out.append(ln)
    return out


def is_none(v):
    """The «no dependencies» value: none, -, — (with .,:;) or empty."""
    return v.rstrip(".,:;").lower() in NO_DEPS or v in ("", ".")


def parse_deps(lines):
    """Names from "Depends On": values in backquotes, else the first word of the item; notes in parentheses do not interfere."""
    deps = []
    for ln in lines:
        s = ln.strip().lstrip("-* ")
        vals = s.split("`")[1::2] or [v.split()[0] for v in s.split(",") if v.split()]
        head = s.split("`")[0].replace(",", " ").split()
        if head and is_none(head[0]):
            continue
        for i, v in enumerate(vals):
            v = v.strip()
            if is_none(v):
                if i == 0:
                    break
            elif re.fullmatch(r"[\w.-]+", v):
                deps.append(v)
    return deps


def is_file(v, main):
    if " " in v or "*" in v or v.endswith("/") or not ("/" in v or re.search(r"\.[A-Za-z0-9]+$", v)):
        return False
    return not os.path.isdir(os.path.join(main, v))


def is_common(v, common):
    """The path is named in common or lies under a directory from there (value ending in /)."""
    return v in common or any(p.endswith("/") and v.startswith(p) for p in common)


# A copy of a block of global/work_hooks.py (this script is deployed alone): edit it there, then run
# python3 scripts/sync_blocks.py.
# process-root:begin
TREE_MARKS = ("project.md", "specs", "changes")


def process_root(project):
    """`solo-sdd` when the project holds that tree (project.md, specs/ or changes/), else `openspec`, read until import.
    solo_sdd/process_format.py (find_tree) keeps the same rule in its own form."""
    return "solo-sdd" if any(os.path.exists(os.path.join(project, "solo-sdd", n)) for n in TREE_MARKS) else "openspec"
# process-root:end


def spec_names(main):
    """Names of the specs subfolders of the process root; no folder means empty."""
    d = os.path.join(main, process_root(main), "specs")
    try:
        return {n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n))}
    except OSError:
        return set()


def apply_ignores(changes, pairs):
    """A copy of changes without the pairs (id, name) in deps; other changes and missing ids are untouched."""
    pairs = set(pairs)
    return {cid: dict(c, deps=[d for d in c["deps"] if (cid, d) not in pairs])
            for cid, c in changes.items()}


def agents_section(main):
    """Shared paths and the limit (None without the item) from the «Working copy» section."""
    common, limit = set(COMMON), None
    agents = os.path.join(main, "AGENTS.md")
    src = text(agents)
    found = migrate_agents(src)[1]
    if found:
        print(migrate_hint(agents, found), file=sys.stderr)
    for ln in sections(src, "Working copy"):
        s = ln.strip().lstrip("-* ").strip()
        if s.startswith("Shared:"):
            common |= {v.lstrip("/") for v in s.split("`")[1::2] if v}
        elif s.startswith("Orchestrators:"):
            m = re.search(r"\d+", s)
            if m:
                limit = int(m.group())
    return common, limit


def loopback_needed(main):
    """The project declares that its tests need local sockets: «Loopback: needed» in «Commands» or «Working copy»."""
    src = text(os.path.join(main, "AGENTS.md"))
    for ln in sections(src, "Commands") + sections(src, "Working copy"):
        s = ln.strip()
        if s.startswith(("-", "*")) and re.match(r"loopback:\s*needed\b", s.replace("*", "").lstrip("- "), re.I):
            return True
    return False


def has_branch(main, cid, prefix="change/"):
    r = subprocess.run(["git", "-C", main, "branch", "--list", prefix + cid],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return bool(r.stdout.strip())


def uncommitted(main, cid):
    """The change folder has untracked or uncommitted files (status does not show ignored ones)."""
    r = subprocess.run(["git", "-C", main, "status", "--porcelain", "--untracked-files=all", "--",
                        process_root(main) + "/changes/" + cid],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return bool(r.stdout.strip())


def ignored_artifacts(main):
    """Git-ignored ones from the process root, AGENTS.md, CLAUDE.md; outside a repository or without matches, empty."""
    r = subprocess.run(["git", "-C", main, "check-ignore", "--", process_root(main) + "/", "AGENTS.md", "CLAUDE.md"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.stdout.split() if r.returncode == 0 else []


def worktree_of(main, cid, prefix="change/"):
    """Path of the worktree of branch <prefix><id>, or an empty string."""
    r = subprocess.run(["git", "-C", main, "worktree", "list", "--porcelain"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    path = ""
    for ln in r.stdout.splitlines():
        if ln.startswith("worktree "):
            path = ln[len("worktree "):]
        elif ln == "branch refs/heads/" + prefix + cid:
            return path
    return ""


def abandoned(claim):
    """The waiting reason for an abandoned marker, or None. Could not read means not abandoned: not asking about a live one matters more."""
    now = time.time()
    try:
        born = os.path.getmtime(claim)
        with open(claim, encoding="utf-8", errors="replace") as f:
            m = re.search(r"session=([\w-]+)", f.read())
        if not m:
            return "CLAIM abandoned: label %d h" % ((now - born) / 3600) if now - born >= LABEL_AGE else None
        marks = []
        for suffix in ("json", "claims"):
            try:
                marks.append(os.path.getmtime(os.path.join(STATE, "%s.%s" % (m.group(1), suffix))))
            except FileNotFoundError:
                pass
    except OSError:
        return None
    if marks and now - max(marks) < SESSION_SILENCE:
        return None
    return "CLAIM abandoned: session %s silent %d h" % (m.group(1)[:8], (now - max(marks or [born])) / 3600)


def read_project(main, shared=()):
    """Disk -> (changes, archived, limit); changes: id -> {claim, waiting, branch, deps, reqs, files, shared}."""
    base = os.path.join(main, process_root(main), "changes")
    if not os.path.isdir(base):
        raise OSError("no folder " + base)
    values = read_settings(main)
    prefix = values["delivery.branch-prefix"][0]
    common, limit = agents_section(main)
    if values["dispatch.limit"][1] == "file" or limit is None:
        limit = int(values["dispatch.limit"][0])
    common |= set(shared)
    archived = set()
    arch = os.path.join(base, "archive")
    if os.path.isdir(arch):
        archived = {re.sub(r"^\d{4}-\d{2}-\d{2}-", "", d) for d in os.listdir(arch)
                    if os.path.isdir(os.path.join(arch, d))}
    changes = {}
    for cid in sorted(os.listdir(base)):
        d = os.path.join(base, cid)
        prop = os.path.join(d, "proposal.md")
        if cid == "archive" or not os.path.isfile(prop):
            continue
        src = text(prop)
        reqs = set()
        sd = os.path.join(d, "specs")
        for cap in sorted(os.listdir(sd)) if os.path.isdir(sd) else []:
            for ln in text(os.path.join(sd, cap, "spec.md")).splitlines():
                m = re.search(r"###\s*Requirement:\s*(.+?)`?\s*$", ln)
                if m:
                    reqs.add((cap, m.group(1)))
        files, shared = set(), set()
        for ln in sections(src, "Impact"):
            for v in ln.split("`")[1::2]:
                if is_common(v, common):
                    shared.add(v)
                elif is_file(v, main):
                    files.add(v)
        changes[cid] = {
            "claim": os.path.exists(os.path.join(d, "CLAIM")),
            "abandoned": abandoned(os.path.join(d, "CLAIM")),
            "waiting": os.path.exists(os.path.join(d, "WAITING")),
            "branch": has_branch(main, cid, prefix),
            "worktree": worktree_of(main, cid, prefix),
            "uncommitted": uncommitted(main, cid),
            "deps": parse_deps(sections(src, "Depends On")),
            "reqs": reqs, "files": files, "shared": shared,
        }
    return changes, archived, limit


def dependents(changes):
    """id -> number of open changes that depend on it directly or through a chain (cycles are safe)."""
    rev = {}
    for cid, c in changes.items():
        for d in c["deps"]:
            rev.setdefault(d, set()).add(cid)
    out = {}
    for cid in changes:
        seen, todo = set(), [cid]
        while todo:
            for n in rev.get(todo.pop(), ()):
                if n not in seen and n != cid:
                    seen.add(n)
                    todo.append(n)
        out[cid] = len(seen)
    return out


def conflict(a, b):
    """Reason for a hard conflict of change a with b, or None."""
    for cap, name in sorted(a["reqs"] & b["reqs"]):
        return "requirement %s/%s" % (cap, name)
    for f in sorted(a["files"] & b["files"]):
        return "file " + f
    return None


def busy(changes, running=(), waiting=()):
    """(running, waiting for merge) among open changes without repeats; an id in both lists counts as running."""
    run = [r for r in dict.fromkeys(running) if r in changes]
    wait = [w for w in dict.fromkeys(waiting) if w in changes and w not in run]
    return run, wait


def plan(changes, archived, limit, running=(), specs=(), waiting=(), prefix="change/"):
    """Pure planning -> (issued in order, [(id, reason)]); prefix: the change branch prefix in the reasons."""
    run, wait = busy(changes, running, waiting)
    over = max(0, len(wait) - limit)
    cands = [c for c in changes if c not in run and c not in wait]
    waits, ready = [], []
    for cid in cands:
        c = changes[cid]
        miss = [d for d in c["deps"] if d not in archived]
        if c["branch"]:
            wt = c.get("worktree")
            waits.append((cid, "not merged: branch " + prefix + cid + (", worktree " + wt if wt else "")))
        elif c["claim"]:
            waits.append((cid, c.get("abandoned") or "CLAIM"))
        elif c["waiting"]:
            waits.append((cid, "WAITING"))
        elif c.get("uncommitted"):
            waits.append((cid, "not committed"))
        elif miss:
            unknown = [d + (" (a spec, not a change)" if d in specs else "") for d in miss if d not in changes]
            opened = [d for d in miss if d in changes]
            waits.append((cid, "; ".join(([("unknown dependency: " + ", ".join(unknown))] if unknown else [])
                                         + (["depends on " + ", ".join(opened)] if opened else []))))
        else:
            ready.append(cid)
    cnt = dependents(changes)
    ready.sort(key=lambda i: (-cnt[i], i))
    granted = []
    for cid in ready:
        why = None
        for o in run + wait + granted:
            r = conflict(changes[cid], changes[o])
            if r:
                why = "conflict with %s: %s" % (o, r)
                break
        if why is None and limit - len(run) - over - len(granted) <= 0:
            why = "limit"
        if why:
            waits.append((cid, why))
        else:
            granted.append(cid)
    return granted, waits


def together(changes, granted, running, waiting=()):
    """«together:» lines: pairs of a granted change with a granted, running or waiting one over a shared path."""
    out = []
    run, wait = busy(changes, running, waiting)
    run = run + wait
    for i, a in enumerate(granted):
        for b in granted[i + 1:] + run:
            paths = sorted(changes[a]["shared"] & changes[b]["shared"])
            if paths:
                out.append("together: %s and %s — %s" % (a, b, ", ".join(paths)))
    return out


def loopback(needed=False):
    """«ok» or «blocked: <error>» («blocked (needed by the project): <error>» if needed): listen on a free 127.0.0.1 port and connect to it."""
    try:
        with socket.socket() as srv:
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            with socket.create_connection(srv.getsockname(), timeout=LOOPBACK_TIMEOUT):
                return "ok"
    except OSError as e:
        return "blocked%s: %s" % (" (needed by the project)" if needed else "", str(e) or type(e).__name__)


def render(granted, waits, limit, running, pairs=(), outside=(), waiting=(), probe=None, deliver=None):
    out = ["limit: %d, running: %d, waiting for merge: %d" % (limit, len(running), len(waiting))]
    if probe is not None:
        out.append("loopback: " + probe)
    if deliver:
        out.append("delivery: %s (%s), merge: %s (%s)" % (deliver["delivery.mode"] + deliver["delivery.merge"]))
    out += ["launch: " + (" ".join(granted) or "none")] + list(pairs)
    if outside:
        out.append("Artifacts outside git: " + ", ".join(outside))
    if waits:
        out.append("waiting:")
        out += ["  %s — %s" % w for w in waits]
    return "\n".join(out)


def main(argv):
    args, running, waiting, ignores, shared = [], [], [], [], []
    it = iter(argv)
    for a in it:
        if a == "--running":
            running = [x for x in next(it, "").split(",") if x]
        elif a == "--waiting":
            waiting = [x for x in next(it, "").split(",") if x]
        elif a == "--ignore-dep":
            cid, _, name = next(it, "").partition(":")
            ignores.append((cid, name))
        elif a == "--shared":
            shared.append(next(it, "").lstrip("/"))
        else:
            args.append(a)
    if len(args) != 1 or not all(all(i) for i in ignores) or not all(shared):
        print("Run: sdd_dispatch_plan.py <MAIN> [--running id1,id2] [--waiting id1,id2] [--ignore-dep id:name]..."
              " [--shared path]...\n--running: orchestrators at work; --waiting: waiting for merge (status accepted,"
              " the branch went to CI): conflicts as for running ones, a place only beyond the limit", file=sys.stderr)
        return 2
    try:
        changes, archived, limit = read_project(os.path.abspath(args[0]), shared)
        deliver = read_settings(os.path.abspath(args[0]))
    except (OSError, ValueError) as e:
        print("read error: %s" % e, file=sys.stderr)
        return 1
    granted, waits = plan(apply_ignores(changes, ignores), archived, limit, running,
                          spec_names(os.path.abspath(args[0])), waiting, deliver["delivery.branch-prefix"][0])
    run, wait = busy(changes, running, waiting)
    print(render(granted, waits, limit, run, together(changes, granted, run, wait),
                 ignored_artifacts(os.path.abspath(args[0])), wait, loopback(loopback_needed(os.path.abspath(args[0]))), deliver))
    if process_root(os.path.abspath(args[0])) == "openspec":
        print(IMPORT_HINT)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
