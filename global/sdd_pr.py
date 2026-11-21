#!/usr/bin/env python3
"""sdd-pr.py: PRs for spec-dispatch: open, wait (CI and code scanning alerts), merge, ship, land, promote.
Every gh call goes by the PR URL."""
import collections
import json
import os
import re
import shlex
import subprocess
import sys
import time
from urllib.parse import quote

USAGE = """usage:
  sdd-pr.py open <WORKTREE> <main branch> <title>
  sdd-pr.py wait <url> [--timeout <sec>] [--interval <sec>] [--stuck <sec>]
  sdd-pr.py merge <url> <squash|merge|rebase> <hash> [--title <title>]
  sdd-pr.py ship <MAIN> <WORKTREE> <main branch> <title>
  sdd-pr.py land <MAIN> <WORKTREE> <url> <squash|merge|rebase>
  sdd-pr.py land <MAIN> <WORKTREE> <url> --after-merge
  sdd-pr.py promote <from> <to>
  sdd-pr.py overwrites <WORKTREE> <ref>
  overwrites changes nothing: code 1 «merge would overwrite ignored files in WORKTREE: <paths>» when merging <ref>
    writes over an untracked WORKTREE file, «<step>: <reason>» when a git step fails; no output and code 0 otherwise
  delivery.merge-by: human in solo-sdd/config: merge and land never merge (code 8 «waits for human merge: <url>»);
    land --after-merge, after a person merged, pulls, transports and removes the worktree; an open PR: code 8
  checklist.<name>.paths and .file of solo-sdd/config: open and ship add «## Checklist: <name>» with the file's items
    to a PR touching the paths; merge and land: code 8 «checklist <name>: <n> open items» while an item is unticked,
    then «checklist <name>: no approval on <sha>» until another account than the PR author approved the head commit
  delivery.base of solo-sdd/config in the main folder replaces <main branch>; broken settings: code 1
  promote opens (or prints the open) PR <from> -> <to> and never merges it; <to> `release/*`: the newest release/ branch
  delivery.ci-timeout, .ci-stuck and .ci-no-checks of the main folder's solo-sdd/config set the wait limits (a flag wins);
    delivery.require-ci: off gives CI: none (code 0) and merges a PR without checks while the base requires none;
    delivery.code-scanning: warn prints the alerts as green, off asks for none; delivery.delete-branch: off keeps the
    branch; delivery.draft: on opens a draft PR and marks it ready right before the merge request
  wait codes: 0 green or none, 3 red, 4 infra, 8 codeql (checks passed, code scanning alerts are open)
  merge codes: 0 merged, 1 error, 5 main moved ahead (PR is behind), 8 waits for the owner (delivery.owner-only paths, .github/workflows or solo-sdd/config), a human merge or checklist items
  ship codes: 0 green or none, 1 step failed, 3 red, 4 infra, 6 conflict, 8 codeql
  land codes: 0 all done, 1 merge failed, 5 main moved ahead, 7 merged, a step after merge failed, 8 waits for the owner (delivery.owner-only paths, .github/workflows or solo-sdd/config), a human merge or checklist items"""
