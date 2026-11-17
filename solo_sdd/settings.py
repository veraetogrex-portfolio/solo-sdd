"""Project settings: `solo-sdd/config` and the `solo-sdd config list|get|set|unset` command.

The block between the settings markers is copied into the scripts of global/ that hold its markers
(they are laid out as separate files and run on /usr/bin/python3 3.9) by python3 scripts/sync_blocks.py: edit it here.
"""
import json
import os
import re
import subprocess
import sys

from solo_sdd import process_format as pf, providers

# settings:begin
# solo-sdd/config: one `key: value` per line, lines starting with # are comments, list values are separated by commas.
SETTINGS_FILE = "solo-sdd/config"
# key -> (type: choice | int | list | model | names | paths | text, allowed values (None: any), default, default under `mode: team` (None: the same));
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
}
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
    if kind == "int":
        low = INT_MIN.get(key, 1)
        if not (v.isascii() and v.isdigit()) or int(v) < low:
            raise SettingsError("%s takes a whole number from %d, not %r" % (key, low, v))
        return str(int(v))
    items = [i.strip() for i in v.split(",")] if kind in ("list", "paths", "names") else [v]
    items = [i for i in items if i]
    if not items and (default == "" or key == IGNORE_KEY):  # an empty git.ignore removes the block
        return ""
    paths = kind in ("path", "paths")
    for i in items if key == IGNORE_KEY else ():
        hides = "starts with #: git reads it as a comment" if i.startswith("#") else ignore_hides(i)
        if hides:
            raise SettingsError(ignore_refusal(key, i, hides))
    bad = [i for i in items if (bad_path(i) if paths else not good_name(i) if kind == "names" else
                                i not in allowed if allowed else bad_name(i))]
    if kind == "names" and len(set(items)) < len(items):
        raise SettingsError("%s takes each name once, not %r" % (key, v))
    if bad or not items:
        what = ", ".join(allowed) if allowed else (
            "relative paths (no spaces, \\ or .., not starting with / or -)" if paths else
            "names (lowercase letters, digits and -, not starting with -)" if kind == "names" else
            "branch names (no spaces, ~^:?[\\ or .., not starting with - or +)") + (
            ", separated by commas" if kind in ("list", "paths", "names") else "")
        raise SettingsError("%s takes %s, not %r" % (key, what, v))
    return ", ".join(items)


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
    """{key: (value, source)}: source `file`, else `AGENTS.md` (agents: agents_delivery), else `mode` (the team default
    under `mode: team`), else `default`."""
    team = found.get("mode") == "team"
    agents = agents or {}
    out = {}
    for key, (_, _, default, team_default) in registry.items():
        if key in found:
            out[key] = (found[key], "file")
        elif key in agents:
            out[key] = (agents[key], "AGENTS.md")
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


def agents_delivery(root, registry=REGISTRY):
    """{key: value} of the «## Delivery» section of AGENTS.md at root, the old source of its keys: the first allowed
    «Mode:» and «Merge:» items, the first non-empty «PR title:» and «Deploy:» texts trimmed and as written, and the
    backquoted patterns of every «Owner only:» item; a file that cannot be opened: {}."""
    try:
        with open(os.path.join(root, "AGENTS.md"), encoding="utf-8", errors="replace") as f:  # other readers own the encoding
            lines = f.read().splitlines()
    except OSError:
        return {}
    out, inside = {}, False
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
# The block above is copied into files that cannot import the package: the agents default is the detected ones here.
REGISTRY["agents"] = REGISTRY["agents"][:2] + (", ".join(providers.detected()), None)

