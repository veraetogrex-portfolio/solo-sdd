#!/usr/bin/env python3
"""Working copy of a change: git-ignored artifacts between the main folder and a worktree.

Run: sdd_worktree.py <setup|refresh|transport|undo|remove|discard> <MAIN> <WORKTREE>

Artifact set: everything under the process root (solo-sdd/ if it holds project.md, specs/ or changes/, else
openspec/), the files AGENTS.md and CLAUDE.md at the root and the worktree.paths that git ignores in MAIN.
The worktree.* keys come from solo-sdd/config of MAIN:

    worktree.paths: docs/architecture.md, docs/waiting.md
    worktree.prepare: npm ci --prefer-offline
    worktree.after-refresh: npm run build:ocr
    worktree.links: node_modules, .venv

Without a file value a key takes its item of the AGENTS.md section «Working copy» (Paths:, Prepare:, After refresh:,
values in backticks), else its default; an item value the key refuses is named on stderr and left out.
Paths are relative to the root, files or folders. The prepare command and the after-refresh command run
through sh -c in WORKTREE; setup runs the prepare command, refresh runs the after-refresh command.

Besides, setup adds to the set the documents MAIN ignores one by one (not as a whole ignored
folder): .md, .txt, .rst, .adoc up to 1 MiB, no links, nothing under worktree.links, no .env*. Their list
lives in the snapshot (<WORKTREE>.base/.sdd-ignored); after that they are handled like the whole set.

setup      copies what is needed into WORKTREE, puts the snapshot into <WORKTREE>.base/, links the worktree.links
           folders (a node_modules item up to three levels deep, any other at its path from the root, default
           node_modules and .venv), adds the items to info/exclude, runs the prepare command.
           With `delivery.base` in solo-sdd/config it first moves a worktree without own commits to
           origin/<base> (no such ref: the local <base>) unless HEAD already contains it or a local <base>
           ahead of it, and then prints «start: <ref>»; own commits or broken settings: code 1.
refresh    brings MAIN edits made after setup into WORKTREE (three-way merge: base = snapshot);
           on conflict the WORKTREE file gets markers, code 3; the snapshot is updated to MAIN.
           Without conflicts it then runs the worktree.after-refresh command (stdin closed, limit 600 s):
           success is the line «after refresh: <command> — code 0» without the command output; a non-zero
           code or a timeout prints at most the last 20 lines of its output, then a line with the command and
           the code or «timeout», code 4. The transfer and the snapshot are already updated by then. No item or
           a conflict (code 3): the command does not run.
transport  brings artifact edits into MAIN (three-way merge: base = snapshot);
           on conflict MAIN is not changed (code 3). The previous state lives in <WORKTREE>.undo/.
           Files ignored one by one outside the set that differ between MAIN and WORKTREE are named
           in the line «not transported: ...»; the exit code does not change because of them.
undo       returns MAIN to the state before the last transport.
remove     removes the links (by the <WORKTREE>.links record setup writes, never by the settings), the snapshot,
           .undo, the .start and .links records and the worktree itself.
discard    removes a worktree without its own commits (HEAD equals the <WORKTREE>.start record made by setup,
           the commit is not only in the branch being removed) together with its branch; otherwise code 1, nothing changes.
"""
import contextlib
import filecmp
import os
import re
import shutil
import signal
import subprocess
import sys

ROOTS = ["AGENTS.md", "CLAUDE.md"]
MARK = ".sdd-worktree"
LISTED = ".sdd-ignored"  # in the snapshot: documents of the set ignored one by one, separator \0
DOCS = (".md", ".txt", ".rst", ".adoc")
DOC_LIMIT = 1024 * 1024
AFTER_LIMIT = 600  # s, limit of the «After refresh:» command; tests override it
AFTER_LINES = 20  # output lines of a failed command in the refresh output


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


def delivery_base(main):
    """delivery.base of the project at main, "" for the remote's default branch.
    Broken settings raise RuntimeError naming the line: never a silent fall back to the default."""
    try:
        return read_settings(main)["delivery.base"][0]
    except (OSError, ValueError) as e:
        raise RuntimeError("settings: %s" % e)


def only_here(main, wt, head):
    """The branch of wt when commit head is in no other branch, remote branch or tag, else None."""
    branch = git(wt, "branch", "--show-current").stdout.decode().strip()
    refs = git(main, "for-each-ref", "--contains", head, "--format=%(refname)",
               "refs/heads", "refs/remotes", "refs/tags").stdout.decode().split()
    return None if [x for x in refs if x != "refs/heads/" + branch] else "branch " + branch if branch else "this worktree"