SIGNS = ("FAIL:", "ERROR:", "FAILED", "AssertionError", "failed")
REVIEWS_SEC = 60
LOG_LINES = 20
LOG_RETRY_SEC = 5
SCAN_OFF = re.compile(r"advanced security|code scanning", re.I)  # 403 of disabled scanning
SCAN_UNCHECKED = "code scanning alerts not checked"
CI_PATTERN = ".github/workflows/**"
OWNER = "Owner only:"
HUMAN = "waits for human merge"
AFTER = "--after-merge"
CHECKLIST = "## Checklist:"
ITEM = re.compile(r"\s*[-*]\s+\[([ xX])\]\s+(.*)")
HEADING = re.compile(r"#{1,6}(?:\s|$)")
OLD_OWNER_HIT = "AGENTS.md (pre-English «Owner only:» item: run solo-sdd migrate-agents)"


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
    "dispatch.shared": ("paths", None, "", None),  # sdd-dispatch-plan.py: paths changes may share without a conflict
    "dispatch.loopback": ("choice", ("on", "off"), "off", None),  # on: the project's tests need local sockets
    "dispatch.check-timeout": ("int", None, "600", None),  # seconds of each land-local command; SDD_DISPATCH_TIMEOUT wins
    "worktree.paths": ("paths", None, "", None),  # sdd-worktree.py: git-ignored paths copied into a worktree
    "worktree.prepare": ("text", None, "", None),  # the command setup runs in a new worktree
    "worktree.after-refresh": ("text", None, "", None),  # the command refresh runs after a transfer without conflicts
    "worktree.links": ("paths", None, "node_modules, .venv", None),  # folders linked from the main folder
    "process.review-rounds": ("int", None, "5", None),
    "process.light-path": ("choice", ("on", "off"), "on", None),  # off: every code edit goes through a change
    "process.light-path.max-files": ("int", None, "3", None),
    "process.max-tasks": ("int", None, "10", None),  # solo-sdd validate: tasks of one change
    "process.bugfix-max-tasks": ("int", None, "5", None),  # spec-plan, spec-analyze: a bug fix takes the smaller limit
    "process.requirement-max-chars": ("int", None, "500", None),  # solo-sdd validate: one requirement text
    "process.audit-every": ("int", None, "5", None),  # spec-next proposes spec-audit at a multiple of the archive count
    "process.analyze": ("choice", ("on", "off"), "on", None),  # off: spec-plan and spec-next skip spec-analyze
    "process.analyze-attackers": ("int", None, "3", None),  # spec-plan, spec-next: Attack: subagents, 0 for one Analyze:
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
    "agents.attack-model": ("model", None, "haiku", None),  # work_hooks.py: the cheap list
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
INT_MIN = {"process.max-tasks": 3, "process.bugfix-max-tasks": 3, "process.requirement-max-chars": 100,
           "process.analyze-attackers": 0}
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
# the «Working copy» items of AGENTS.md read as the old source of a key: item -> key
WORKING_ITEMS = (("Paths:", "worktree.paths"), ("Prepare:", "worktree.prepare"),
                 ("After refresh:", "worktree.after-refresh"), ("Shared:", "dispatch.shared"),
                 ("Orchestrators:", "dispatch.limit"))


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
        if not v and default == "":
            return v
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
    written, and the backquoted patterns of every «Owner only:» item; the working_items values; a file that cannot be
    opened adds nothing."""
    out, inside = dict(project_lines(root, registry)[0], **working_items(root, registry)[0]), False
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


def working_items(root, registry=REGISTRY):
    """({key: value}, [line left out]) of AGENTS.md at root, the old source of the WORKING_ITEMS keys and of
    dispatch.loopback. In «## Working copy»: the backquoted values of every «Paths:» and «Shared:» item (a leading / of
    a shared path dropped), the first backquoted value of the first «Prepare:» and «After refresh:» item, as written,
    and the first number of the first «Orchestrators:» item; a list item «Loopback: needed» of «## Working copy» or
    «## Commands» is `on`. A path or number check_value refuses is left out and named as AGENTS.md:<line> with the
    reason; a file that cannot be opened: ({}, [])."""
    try:
        with open(os.path.join(root, "AGENTS.md"), encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return {}, []
    out, bad, section = {}, [], ""
    for n, ln in enumerate(lines, 1):
        if ln.startswith("## "):
            section = ln.strip()
            continue
        s = ln.strip()
        if section in ("## Working copy", "## Commands") and s.startswith(("-", "*")) and "dispatch.loopback" in registry \
                and re.match(r"loopback:\s*needed\b", s.replace("*", "").lstrip("- "), re.I):
            out["dispatch.loopback"] = "on"
        s = s.lstrip("-* ").strip()
        for item, key in WORKING_ITEMS if section == "## Working copy" else ():
            if not s.startswith(item) or key not in registry or key in out and registry[key][0] not in LIST_KINDS:
                continue
            rest = s[len(item):]
            if key == "dispatch.limit":
                m = re.search(r"\d+", rest)
                vals = [m.group()] if m else []
            else:
                vals = [v.lstrip("/") if key == "dispatch.shared" else v for v in rest.split("`")[1::2] if v.strip()]
            if registry[key][0] == "text":  # a command is read as written, without the length limit
                if vals:
                    out[key] = vals[0].strip()
                continue
            good = []
            for v in vals:
                try:
                    good.append(check_value(key, v, registry))
                except SettingsError as e:
                    bad.append("AGENTS.md:%d: %s is left out: %s" % (n, v, e))
            if good:
                out[key] = ", ".join(([out[key]] if key in out else []) + good)
    return out, bad


def read_settings(root, registry=REGISTRY):
    """Settings in effect of the project at root; no file means all defaults; a broken file raises SettingsError."""
    return effective(parse_settings(read_settings_text(root), registry), registry, agents_delivery(root, registry))
# settings:end


def delivery(root):
    """(delivery.base, delivery.promote as a list) of the project at root; base "" is the default branch passed in.
    Broken settings: exit 1 naming the line, never a silent fall back to the default branch."""
    try:
        s = read_settings(root)
    except (OSError, ValueError) as e:
        die("settings: %s" % e)
    return s["delivery.base"][0], [x.strip() for x in s["delivery.promote"][0].split(",") if x.strip()]


def pr_settings(root):
    """Settings in effect of the main folder at root; broken settings: exit 1 naming the line."""
    try:
        return read_settings(root)
    except (OSError, ValueError) as e:
        die("settings: %s" % e)


LIMITS = (("timeout", "delivery.ci-timeout"), ("stuck", "delivery.ci-stuck"), ("no checks", "delivery.ci-no-checks"))


def ci_limits(s, timeout=None, stuck=None):
    """([timeout, stuck, no checks] in seconds, the stderr line naming each with its source): a flag wins over the
    setting; the line is None while none of the three keys is set, so a run on the defaults prints nothing."""
    out, named = [], []
    for (label, key), flag in zip(LIMITS, (timeout, stuck, None)):
        value, source = (flag, "flag") if flag is not None else (float(s[key][0]), s[key][1])
        out.append(value)
        named.append("%s %s s (%s)" % (label, ("%d" if value.is_integer() else "%g") % value, source))
    return out, ("limits: " + ", ".join(named) if any(s[k][1] != "default" for _, k in LIMITS) else None)


def merge_by(root):
    """delivery.merge-by of the project at root: agent or human; broken settings: exit 1 naming the line."""
    try:
        return read_settings(root)["delivery.merge-by"][0]
    except (OSError, ValueError) as e:
        die("settings: %s" % e)


def checklists(root):
    """{name: (globs with the checklist's own file and the settings file, items)} of the project at root. Broken settings, a checklist with
    one of its two keys, or a file unreadable or without `- [ ]` items: exit 1 naming it, never a silently open gate."""
    try:
        values = read_settings(root)
    except (OSError, ValueError) as e:
        die("settings: %s" % e)
    keys = {}
    for key, (value, _) in values.items():
        if key.startswith("checklist.") and value:
            name, _, part = key[len("checklist."):].rpartition(".")
            keys.setdefault(name, {})[part] = value
    out = {}
    for name, parts in sorted(keys.items()):
        if len(parts) < 2:
            die(f"checklist {name}: set both checklist.{name}.paths and checklist.{name}.file")
        rel = parts["file"]
        text = read_text(os.path.join(root, rel))
        items = [" ".join(m.group(2).split()) for m in map(ITEM.fullmatch, (text or "").splitlines()) if m and m.group(2).strip()]
        if not items:
            die(f"checklist {name}: {rel} " + ("not readable" if text is None else "holds no `- [ ]` item"))
        out[name] = ([x.strip() for x in parts["paths"].split(",")] + [rel, SETTINGS_FILE], items)
    return out


def section_items(body):
    """{name: [(ticked, text), ...]} of the «## Checklist: <name>» sections of a PR body; a section ends at the next
    heading; a heading without a name is no section; item texts with whitespace collapsed."""
    out, name = {}, None
    for line in (body if isinstance(body, str) else "").splitlines():
        if HEADING.match(line):
            name = (line[len(CHECKLIST):].strip() or None) if line.startswith(CHECKLIST) else None
            if name is not None:
                out.setdefault(name, [])
        elif name is not None:
            m = ITEM.fullmatch(line)
            if m:
                out[name].append((m.group(1) != " ", " ".join(m.group(2).split())))
    return out


def sections(body):
    """{name: unticked items} of the checklist sections of a PR body."""
    return {name: sum(not t for t, _ in rows) for name, rows in section_items(body).items()}


def matched(files, lists):
    return [name for name, (globs, _) in lists.items() if owner_hits(files, globs)]


def add_checklists(url, n, lists):
    """Appends a section for every checklist the PR files match and the body lacks; an existing section is never rewritten."""
    if not lists:
        return
    repo = re.search(r"github\.com/([^/]+/[^/]+)/pull/", url)
    if not repo:
        die("cannot parse owner/repo from url: " + url)
    files = pr_files(repo.group(1), n, "checklist")[0]
    try:
        body = gh_json("pr", "view", url, "--json", "body").get("body")
    except (ValueError, AttributeError) as e:
        die("checklist: gh pr view: " + str(e).strip())
    have = sections(body)
    add = [x for x in matched(files, lists) if x not in have]
    if not add:
        return
    old = body.rstrip() if isinstance(body, str) and body.strip() else None
    text = "\n\n".join(([old] if old else []) + [
        "\n".join([f"{CHECKLIST} {x}", ""] + ["- [ ] " + i for i in lists[x][1]]) for x in add]) + "\n"
    p = sh("gh", "pr", "edit", url, "--body", text)
    if p.returncode:
        die("checklist: gh pr edit: " + p.stderr.strip())
    for x in add:
        print(f"PR #{n} checklist {x}: {len(lists[x][1])} open items")


def read_reviews(repo, n):
    """(reviews as [{login, state, commit_id}] in GitHub's order, None) or (None, why they were not read): a failed or
    late call, or any row that is not an object with a string state and a string or null login and commit_id. A null
    login (a deleted account) is no account and is skipped; a null commit_id (a commit gone after a force-push) is kept
    as that account's review and never matches the head."""
    try:
        p = sh("gh", "api", f"repos/{repo}/pulls/{n}/reviews", "--paginate",
               "--jq", ".[] | {login: .user.login, state, commit_id}", timeout=REVIEWS_SEC)
    except subprocess.TimeoutExpired:
        return None, f"gh api: no answer in {REVIEWS_SEC} s"
    if p.returncode:
        return None, brief(p.stderr or p.stdout) or "gh api failed"
    out = []
    for line in p.stdout.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            return None, "not JSON: " + line[:100]
        if not isinstance(row, dict) or not isinstance(row.get("state"), str) or not all(
                k in row and (row[k] is None or isinstance(row[k], str)) for k in ("login", "commit_id")):
            return None, "not a review: " + line[:100]
        if row["login"] is not None:
            out.append(row)
    return out, None


def approved(reviews, author, sha):
    """Some account other than the author has, as its latest review, an APPROVED one on sha."""
    latest = {r["login"]: r for r in reviews}
    return any(a != author and r["state"] == "APPROVED" and r["commit_id"] == sha for a, r in latest.items())


def approval_gate(repo, n, names, author, sha):
    """Lines «checklist <name>: no approval on <sha>» for the checklists of a PR without a person's approval: GitHub
    refuses an author's approval of their own PR, so the agent pushing as the author cannot give it."""
    if not names:
        return []
    reviews, why = read_reviews(repo, n) if author else (None, "no PR author")
    if reviews is not None and approved(reviews, author, sha):
        return []
    tail = f" (reviews not read: {why})" if why else ""
    return [f"checklist {name}: no approval on {sha}{tail}" for name in sorted(names)]


def checklist_gate(repo, n, body, root):
    """{name: open items} of the PR's checklists. A matching checklist counts its file's items, not the marks the body
    holds: an item is closed only when the section has it ticked with the file's text, so a section emptied, cut or
    replaced by an agent stays open; an extra unticked line in the section is open too."""
    lists, rows = checklists(root), section_items(body)
    have = {name: sum(not t for t, _ in r) for name, r in rows.items()}
    if lists:
        for name in matched(pr_files(repo, n)[0], lists):
            items, got = lists[name][1], rows.get(name, [])
            need, done = collections.Counter(items), collections.Counter(x for t, x in got if t)
            have[name] = sum((need - done).values()) + sum(not t and x not in need for t, x in got)
    return have


def sh(*cmd, cwd=None, timeout=None):
    return subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, cwd=cwd, timeout=timeout)


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def number(url):
    m = re.search(r"/pull/(\d+)", url)
    return m.group(1) if m else "?"


def open_pr(wt, base, title, root):
    lists = checklists(root)  # a broken checklist stops before the push
    draft = ["--draft"] if pr_settings(root)["delivery.draft"][0] == "on" else []
    p = sh("git", "-C", wt, "push", "-u", "origin", "HEAD")
    if p.returncode:
        die("push: " + p.stderr.strip())
    branch = sh("git", "-C", wt, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    p = sh("gh", "pr", "list", "--head", branch, "--state", "open", "--json", "number,url", cwd=wt)  # gh takes the repository from the folder
    if p.returncode:
        die("gh pr list: " + p.stderr.strip())
    prs = json.loads(p.stdout or "[]")
    if prs:
        n, url = prs[0]["number"], prs[0]["url"]
    else:
        p = sh("gh", "pr", "create", "--base", base, "--head", branch, "--title", title,
               "--body", f"Branch {branch}, opened by sdd-pr.py", *draft, cwd=wt)
        if p.returncode:
            die("gh pr create: " + p.stderr.strip())
        url = p.stdout.strip().splitlines()[-1]
        n = number(url)
    add_checklists(url, n, lists)
    return n, url


def cmd_open(wt, base, title):
    root = main_folder(wt) or wt
    n, url = open_pr(wt, delivery(root)[0] or base, title, root)
    print(f"PR #{n} {url}")
    return 0


def brief(text):
    return "\n".join(text.strip().splitlines()[-LOG_LINES:])


def checks(url):
    """(rows, error): the PR check rows; [] when gh reports no checks, None with gh's brief error when the request failed
    otherwise (a failure is never "no checks": under delivery.require-ci: off that would merge without seeing a red check)."""
    p = sh("gh", "pr", "checks", url, "--json", "name,state,bucket,link")
    try:
        return json.loads(p.stdout), ""
    except ValueError:
        if "no checks reported" in p.stderr:  # gh without checks prints an error, not JSON
            return [], ""
        return None, brief(p.stderr) or f"gh exit {p.returncode}"


def failed_log(rows):
    out = []
    for r in rows:
        m = re.search(r"github\.com/([^/]+/[^/]+)/actions/runs/(\d+)", r.get("link", ""))
        if m:
            for _ in range(3):  # the log appears seconds after the check finishes
                log = sh("gh", "run", "view", m.group(2), "-R", m.group(1), "--log-failed").stdout
                if log.strip():
                    break
                time.sleep(LOG_RETRY_SEC)
            out += log.splitlines()
    clean = []
    for line in out:
        line = line.split("\t")[-1]  # without the job and step name
        clean.append(re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ?", "", line))
    hits = {i for i, s in enumerate(clean) if any(k in s for k in SIGNS)}
    keep = sorted({j for i in hits for j in (i - 1, i, i + 1) if 0 <= j < len(clean)})
    return bool(hits), [clean[i] for i in (keep or range(len(clean)))][-LOG_LINES:]  # the test summary is at the end of the log


def gh_json(*cmd):
    p = sh("gh", *cmd)
    if p.returncode:
        raise ValueError(p.stderr)
    return json.loads(p.stdout)


def required_checks(url):
    """Required checks of the PR base branch, or None if the rules could not be read."""
    try:
        repo = re.search(r"github\.com/([^/]+/[^/]+)/pull/", url).group(1)
        branch = quote(gh_json("pr", "view", url, "--json", "baseRefName")["baseRefName"], safe="/")
        # ponytail: one page, more than 100 active rules per branch does not happen in practice
        rules = gh_json("api", f"repos/{repo}/rules/branches/{branch}?per_page=100")
        names = [c["context"] for r in rules if r["type"] == "required_status_checks"
                 for c in r["parameters"]["required_status_checks"]]
        protection = gh_json("api", f"repos/{repo}/branches/{branch}").get("protection") or {}
        classic = protection.get("required_status_checks") or {}  # /protection needs admin rights
        names += [c["context"] for c in classic.get("checks") or []] + (classic.get("contexts") or [])
        if not all(isinstance(x, str) for x in names):
            raise ValueError
        return set(names)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def alert_line(a):
    """One line "#<number> <rule> <file>:<line> <text>"; newlines in fields collapsed."""
    inst = a.get("most_recent_instance") or {}
    loc, rule = inst.get("location") or {}, a.get("rule") or {}
    text = (inst.get("message") or {}).get("text") or rule.get("description") or ""
    line = f"#{a.get('number', '?')} {rule.get('id') or rule.get('name') or '?'} " \
           f"{loc.get('path') or '?'}:{loc.get('start_line') or '?'} {text}"
    return " ".join(line.split())


def scan_alerts(url):
    """Lines of open code scanning alerts for the PR: [] means none or scanning is off, None means not checked."""
    m = re.search(r"github\.com/([^/]+/[^/]+)/pull/(\d+)", url)
    if not m:
        return None
    # ref of the PR merge commit, as in the GitHub docs; one page: the summary needs only "some or none", at most 20 lines
    p = sh("gh", "api", f"repos/{m.group(1)}/code-scanning/alerts?ref=refs/pull/{m.group(2)}/merge&state=open&per_page=100")
    if p.returncode:
        off = "(HTTP 404)" in p.stderr or ("(HTTP 403)" in p.stderr and SCAN_OFF.search(p.stderr))
        return [] if off else None  # the text is checked on stderr: the response body has a link to the code-scanning docs
    try:
        alerts = json.loads(p.stdout)
        if not isinstance(alerts, list):
            raise ValueError
        return [alert_line(a) for a in alerts]
    except (ValueError, TypeError, AttributeError):
        return None


def stuck_checks(rows, required):
    """Required checks that are missing or have not started, when there is nothing else to wait for."""
    # ponytail: external CI on commit statuses (state PENDING) cannot be told apart from a check that has not started
    pending = {r.get("name") for r in rows if r.get("bucket") == "pending"}
    running = any(r.get("bucket") == "pending" and r.get("state") == "IN_PROGRESS" for r in rows)
    if running or pending - required:
        return []
    return sorted(required - ({r.get("name") for r in rows} - pending))


def ci_verdict(rows, required, stuck_sec, limit):
    """Checks summary: "bad", "green", "stuck" or None to keep waiting."""
    if any(r.get("bucket") in ("fail", "cancel") for r in rows):
        return "bad"
    if stuck_checks(rows, required):
        return "stuck" if stuck_sec >= limit else None
    return "green" if rows and not any(r.get("bucket") == "pending" for r in rows) else None


def cmd_wait(url, timeout=1200.0, interval=15.0, limit=300.0, root=None, no_checks=None):
    """The CI summary of the PR; delivery.* of the main folder at root (default: the one of the current folder) set
    the no-checks limit, whether no checks is none and what open code scanning alerts do."""
    s = pr_settings(root or main_folder() or ".")
    no_checks = ci_limits(s)[0][2] if no_checks is None else no_checks
    optional, scan = s["delivery.require-ci"][0] == "off", s["delivery.code-scanning"][0]
    n = number(url)
    head = f"PR #{n} {url} CI: "
    required = required_checks(url)
    known = required is not None  # unread rules may hide a required check: then no checks is never none
    if not known:
        print("warning: branch rules not read, required checks not checked", file=sys.stderr)
        required = set()
    start = time.monotonic()  # the deadline is for CI, reading the rules is not part of it
    since = None  # from which poll there is nothing to wait for but the stuck ones
    while True:
        rows, error = checks(url)
        unread, rows = rows is None, rows or []
        now = time.monotonic()
        elapsed = now - start
        # an unread poll is no evidence that a check started or did not: no stuck, the stuck timer stays as it was
        stuck = [] if unread else stuck_checks(rows, required)
        if not unread:
            since = (since or now) if stuck else None
        verdict = None if unread else ci_verdict(rows, required, now - since if stuck else 0, limit)
        if verdict == "green":
            alerts = scan_alerts(url) if scan != "off" else []
            if alerts and scan == "gate":
                print(head + "codeql")
                print("\n".join(alerts[:LOG_LINES]))
                return 8
            print(head + "green")
            lines = [SCAN_UNCHECKED] if alerts is None else alerts[:LOG_LINES]  # warn: the alerts, the merge goes on
            if lines:
                print("\n".join(lines))
            return 0
        if verdict == "bad":  # a failed check is the summary at once
            test, lines = failed_log([r for r in rows if r.get("bucket") in ("fail", "cancel")])
            print(head + ("red" if test else "infra"))
            print("\n".join(lines))
            return 3 if test else 4
        no_rows_end = not rows and not required and elapsed >= min(no_checks, timeout)
        if no_rows_end and optional and known and not unread:
            print(head + "none")
            return 0
        if verdict == "stuck" or elapsed >= timeout or no_rows_end:
            print(head + "infra")
            print("\n".join(f"required check did not start: {x}" for x in stuck)
                  or (f"checks not read: {error}" if unread else "no checks" if not rows else "timeout: checks did not finish"))
            return 4
        time.sleep(interval)


def view(url):
    p = sh("gh", "pr", "view", url, "--json", "headRefOid,headRefName,baseRefName,state,title,isCrossRepository,body,author,isDraft")
    if p.returncode:
        die("gh pr view: " + p.stderr.strip())
    try:
        return json.loads(p.stdout)
    except ValueError:
        die("gh pr view: not JSON: " + p.stdout[:200])


def owner_rule(text):
    """Lines of the «Owner only:» item of the «## Delivery» section (all of them, newline-separated) or None."""
    if text is None:
        return None
    inside, found = False, []
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Delivery"
        elif inside and line.strip().lstrip("-* ").startswith(OWNER):
            found.append(line.strip())
    return "\n".join(found) or None


def owner_patterns(rule):
    """Patterns from backquotes; a path ending in `/` is the whole directory."""
    return gate_patterns(re.findall(r"`([^`]*)`", rule or ""))


def gate_patterns(pats):
    """CI_PATTERN and pats without a leading `./` or `/`; a path ending in `/` is the whole directory."""
    pats = (re.sub(r"^(\./|/)+", "", y) for y in pats)
    return [CI_PATTERN] + [x + "**" if x.endswith("/") else x for x in pats if x]


def settings_hits(main, files, wt=None):
    """Files matching CI_PATTERN or delivery.owner-only of the main folder's settings (its old source the «Owner only:»
    items of the main AGENTS.md), never of the PR or the worktree, plus the settings file itself when the change edits
    it or the transfer after merge would carry the worktree's copy (carried_config). Broken settings raise
    SettingsError (OSError): the gate never falls back to fewer paths."""
    value = read_settings(main)["delivery.owner-only"][0] if main else ""
    hits = owner_hits(files, gate_patterns(x.strip() for x in value.split(",")))
    if SETTINGS_FILE not in hits and (SETTINGS_FILE in files or wt is not None and carried_config(main, wt)):
        hits.append(SETTINGS_FILE)
    return hits


def carried_config(main, wt):
    """True when sdd-worktree.py transport would carry the worktree's settings file into main: its bytes differ from
    the setup snapshot <wt>.base (a copy deleted from the worktree is carried as a deletion), and git ignores it in main (a tracked file comes with the merge, not the transfer);
    a check-ignore that fails counts as ignored. An owner edit of the main copy alone is no hit."""
    def raw(path):
        try:
            with open(path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None
    if raw(os.path.join(wt, SETTINGS_FILE)) == raw(os.path.join(wt + ".base", SETTINGS_FILE)):
        return False
    return not main or sh("git", "-C", main, "check-ignore", "-q", "--", SETTINGS_FILE).returncode != 1


def glob_re(pat):
    """`*` within a name, `**` across folders; runs of asterisks collapsed (no catastrophic backtracking)."""
    parts = re.split(r"(\*+)", pat)
    out = []
    for i, x in enumerate(parts):
        if not x.startswith("*"):
            out.append(re.escape(x))
        elif len(x) == 1:
            out.append("[^/]*")
        elif i + 1 < len(parts) and parts[i + 1].startswith("/"):
            out.append("(?:.*/)?")  # `**/` includes zero depth
            parts[i + 1] = parts[i + 1][1:]
        else:
            out.append(".*")
    return re.compile("".join(out))


def owner_hits(files, patterns):
    res = [glob_re(x) for x in patterns]
    return sorted({f for f in files if any(r.fullmatch(f) for r in res)})


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def main_folder(cwd=None):
    p = sh("git", "rev-parse", "--path-format=absolute", "--git-common-dir", cwd=cwd)
    return os.path.dirname(p.stdout.strip()) if p.returncode == 0 and p.stdout.strip() else None


def pr_files(repo, n, step="not merged"):
    """PR file names (including previous ones) and each file's patch; a failure or broken response means die."""
    p = sh("gh", "api", "--paginate", f"repos/{repo}/pulls/{n}/files",
           "--jq", ".[] | {filename, previous_filename, patch}")
    if p.returncode:
        die(f"{step}: PR files: " + (p.stderr or p.stdout).strip())
    names, patches = [], {}
    for line in p.stdout.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            name = row["filename"]
        except (ValueError, TypeError, KeyError):
            die(f"{step}: PR files: not JSON: " + line[:200])
        if not isinstance(name, str):
            die(f"{step}: PR files: no filename: " + line[:200])
        names.append(name)
        patches[name] = row.get("patch")
        if isinstance(row.get("previous_filename"), str):
            names.append(row["previous_filename"])
    return names, patches


def rule_touched(patch):
    """An AGENTS.md edit touched the «Owner only:» item: no patch (too large) or the item is in added/removed lines."""
    if not patch:
        return True
    return any(l[:1] in ("+", "-") and not l.startswith(("+++", "---")) and OWNER in l for l in patch.splitlines())


def owner_gate(repo, n, main, wt):
    """Paths that wait for the owner (list of lines); empty means merge is allowed."""
    files, patches = pr_files(repo, n)
    main = main_folder() if main is None else main
    text = read_text(os.path.join(main, "AGENTS.md")) if main else None
    found = migrate_agents(text or "")[1]
    if found:
        print(migrate_hint(os.path.join(main, "AGENTS.md"), found), file=sys.stderr)
    rule = owner_rule(text)
    try:
        hits = settings_hits(main, files, wt)
    except (OSError, ValueError) as e:
        die("settings: %s" % e)
    if OWNER in found:  # the old item is not read, but its paths are not opened silently either: the owner decides
        hits.append(OLD_OWNER_HIT)
    if text is not None and ("AGENTS.md" in patches and rule_touched(patches["AGENTS.md"])
                             or wt is not None and owner_rule(read_text(os.path.join(wt, "AGENTS.md"))) != rule):
        hits.append(f"AGENTS.md («{OWNER}»)")
    return hits


def cmd_merge(url, how, sha, title=None, main=None, wt=None):
    n, v = number(url), view(url)
    if v["state"] == "MERGED":
        print(f"PR #{n} merged (already)")
        return 0
    s = pr_settings(main or main_folder() or ".")
    if s["delivery.merge-by"][0] == "human":  # a person merges: the PR stays open
        print(f"PR #{n} {HUMAN}: {url}")
        return 8
    if v["headRefOid"] != sha:
        die(f"hash {sha} is not the PR head ({v['headRefOid']})")
    if how != "rebase":
        title = (v.get("title", "") if title is None else title).strip()
        if not title:
            die(f"PR #{n}: empty commit title (pass --title)")
    owner_repo = re.search(r"github\.com/([^/]+/[^/]+)/pull/", url)
    if not owner_repo:
        die("cannot parse owner/repo from url: " + url)
    hits = owner_gate(owner_repo.group(1), n, main, wt)
    if hits:
        print(f"PR #{n} waits for the owner: " + ", ".join(hits))
        return 8
    have = checklist_gate(owner_repo.group(1), n, v.get("body"), main or main_folder() or ".")
    lines = [f"checklist {name}: {k} open items" for name, k in sorted(have.items()) if k]
    author = v.get("author")
    lines = lines or approval_gate(owner_repo.group(1), n, have, author.get("login") if isinstance(author, dict) else None,
                                   v["headRefOid"])
    if lines:  # a person ticks the items in the PR body and approves the head commit
        print("\n".join(f"PR #{n} {x}" for x in lines))
        return 8
    p = sh("gh", "api", f"repos/{owner_repo.group(1)}/compare/{v['baseRefName']}...{v['headRefOid']}",
           "--jq", ".behind_by")
    if p.returncode:
        die("gh api compare: " + p.stderr.strip())
    try:
        behind = int(p.stdout.strip() or 0)
    except ValueError:
        die("gh api compare: not a number: " + p.stdout[:200])
    if behind > 0:
        print(f"PR #{n} behind {behind}: main moved ahead")
        return 5
    rows = checks(url)[0]
    if rows is None:
        die(f"PR #{n} CI not green: checks not read")
    bad = [f"{r.get('name')} ({r.get('bucket')})" for r in rows if r.get("bucket") not in ("pass", "skipping")]
    if bad or not rows and (s["delivery.require-ci"][0] == "on" or required_checks(url) != set()):
        die(f"PR #{n} CI not green: " + (", ".join(bad) or "no checks"))
    repo = owner_repo.group(1)
    if v.get("isDraft") and s["delivery.draft"][0] == "on":  # after every gate: a gated PR stays a draft
        p = sh("gh", "pr", "ready", url)
        if p.returncode:
            die(f"PR #{n} not merged: ready: " + ((p.stderr or p.stdout).strip() or "gh pr ready failed"))
    extra = ["-f", f"commit_title={title} (#{n})"] if how != "rebase" else []
    p = sh("gh", "api", "-X", "PUT", f"repos/{repo}/pulls/{n}/merge", "-f", f"merge_method={how}", "-f", f"sha={sha}", *extra)
    if p.returncode:
        die((p.stderr or p.stdout).strip() or "merge refused")
    print(f"PR #{n} {url} merged ({how})")
    if v.get("isCrossRepository") or s["delivery.delete-branch"][0] == "off":  # a fork's branch is someone else's
        return 0
    branch = v["headRefName"]
    p = sh("gh", "api", "-X", "DELETE", f"repos/{repo}/git/refs/heads/{branch}")
    if p.returncode and not any(c in p.stderr for c in ("HTTP 404", "HTTP 422")):
        print(f"branch {branch} not deleted: " + (p.stderr or p.stdout).strip())
    return 0


def worktree_script():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("sdd-worktree.py", "sdd_worktree.py"):
        if os.path.exists(os.path.join(here, name)):
            return os.path.join(here, name)
    return None


def written_over(repo, written, untracked, fold):
    """The untracked entries (git's own list, ignored files, links and nested repositories as `sub/` included) that
    writing the paths deletes: the same path, an entry where a written path needs a directory, an entry inside a
    directory a path turns into a file; fold compares case-insensitively, as a case-insensitive disk does."""
    key = str.lower if fold else str
    names, under = {}, {}
    for u in untracked:
        k = key(u.rstrip("/"))
        names.setdefault(k, u)
        parts = k.split("/")
        for n in range(1, len(parts)):
            under.setdefault("/".join(parts[:n]), []).append(u)
    hits = []
    for w in written:
        parts = key(w).split("/")
        for n in range(1, len(parts) + 1):
            u = names.get("/".join(parts[:n]))
            if u and (not u.endswith("/") or n == len(parts) or inside(repo, w, n)):
                hits.append(u)
        hits += under.get(key(w), [])
    return list(dict.fromkeys(hits))


def inside(repo, path, n):
    """A path under a nested repository (its first n parts) writes over a file there: the path itself, or an inner part
    that is a file or a link where the path needs a directory. git lists none of a nested repository's files."""
    parts = path.split("/")
    for m in range(n + 1, len(parts) + 1):
        full = os.path.join(repo, *parts[:m])
        if m < len(parts) and os.path.isdir(full) and not os.path.islink(full):
            continue
        return os.path.lexists(full)
    return False


def untracked_written(wt, ref):
    """Untracked entries of WORKTREE that merging ref deletes (the paths it writes: from the merge base to ref): a merge
    takes an ignored file as expendable and overwrites it."""
    def out(*args):
        p = sh("git", "-C", wt, *args)
        if p.returncode:
            die(f"{args[0]}: " + (brief(p.stderr or p.stdout) or f"code {p.returncode}"))
        return [f for f in p.stdout.split("\0") if f]
    diff = out("diff", "--name-only", "-z", "--no-renames", "--diff-filter=d", "".join(out("merge-base", "HEAD", ref)).strip(), ref)
    return written_over(wt, diff, out("ls-files", "-z", "--others"), os.path.lexists(os.path.join(wt, ".GIT")))


def cmd_overwrites(wt, ref):
    hit = untracked_written(wt, ref)
    if hit:
        die("merge would overwrite ignored files in WORKTREE: " + ", ".join(hit))
    return 0


def cmd_ship(main, wt, base, title):
    base = delivery(main)[0] or base
    p = sh("git", "-C", wt, "fetch", "-q", "origin")
    if p.returncode:
        die("fetch: " + brief(p.stderr))
    hit = untracked_written(wt, "origin/" + base)
    if hit:
        die("not shipped: merge would overwrite ignored files in WORKTREE: " + ", ".join(hit))
    p = sh("git", "-C", wt, "merge", "-q", "--no-edit", "origin/" + base)
    if p.returncode:
        files = sh("git", "-C", wt, "diff", "--name-only", "--diff-filter=U").stdout.split("\n")
        files = [f for f in files if f]
        if not files:
            die("merge: " + brief(p.stderr or p.stdout))
        if sh("git", "-C", wt, "merge", "--abort").returncode:
            die("merge --abort: conflict not aborted: " + ", ".join(files))
        die("conflict on update: " + ", ".join(files), 6)
    script = worktree_script()
    if not script:
        die("refresh: no sdd-worktree.py next to the script")
    p = sh(sys.executable, script, "refresh", main, wt)
    if p.returncode == 3:
        die(brief(p.stdout), 6)
    if p.returncode:
        # stderr before stdout: the command summary line "After update:" stays last in the tail
        die("refresh: " + brief("\n".join(x for x in (p.stderr, p.stdout) if x.strip())))
    n, url = open_pr(wt, base, title, main)
    (timeout, stuck, no_checks), line = ci_limits(pr_settings(main))
    if line:
        print(line, file=sys.stderr)
    return cmd_wait(url, timeout, 15.0, stuck, main, no_checks)


def cmd_land(main, wt, url, how):
    base, promote = delivery(main)
    s = pr_settings(main)  # read before the merge: a broken file merges nothing
    keep, prefix = s["delivery.delete-branch"][0] == "off", s["delivery.branch-prefix"][0]
    n, v = number(url), view(url)
    if v["state"] != "MERGED" and (how == AFTER or merge_by(main) == "human"):  # before Land after green: nothing merges
        print(f"PR #{n} {HUMAN}: {url}")
        return 8
    if v["state"] != "MERGED":  # the head is read only here: after merge the WORKTREE folder may be gone
        sha = sh("git", "-C", wt, "rev-parse", "HEAD").stdout.strip()
        title = sh("git", "-C", wt, "log", "-1", "--first-parent", "--no-merges", "--diff-filter=ACDMRTB",
                   "--format=%s").stdout.strip()
        if not sha or not title:
            die("not merged: merge: no title in the last own commit of the branch")
        try:
            code = cmd_merge(url, how, sha, title, main, wt)
        except SystemExit:
            die("not merged: merge")  # cmd_merge already printed the reason
        if code:
            return code

    def fail(step, p):
        out, err = p.stdout.strip(), p.stderr.strip()
        why = (out or err) if step in ("transport", "remove") else (err or out)
        die(f"PR #{n} merged, not finished: {step}: " + brief(why), 7)

    target = v["baseRefName"]
    if sh("git", "-C", main, "branch", "--show-current").stdout.strip() == target:
        update = ("merge --ff-only", ("merge", "--ff-only", "-q", "origin/" + target))
    else:  # the main folder is on another branch: move only the local base branch, and only forward
        update = ("fetch " + target, ("fetch", "-q", "origin", "%s:%s" % (target, target)))
    for step, cmd in (("fetch", ("fetch", "-q", "origin")), update):
        p = sh("git", "-C", main, *cmd)
        if p.returncode:
            fail(step, p)
    if os.path.isdir(wt):
        script = worktree_script()
        for sub in ("transport", "remove"):
            if not script:
                die(f"PR #{n} merged, not finished: {sub}: no sdd-worktree.py next to the script", 7)
            p = sh(sys.executable, script, sub, main, wt)
            if p.returncode:
                fail(sub, p)
            if sub == "transport":
                print(p.stdout, end="")  # the dispatcher reads the «not transported: …» line
    branch = v["headRefName"]
    if not keep and branch.startswith(prefix) and sh("git", "-C", main, "show-ref", "--verify", "--quiet",
                                           "refs/heads/" + branch).returncode == 0:
        p = sh("git", "-C", main, "branch", "-D", branch)
        if p.returncode:
            fail("branch -D", p)
    print(f"PR #{n} {url} land: done")
    if promote and (base or target) == target:
        print(promotion(target, promote[0]))
    return 0


def promotion(base, nxt):
    """The report line of the next promotion step; the command is for the user, nothing runs it."""
    return f"promotion: {base} → {nxt}: sdd-pr.py promote {shlex.quote(base)} {shlex.quote(nxt)}"


def version(rest):
    """Sort key of the part after the prefix: the leading dotted number, then a plain release above a suffix (-rc1)."""
    m = re.match(r"v?(\d+(?:\.\d+)*)(.*)", rest)
    return (tuple(int(x) for x in m.group(1).split(".")), not m.group(2), rest) if m else ((), False, rest)


def resolve(to):
    """<to> itself, or for `<prefix>*` the newest origin branch with that prefix by version; none: exit 1."""
    if not to.endswith("*"):
        return to
    p = sh("git", "ls-remote", "--heads", "origin", to)
    if p.returncode:
        die("git ls-remote: " + p.stderr.strip())
    names = [ln.split("refs/heads/", 1)[1] for ln in p.stdout.splitlines() if "refs/heads/" in ln]
    names = [x for x in names if x.startswith(to[:-1])]
    if not names:
        die(f"no branch matches {to} on origin")
    return max(names, key=lambda x: version(x[len(to) - 1:]))


def cmd_promote(frm, to):
    bad = [x for x in (frm, to) if bad_name(x)]
    if bad:
        die("not a branch name: " + ", ".join(bad))
    to = resolve(to)
    p = sh("gh", "pr", "list", "--head", frm, "--base", to, "--state", "open", "--json", "number,url")
    if p.returncode:
        die("gh pr list: " + p.stderr.strip())
    try:
        prs = json.loads(p.stdout or "[]")
        n, url = (prs[0]["number"], prs[0]["url"]) if prs else (None, None)
    except (ValueError, TypeError, KeyError, IndexError):
        die("gh pr list: not JSON: " + p.stdout[:200])
    if not prs:
        p = sh("gh", "pr", "create", "--base", to, "--head", frm, "--title", f"Promote {frm} to {to}",
               "--body", f"Promotion {frm} → {to}, opened by sdd-pr.py; merged by a person")
        if p.returncode:
            die("gh pr create: " + p.stderr.strip())
        url = p.stdout.strip().splitlines()[-1]
        n = number(url)
    print(f"PR #{n} {url} {frm} → {to}: open, not merged")
    return 0


def main(a):
    if a[:1] == ["ship"] and len(a) == 5:
        return cmd_ship(*a[1:])
    if a[:1] == ["land"] and len(a) == 5 and a[4] in ("squash", "merge", "rebase", AFTER):
        return cmd_land(*a[1:])
    if a[:1] == ["overwrites"] and len(a) == 3:
        return cmd_overwrites(*a[1:])
    if a[:1] == ["promote"] and len(a) == 3:
        return cmd_promote(*a[1:])
    if a[:1] == ["open"] and len(a) == 4:
        return cmd_open(*a[1:])
    if a[:1] == ["merge"] and len(a) in (4, 6) and a[2] in ("squash", "merge", "rebase") \
            and (len(a) == 4 or a[4] == "--title"):
        return cmd_merge(*a[1:4], *a[5:])
    if a[:1] == ["wait"] and len(a) >= 2:
        opt, rest = {"--timeout": None, "--interval": 15.0, "--stuck": None}, a[2:]
        try:  # ValueError is caught only while parsing arguments: a gh failure inside the command is code 1, not 2
            while rest:
                if rest[0] not in opt or len(rest) < 2:
                    raise ValueError
                opt[rest[0]], rest = float(rest[1]), rest[2:]
        except ValueError:
            die(USAGE, 2)
        (timeout, stuck, _), line = ci_limits(pr_settings(main_folder() or "."), opt["--timeout"], opt["--stuck"])
        if line:
            print(line, file=sys.stderr)
        return cmd_wait(a[1], timeout, opt["--interval"], stuck)
    die(USAGE, 2)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