GROUPS = ("process", "delivery", "dispatch", "agents", "git", "integrations", "checklists")
# key or pattern -> (group, what it changes); kept out of the block above: the scripts do not show them
ABOUT = {
    "mode": ("process", "Solo or team project; a team project takes the team default of every key that has one."),
    "delivery.mode": ("delivery", "How finished work reaches the base branch: a local merge or a pull request."),
    "delivery.merge": ("delivery", "How a pull request is merged into the base branch; a local merge follows delivery.local-merge."),
    "delivery.local-merge": ("delivery", "How sdd-dispatch.py land-local merges a change branch in local delivery: a merge commit, one squashed commit, or a rebase."),
    "delivery.merge-by": ("delivery", "Who merges into the base branch: the agent, or a person while the agent waits."),
    "delivery.base": ("delivery", "The branch worktrees start from and merges go into; empty means the remote's default branch."),
    "delivery.promote": ("delivery", "The branches after the base in order, each promoted from the one before by a pull request."),
    "delivery.pr-title": ("delivery", "The rule ship and the dispatcher follow for a pull request title."),
    "delivery.deploy": ("delivery", "What a push or a merge deploys and where, so an agent stops before it and asks."),
    "delivery.owner-only": ("delivery", "Paths a merge waits for the owner on, as globs, besides the CI workflows and the settings file."),
    "delivery.ci-timeout": ("delivery", "The most seconds sdd-pr.py wait and ship give CI before the result infra; a --timeout flag wins."),
    "delivery.ci-stuck": ("delivery", "The seconds a required check may stay missing or not started after the others finished; a --stuck flag wins."),
    "delivery.ci-no-checks": ("delivery", "The seconds a pull request may show no checks at all before the wait ends."),
    "delivery.require-ci": ("delivery", "Whether a pull request needs checks: off merges one without any, as CI: none, while the base branch requires none."),
    "delivery.code-scanning": ("delivery", "What open code scanning alerts do after green checks: gate waits for a fix, warn prints them and merges, off skips them."),
    "delivery.delete-branch": ("delivery", "Whether merge and land delete the branch of a merged pull request."),
    "delivery.draft": ("delivery", "Whether a pull request opens as a draft, marked ready for review right before the merge."),
    "delivery.branch-prefix": ("delivery", "The start of every change branch name: the branch of a change is this prefix and the change id."),
    "delivery.plan-prefix": ("delivery", "The start of the branch spec-plan commits a plan on in pull request delivery, before the first change id."),
    "dispatch.limit": ("dispatch", "The most orchestrators the dispatcher runs at the same time."),
    "process.review-rounds": ("process", "The most independent acceptance rounds of one change, plus one extra round for findings on the last fix, before it counts as not done."),
    "process.light-path": ("process", "Whether a small code edit outside every spec may skip the change cycle."),
    "process.light-path.max-files": ("process", "The most files a light path edit may change."),
    "process.max-tasks": ("process", "The most tasks one change may hold; solo-sdd validate refuses more and spec-plan splits a larger unit."),
    "process.bugfix-max-tasks": ("process", "The most tasks of a bug fix change; the smaller of it and process.max-tasks holds."),
    "process.requirement-max-chars": ("process", "The most characters of one requirement text; solo-sdd validate refuses a longer one."),
    "process.audit-every": ("process", "After how many archives spec-next proposes a spec-audit of the main specs."),
    "process.analyze": ("process", "Whether spec-plan and spec-next run the spec-analyze check before code; off skips it and the report says so."),
    "commit.light-prefix": ("process", "The text a light path commit subject starts with; work-status, report and spec-plan count such commits by it as plain text."),
    "reply.language": ("agents", "The language the stop hook expects in the agent's final reply; off checks none."),
    "agents": ("agents", "The agents this project is worked on with; doctor warns about one the installation lacks."),
    "rules.scope": ("agents", "Where the agents get the rules: a block in this project's AGENTS.md, or only the global rules."),
    "agents.orchestrator-model": ("agents", "The model the dispatcher launches each orchestrator on; the guard hook refuses one outside the machine main list."),
    "agents.review-model": ("agents", "The model of the independent reviewer; empty runs it on the session's main model, the guard hook refuses one outside the machine main list."),
    "agents.lookup-model": ("agents", "The model of the search subagents; the guard hook refuses one outside the machine cheap list."),
    "agents.test-model": ("agents", "The model of paid product calls in tests, acceptance and experiments, within the machine test allowlist."),
    "agents.dispatcher-effort": ("agents", "The effort the dispatcher session is started with."),
    "agents.executor": ("agents", "Who writes the change code: the lead agent itself, or Codex executors as if the owner named codex-orchestration."),
    "git.ignore": ("git", "What the project keeps out of git: solo-sdd ignore --write puts these .gitignore lines into its block; an item starting with ! keeps a path in."),
    "integrations": ("integrations", "The integrations enabled in this project, by folder name."),
    "integrations.off": ("integrations", "The bundled integrations switched off in this project, by folder name."),
    "checklist.<name>.paths": ("checklists", "The files a person checks by this list before merging, as globs."),
    "checklist.<name>.file": ("checklists", "The markdown file of the list's items, from the repository root."),
}
KIND_TEXT = {"model": "one model name of ASCII letters, digits, ., -, _, [ and ]", "text": "one line, at most %d characters" % TEXT_MAX, "names": "lowercase letters, digits and -, separated by commas",
             "paths": "relative paths, separated by commas", "path": "a relative path",
             "choice": "a branch name", "list": "branch names, separated by commas"}