def start_at_base(main, wt, head):
    """Moves a fresh worktree to delivery.base (origin/<base>, else the local branch) unless HEAD already contains it
    or contains a local <base> with commits origin/<base> lacks (a run's local merges). The ref moved to, or None."""
    base = delivery_base(main)
    if not base:
        return None
    found = []
    for ref in ("refs/remotes/origin/" + base, "refs/heads/" + base):
        r = git(main, "rev-parse", "--verify", "-q", ref + "^{commit}")
        if r.returncode == 0:
            found.append((r.stdout.decode().strip(), ref.split("/", 2)[2]))
    if not found:
        raise RuntimeError("delivery.base %s: neither origin/%s nor the local branch exists" % (base, base))
    sha, name = found[0]
    has = lambda a, b: git(wt, "merge-base", "--is-ancestor", a, b).returncode == 0  # b contains a
    local = found[-1][0] if found[-1][1] == base else None
    if has(sha, head) or local and has(local, head) and not has(local, sha):  # the local base has unpushed merges
        return None
    own = only_here(main, wt, head)
    if own:
        raise RuntimeError("the worktree has its own commits (%s): not moved to %s" % (own, name))
    r = git(wt, "reset", "-q", "--keep", sha)
    if r.returncode:
        raise RuntimeError("git reset --keep %s: %s" % (name, r.stderr.decode("utf-8", "replace").strip()))
    write(wt + ".start", (sha + "\n").encode())
    return name


def git(repo, *args, data=None):
    return subprocess.run(["git", "-C", repo] + list(args), input=data, capture_output=True)


def read(p):
    with open(p, "rb") as f:
        return f.read()


def write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


WARNED = set()  # AGENTS.md files already named for old keywords in this process


def section(main):
    """(paths, the prepare command or None, the after-refresh command or None, linked folders) of the worktree.* keys:
    solo-sdd/config, else the «Working copy» items of AGENTS.md, else the defaults. An item value the key refuses is
    named on stderr once; broken settings raise RuntimeError naming the line: never a silent fall back."""
    agents = os.path.join(main, "AGENTS.md")
    try:
        found = migrate_agents(read(agents).decode("utf-8", "replace"))[1]
    except OSError:
        found = []
    try:
        values, bad = read_settings(main), working_items(main)[1]
    except (OSError, ValueError) as e:
        raise RuntimeError("settings: %s" % e)
    if agents not in WARNED:
        WARNED.add(agents)
        if found:
            print(migrate_hint(agents, found), file=sys.stderr)
        for ln in bad:
            print(ln, file=sys.stderr)
    # one form per path: `./data`, `data/.` and `vendor//bundle` are data and vendor/bundle; `.` alone names no path
    split = lambda key: [p for p in (os.path.normpath(v.strip()).strip("/") for v in values[key][0].split(",")
                                     if v.strip()) if p not in ("", ".")]
    return (split("worktree.paths"), values["worktree.prepare"][0] or None, values["worktree.after-refresh"][0] or None,
            split("worktree.links"))


def under_link(f, links):
    """The path lies in a linked folder: a `node_modules` item anywhere in it, any other item at its path from the root."""
    return any("node_modules" in f.split("/") if x == "node_modules" else f.startswith(x + "/") for x in links)


def listed(wt):
    try:
        return read(os.path.join(wt + ".base", LISTED)).decode("utf-8").split("\0")
    except OSError:
        return []


# A copy of a block of global/work_hooks.py (this script is deployed alone): edit it there, then run
# python3 scripts/sync_blocks.py.
# process-root:begin
TREE_MARKS = ("project.md", "specs", "changes")


def process_root(project):
    """`solo-sdd` when the project holds that tree (project.md, specs/ or changes/), else `openspec`, read until import.
    solo_sdd/process_format.py (find_tree) keeps the same rule in its own form."""
    return "solo-sdd" if any(os.path.exists(os.path.join(project, "solo-sdd", n)) for n in TREE_MARKS) else "openspec"
# process-root:end


def roots(main, wt):
    return [process_root(main)] + ROOTS + section(main)[0] + listed(wt)


def regular(p):
    return os.path.isfile(p) and not os.path.islink(p)