def pattern_of(key, registry=REGISTRY):
    """The registry key or the pattern a key is described under; None when the key is unknown."""
    if key in registry or key in PATTERNS:
        return key
    for pattern in PATTERNS:
        head, tail = pattern.split("<name>")
        if key.startswith(head) and key.endswith(tail) and good_name(key[len(head):len(key) - len(tail)]):
            return pattern
    return None


def describe(key, values, registry=REGISTRY):
    """{field: value} of a key, a pattern or a pattern key: values is the `effective` dict; a pattern has no value."""
    name = pattern_of(key, registry)
    kind, allowed, default, team = registry.get(name) or PATTERNS[name]
    group, about = ABOUT.get(name, ("", ""))  # a key of a registry passed to run, described nowhere
    row = {"key": key, "group": group, "about": about,
           "type": "%s: %s" % (kind, ", ".join(allowed) if allowed else KIND_TEXT[kind] if kind != "int" else
                               "a whole number from %d" % INT_MIN.get(name, 1)),
           "allowed": list(allowed) if allowed else None, "default": default, "team_default": team}
    if key not in PATTERNS:
        row["value"], row["source"] = values.get(key, ("", "default"))
    return row


def describe_text(row):
    lines = [row["key"], "  group: " + row["group"], "  about: " + row["about"], "  type: " + row["type"],
             "  default: " + (row["default"] or "(none)"), "  team default: " + (row["team_default"] or "(same)")]
    if "value" in row:
        lines.append("  value: %s (%s)" % (row["value"] or "(none)", row["source"]))
    return "\n".join(lines)


def set_text(text, key, value):
    """The text with the line of key replaced by `key: value` (appended when missing); value None removes it.
    Every other line keeps its bytes and place. The text must parse: a key has at most one line."""
    lines = text.splitlines(True)
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s and not s.startswith("#") and s.partition(":")[0].strip() == key:
            if value is None:
                del lines[i]
            else:
                lines[i] = "%s: %s%s" % (key, value, ln[len(ln.rstrip("\r\n")):])
            return "".join(lines)
    if value is None:
        return text
    end = "\r\n" if "\r\n" in text else "\n"
    return text + ("" if not text or text.endswith(("\n", "\r")) else end) + "%s: %s%s" % (key, value, end)


IGNORE_HINT = "run: solo-sdd ignore --write"


def tree_refusal(root, value):
    """Why a git.ignore value would hide a file or folder of the project's own solo-sdd/ tree (the archive aside) or
    its AGENTS.md or CLAUDE.md, or None: the names a capability, a change or an integration has on disk."""
    paths = ["AGENTS.md", "CLAUDE.md"]
    top = os.path.join(root, "solo-sdd")
    for d, dirs, files in os.walk(top):
        rel = os.path.relpath(d, root).replace(os.sep, "/")
        if rel == "solo-sdd/changes":
            dirs[:] = [x for x in dirs if x.lower() != "archive"]
        paths += [rel + "/" + x + "/" for x in dirs] + [rel + "/" + x for x in files]
    for item in [i.strip() for i in value.split(",") if i.strip()]:
        hides = ignore_hides(item, paths)
        if hides:
            return ignore_refusal(IGNORE_KEY, item, hides)
    return None
BRANCH_KEYS = ("delivery.branch-prefix", "delivery.plan-prefix")


def git(root, *args):
    """git in root -> (code, stdout, stderr); a git that cannot run is code 127 with the reason."""
    try:
        r = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, stdin=subprocess.DEVNULL,
                           timeout=30, env=dict(os.environ, LC_ALL="C"))  # git's own words: "not a git repository"
    except (OSError, subprocess.SubprocessError) as e:
        return 127, "", str(e)
    return r.returncode, r.stdout, r.stderr.strip()