def loose_ignored(main):
    """Files git ignores one by one: entries from --directory without a trailing /."""
    r = git(main, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory")
    if r.returncode:
        raise RuntimeError("git ls-files: " + r.stderr.decode("utf-8", "replace").strip())
    names = [x.decode("utf-8", "replace") for x in r.stdout.split(b"\0") if x and not x.endswith(b"/")]
    # git does not collapse an ignored folder with a tracked file: its files come one by one;
    # --no-index, otherwise check-ignore treats such a folder as tracked
    hidden = set(ignored(main, sorted({os.path.dirname(f) for f in names} - {""}), "--no-index"))
    links = section(main)[3]
    return sorted(f for f in names if regular(os.path.join(main, f)) and os.path.dirname(f) not in hidden
                  and not under_link(f, links))


def is_document(main, f):
    return (f.lower().endswith(DOCS) and not os.path.basename(f).startswith(".env")
            and os.path.getsize(os.path.join(main, f)) <= DOC_LIMIT)


def not_carried(main, wt):
    """Individually ignored files outside the set that exist on both sides and differ."""
    known = set(files_under(main, roots(main, wt)))
    out = []
    for f in loose_ignored(main):
        w = os.path.join(wt, f)
        if f not in known and regular(w) and not filecmp.cmp(os.path.join(main, f), w, shallow=False):
            out.append(f)
    return out


def files_under(base, rels):
    """Relative paths of files (not links) under the artifact roots."""
    out = []
    for r in rels:
        p = os.path.join(base, r)
        if os.path.islink(p):
            continue
        if os.path.isfile(p):
            out.append(r)
        elif os.path.isdir(p):
            for d, _, fs in os.walk(p):
                for f in fs:
                    fp = os.path.join(d, f)
                    if not os.path.islink(fp):
                        out.append(os.path.relpath(fp, base))
    return sorted(set(out))


def ignored(repo, rels, *opts):
    """Which of the paths git ignores (tracked ones do not count unless --no-index is passed)."""
    if not rels:
        return []
    r = git(repo, "check-ignore", *opts, "-z", "--stdin", data="\0".join(rels).encode("utf-8"))
    if r.returncode not in (0, 1):
        raise RuntimeError("git check-ignore: " + r.stderr.decode("utf-8", "replace").strip())
    return [x.decode("utf-8") for x in r.stdout.split(b"\0") if x]


def prune_empty(path, stop):
    path = os.path.dirname(path)
    stop = os.path.abspath(stop)
    while os.path.abspath(path) != stop and path.startswith(stop):
        try:
            os.rmdir(path)
        except OSError:
            return
        path = os.path.dirname(path)


def find_links(main, links):
    """The worktree.links folders of main: a `node_modules` item no deeper than three levels (not entering them or
    .git), any other item at its path from the root."""
    found = []
    for d, dirs, _ in os.walk(main) if "node_modules" in links else ():
        rel = os.path.relpath(d, main)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if ".git" in dirs:
            dirs.remove(".git")
        if "node_modules" in dirs:
            dirs.remove("node_modules")
            found.append(os.path.normpath(os.path.join(rel, "node_modules")))
        if depth >= 2:
            dirs[:] = []
    return found + [x for x in links if x != "node_modules" and os.path.isdir(os.path.join(main, x))]


def link_modules(src, dst, level=0):
    """A real node_modules in WORKTREE: links to MAIN entries, package links copied with the same target."""
    os.makedirs(dst)
    for name in sorted(os.listdir(src)):
        s, d = os.path.join(src, name), os.path.join(dst, name)
        if os.path.islink(s):
            os.symlink(os.readlink(s), d)
        elif os.path.isdir(s) and level == 0 and (name.startswith("@") or name == ".bin"):
            link_modules(s, d, 1)
        elif os.path.isdir(s) and name.startswith("."):
            continue
        else:
            os.symlink(os.path.abspath(s), d)
    if level == 0:
        write(os.path.join(dst, MARK), b"")


def add_exclude(main, links):
    r = git(main, "rev-parse", "--git-common-dir")
    if r.returncode:
        raise RuntimeError("git rev-parse: " + r.stderr.decode("utf-8", "replace").strip())
    p = os.path.join(main, r.stdout.decode().strip(), "info", "exclude")
    have = read(p).decode("utf-8").splitlines() if os.path.exists(p) else []
    # node_modules is linked at any depth up to three levels; any other item only at its path from the root
    add = [x for x in (x if x == "node_modules" else "/" + x for x in links) if x not in have]
    if add:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            if have and not read(p).endswith(b"\n"):
                f.write("\n")
            f.write("\n".join(add) + "\n")


def setup(main, wt):
    head = git(wt, "rev-parse", "HEAD")  # record the start before anything else: needed even when preparation fails
    if head.returncode:
        raise RuntimeError("git rev-parse: " + head.stderr.decode("utf-8", "replace").strip())
    write(wt + ".start", head.stdout)
    start = start_at_base(main, wt, head.stdout.decode().strip())
    base = wt + ".base"
    paths, cmd, _, linked = section(main)
    known = files_under(main, [process_root(main)] + ROOTS + paths)
    extra = [f for f in loose_ignored(main) if f not in known and is_document(main, f)]
    cand = [f for f in known + extra if not os.path.exists(os.path.join(wt, f))]
    copied = ignored(main, cand)
    os.makedirs(base, exist_ok=True)  # refresh needs a snapshot even when there is nothing to copy
    for f in copied:
        data = read(os.path.join(main, f))
        write(os.path.join(wt, f), data)
        write(os.path.join(base, f), data)
    extra = [f for f in extra if os.path.isfile(os.path.join(base, f))]
    if extra:
        write(os.path.join(base, LISTED), "\0".join(extra).encode("utf-8"))
    made = listed_links(wt)
    before = len(made)
    try:
        for rel in find_links(main, linked):
            dst = os.path.join(wt, rel)
            if rel in linked and "/" in rel and not os.path.lexists(dst):  # a named item gets its parent folders
                os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.lexists(dst) or not os.path.isdir(os.path.dirname(dst)):
                continue
            if os.path.basename(rel) == "node_modules":
                link_modules(os.path.join(main, rel), dst)
            else:
                os.symlink(os.path.abspath(os.path.join(main, rel)), dst)
            made.append(rel)
            write(wt + ".links", "\0".join(made).encode("utf-8"))  # after each link: a setup failing later leaves the record
    except BaseException:  # a later link failing still hides the links made before it; its own error is the one shown
        with contextlib.suppress(RuntimeError, OSError):
            add_exclude(main, linked)
        raise
    add_exclude(main, linked)
    if cmd:
        r = subprocess.run(["sh", "-c", cmd], cwd=wt, stdin=subprocess.DEVNULL)
        if r.returncode:
            raise RuntimeError("prepare command exited with code %d: %s" % (r.returncode, cmd))
    if start:
        print("start: " + start)
    print("copied files %d, link folders %d, command: %s" % (len(copied), len(made) - before, cmd or "none"))
    return 0


def merge3(mine, base, theirs):
    """git merge-file merge; None on conflict."""
    r = subprocess.run(["git", "merge-file", "-p", mine, base, theirs], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def plan(main, wt):
    """What to do with MAIN: (create/write {rel: bytes}, delete [rel], conflicts [rel])."""
    base = wt + ".base"
    rels = roots(main, wt)
    in_base = set(files_under(base, rels)) if os.path.isdir(base) else set()
    in_wt = set(ignored(wt, files_under(wt, rels))) | (in_base & set(files_under(wt, rels)))
    put, drop, bad = {}, [], []
    history = process_root(main) + "/changes/archive/"  # the archive only grows: a file gone from WORKTREE stays
    for f in sorted(in_base | in_wt):
        m, b, w = (os.path.join(x, f) for x in (main, base, wt))
        wd = read(w) if f in in_wt else None
        if wd is None and f.startswith(history):
            continue
        bd = read(b) if f in in_base else None
        md = read(m) if os.path.isfile(m) else None
        if wd is not None and bd is None:
            if md is None:
                put[f] = wd
            elif md != wd:
                bad.append(f)
        elif wd is not None:
            if wd == bd:
                continue
            res = merge3(m, b, w) if md is not None else None
            if res is None:
                bad.append(f)
            elif res != md:
                put[f] = res
        elif md is not None:
            if md == bd:
                drop.append(f)
            else:
                bad.append(f)
    return put, drop, bad


def merge_marked(mine, base, theirs):
    """Merge with conflict markers: (result, whether clean)."""
    r = subprocess.run(["git", "merge-file", "-p", "-L", "WORKTREE", "-L", "base", "-L", "MAIN", mine, base, theirs],
                       capture_output=True)
    if r.returncode < 0 or r.returncode > 127:
        raise RuntimeError("git merge-file: " + r.stderr.decode("utf-8", "replace").strip())
    return r.stdout, r.returncode == 0


def after_refresh(wt, cmd):
    """The "After update:" command in WORKTREE: 0 or 4. The command output is printed only on failure;
    the line with the command and summary comes last, so it lands in the output tail that sdd-pr.py ship takes."""
    p = subprocess.Popen(["sh", "-c", cmd], cwd=wt, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, start_new_session=True)
    try:
        out = p.communicate(timeout=AFTER_LIMIT)[0]
        verdict = "code %d" % p.returncode
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)  # own process group: the build stops together with sh
        except OSError:
            pass
        try:
            out = p.communicate(timeout=10)[0]  # read the rest of the output; a process that left the group may hold the pipe
        except subprocess.TimeoutExpired as e:
            out = e.output or b""
        p.wait()
        verdict = "timeout %g s" % AFTER_LIMIT
    else:
        if p.returncode == 0:
            print("after refresh: %s — code 0" % cmd)
            return 0
    for ln in out.decode("utf-8", "replace").splitlines()[-AFTER_LINES:]:
        print(ln)
    print("after refresh: %s — %s" % (cmd, verdict))
    return 4


def refresh(main, wt):
    base = wt + ".base"
    if not os.path.isdir(base):
        raise RuntimeError("no snapshot %s: run setup first" % base)
    rels = roots(main, wt)
    in_base = set(files_under(base, rels))
    names = sorted(set(ignored(main, files_under(main, rels))) | in_base)
    copied = merged = deleted = 0
    bad, keep = [], set()  # keep: a conflict without markers, the snapshot stays old so transport does not carry the file silently
    for f in names:
        m, b, w = (os.path.join(x, f) for x in (main, base, wt))
        md = read(m) if os.path.isfile(m) else None
        bd = read(b) if f in in_base else None
        wd = read(w) if os.path.isfile(w) else None
        if md is not None and bd is None:
            if wd is None:
                write(w, md)
                copied += 1
            elif wd != md:
                bad.append(f)
                keep.add(f)
        elif md is not None:
            if md != bd:
                if wd is None:
                    bad.append(f)
                    keep.add(f)
                else:
                    res, clean = merge_marked(w, b, m)
                    write(w, res)
                    if clean:
                        merged += 1
                    else:
                        bad.append(f)
        elif wd is not None:
            if wd == bd:
                os.unlink(w)
                prune_empty(w, wt)
                deleted += 1
            else:
                bad.append(f)
                keep.add(f)
        if f in keep:
            continue
        if md is None:
            if os.path.isfile(b):
                os.unlink(b)
                prune_empty(b, base)
        elif md != bd:
            write(b, md)
    if bad:
        print("conflict, resolve in WORKTREE: " + ", ".join(bad))
        return 3
    print("refreshed: copied %d, merged %d, deleted %d" % (copied, merged, deleted))
    after = section(main)[2]
    return after_refresh(wt, after) if after else 0


def transport(main, wt):
    skipped = not_carried(main, wt)
    if skipped:
        print("not transported: " + ", ".join(skipped))
    put, drop, bad = plan(main, wt)
    if bad:
        print("conflict, MAIN not changed: " + ", ".join(bad))
        return 3
    if not (put or drop):
        print("transported: nothing changed")
        return 0
    undo = wt + ".undo"
    shutil.rmtree(undo, ignore_errors=True)
    os.makedirs(undo)
    created = []
    for f in list(put) + drop:
        m = os.path.join(main, f)
        if os.path.isfile(m):
            write(os.path.join(undo, "files", f), read(m))
        else:
            created.append(f)
    with open(os.path.join(undo, ".created"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(created) + ("\n" if created else ""))
    merged = sum(1 for f in put if os.path.isfile(os.path.join(main, f)))
    for f, data in put.items():
        write(os.path.join(main, f), data)
    for f in drop:
        os.unlink(os.path.join(main, f))
        prune_empty(os.path.join(main, f), main)
    print("transported: copied %d, merged %d, deleted %d" % (len(put) - merged, merged, len(drop)))
    return 0


def undo(main, wt):
    u = wt + ".undo"
    if not os.path.isdir(u):
        print("nothing to undo")
        return 0
    cr = os.path.join(u, ".created")
    r = git(main, "ls-files", "-z")
    if r.returncode:
        raise RuntimeError("git ls-files: " + r.stderr.decode("utf-8", "replace").strip())
    # a file git tracks again (a rollback reset to the commit before a merge that removed it from the index) stays
    tracked = set(r.stdout.decode("utf-8", "replace").split("\0"))
    for f in (read(cr).decode("utf-8").splitlines() if os.path.exists(cr) else []):
        p = os.path.join(main, f)
        if os.path.isfile(p) and f not in tracked:
            os.unlink(p)
            prune_empty(p, main)
    saved = os.path.join(u, "files")
    for f in files_under(saved, ["."]) if os.path.isdir(saved) else []:
        write(os.path.join(main, f), read(os.path.join(saved, f)))
    shutil.rmtree(u)
    print("undone")
    return 0


def listed_links(wt):
    """The folders of the <WORKTREE>.links record, [] without one."""
    try:
        return [x for x in read(wt + ".links").decode("utf-8").split("\0") if x]
    except OSError:
        return []


def unlink_links(wt):
    """Removes the folders setup linked, by its record <WORKTREE>.links (a worktree set up before the record: the
    default node_modules and .venv); never reads the settings, so a broken or changed file does not block cleanup."""
    for rel in listed_links(wt) if os.path.exists(wt + ".links") else find_links(wt, ["node_modules", ".venv"]):
        p = os.path.join(wt, rel)
        if os.path.islink(p):
            os.unlink(p)
        elif os.path.isfile(os.path.join(p, MARK)):
            shutil.rmtree(p)  # links inside are not followed, targets in MAIN are intact


def rmdir_temp_parent(wt):
    parent = os.path.dirname(wt)
    if os.path.basename(parent).startswith("sdd-"):  # the dispatcher's mktemp folder: remove it if empty
        try:
            os.rmdir(parent)
        except OSError:
            pass


def remove(main, wt):
    # uncommitted work: refuse before cleanup, otherwise the worktree would be left without a snapshot and links
    dirty = git(wt, "status", "--porcelain")
    if dirty.returncode or dirty.stdout.strip():
        raise RuntimeError("git worktree remove: the worktree has uncommitted changes, nothing removed")
    unlink_links(wt)
    for x in (wt + ".base", wt + ".undo"):
        shutil.rmtree(x, ignore_errors=True)
    if os.path.exists(wt + ".links"):
        os.unlink(wt + ".links")
    # without --force: ignored copies and excluded links do not get in the way, and git will not let uncommitted work be erased
    r = git(main, "worktree", "remove", wt)
    if r.returncode:
        raise RuntimeError("git worktree remove: " + r.stderr.decode("utf-8", "replace").strip())
    if os.path.exists(wt + ".start"):
        os.unlink(wt + ".start")
    rmdir_temp_parent(wt)
    print("worktree removed")
    return 0


def discard(main, wt):
    try:
        start = read(wt + ".start").decode("utf-8").strip()
    except OSError:
        raise RuntimeError("no start record %s.start: nothing removed" % wt)
    r = git(wt, "rev-parse", "HEAD")
    if r.returncode:
        raise RuntimeError("git rev-parse: %s: nothing removed" % r.stderr.decode("utf-8", "replace").strip())
    head = r.stdout.decode().strip()
    if head != start:
        raise RuntimeError("the worktree has its own commits (HEAD %s, start %s): nothing removed" % (head, start))
    branch = git(wt, "branch", "--show-current").stdout.decode().strip()
    own = only_here(main, wt, head)
    if own:
        raise RuntimeError("commit %s exists only in %s: nothing removed" % (head, own))
    unlink_links(wt)
    for x in (wt + ".base", wt + ".undo"):
        shutil.rmtree(x, ignore_errors=True)
    if os.path.exists(wt + ".links"):
        os.unlink(wt + ".links")
    r = git(main, "worktree", "remove", "--force", wt)
    if r.returncode:
        raise RuntimeError("git worktree remove: " + r.stderr.decode("utf-8", "replace").strip())
    if branch:
        r = git(main, "branch", "-D", branch)
        if r.returncode:
            raise RuntimeError("git branch -D: " + r.stderr.decode("utf-8", "replace").strip())
    os.unlink(wt + ".start")
    rmdir_temp_parent(wt)
    print("worktree discarded: " + (branch or "no branch"))
    return 0


COMMANDS = {"setup": setup, "refresh": refresh, "transport": transport, "undo": undo, "remove": remove, "discard": discard}


def main_cli(argv):
    if len(argv) != 4 or argv[1] not in COMMANDS:
        print("usage: sdd_worktree.py <setup|refresh|transport|undo|remove|discard> <MAIN> <WORKTREE>", file=sys.stderr)
        return 2
    main, wt = os.path.abspath(argv[2]), os.path.abspath(argv[3])
    try:
        return COMMANDS[argv[1]](main, wt)
    except (RuntimeError, OSError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main_cli(sys.argv))