def prefix_refusal(root, old, new):
    """Why the branch prefixes of new cannot replace those of old ({key: (value, source)} both), or None: equal branch
    and plan prefixes, a prefix git takes no branch name under, a local branch of an open change under the old branch
    prefix. Outside a git repository the branches pass; a listing that fails refuses."""
    was, now = [old.get(k, ("",))[0] for k in BRANCH_KEYS], [new.get(k, ("",))[0] for k in BRANCH_KEYS]
    if was == now:
        return None
    if now[0] == now[1]:
        return "delivery.branch-prefix and delivery.plan-prefix would both be %s: a plan branch would read as a change branch" % now[0]
    for key, a, b in zip(BRANCH_KEYS, was, now):
        code, _, err = git(root, "check-ref-format", "--branch", b + "a") if a != b else (0, "", "")
        if code == 127:
            return "%s: cannot run git to check the name: %s" % (key, err)
        if code:
            return "%s: %s is no valid branch name, so %s cannot start one (%s)" % (key, b + "a", b, err)
    if was[0] == now[0]:
        return None
    code, out, err = git(root, "for-each-ref", "--format=%(refname)", "refs/heads/")
    if code:
        return None if "not a git repository" in err else "delivery.branch-prefix: cannot list the branches: " + err
    base = os.path.join(root, os.path.dirname(SETTINGS_FILE), "changes")
    opened = {d for d in (os.listdir(base) if os.path.isdir(base) else ()) if d != "archive"}
    names = [r[len("refs/heads/"):] for r in out.split()]
    left = [n for n in names if n.startswith(was[0]) and n[len(was[0]):] in opened]
    if left:
        return ("delivery.branch-prefix stays %s: open changes still have branches under it: %s; merge or delete them"
                " first, the dispatcher would no longer see them" % (was[0], ", ".join(left)))
    return None


def unknown_key(key, registry=REGISTRY):
    return None if entry(key, registry) else "unknown key %s; known: %s" % (key, ", ".join(list(registry) + list(PATTERNS)))


def run(args, cwd=".", registry=REGISTRY):
    """`config list [--json] | describe [<key>] | get <key> | set <key> <value> | unset <key>`; the exit code, or None
    on bad arguments."""
    if not args or (args[0], len(args)) not in (("list", 1), ("describe", 1), ("describe", 2), ("get", 2), ("set", 3),
                                                ("unset", 2)) and args != ["list", "--json"]:
        return None
    tree = pf.find_tree(cwd)
    if tree is None:
        print("no solo-sdd/ tree")
        return 1
    root = str(tree.parent)
    try:
        text = read_settings_text(root)
        agents = agents_delivery(root, registry)
        values = effective(parse_settings(text, registry), registry, agents)
    except (OSError, ValueError) as e:
        print(e)
        return 1
    if args == ["list"]:
        for key, (value, source) in values.items():
            print("%s %s %s" % (key, value, source))
        return 0
    if args == ["list", "--json"]:
        print(json.dumps([describe(key, values, registry) for key in values], indent=2, ensure_ascii=False))
        return 0
    if args == ["describe"]:
        keys = list(registry) + list(PATTERNS) + [k for k in values if k not in registry]
        print("\n".join(describe_text(describe(key, values, registry)) for key in keys))
        return 0
    bad = None if args[0] == "describe" and args[1] in PATTERNS else unknown_key(args[1], registry)
    if bad:
        print(bad)
        return 1
    if args[0] == "describe":
        print(describe_text(describe(args[1], values, registry)))
        return 0
    if args[0] == "get":
        value, source = values.get(args[1], ("", "default"))  # a pattern key not set reads as empty
        print(value)
        print("source: " + source, file=sys.stderr)
        return 0
    value = None
    if args[0] == "set":
        try:
            value = check_value(args[1], args[2], registry)
        except SettingsError as e:
            print(e)
            return 1
    new = set_text(text, args[1], value)
    why = prefix_refusal(root, values, effective(parse_settings(new, registry), registry, agents)) or (
        tree_refusal(root, value) if args[1] == IGNORE_KEY and value else None)
    if why:
        print(why)
        return 1
    if new != text:
        try:
            with open(os.path.join(root, SETTINGS_FILE), "w", encoding="utf-8", newline="") as f:
                f.write(new)
        except OSError as e:
            print(e)
            return 1
    print("%s: %s" % (args[1], value) if value is not None else "%s: removed, in effect %s" % (
        args[1], effective(parse_settings(new, registry), registry, agents).get(args[1], ("",))[0]))
    if args[1] == IGNORE_KEY:
        print(IGNORE_HINT)
    return 0

