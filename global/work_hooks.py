#!/usr/bin/python3
"""Claude Code workflow hooks. Subcommands: context, subagent-context, guard, claims, stop, beat, end, status.

Source of the requirements: analysis of sessions 2026-09-16..2026-10-15 (repeated "read agents md",
"continue", "archive", "who will merge", "status?", secrets, expensive models).
Any internal error lets the action through (fail-open) and is written to hook-state/errors.log.
"""
import datetime
import fnmatch
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.realpath(__file__))
STATE = os.path.join(HOME, ".claude", "hook-state")
TMP_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")
UI_EXT = (".html", ".htm", ".css", ".scss", ".sass", ".less", ".tsx", ".jsx", ".vue", ".svelte")
BROWSER_TOOLS = ("mcp__claude-in-chrome__", "mcp__agent-browser__", "mcp__peekaboo__")
BROWSER_SKILLS = ("ui-check", "agent-browser", "claude-in-chrome", "webapp-testing", "run", "web-perf")
# Built-in browser signs; the `browser` key of model-policy.json adds to them (browser_signs) and cannot remove one.
BROWSER_BASH = ("agent-browser", "playwright", "puppeteer", "--headless", "chrome-devtools", "screencapture",
                "--remote-debugging-port", "json/version", "webSocketDebuggerUrl")
ENV_FILE = r"(?:[^\s;&|'\"<>]*/)?(?:[\w.-]*\.env|\.env\.(?!(?:example|sample|template|dist)(?![\w.-]))[\w.-]+)(?![\w.-])"
SECRET_WORDS = {"KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "WEBHOOK", "CREDENTIAL"}


# settings:begin
# solo-sdd/config: one `key: value` per line, lines starting with # are comments, list values are separated by commas.
SETTINGS_FILE = "solo-sdd/config"
# key -> (type: choice | int | list | names, allowed values (None: any), default, default under `mode: team` (None: the same));
# a key with the default "" takes an empty value, read as "not set"
REGISTRY = {
    "mode": ("choice", ("solo", "team"), "solo", None),
    "delivery.mode": ("choice", ("local", "pr"), "local", "pr"),
    "delivery.merge": ("choice", ("squash", "merge", "rebase"), "squash", None),
    "delivery.merge-by": ("choice", ("agent", "human"), "agent", "human"),  # who merges into the base
    "delivery.base": ("choice", None, "", None),  # "": the remote's default branch
    "delivery.promote": ("list", None, "", None),  # branches after the base in order; `release/*`: the newest by version
    "dispatch.limit": ("int", None, "2", None),
    "process.review-rounds": ("int", None, "3", None),
    "process.light-path": ("choice", ("on", "off"), "on", None),  # off: every code edit goes through a change
    "process.light-path.max-files": ("int", None, "3", None),
    "reply.language": ("choice", ("ru", "en", "off"), "off", None),
    "agents": ("list", ("claude", "codex", "cursor", "other"), "claude, codex, other", None),
    "rules.scope": ("choice", ("project", "global"), "project", None),  # project: init writes the rules block into AGENTS.md
    "integrations": ("names", None, "", None),  # the enabled integrations, by folder name (solo_sdd/integrations.py)
    "integrations.off": ("names", None, "", None),  # the bundled integrations switched off, by folder name
}
# pattern keys: <name> is lowercase letters, digits and -, not starting with -; set keys show in `config list` as `file`
PATTERNS = {
    "checklist.<name>.paths": ("paths", None, "", None),  # globs of the files a person checks by the list
    "checklist.<name>.file": ("path", None, "", None),  # a markdown file of `- [ ]` items, from the repository root
}
NAME_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789-"


class SettingsError(ValueError):
    pass


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
    if kind == "int":
        if not (v.isascii() and v.isdigit()) or int(v) < 1:
            raise SettingsError("%s takes a whole number from 1, not %r" % (key, v))
        return str(int(v))
    items = [i.strip() for i in v.split(",")] if kind in ("list", "paths", "names") else [v]
    items = [i for i in items if i]
    if not items and default == "":
        return ""
    paths = kind in ("path", "paths")
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
    """{key: value} of the first allowed «Mode:» and «Merge:» items of the «## Delivery» section of AGENTS.md at root,
    the old source of delivery.mode and delivery.merge; a file that cannot be opened: {}."""
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
    return out


def read_settings(root, registry=REGISTRY):
    """Settings in effect of the project at root; no file means all defaults; a broken file raises SettingsError."""
    return effective(parse_settings(read_settings_text(root), registry), registry, agents_delivery(root, registry))
# settings:end


# ---------- common ----------

def log_error(cmd, e):
    try:
        os.makedirs(STATE, exist_ok=True)
        with open(os.path.join(STATE, "errors.log"), "a") as f:
            f.write("%s %s %r\n" % (datetime.datetime.now().isoformat(timespec="seconds"), cmd, e))
    except Exception:
        pass


def reply_language(root):
    """reply.language of solo-sdd/config, else SOLO_SDD_REPLY_LANG, else the default; a broken file: the defaults and a log line."""
    try:
        value, source = read_settings(root)["reply.language"]
    except Exception as e:
        log_error("stop settings %s" % root, e)
        value, source = effective({})["reply.language"]
    return value if source == "file" else os.environ.get("SOLO_SDD_REPLY_LANG") or value


def human_merge(root):
    """delivery.merge-by of solo-sdd/config is human; a broken file: the defaults (agent) and a log line."""
    try:
        return read_settings(root)["delivery.merge-by"][0] == "human"
    except Exception as e:
        log_error("stop settings %s" % root, e)
        return False


def sh(args, cwd=None, timeout=5):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def git_strict(args, cwd=None, timeout=5):
    """Like sh, but a git failure (non-zero code, timeout) raises: a status check must not guess on failure."""
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL, check=True).stdout


_roots = {}


def git_root(path):
    d = path if os.path.isdir(path) else os.path.dirname(path)
    while d and not os.path.isdir(d):
        d = os.path.dirname(d)
    if d not in _roots:
        out = sh(["git", "rev-parse", "--show-toplevel"], cwd=d or None).strip()
        _roots[d] = nfc(os.path.realpath(out)) if out else None
    return _roots[d]


def nfc(path):
    # git on macOS returns paths in NFD (a letter + combining mark), Claude in NFC; without this, folders with such letters look "foreign"
    return unicodedata.normalize("NFC", path)


def under(path, root):
    path, root = nfc(os.path.realpath(path)), nfc(os.path.realpath(root))
    return path == root or path.startswith(root.rstrip("/") + "/")


def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))


def state_path(sid, suffix="json"):
    os.makedirs(STATE, exist_ok=True)
    return os.path.join(STATE, "%s.%s" % (re.sub(r"[^\w-]", "_", sid or "nosession"), suffix))


def load_state(sid):
    try:
        with open(state_path(sid)) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(sid, st):
    p = state_path(sid)
    tmp = p + ".%d.tmp" % os.getpid()
    with open(tmp, "w") as f:
        json.dump(st, f, ensure_ascii=False)
    os.replace(tmp, p)


def read_head(path, limit):
    try:
        with open(path, errors="replace") as f:
            text = f.read(limit + 1)
    except Exception:
        return None
    return text if len(text) <= limit else text[:limit] + "\n…[cut by the hook]"


# ---------- context: SessionStart ----------

def done_tasks(text):
    return len(re.findall(r"^\s*- \[[xX]\]", text, re.M))


IMPORT_HINT = "process in openspec/: run solo-sdd import openspec"
CHANGE_FILE = re.compile(r"(.*)/(openspec|solo-sdd)/changes/([^/]+)/(.+)$")


# The source of the process-root block; its copies in the other scripts are written by scripts/sync_blocks.py.
# process-root:begin
TREE_MARKS = ("project.md", "specs", "changes")


def process_root(project):
    """`solo-sdd` when the project holds that tree (project.md, specs/ or changes/), else `openspec`, read until import.
    solo_sdd/process_format.py (find_tree) keeps the same rule in its own form."""
    return "solo-sdd" if any(os.path.exists(os.path.join(project, "solo-sdd", n)) for n in TREE_MARKS) else "openspec"
# process-root:end


def change_file(path):
    """(change folder, name, path inside it) of a file under the process root's changes/, else None."""
    m = CHANGE_FILE.match(nfc(os.path.realpath(path)))
    if not m or process_root(m.group(1)) != m.group(2):
        return None
    return "%s/%s/changes/%s" % m.group(1, 2, 3), m.group(3), m.group(4)


def process_changes(root):
    base = os.path.join(root, process_root(root), "changes")
    if not os.path.isdir(base):
        return []
    rows = []
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if name == "archive" or not os.path.isdir(d):
            continue
        tasks = read_head(os.path.join(d, "tasks.md"), 200000) or ""
        done = done_tasks(tasks)
        todo = len(re.findall(r"^\s*- \[ \]", tasks, re.M))
        marks = []
        for flag in ("CLAIM", "WAITING"):
            body = read_head(os.path.join(d, flag), 200)
            if body is not None:
                marks.append("%s: %s" % (flag, body.strip().splitlines()[0] if body.strip() else "empty"))
        rows.append("- %s — tasks %d/%d%s" % (name, done, done + todo, ("; " + "; ".join(marks)) if marks else ""))
    return rows


# integration-reader:begin
# needs: import os, stat, unicodedata
# An integration is a folder <name>/ holding a file `integration` of `key: value` lines (# starts a comment), found in
# the project's solo-sdd/integrations/ and the owner's ~/.local/share/solo-sdd/integrations/; the project one wins.
INTEGRATION_FILE = "integration"
INTEGRATION_SOURCES = (("project", "solo-sdd/integrations"), ("owner", "~/.local/share/solo-sdd/integrations"))
INTEGRATION_POINTS = ("checks", "review", "ship", "audit")
INTEGRATION_NEEDS = (("checks", "command"), ("ship", "command"), ("review", "material"), ("audit", "material"))
# key -> default; None: required. points, applies and tags read as lists, timeout and output as whole numbers
INTEGRATION_FIELDS = {"name": None, "about": None, "points": None, "command": "", "material": "", "applies": "",
                      "requires": "", "mode": "advice", "missing": "warn", "timeout": "120", "output": "20", "tags": ""}
INTEGRATION_CHOICES = {"mode": ("gate", "advice"), "missing": ("warn", "fail")}
INTEGRATION_MAX_BYTES = 65536
INTEGRATION_PROGRAM_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._+-"


class IntegrationError(ValueError):
    pass


def integration_name(name):
    """True for lowercase ASCII letters, digits and -, not starting with -."""
    return bool(name) and name[0] != "-" and all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in name)


def integration_shown(name):
    """A folder name as it may be printed: a valid name as it is, any other as an ASCII escape (no control, bidi or
    undecodable character reaches the terminal)."""
    return name if integration_name(name) else ascii(name)


def _outside(path):
    """True for a path that leaves the folder it is read from, or one the lists would split."""
    return (not path or path.startswith(("/", "-")) or ".." in path.split("/")
            or any(c in path for c in " \t\\,"))


def _integration_value(key, value, folder, base):
    """The read value of one key; IntegrationError (without the place) naming the allowed values."""
    if key == "name":
        if value != folder or not integration_name(value):
            raise IntegrationError("name takes the folder name %s (lowercase letters, digits and -), not %r"
                                   % (folder, value))
        return value
    if key in ("about", "command"):
        if key == "about" and not value:
            raise IntegrationError("about takes a line of text, not ''")
        return value
    if key in INTEGRATION_CHOICES:
        if value not in INTEGRATION_CHOICES[key]:
            raise IntegrationError("%s takes %s, not %r" % (key, ", ".join(INTEGRATION_CHOICES[key]), value))
        return value
    if key in ("timeout", "output"):
        if not (value.isascii() and value.isdigit()) or int(value) < 1:
            raise IntegrationError("%s takes a whole number from 1, not %r" % (key, value))
        return int(value)
    if key == "requires":
        if value.startswith("-") or any(c not in INTEGRATION_PROGRAM_CHARS for c in value):
            raise IntegrationError("requires takes one program name, not %r" % value)
        return value
    items = [i.strip() for i in value.split(",")] if key in ("points", "applies", "tags") else [value]
    items = [i for i in items if i]
    if key == "tags":
        if any(not integration_name(i) for i in items) or len(set(items)) < len(items):
            raise IntegrationError("tags takes names (lowercase letters, digits and -), each once, separated by commas, "
                                   "not %r" % value)
        return items
    if key == "points":
        if not items or any(i not in INTEGRATION_POINTS for i in items) or len(set(items)) < len(items):
            raise IntegrationError("points takes %s, each once, separated by commas, not %r"
                                   % (", ".join(INTEGRATION_POINTS), value))
        return items
    if key == "applies":
        if any(_outside(i) for i in items):
            raise IntegrationError("applies takes globs of repository paths, separated by commas (no spaces, \\ or "
                                   ".., not starting with / or -), not %r" % value)
        return items
    if not value:  # material
        return ""
    real = os.path.realpath(os.path.join(base, value)) if base else ""
    inside = not base or real.startswith(os.path.realpath(base) + os.sep)
    if _outside(value) or os.path.normpath(value) == "." or not inside:
        raise IntegrationError("material takes a path inside the integration folder, not %r" % value)
    return value


def parse_integration(text, folder, where, base=None):
    """{key: value} of an `integration` file text with every default; folder is the folder name, where the path the
    errors name, base the folder path a `material` link is resolved in (None: not resolved). IntegrationError names
    <where>:<line> and the key, or <where> and the key for a missing one."""
    found = {}
    for n, line in enumerate(text.split("\n"), 1):
        line, at = line[:-1] if line.endswith("\r") else line, "%s:%d" % (where, n)
        bad = [c for c in line if c != "\t" and unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp")]
        if bad:
            raise IntegrationError("%s: a control character U+%04X in the line" % (at, ord(bad[0])))
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        key, colon, value = s.partition(":")
        key, value = key.strip(), value.strip()
        if not colon or not key:
            raise IntegrationError('%s: not "key: value"' % at)
        if key not in INTEGRATION_FIELDS:
            raise IntegrationError("%s: unknown key %s; known: %s" % (at, key, ", ".join(INTEGRATION_FIELDS)))
        if key in found:
            raise IntegrationError("%s: %s is set twice" % (at, key))
        try:
            found[key] = _integration_value(key, value, folder, base)
        except IntegrationError as e:
            raise IntegrationError("%s: %s" % (at, e))
    out = {}
    for key, default in INTEGRATION_FIELDS.items():
        if key not in found and default is None:
            raise IntegrationError("%s: %s is required" % (where, key))
        out[key] = found[key] if key in found else _integration_value(key, default, folder, None)
    for point, key in INTEGRATION_NEEDS:
        if point in out["points"] and not out[key]:
            raise IntegrationError("%s: %s is required for the point %s" % (where, key, point))
    return out


def integration_text(path, where, limit):
    """The UTF-8 text of the file at path; IntegrationError naming where for a file that is missing, a link, not a
    regular file (a FIFO is not waited on), over limit bytes or not UTF-8."""
    data = b""
    if os.path.islink(path):
        raise IntegrationError("%s: a link, not the file itself" % where)
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise IntegrationError("%s: not a regular file" % where)
            while len(data) <= limit:
                chunk = os.read(fd, limit + 1 - len(data))
                if not chunk:
                    break
                data += chunk
        finally:
            os.close(fd)
    except OSError as e:
        raise IntegrationError("%s: %s" % (where, e.strerror or e))
    if len(data) > limit:
        raise IntegrationError("%s: larger than %d bytes" % (where, limit))
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise IntegrationError("%s: not UTF-8 text at byte %d" % (where, e.start))


def read_integration(folder_path, folder, where):
    """The fields of the `integration` file in folder_path; IntegrationError for a file integration_text refuses or a
    broken description."""
    text = integration_text(os.path.join(folder_path, INTEGRATION_FILE), where, INTEGRATION_MAX_BYTES)
    return parse_integration(text, folder, where, folder_path)


def find_integrations(root, home, sources=INTEGRATION_SOURCES):
    """[entry] of the sources (default: both), sorted by name, then in the order of sources: an entry is {name, source,
    dir, file, shadowed, fields, error}; a folder whose name an earlier source also holds is shadowed and not read. Every folder of a
    source is an integration and one it cannot read gets `error`, never a silent skip; a plain file is not one. A
    project folder that is a link leading out of the project, or a link to no folder, gets `error` too. A name that is
    not a valid one is kept as its ASCII escape. A source that is not a folder or cannot be listed gives an entry with
    the name "" and its error. home is the only home read; a source path may be absolute."""
    out, seen = [], set()
    for source, rel in sources:
        base = os.path.join(home, rel[2:]) if rel.startswith("~/") else os.path.join(root, rel)
        if not os.path.lexists(base):
            continue
        try:
            if not os.path.isdir(base):
                raise OSError("not a folder")
            names = sorted(os.listdir(base))
        except OSError as e:
            out.append({"name": "", "source": source, "dir": base, "file": rel, "shadowed": False, "fields": None,
                        "error": "%s: %s" % (rel, e.strerror or e)})
            continue
        inside, here = os.path.realpath(root) + os.sep, set()
        for raw in names:
            path, name = os.path.join(base, raw), integration_shown(raw)
            if not os.path.isdir(path) and not os.path.islink(path):
                continue
            entry = {"name": name, "source": source, "dir": path, "file": "%s/%s/%s" % (rel, name, INTEGRATION_FILE),
                     "shadowed": name in seen, "fields": None, "error": None}
            here.add(name)
            if not os.path.isdir(path):
                entry["error"] = "%s/%s: a link to no folder" % (rel, name)
            elif source == "project" and not os.path.realpath(path).startswith(inside):
                entry["error"] = "%s/%s: a link leading out of the project" % (rel, name)
            elif not entry["shadowed"]:
                try:
                    entry["fields"] = read_integration(path, name, entry["file"])
                except IntegrationError as e:
                    entry["error"] = str(e)
            out.append(entry)
        seen |= here
    order = [s for s, _ in sources]
    return sorted(out, key=lambda e: (e["name"], order.index(e["source"])))


LISTED = "integrations"  # the settings key of the enabled names
NOWHERE = "no folder in %s/ or %s/" % tuple(rel for _, rel in INTEGRATION_SOURCES)


def listed_names(value):
    return [n.strip() for n in value.split(",") if n.strip()]


def integration_errors(entries, listed, settings_file):
    """[(name, error)] a project carries, entries from find_integrations: a broken project integration or project
    source, a broken enabled owner integration, an unreadable owner source while an enabled name is not in the
    project, and an enabled name with no folder. A broken owner integration the project does not enable is not one."""
    project = {e["name"] for e in entries if e["source"] == "project" and e["name"]}
    used = {e["name"] for e in entries if e["name"] and not e["shadowed"]}
    out = [(e["name"], e["error"]) for e in entries if e["error"] and not e["shadowed"] and (
        e["source"] == "project" or e["name"] in listed or (not e["name"] and any(n not in project for n in listed)))]
    return out + [(n, "%s: listed in %s of %s, %s" % (n, LISTED, settings_file, NOWHERE)) for n in listed
                  if n not in used]
# integration-reader:end


# The source of the tree-hash block is solo_sdd/integration_run.py; scripts/sync_blocks.py writes this copy.
# tree-hash:begin
# needs: import hashlib, json, os, re, shutil, stat, subprocess, tempfile; read_settings of the settings block
CHECKS_DIR = os.path.join(".local", "share", "solo-sdd", "checks")
MAX_RECORD = 4 << 20
GIT_TIMEOUT = 120


class CheckError(Exception):
    pass


def git(root, *args, env=None):
    try:
        p = subprocess.run(["git", "-C", root, *args], capture_output=True, env=env, stdin=subprocess.DEVNULL,
                           timeout=GIT_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise CheckError("git %s: no answer in %d s" % (args[0], GIT_TIMEOUT))
    if p.returncode:
        raise CheckError("git %s: %s" % (args[0], p.stderr.decode("utf-8", "replace").strip()))
    return p.stdout


def tree_hash(root):
    """The git tree of the whole working copy (tracked files and untracked not ignored ones), built in a copy of the
    real index so the real one stays untouched."""
    tmp = tempfile.mkdtemp(prefix="solo-sdd-index-")
    try:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(tmp, "index"))
        real = os.path.join(root, git(root, "rev-parse", "--git-path", "index").decode().strip())
        if os.path.exists(real):  # tracked files that match an ignore pattern stay in the tree
            # the copy keeps the index time, taken before the bytes: git rereads a file no older than the index it
            # loads, so a newer copy would hide such an edit
            st = os.stat(real)
            shutil.copyfile(real, env["GIT_INDEX_FILE"])
            os.utime(env["GIT_INDEX_FILE"], ns=(st.st_atime_ns, st.st_mtime_ns))
        git(root, "add", "-A", env=env)
        return git(root, "write-tree", env=env).decode().strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def repo_dir(root, home):
    """The records folder of the repository: its folder name and a short digest of its absolute path."""
    path = os.path.realpath(root)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(path)) or "_"
    return os.path.join(home, CHECKS_DIR, "%s-%s" % (name, hashlib.sha256(path.encode("utf-8", "surrogateescape"))
                                                     .hexdigest()[:12]))


def read_json(path):
    """The object of a JSON file; {} for a missing, truncated, too large, too deep or non-JSON file, one that is not
    an object, or one that is not a regular file (a FIFO is not waited on)."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_RECORD:
                return {}
            with os.fdopen(fd, "rb") as f:
                fd = None
                data = json.loads(f.read(MAX_RECORD + 1))
        finally:
            if fd is not None:
                os.close(fd)
    except (OSError, ValueError, RecursionError):
        return {}
    return data if isinstance(data, dict) else {}


def base_ref(root):
    """The merge base of HEAD with the base branch (delivery.base, else origin's default branch), else HEAD, else None
    for a repository without commits."""
    base = read_settings(root)["delivery.base"][0]
    for ref in (["origin/" + base, base] if base else ["refs/remotes/origin/HEAD"]):
        try:
            return git(root, "merge-base", "HEAD", ref).decode().strip()
        except CheckError:
            pass
    try:
        git(root, "rev-parse", "--verify", "-q", "HEAD")
        return "HEAD"
    except CheckError:
        return None


def changed_files(root):
    """Sorted paths from the root that differ between the working copy and base_ref, untracked not ignored included."""
    ref = base_ref(root)
    out = git(root, "diff", "--name-only", "-z", "--relative", ref) if ref else git(root, "ls-files", "-z")
    out += git(root, "ls-files", "--others", "--exclude-standard", "-z")
    return sorted({os.fsdecode(p) for p in out.split(b"\0") if p})
# tree-hash:end
GIT_TIMEOUT = 10  # the hook's own bound for the block's git calls: a stop never waits on git for long


# errors:begin
def recent_errors(path, days=7):
    """(count, last line) of the hooks' errors.log lines dated within `days`; a line without a leading ISO time is not
    counted. The source is solo_sdd/doctor.py, the copy in work_hooks.py (deployed alone) is written by
    scripts/sync_blocks.py."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return 0, None
    since, found = datetime.datetime.now() - datetime.timedelta(days=days), []
    for line in lines:
        try:
            t = datetime.datetime.fromisoformat(line.split(" ", 1)[0])
        except ValueError:
            continue
        if t.tzinfo:
            t = t.astimezone().replace(tzinfo=None)
        if t >= since:
            found.append(line)
    return len(found), (found[-1] if found else None)
# errors:end


def cmd_context(inp):
    cwd = os.path.realpath(inp.get("cwd") or os.getcwd())
    root = git_root(cwd)
    top = root or cwd
    parts = []
    n, last = recent_errors(os.path.join(STATE, "errors.log"))
    if n:
        parts.append("hook errors: %d in the last 7 days, last: %s (%s)" % (n, last, os.path.join(STATE, "errors.log")))
    if cwd != os.path.realpath(HOME) and process_root(top) == "solo-sdd":
        try:  # its own guard, before the long parts the context limit cuts: a broken read is logged, the rest stays
            listed = listed_names(parse_settings(read_settings_text(top)).get(LISTED, ""))
            errors = integration_errors(find_integrations(top, HOME), listed, SETTINGS_FILE)
            if errors:
                parts.append("integration errors: %s%s" % (errors[0][1], "; %d in all" % len(errors) if len(errors) > 1 else ""))
        except Exception as e:
            log_error("context integrations", e)
    if cwd != os.path.realpath(HOME):
        d, seen = cwd, []
        while True:
            seen.append(d)
            if d == top or d == os.path.dirname(d) or os.path.realpath(d) == os.path.realpath(HOME):
                break
            d = os.path.dirname(d)
        for d in reversed(seen):
            if os.path.realpath(d) == os.path.realpath(HOME):
                continue
            agents = read_head(os.path.join(d, "AGENTS.md"), 12000)
            claude = read_head(os.path.join(d, "CLAUDE.md"), 12000)
            # Claude Code itself loads AGENTS.md when CLAUDE.md imports it with an @AGENTS.md line
            if agents and agents != claude and not re.search(r"(?m)^\s*@AGENTS\.md\s*$", claude or ""):
                parts.append("### %s/AGENTS.md\n%s" % (d, agents))
        tree = process_root(top)
        intent = "solo-sdd/project.md" if tree == "solo-sdd" else "openspec/config.yaml"
        for rel, limit in ((intent, 6000), ("docs/status.md", 6000)):
            body = read_head(os.path.join(top, rel), limit)
            if body:
                parts.append("### %s\n%s" % (rel, body))
        if tree == "openspec" and os.path.isdir(os.path.join(top, "openspec")):
            parts.append("### Process tree\n" + IMPORT_HINT)
    if root:
        branch = sh(["git", "branch", "--show-current"], cwd=root).strip() or "detached"
        status = sh(["git", "-c", "core.quotepath=off", "status", "--short"], cwd=root).splitlines()
        shown = "\n".join(status[:25]) + ("\n…%d more" % (len(status) - 25) if len(status) > 25 else "")
        parts.append("### git: branch %s, uncommitted paths %d\n%s" % (branch, len(status), shown or "clean"))
        changes = process_changes(root)
        if changes:
            parts.append("### Active changes in %s/ (CLAIM: taken, WAITING: waits)\n" % process_root(root) + "\n".join(changes))
    if not parts:
        return
    text = ("Project autocontext from the SessionStart hook (%s, source: files and git at start). "
            "The rules below are already read, no need to read them again. Do not revert uncommitted changes of others.\n\n"
            % inp.get("source", "startup")) + "\n\n".join(parts)
    emit({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text[:30000]}})


# ---------- subagent-context: SubagentStart ----------

SUBAGENT_LIMIT = 4000


def subagent_context_text(agents, rows):
    """Subagent context: path to AGENTS.md first, then the change; when space runs out the list is trimmed.
    ponytail: a path longer than ~3900 chars will not fit the limit; does not happen in practice."""
    head = ["Project rules: read %s before work (the file is not inserted, read it yourself)." % agents] if agents else []
    if rows:
        head.append("Open changes of the main folder (CLAIM: taken, WAITING: waits):")
    out, reserve = "\n".join(head), 30
    for i, row in enumerate(rows):
        row = row[:300]
        if len(out) + len(row) + 1 > SUBAGENT_LIMIT - reserve:
            out += "\n…%d more" % (len(rows) - i)
            break
        out += "\n" + row
    return out


def cmd_subagent_context(inp):
    root = git_root(os.path.realpath(inp.get("cwd") or os.getcwd()))
    if not root:
        return
    main = main_checkout(root)
    agents = os.path.join(main, "AGENTS.md")
    text = subagent_context_text(agents if os.path.isfile(agents) else None, process_changes(main))
    if text:
        emit({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": text}})


# ---------- guard: PreToolUse ----------

def deny(reason):
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                 "permissionDecisionReason": reason}})
    sys.exit(0)


def project_roots(cwd):
    # the session cwd follows `cd` in Bash (into scratchpad etc.), CLAUDE_PROJECT_DIR is the launch folder
    roots = [git_root(cwd) or cwd]
    pd = os.environ.get("CLAUDE_PROJECT_DIR")
    if pd and os.path.isdir(pd):
        roots.append(git_root(pd) or nfc(os.path.realpath(pd)))
    return list(dict.fromkeys(roots))


def allowed_roots(cwd):
    roots = project_roots(cwd) + [os.path.join(HOME, ".claude"), os.path.join(HOME, ".codex")] + list(TMP_ROOTS)
    for p in (os.path.join(HOME, ".claude", "settings.json"),
              os.path.join(cwd, ".claude", "settings.json"), os.path.join(cwd, ".claude", "settings.local.json")):
        try:
            with open(p) as f:
                roots += json.load(f).get("permissions", {}).get("additionalDirectories", [])
        except Exception:
            pass
    return [os.path.expanduser(r) for r in roots]


def guard_scope(sid, cwd, path):
    if under(cwd, HOME) and os.path.realpath(cwd) == os.path.realpath(HOME):
        return
    if any(under(path, r) for r in allowed_roots(cwd)):
        return
    # its own file: the async beat rewrites <sid>.json and would drop a key written here
    p = state_path(sid, "scope")
    if path in (read_head(p, 1 << 20) or "").splitlines():
        return
    with open(p, "a") as f:
        f.write(path + "\n")
    deny("Write outside the project folder: %s. By the rules every project file lives inside the project folder. "
         "If the user explicitly asked to write there, repeat the same write: the hook lets it through the second time." % path)


def env_files_near(cwd):
    found = []
    for d in {cwd, git_root(cwd) or cwd}:
        try:
            found += [os.path.join(d, n) for n in os.listdir(d) if re.fullmatch(ENV_FILE, n)]
        except Exception:
            pass
    return found


def guard_env_write(tool, path, cwd):
    if not re.fullmatch(ENV_FILE, os.path.basename(path)):
        return
    if tool == "Write" and os.path.exists(path):
        deny("Overwriting the existing %s is forbidden: it holds the user's keys. A field is missing: "
             "name the variable to the user, they add it themselves (or append an empty field with >>)." % path)
    others = [p for p in env_files_near(cwd) if os.path.realpath(p) != os.path.realpath(path)]
    if tool == "Write" and others:
        deny("The user already has %s. Do not create a second .env: use the existing one." % ", ".join(others))


CLAIM_LINE = 'echo "claude $(date +%F) session=$CLAUDE_CODE_SESSION_ID" > '


def claim_log(sid, line=None):
    """Absolute paths of CLAIM files this session created (itself, via Write or Bash).
    A separate append-only file: the async beat hook rewrites the json state and would lose the entry."""
    p = state_path(sid, "claims")
    if line:
        with open(p, "a") as f:
            f.write(line + "\n")
        return None
    try:
        with open(p) as f:
            return f.read().splitlines()
    except Exception:
        return []


def change_dirs(cwd, name):
    mains = [main_checkout(r) for r in project_roots(cwd)]
    return [os.path.join(m, process_root(m), "changes", name) for m in mains]


def bash_log(inp, **rec):
    with open(state_path(inp.get("session_id", ""), "cmds"), "a") as f:
        f.write(json.dumps(dict(rec, id=inp.get("tool_use_id", "")), ensure_ascii=False) + "\n")


def note_claim_cmd(inp, cmd):
    # Bash creates CLAIM in any way (>, cp, python). We remember the command time instead of parsing its text.
    if "CLAIM" in cmd:
        bash_log(inp, t=time.time(), cmd=cmd[:4000])


def cmd_claims(inp):
    """PostToolUse and PostToolUseFailure for Bash: end of a command. Arrives late, after the
    next call has started, so guard makes the decision, not this hook."""
    if "CLAIM" in ((inp.get("tool_input") or {}).get("command") or ""):
        bash_log(inp, end=time.time())


def bash_created(sid, claim, name):
    """CLAIM changed during a command of this session that names CLAIM and the change itself."""
    try:
        with open(state_path(sid, "cmds")) as f:
            recs = [json.loads(l) for l in f if l.strip()]
    except Exception:
        return False
    ends = {r["id"]: r["end"] for r in recs if "end" in r}
    mt, now = os.path.getmtime(claim), time.time()
    for r in recs:
        if "t" in r and name in r["cmd"]:
            end = ends.get(r["id"], min(now, r["t"] + 600))
            if r["t"] <= mt <= end:
                return True
    return False


def foreign_claim(sid, claim, name):
    """Refusal text if the CLAIM is foreign, else None. The hook adds the session id to an own CLAIM without one."""
    body = (read_head(claim, 300) or "").strip()
    owner = re.search(r"session=([\w-]+)", body)
    mine = bool(sid) and (owner.group(1) == sid if owner else
                          claim in claim_log(sid) or bash_created(sid, claim, name))
    if mine:
        if not owner:
            with open(claim, "w") as f:
                f.write("%s session=%s\n" % (body or "claude " + datetime.date.today().isoformat(), sid))
        if claim not in claim_log(sid):
            claim_log(sid, claim)
        return None
    age = int((time.time() - os.path.getmtime(claim)) / 60)
    if owner:
        marks = [os.path.getmtime(p) for p in (state_path(owner.group(1)), state_path(owner.group(1), "claims"))
                 if os.path.exists(p)]
        seen = ("the owner session was last active %d min ago" % ((time.time() - max(marks)) / 60)
                if marks else "no trace of owner session activity")
    else:
        seen = ("no session id. If you set it yourself (for example, before /clear), rewrite it: %s%s"
                % (CLAIM_LINE, claim))
    return ("Change %s is taken by another agent: CLAIM «%s», set %d min ago, %s. Take another change. "
            "If the CLAIM is clearly abandoned, tell the user; do not remove it yourself." % (name, body, age, seen))


def main_checkout(root, run=sh):
    common = run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=root).strip()
    return nfc(os.path.realpath(os.path.dirname(common))) if common.endswith("/.git") else root


def more_done(tool, ti, path):
    """The edit increases the number of checked tasks: text on disk versus text after the edit."""
    old = read_head(path, 200000) or ""
    if tool == "Write":
        return done_tasks(ti.get("content") or "") > done_tasks(old)
    new = old
    for e in ti.get("edits") or [ti]:
        s = e.get("old_string") or ""
        if s not in new or new.count(s) > 1 and not e.get("replace_all"):
            return False  # the tool refuses as a whole, MultiEdit too: there will be no edit
        new = new.replace(s, e.get("new_string") or "")
    return done_tasks(new) > done_tasks(old)


def guard_claim(sid, path, tool, ti):
    found = change_file(path)
    if found and found[2] == "CLAIM" and not os.path.exists(path):
        claim_log(sid, os.path.join(found[0], "CLAIM"))
    if not found or found[1] == "archive" or found[2] in ("CLAIM", "WAITING"):
        return
    cdir, name, rest = found
    if not os.path.isdir(cdir):
        return
    root = git_root(cdir)
    if root and main_checkout(root) != root:
        # worktree: CLAIM lives in the main folder, where neighbours see it; in a worktree it would get committed
        cdir = os.path.join(main_checkout(root), os.path.relpath(cdir, root))
        if not os.path.isdir(cdir):
            return
    claim, waiting = os.path.join(cdir, "CLAIM"), os.path.join(cdir, "WAITING")
    if os.path.exists(claim):
        reason = foreign_claim(sid, claim, name)
        if reason:
            deny(reason)
        return
    if os.path.exists(waiting):
        deny("Change %s waits for an external condition (WAITING: %s). Take another change."
             % (name, (read_head(waiting, 300) or "").strip()))
    if rest != "tasks.md" or not more_done(tool, ti, path):
        return
    try:
        fd = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return guard_claim(sid, path, tool, ti)
    with os.fdopen(fd, "w") as f:
        f.write("claude %s session=%s\n" % (datetime.date.today().isoformat(), sid))
    claim_log(sid, claim)


def guard_archive(sid, cmd, cwd, inp=None):
    """cmd is the command without text (command_text): heredoc bodies and search patterns are not runs."""
    names = archive_runs(cmd)
    for name in names:
        for d in change_dirs(cwd, name):
            claim = os.path.join(d, "CLAIM")
            reason = os.path.exists(claim) and foreign_claim(sid, claim, name)
            if reason:
                deny("Archiving is not allowed. " + reason)
    if names and inp:
        unreviewed = unreviewed_edit(inp, cwd)
        if unreviewed:
            deny("Archiving is not allowed: this session (or orchestrator subagent) edited %s and ran no `Review:` agent "
                 "after its first code edit. Run the independent acceptance first (spec-next step 7a): an Agent with the "
                 "description `Review: <id>`, then archive." % unreviewed)


def actor_transcript(inp):
    """The transcript of whoever makes the call: a subagent's own file, else the session's; None when none is given."""
    tp = inp.get("transcript_path") or ""
    if tp and inp.get("agent_id"):
        return re.sub(r"\.jsonl$", "", tp) + "/subagents/agent-%s.jsonl" % inp["agent_id"]
    return tp or None


def code_file(path, cwd):
    """path relative to its working copy when it is code there (outside solo-sdd/ and docs/), else None."""
    p = nfc(os.path.realpath(os.path.join(cwd, os.path.expanduser(path))))
    root = git_root(p)
    if not root or "/scratchpad/" in p:
        return None
    rel = os.path.relpath(p, root)
    return None if rel.startswith(("solo-sdd/", "docs/", "../")) or rel == "." else rel


def unreviewed_edit(inp, cwd):
    """The first code edit of the actor's transcript when no `Review:` agent follows it, else None; an unreadable
    transcript passes and is logged (fail-open)."""
    tp = actor_transcript(inp)
    if not tp:
        return None
    try:
        with open(tp, "rb") as f:
            first = None
            for ev in transcript_events(f):
                if ev[0] == "edit":
                    first = first or code_file(ev[1], cwd)
                elif first and ev[1] in ("Agent", "Task") and agent_role(ev[2].get("description")) == "review":
                    return None
    except Exception as e:
        log_error("guard archive review %s" % tp, e)
        return None
    return first


def policy():
    with open(os.path.join(HERE, "model-policy.json")) as f:
        return json.load(f)


def policy_or_none(where):
    """The policy, or None with a log line: a broken policy lets through only the checks that read it."""
    try:
        pol = policy()
        for key in ("cheap", "expensive_always", "expensive", "main", "roles", "test_markers"):
            pol[key]
        return pol
    except Exception as e:
        log_error("%s model-policy.json" % where, e)
        return None


def model_hits(text, names):
    return [n for n in names if re.search(r"(?i)(?<![a-z])%s(?![a-z])" % re.escape(n), text)]


OVERRIDE_VAR = "SOLO_SDD_EXPENSIVE_OK"
OWNER_ONLY = "Only the owner allows an expensive model."


def owner_override():
    return os.environ.get(OVERRIDE_VAR) == "1"


# ---------- text is not a command: heredoc bodies and search patterns are cut before the checks ----------
# The source of the shell block; its copy in process-guard.py is written by scripts/sync_blocks.py.
# shell:begin
# a heredoc body is text only if one of these programs reads it; any other receiver (shell, wrapper) means commands
TEXT_SINKS = {"cat", "tee", "head", "tail", "wc", "sort", "uniq", "grep", "egrep", "rg", "jq", "cut", "tr", "nl",
              "column", "fold", "fmt", "paste", "rev", "tac", "comm", "diff", "less", "more", "base64", "od", "xxd",
              "shasum", "md5", "python", "python3", "node"}
WRAPPERS = {"sudo", "env", "command", "exec", "nohup", "time", "timeout", "gtimeout", "nice", "caffeinate", "npx"}
GREPS = {"grep", "egrep", "rg", "ag"}
VALUE_OPTS = {"-A", "-B", "-C", "-m", "-g", "-t", "-f", "--file", "--include", "--exclude", "--glob", "--type", "--pre"}
SED_VALUE_OPTS = {"-f", "--file", "-l", "--line-length"}
HEREDOC = re.compile(r"(?<![<\\])<<(?!<)(-?)\s*([\"']?)([A-Za-z_]\w*)\2")


def split_cmd(text):
    """Splits a command into parts on ; && || | & and newline outside quotes: [part, separator, part, ...]."""
    out, cur, q, i, n = [], [], None, 0, len(text)
    while i < n:
        c = text[i]
        if c == "\\" and q != "'" and i + 1 < n:
            cur.append(text[i:i + 2])
            i += 2
            continue
        if q:
            q = None if c == q else q
        elif c in "'\"":
            q = c
        else:
            sep = None
            if text.startswith("&&", i) or text.startswith("||", i):
                sep = text[i:i + 2]
            elif c in ";|\n":
                sep = c
            elif c == "&" and not (i and text[i - 1] in "<>&") and text[i + 1:i + 2] not in (">", "&"):
                sep = c
            if sep:
                out += ["".join(cur), sep]
                cur, i = [], i + len(sep)
                continue
        cur.append(c)
        i += 1
    return out + ["".join(cur)]


def quote_end(text, q=None):
    """Open quote at the end of the text (None, ' or \")."""
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\" and q != "'":
            i += 2
            continue
        if q:
            q = None if c == q else q
        elif c in "'\"":
            q = c
        i += 1
    return q


LEAD = {"then", "do", "else", "elif", "if", "while", "until"}
NUM_ARG = re.compile(r"[\d.]+[smhd]?")
VALUED = {"-s", "--signal", "-n", "--adjustment", "-k", "--kill-after"}


def cmd_start(words, extra=()):
    """Index of the program word: skips leading ( { !, keywords, assignments, wrappers and their numbers/options."""
    i = 0
    while i < len(words):
        w = words[i]
        if w[:1] in ("(", "{", "!") and w:
            words[i] = w.lstrip("({!")
            if words[i]:
                continue
            i += 1
        elif w in LEAD or w in WRAPPERS or w in extra or re.fullmatch(r"\w+=\S*", w) or (i and w.startswith("-")):
            i += 1
            if w in ("timeout", "gtimeout", "nice"):
                while i < len(words) and (words[i] in VALUED or words[i].startswith("-") or NUM_ARG.fullmatch(words[i])):
                    i += 2 if words[i] in VALUED else 1
        else:
            break
    return i


def first_word(seg):
    w = re.split(r"[<>]", seg, 1)[0].split()  # `bash<<EOF`: the program is before the redirection
    i = cmd_start(w)
    return os.path.basename(w[i].strip("'\"")) if i < len(w) else ""


def runs_text(parts, k):
    """Text of part k goes to a process: it, or the pipeline command after it, is not a text reader, or has <(…), >(…)."""
    while True:
        if first_word(parts[k]) not in TEXT_SINKS or re.search(r"[<>]\(", parts[k]):
            return True
        if parts[k + 1:k + 2] != ["|"]:
            return False
        k += 2


def strip_heredocs(cmd):
    lines, out, i, q = cmd.split("\n"), [], 0, None
    while i < len(lines):
        line = lines[i]
        i += 1
        while not q and re.search(r"(?<!\\)(?:\\\\)*\\$", line) and i < len(lines):
            line, i = line[:-1] + lines[i], i + 1  # a `\` continuation is the same command, the body starts after it
        out.append(line)
        if q:  # continuation of a quoted line: no heredoc here
            q = quote_end(line, q)
            continue
        found = [m for m in HEREDOC.finditer(line) if quote_end(line[:m.start()]) is None]
        q = quote_end(line)
        if not found:
            continue
        parts = split_cmd(line)
        starts = [sum(len(p) for p in parts[:k]) for k in range(len(parts))]
        for m in found:
            # the body is read by the receiver of this heredoc and the pipeline commands after it
            shell = runs_text(parts, max(k for k in range(0, len(parts), 2) if starts[k] <= m.start()))
            body = []
            while i < len(lines) and (lines[i].lstrip("\t") if m.group(1) else lines[i]) != m.group(3):
                body.append(lines[i])
                i += 1
            # unquoted marker: the shell performs substitutions in the body
            if shell or (not m.group(2) and re.search(r"\$\(|`", "\n".join(body))):
                out.extend(body)
            if i < len(lines):
                out.append(lines[i])
                i += 1
    return "\n".join(out)


def split_words(seg):
    try:
        return shlex.split(seg)
    except ValueError:
        return seg.split()


def substitution(x):
    return any(t in x for t in ("$(", "`", "<(", ">("))


GIT_GLOBAL_VALUED = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
MESSAGE_OPTS = {"git": ("commit", "tag"), "gh": ("pr", "issue")}


def git_sub(w, i):
    """Index of the git subcommand after the program word i, past the global options."""
    j = i + 1
    while j < len(w) and w[j].startswith("-"):
        j += 2 if w[j] in GIT_GLOBAL_VALUED else 1
    return j


def strip_message(w, i):
    """Replaces in place the message values of git commit/tag (-m, --message) and gh pr/issue (-t, --title, -b, --body):
    text for a person, not a command. A value with a substitution stays. True if anything was replaced."""
    prog = os.path.basename(w[i])
    j = git_sub(w, i) if prog == "git" else i + 1
    if prog not in MESSAGE_OPTS or w[j:j + 1] == [] or w[j] not in MESSAGE_OPTS[prog]:
        return False
    short, longs = ("m", ("--message",)) if prog == "git" else ("tb", ("--title", "--body"))
    text, hit, j = lambda x: not substitution(x), False, j + 1
    while j < len(w):
        a = w[j]
        if a == "--":
            break
        long_eq = next((o for o in longs if a.startswith(o + "=")), None)
        if a in longs or re.fullmatch(r"-[A-Za-z]*[%s]" % short, a) and (prog == "git" or len(a) == 2):
            if j + 1 < len(w) and text(w[j + 1]):
                w[j + 1], hit = "MESSAGE", True
            j += 2
            continue
        if long_eq and text(a):
            w[j], hit = long_eq + "=MESSAGE", True
        elif re.fullmatch(r"-[%s].+" % short, a) and text(a):
            w[j], hit = a[:2] + "MESSAGE", True
        j += 1
    return hit


# $'…', a word starting with # and any ${ other than a plain parameter expansion (${NAME}, ${NAME:-/tmp}, ${#NAME}:
# only the characters of this allowlist up to the first }) are read by the shell differently from this parser and shlex:
# anywhere on the line they can move quote boundaries, so nothing is cut; zsh runs the command inside =(…) (process
# substitution into a file), which this parser does not read, so =( anywhere, an array assignment A=(x) included, cuts nothing
UNCUT = re.compile(r"\$'|=\(|\$\{(?![A-Za-z0-9_#:=+?%/.@*!,^~-]*\})|(?:^|[\s;&|()])#")


def strip_patterns(cmd):
    if UNCUT.search(cmd):
        return cmd
    parts = split_cmd(cmd)
    for k in range(0, len(parts), 2):
        w = split_words(parts[k])
        i = cmd_start(w)
        if i >= len(w):
            continue
        prog = os.path.basename(w[i])
        if strip_message(w, i):
            parts[k] = " ".join(shlex.quote(x) for x in w)
            continue
        if prog == "git" and w[i + 1:i + 2] == ["grep"]:
            i, prog = i + 1, "grep"
        sed = prog == "sed"
        if not sed and prog not in GREPS or parts[k + 1:k + 2] == ["|"] and runs_text(parts, k + 2):
            continue  # search output goes to the shell: the pattern stays for checking
        # a sed script with r/w commands reads and writes files: do not cut it
        text = lambda x: not substitution(x) and not (sed and re.search(r"(?:^|[;\n{}\d$/])\s*[rRwW]\s+\S", x))
        e_opts = ("-e", "--expression") if sed else ("-e", "--regexp")
        value_opts = SED_VALUE_OPTS if sed else VALUE_OPTS
        rest, pat, has_e, j = w[i + 1:], None, False, 0
        while j < len(rest):
            a = rest[j]
            if a in e_opts:
                has_e = True
                if j + 1 < len(rest) and text(rest[j + 1]):
                    rest[j + 1] = "PATTERN"
                j += 2
                continue
            if a.startswith(e_opts[1] + "=") or a.startswith("--file="):
                has_e = True
                if a.startswith(e_opts[1] + "=") and text(a):
                    rest[j] = e_opts[1] + "=PATTERN"
            elif a in value_opts:
                has_e = has_e or a in ("-f", "--file")  # patterns in a file: all positionals are paths
                j += 2
                continue
            elif sed and a == "-i" and rest[j + 1:j + 2] == [""]:
                j += 2  # macOS: an empty argument after -i is the backup suffix
                continue
            elif not a.startswith("-") and pat is None:
                pat = j
            j += 1
        if pat is not None and not has_e and text(rest[pat]):
            rest[pat] = "PATTERN"
        if rest != w[i + 1:]:  # rebuild only on replacement: shlex quoting breaks <(…) and $(…)
            parts[k] = " ".join(shlex.quote(x) for x in w[:i + 1] + rest)
    return "".join(parts)
# shell:end


def command_text(cmd):
    return strip_patterns(strip_heredocs(cmd))


def substituted(cmd):
    """Texts inside $(…), <(…), >(…) and `…`: the shell runs them."""
    out, i = [], 0
    while i < len(cmd):
        if cmd[i] == "`" and "`" in cmd[i + 1:]:
            j = cmd.index("`", i + 1)
            out.append(cmd[i + 1:j])
            i = j + 1
            continue
        if cmd[i] in "$<>" and cmd[i + 1:i + 2] == "(":
            depth, j = 1, i + 2
            while j < len(cmd) and depth:
                depth += {"(": 1, ")": -1}.get(cmd[j], 0)
                j += 1
            out.append(cmd[i + 2:j - 1])
            i = j
            continue
        i += 1
    return out


def codex_launches(cmd, depth=0):
    """codex exec runs: a separate word codex (outside a quoted string) followed by exec, wherever it stands
    (after a wrapper, in find -exec, xargs); substitutions, eval and a shell's -c string are parsed recursively."""
    found = []
    for part in split_cmd(cmd)[::2] + (substituted(cmd) if depth < 3 else []):
        w = split_words(part)
        for k, a in enumerate(w):
            prog = os.path.basename(a.lstrip("({!"))
            if prog == "codex" and (w[k + 1:k + 2] == ["e"] or "exec" in w[k + 1:k + 4]):  # codex -m x exec
                found.append(" ".join(w[k:]))
            elif depth < 3 and (prog == "eval" or prog in ("sh", "bash", "zsh", "dash", "ksh") and any(re.fullmatch(r"-\w*c\w*", x) for x in w[k + 1:k + 3])):
                found += codex_launches(" ".join(w[k + 1:]), depth + 1)
                break
    return found


ARCHIVE_PROGS = {"solo-sdd", "openspec"}
RUNNERS = {"uv", "uvx", "pipx", "npm", "pnpm", "yarn", "bunx", "npx"}  # the program is a later word: uv run --with y solo-sdd
SHELLS = ("sh", "bash", "zsh", "dash", "ksh")
SUDO_VALUED = {"-u", "--user", "-g", "--group", "-U", "--other-user", "-C", "--close-from", "-D", "--chdir", "-h", "--host",
               "-p", "--prompt", "-r", "--role", "-t", "--type", "-T", "--command-timeout", "-R", "--chroot"}
PY_VALUED = {"-W", "-X"}


def wrapper_values_cut(w):
    """The words with the values of sudo's and env's valued options read as options: `sudo -u root x` as `sudo -u - x`
    (replaced, not dropped, so an index still points at the same raw word)."""
    out, opts = list(w), None
    for j, x in enumerate(w):
        if opts is not None and j and w[j - 1] in opts and out[j - 1] != "-":
            out[j] = "-"
        elif x in ("sudo", "env"):
            opts = SUDO_VALUED if x == "sudo" else ENV_VALUED
        elif not x.startswith("-"):
            opts = None
    return out


def archive_name(w, i):
    """The change name when w[i:] is an archive run (solo-sdd/openspec archive <id>, python … -m solo_sdd archive <id>)."""
    prog = os.path.basename(w[i]).split("@")[0]  # npx solo-sdd@latest
    if re.fullmatch(r"python[\d.]*", prog):
        j = i + 1
        while j < len(w) and w[j].startswith("-") and w[j] not in ("-m", "-msolo_sdd"):
            j += 2 if w[j] in PY_VALUED else 1
        if w[j:j + 1] == ["-msolo_sdd"]:
            i = j
        elif w[j:j + 2] == ["-m", "solo_sdd"]:
            i = j + 1
        else:
            return None
    elif prog not in ARCHIVE_PROGS:
        return None
    rest = [x for x in w[i + 1:] if not x.startswith("-")]  # options of the program and of archive (--yes, --)
    if rest[:1] == ["archive"] and len(rest) > 1 and re.fullmatch(r"[\w.][\w.-]*", rest[1]):
        return rest[1]
    return None


def archive_runs(cmd, depth=0):
    """Change names of `solo-sdd archive <id>` runs (also openspec, python -m solo_sdd), read with the same parser as
    the Codex check: the program word after wrappers and assignments, quotes removed; substitutions, eval and a shell's
    -c string are parsed again. An argument of another program (echo, man, a commit message) is not a run."""
    found = []
    for part in split_cmd(cmd)[::2] + (substituted(cmd) if depth < 3 else []):
        raw = split_words(part)
        # a word ends at a glued redirection or a subshell end, as in first_word: `x>log`, `x&>log`, `x)` (a lone `&` has
        # already split the commands, so one left in a word belongs to a redirection); /usr/bin/env is env
        w = [os.path.basename(x) if os.path.basename(x) in WRAPPERS else x for x in (re.split(r"[<>)&]", y, 1)[0] for y in raw)]
        w = wrapper_values_cut(w)
        i = cmd_start(w)
        if i >= len(w):
            continue
        prog = os.path.basename(w[i])
        if depth < 3 and prog == "eval":
            found += archive_runs(" ".join(raw[i + 1:]), depth + 1)
            continue
        if depth < 3 and prog in SHELLS:
            c = next((k for k in range(i + 1, len(w)) if re.fullmatch(r"-\w*c\w*", w[k])), None)
            if c is not None and w[c + 1:c + 2] == ["--"]:
                c += 1  # bash -c -- 'cmd': the string is after the end of options
            if c is not None and c + 1 < len(w):
                found += archive_runs(raw[c + 1], depth + 1)  # the -c string uncut: it is a command again
            continue
        # after a runner (npx is also a wrapper, so it may be before i) every later word is tried as the program: an option
        # value may carry its name (uvx --from solo-sdd solo-sdd archive x), and the runner may start a wrapper or another
        # runner (uv run env A=1 solo-sdd archive x). Known limit, kept over a missed run: an argument of another program
        # the runner starts reads as a run (npx prettier solo-sdd archive x is refused)
        r = next((k for k in range(i + 1) if os.path.basename(w[k]).split("@")[0] in RUNNERS), None)
        names = [archive_name(w, k) for k in range(r + 1, len(w))] if r is not None else [archive_name(w, i)]
        found += [n for n in names if n][:1]
    return found


def guard_models_bash(cmd, raw=None):
    """cmd is the command without text (command_text), raw is the whole: a test marker in a search pattern is a marker too."""
    if owner_override():
        return
    pol = policy_or_none("guard")
    if pol is None:
        return
    is_test = re.search(pol["test_markers"], raw or cmd)
    launches = codex_launches(cmd)
    if launches:
        models = re.findall(r"(?:\s-m|--model)[\s=]+[\"']?([\w.\-]+)|model\s*=\s*[\"']?([\w.\-]+)", " ".join(launches))
        models = [a or b for a, b in models]
        if not models:
            cfg = read_head(os.path.join(HOME, ".codex", "config.toml"), 20000) or ""
            mm = re.search(r'^model\s*=\s*"([^"]+)"', cfg, re.M)
            models = [mm.group(1) if mm else "default"]
        joined = " ".join(models)
        if model_hits(joined, pol["expensive_always"]):
            deny("Codex with model %s is the most expensive. Take a cheap one (%s). %s" % (joined, ", ".join(pol["cheap"]), OWNER_ONLY))
        if is_test and not model_hits(joined, pol["cheap"]):
            deny("Test or acceptance on Codex %s. By the rules tests run on the cheapest models: %s. "
                 "Pass -m explicitly. %s" % (joined, ", ".join(pol["cheap"]), OWNER_ONLY))
        return
    if is_test:
        for m in re.findall(r"(?i)--model(?:\s+|=)[\"']?([\w.\-/:]+)", cmd):
            if not model_hits(m, pol["cheap"]):
                deny("Test or acceptance with model %s, not a cheap one. Tests run on the cheapest models: %s. %s"
                     % (m, ", ".join(pol["cheap"]), OWNER_ONLY))
        flags = " ".join(re.findall(r"(?i)(?:--model|(?<![\w-])-m|\bmodel)[\s=:]+[\"']?([\w.\-]+)", cmd))
        hits = model_hits(flags, pol["expensive"])
        if hits:
            deny("Test or acceptance with an expensive model (%s). Take a cheap one: %s. %s" % (", ".join(hits), ", ".join(pol["cheap"]), OWNER_ONLY))


def agent_role(desc, pol=None):
    d = (desc or "").strip().casefold() + " "  # trailing space: "Orchestrator" without a tail is a tag too
    for role, prefixes in (pol or policy())["roles"].items():
        if any(d.startswith(p.casefold()) for p in prefixes):
            return role
    return "general"


def guard_models_agent(ti, from_subagent=False):
    desc = ti.get("description") or ""
    pol = policy_or_none("guard")
    if pol is None:
        return
    role = agent_role(desc, pol)
    if role == "orchestrator" and from_subagent:
        deny("Only the main session launches orchestrators, not a subagent.")
    if role == "lookup" and ti.get("subagent_type") != "Explore":
        deny("Lookup (`Lookup:`) goes only through Explore: set subagent_type: Explore.")
    # not about models: the owner bypass (SOLO_SDD_EXPENSIVE_OK) does not lift it
    if role in ("general", "implement") and from_subagent:
        deny("The orchestrator writes the change code itself. From a subagent only subagents tagged "
             "`Review:` and `Lookup:` are allowed.")
    if owner_override():
        return
    model = ti.get("model")
    if role == "review" and model and not model_hits(model, pol["main"]):
        deny("Acceptance or review subagent on model %s. Review and acceptance run on the main model: launch without model "
             "(inherits the session model) or with a model from the list: %s." % (model, ", ".join(pol["main"])))
    if role == "lookup" and not (model and not model_hits(model, pol["expensive"])):
        deny("Lookup subagent on model %s. Set a cheap model explicitly (model: haiku). %s"
             % (model or "inherit", OWNER_ONLY))


PROFILES = (".zshenv", ".zshrc", ".zprofile", ".bashrc", ".bash_profile", ".profile")


def is_env_config(path):
    base = os.path.basename(path)
    return base in PROFILES or (base in ("settings.json", "settings.local.json")
                                and os.path.basename(os.path.dirname(path)) == ".claude")


def guard_override_write(tool, ti, path):
    if not is_env_config(path):
        return
    texts = [ti.get("content"), ti.get("new_string")] + [e.get("new_string") for e in ti.get("edits") or [] if isinstance(e, dict)]
    if any(OVERRIDE_VAR in t for t in texts if isinstance(t, str)):
        deny("Writing %s into %s is denied: only the owner turns on the model rules bypass, outside an agent session." % (OVERRIDE_VAR, path))


def guard_override_bash(cmd):
    if OVERRIDE_VAR not in cmd:
        return
    # write target: the file right after >, >>, tee or in sed -i; reading the same file in a neighbouring command does not count
    names = r"[\"']?[^\s;&|]*(?:%s|\.claude/settings(?:\.local)?\.json)" % "|".join(re.escape(n) for n in PROFILES)
    writes = re.search(r"(?:>[>|]?|\btee\b(?:\s+-\w+)*)\s*" + names, cmd) or \
        re.search(r"\bsed\s+[^;&|\n]*-\w*i[^;&|\n]*?\s" + names, cmd)
    if re.search(r"launchctl\s+setenv", cmd) or writes:
        deny("The command carries %s into the environment of future sessions. Only the owner turns on the model rules bypass." % OVERRIDE_VAR)


def secret_var(name):
    """A whole part of the name, split at `_`, digits and a lower-to-upper case change, is a secret word, alone or with a trailing S."""
    for p in re.split(r"[_\d]+|(?<=[a-z])(?=[A-Z])", name):
        p = p.upper()
        if p in SECRET_WORDS or p[-1:] == "S" and p[:-1] in SECRET_WORDS:
            return True
    return False


def env_name(path):
    return isinstance(path, str) and bool(re.fullmatch(ENV_FILE, os.path.basename(path.rstrip("/")), re.I))


def braces(g):
    m = re.search(r"\{([^{}]*)\}", g)
    return [y for x in m.group(1).split(",") for y in braces(g[:m.start()] + x + g[m.end():])] if m else [g]


GLOB_TOKEN = r"(\*+|\?|\[[^\]]*\])"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist", "build", "target"}


def glob_names(g, limit=6):
    """Names a glob spells out: each `*` taken as nothing, a letter or a dot, `?` as a letter or a dot, `[…]` as its
    first character (a letter or a dot when negated); past `limit` wildcards only a letter."""
    names, n = [""], 0
    for t in re.split(GLOB_TOKEN, g):
        if not re.fullmatch(GLOB_TOKEN, t):
            opts = [t]
        else:
            n += 1
            body = t[1:-1]
            opts = ["x"] if n > limit else [body[0]] if t[0] == "[" and body[:1] not in ("", "!", "^") else \
                ["", "x", "."] if t[0] == "*" else ["x", "."]
        names = [a + b for a in names for b in opts]
    return names


def env_files_under(root, cap=20000):
    """Names of the .env files under root, skipping dependency and build folders; at most cap entries are looked at."""
    found, seen = set(), 0
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        seen += len(files) + len(dirs)
        found.update(f for f in files if re.fullmatch(ENV_FILE, f, re.I))
        if seen > cap:  # ponytail: a bounded walk, a huge tree is searched only as far as the cap
            break
    return found


READ_DENY = ("The tool reads %s into the chat: it holds the user's keys. Do not read secrets. Check that a key exists like this: "
             "grep -c '^NAME=.' .env or test -n \"$NAME\".")


def guard_env_read(ti, cwd):
    """Read of a .env file; Grep with a .env path, or with a glob that matches a .env file: `.env` itself, a .env name the
    glob spells out, or a .env file under the search folder. A Grep over a folder without such a glob passes."""
    for k in ("file_path", "path"):
        if env_name(ti.get(k)):
            deny(READ_DENY % ti[k])
    g = ti.get("glob")
    if not isinstance(g, str):
        return
    pats = [x.rstrip("/").rsplit("/", 1)[-1].lower() for x in braces(g)]
    if any(fnmatch.fnmatchcase(".env", p) or any(re.fullmatch(ENV_FILE, n, re.I) for n in glob_names(p)) for p in pats):
        deny(READ_DENY % ("the files of glob " + g))
    root = os.path.join(cwd, os.path.expanduser(ti.get("path") or "."))
    if any(fnmatch.fnmatchcase(f.lower(), p) for f in (env_files_under(root) if os.path.isdir(root) else ()) for p in pats):
        deny(READ_DENY % ("the files of glob " + g))


ENV_WORD = re.compile(r"(?<![\w/.-])" + ENV_FILE + r"(?!/)", re.I)  # a folder named .env (a venv) is not the file
ENV_FILE_OK = {"ls", "test", "[", "[[", "stat", "touch", "chmod", "echo", "printf"}  # names a .env file, never prints it
# grep-like programs by their own option grammar: flags that print only counts, names or nothing, other flags without a
# value, flags with a value (glued or the next word), the same for long options; any other option is not read: no exemption
GREP_LONG_BOOL = {"--ignore-case", "--line-number", "--no-filename", "--with-filename", "--fixed-strings", "--extended-regexp",
                  "--word-regexp", "--line-regexp", "--invert-match", "--recursive", "--null", "--no-messages", "--text"}
GREP_SYNTAX = ("cqlL", "abEFGhHiInorRsTUvVwxyzZP", "ABCDdefm",
               {"--count", "--quiet", "--silent", "--files-with-matches", "--files-without-match"}, GREP_LONG_BOOL,
               {"--regexp", "--file", "--after-context", "--before-context", "--context", "--max-count", "--label", "--include",
                "--exclude", "--exclude-dir"})
NAMES_ONLY = {"grep": GREP_SYNTAX, "egrep": GREP_SYNTAX,
              "rg": ("cql", "abFHiILnNopPsSuUvwxz0", "ABCEefgjMmTtr",
                     {"--count", "--count-matches", "--quiet", "--files-with-matches", "--files-without-match"},
                     GREP_LONG_BOOL | {"--hidden", "--no-ignore", "--smart-case", "--case-sensitive", "--follow"},
                     {"--regexp", "--file", "--glob", "--iglob", "--replace", "--type", "--type-not", "--max-count",
                      "--after-context", "--before-context", "--context", "--encoding", "--threads", "--max-depth"})}
COPIES = {"cp": "aRrfinvpPLHlsuxdT", "mv": "finvuT", "ln": "sfnvirLPT"}  # flags without a value: the last word is the target
FIND_EXEC = {"-exec", "-execdir", "-ok", "-okdir"}
REDIRECT = re.compile(r"(.*?)(<<<|<>|<&?|>>|>[|&]?)(.*)", re.S)
QUOTED_LT, QUOTED_GT = "\x00", "\x01"


def unsubstituted(word):
    """The word without the text of its substitutions: they are checked as commands of their own."""
    for s in substituted(word):
        word = word.replace(s, "", 1)
    return word


def protect_quoted(text):
    """`<` and `>` inside quotes or after a backslash become private characters: only the rest are redirections."""
    out, q, i = [], None, 0
    while i < len(text):
        c = text[i]
        if c == "\\" and q != "'" and i + 1 < len(text):
            out.append(c + text[i + 1].replace("<", QUOTED_LT).replace(">", QUOTED_GT))
            i += 2
            continue
        if q:
            q = None if c == q else q
        elif c in "'\"":
            q = c
        out.append({"<": QUOTED_LT, ">": QUOTED_GT}.get(c, c) if q and c != q else c)
        i += 1
    return "".join(out)


def part_words(part):
    """(words of one command without their redirections, whether a redirection reads a .env file). A word that starts with
    an unquoted operator (`>`, `2>&1`, `<.env`) is a redirection with its target; one glued after text (`x>.env`) only when
    its target is a .env file. Substitution texts are cut out of the words: they are checked as commands of their own."""
    w = [unsubstituted(x) for x in split_words(protect_quoted(part))]
    args, j, reads = [], 0, False
    while j < len(w):
        r = REDIRECT.match(w[j])
        if r:
            lead = re.fullmatch(r"\d*&?", r.group(1))
            target, nxt = (r.group(3), j + 1) if r.group(3) else ((w[j + 1] if j + 1 < len(w) else ""), j + 2)
            env = bool(re.fullmatch(ENV_FILE, target, re.I))
            if lead or env:
                reads |= env and r.group(2).startswith("<")
                if not lead:
                    args.append(r.group(1))
                j = nxt
                continue
        args.append(w[j])
        j += 1
    return [x.replace(QUOTED_LT, "<").replace(QUOTED_GT, ">") for x in args], reads


def shell_reads_stdin(w, i):
    """(the -c string or None, whether the shell reads its commands from stdin), read by the shell's own option grammar:
    clustered letters, `-o name`, long options, `--` ending the options."""
    c = s = False
    j = i + 1
    while j < len(w):
        a = w[j]
        if a in ("--", "-"):
            j += 1
            break
        if a in ("--rcfile", "--init-file"):
            j += 2
        elif a.startswith("--"):
            j += 1
        elif a[:1] in "-+" and len(a) > 1:
            c, s = c or "c" in a, s or "s" in a
            j += 2 if "o" in a[1:] or "O" in a[1:] else 1
        else:
            break
    if c:
        return (w[j] if j < len(w) else ""), False
    return None, s or j >= len(w)


def shell_text(parts, k, words):
    """The command text that part k hands to a shell: eval's words, a shell's -c string, or the words of echo/printf piped
    (also through tee or a bare cat) into a shell that reads its commands from stdin; None when it is no such part."""
    w = list(words)
    i = cmd_start(w)
    prog = os.path.basename(w[i]) if i < len(w) else ""
    if prog == "eval":
        return " ".join(w[i + 1:])
    if prog not in SHELLS:
        return None
    text, stdin = shell_reads_stdin(w, i)
    if text is not None or not stdin:
        return text
    while k >= 2 and parts[k - 1] == "|":
        pw = part_words(parts[k - 2])[0]
        pi = cmd_start(pw)
        p = os.path.basename(pw[pi]) if pi < len(pw) else ""
        if p in ("echo", "printf"):
            return " ".join(pw[pi + 1:])
        if p != "tee" and not (p == "cat" and len(pw) == pi + 1):
            return None
        k -= 2
    return None


def names_only(prog, rest):
    """grep or rg with a flag that prints only counts, file names or nothing, every option read by that program's grammar;
    an option it does not know means no exemption."""
    if prog not in NAMES_ONLY:
        return False
    names, bools, valued, long_names, long_bools, long_valued = NAMES_ONLY[prog]
    hit, j = False, 0
    while j < len(rest):
        a = rest[j]
        j += 1
        if a == "--":
            break
        if a.startswith("--"):
            name = a.split("=", 1)[0]
            if name in long_names:
                hit = True
            elif name in long_valued:
                j += 0 if "=" in a else 1
            elif name not in long_bools:
                return False
        elif a.startswith("-") and len(a) > 1:
            for n, ch in enumerate(a[1:]):
                if ch in valued:
                    j += 0 if a[n + 2:] else 1  # the value is the rest of the word or the next word
                    break
                if ch in names:
                    hit = True
                elif ch not in bools:
                    return False
    return hit


def copy_sources(prog, rest):
    """The words a cp, mv or ln reads: all but the last positional when every option is a known flag without a value;
    otherwise (a target directory option, a value, a long option) every word."""
    if any(a.startswith("-") and (a.startswith("--") or set(a[1:]) - set(COPIES[prog])) for a in rest):
        return rest
    pos = [a for a in rest if not a.startswith("-")]
    return pos[:-1]


NOT_PLAIN = ("#", "$'", "${", "$(", "`", "\\")  # forms the parser here does not read: comments, quoting, expansions
REDIRS = r"(?:\s+\d*>{1,2}&?\s*\S+)*"  # `2>&1`, `> /tmp/x` after a dump word still print the environment
DUMP_WORDS = re.compile(r"(?<![\w.$-])(?:env|printenv)(?![\w.-])"
                        r"|(?<![\w.$-])set" + REDIRS + r"\s*(?:$|[;&|)}`#'\"\\\n])"
                        r"|(?<![\w.$-])(?:export|declare|typeset|readonly)(?:\s+-\w+)*" + REDIRS + r"\s*(?:$|[;&|)}`#'\"\\\n])"
                        r"|(?<![\w.$-])(?:export|declare|typeset|readonly)\s+-\w*p", re.M)


def plain(cmd):
    """The command holds none of NOT_PLAIN: only then are its words read by the parser and its exemptions applied."""
    return not any(t in cmd for t in NOT_PLAIN)


def flat(cmd):
    """The text with line continuations, quotes and backslashes removed, as the shell joins `e\\nv`, `e""nv` or
    `.e\\<newline>nv` into one word."""
    return re.sub(r"[\\'\"]", "", cmd.replace("\\\n", ""))


def env_read(cmd, depth=0):
    """A command that gives a .env file to a program, redirects input from it, sources, copies or moves it; read with the
    parser of archive_runs: the program word after wrappers; substitutions, eval, a shell's -c string and echo piped into
    a shell parsed again by this function, and past that depth any .env name counts. Listing and testing it, grep -c/-q/-l
    on it, a copy into it, find by its name and an output redirect into it are not reads."""
    if depth >= 3:  # past the depth any .env name counts
        return bool(ENV_WORD.search(cmd))
    if any(env_read(command_text(s), depth + 1) for s in substituted(cmd)):
        return True
    parts = split_cmd(cmd)
    for k in range(0, len(parts), 2):
        args, reads = part_words(parts[k])
        if reads:
            return True
        inner = shell_text(parts, k, args)
        if inner is not None:
            if env_read(command_text(inner), depth + 1):
                return True
            continue
        i = cmd_start(args)
        if i >= len(args):
            continue
        prog, rest = os.path.basename(args[i]), args[i + 1:]
        if prog in ENV_FILE_OK or prog == "git" and args[git_sub(args, i):][:1] in (["check-ignore"], ["add"]):
            continue  # git add of a secret has its own refusal
        if names_only(prog, rest) or prog == "find" and not FIND_EXEC & set(rest):
            continue  # find without -exec prints names only
        if prog in COPIES:
            rest = copy_sources(prog, rest)
        if any(ENV_WORD.search(a) for a in [args[i]] + rest):
            return True
    return False


ENV_VALUED = {"-u", "--unset", "-C", "--chdir", "-P"}


def env_alone(rest):
    """env followed only by its options and assignments: it prints the environment."""
    j = 0
    while j < len(rest):
        if rest[j] in ENV_VALUED:
            j += 2
        elif rest[j].startswith("-") or re.fullmatch(r"\w+=\S*", rest[j]):
            j += 1
        else:
            return False
    return True


def env_dump(cmd, depth=0):
    """'dump' for a command that prints the whole environment (env, printenv, set, export/declare/typeset/readonly without names
    or -p), 'secret' for printenv or declare -p of a secret variable, else None; parsed again like env_read."""
    for s in substituted(cmd) if depth < 3 else []:
        d = env_dump(command_text(s), depth + 1)
        if d:
            return d
    parts = split_cmd(cmd)
    for k in range(0, len(parts), 2):
        raw = part_words(parts[k])[0]
        inner = shell_text(parts, k, raw) if depth < 3 else None
        if inner is not None:
            d = env_dump(command_text(inner), depth + 1)
            if d:
                return d
            continue
        # a word ends at a glued redirection or a subshell end, as in archive_runs; /usr/bin/env is env
        w = [os.path.basename(y) if os.path.basename(y) in WRAPPERS else y for y in (re.split(r"[<>)&]", x, 1)[0] for x in raw) if y]
        i = cmd_start(w)
        e = next((j for j in range(min(i, len(w))) if w[j] == "env"), None)
        if e is not None and env_alone(w[e + 1:]):
            return "dump"
        if i >= len(w):
            continue
        prog, args = os.path.basename(w[i]), w[i + 1:]
        names, opts = [a for a in args if not a.startswith("-")], [a for a in args if a.startswith("-")]
        if prog == "printenv" and not names or prog == "set" and not args or \
                prog in ("export", "declare", "typeset", "readonly") and not names:
            return "dump"
        if (prog == "printenv" or prog in ("declare", "typeset") and any("p" in o for o in opts)) and any(map(secret_var, names)):
            return "secret"
    return None


def guard_secrets_bash(cmd, cwd, raw=None):
    """cmd is the command without text (command_text), raw the whole. A guard against the agent's accidental reads, not a
    boundary (docs/hooks.md lists known bypasses): the parser and its exemptions apply only when the command outside its
    text-reader heredoc bodies is plain; otherwise any .env name or dump word in the whole raw command counts."""
    raw = cmd if raw is None else raw
    readable = plain(strip_heredocs(raw))
    for m in re.finditer(r"(?i)\b(?:echo|printf)\b([^;&|\n]*)", cmd):
        if any(map(secret_var, re.findall(r"\$\{?(?!#)([A-Za-z_]\w*)", m.group(1)))):
            deny("The command prints a secret variable. Check that it exists without printing it: test -n \"$NAME\" && echo set.")
    if env_dump(cmd) or not readable and (DUMP_WORDS.search(raw) or DUMP_WORDS.search(flat(raw))):
        deny("The command prints the whole environment or a secret. Ask for a specific non-secret variable.")
    for m in re.finditer(r"(?<![>\d])>\s*(" + ENV_FILE + ")", cmd):
        p = os.path.join(cwd, os.path.expanduser(m.group(1)))
        if os.path.exists(p):
            deny("Overwriting %s with > erases the user's keys. Append an empty field with >>." % m.group(1))
    if re.search(r"\bgit\b[^;&|\n]*\badd\b", cmd):
        add = re.search(r"\badd\b([^;&|\n]*)", cmd).group(1)
        if re.search(r"(?<![\w/.-])" + ENV_FILE, add):
            deny("Do not add .env to git: it holds secrets.")
        if re.search(r"(?:^|\s)(-A|--all|\.|-u)(?:\s|$)", add):
            root = git_root(cwd)
            out = sh(["git", "-c", "core.quotepath=off", "status", "--porcelain", "--untracked-files=all"], cwd=root or cwd)
            bad = [l[3:] for l in out.splitlines() if re.fullmatch(ENV_FILE, os.path.basename(l[3:].strip('"')))]
            if bad:
                deny("git add would take files with secrets: %s. Add them to .gitignore or add files by name." % ", ".join(bad))
    if env_read(cmd) if readable else ENV_WORD.search(raw) or ENV_WORD.search(flat(raw)):
        deny("The command reads .env (a path given to a program, an input redirect, source, a copy or a move): it holds the user's "
             "keys. Do not print secrets. Check that a key exists like this: grep -c '^NAME=.' .env or test -n \"$NAME\".")


WT_RULE = ("The project has one working folder. Copies: the built-in Claude Code worktree or a temporary folder "
           "(scratchpad or /tmp) through git worktree add; remove them after yourself.")
WT_WRAPPERS = ("env", "exec", "command", "nohup", "time", "caffeinate")


def codex_worktree_cli(cmd):
    """A codex run with the built-in --worktree: Codex puts the copy into ~/.codex/worktrees.
    Words inside quotes (commit text etc.) do not count as a command."""
    for seg in re.split(r"&&|\|\||[;&|\n()]", cmd):
        try:
            words = shlex.split(seg)
        except ValueError:
            words = seg.split()
        i = 0
        while i < len(words) and (re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[i]) or words[i] in WT_WRAPPERS):
            i += 1
        if i >= len(words):
            continue
        prog, args = os.path.basename(words[i]), words[i + 1:]
        if prog == "codex" and any(a == "--worktree" or a.startswith("--worktree=") for a in args):
            return "codex --worktree puts the copy into ~/.codex/worktrees"
    return None


WT_PLAIN = ("Only the plain form passes: git worktree add [-b <name> | -B <name> | --detach | -f] <path> [<commit>], "
            "a command of its own, the path literal or after ~, $HOME, $TMPDIR or ${TMPDIR:-/tmp}, under a temporary folder")
WT_PREFIX = re.compile(r"(~|\$HOME|\$TMPDIR|\$\{TMPDIR:-/tmp\})(?=/|$)")


def wt_add(w):
    """The words of one command hold a worktree add: the words `worktree add` anywhere, or a git program word whose
    subcommand is a variable, follows an alias option, or is `worktree` followed by an expansion."""
    if any(a == "worktree" and w[k + 1:k + 2] == ["add"] for k, a in enumerate(w)):
        return True
    v = list(w)
    i = cmd_start(v)
    if i >= len(v) or os.path.basename(v[i]) != "git":
        return False
    s = git_sub(v, i)
    sub, nxt = (v[s:s + 2] + ["", ""])[:2]
    return bool(re.search(r"[$`]", sub) or sub == "worktree" and re.search(r"[$`]", nxt)) or any("alias." in x for x in v[i + 1:s])


def wt_nested(w, depth=0):
    """A worktree add in the words of eval or in the -c string of a shell, read as commands."""
    for k, a in enumerate(w):
        prog = os.path.basename(a)
        if prog == "eval" or prog in SHELLS and any(re.fullmatch(r"-\w*c\w*", x) for x in w[k + 1:k + 3]):
            inner = " ".join(w[k + 1:])
            return any(wt_add(split_words(p)) or depth < 3 and wt_nested(split_words(p), depth + 1)
                       for p in split_cmd(inner)[::2] + substituted(inner))
    return False


def wt_plain_problem(w, earlier, cwd):
    """Why a worktree add is not the plain form under a temporary root, or None. earlier: the words of the commands
    before it on the line."""
    if w[:3] != ["git", "worktree", "add"]:
        return "not a plain git worktree add"
    if any(re.search(r"[()<>;&|]", x) for x in w[3:]):
        return "a shell operator or redirection in its words"
    pos, j = [], 3
    while j < len(w):
        if w[j] in ("-b", "-B") and j + 1 < len(w):
            j += 2
        elif w[j] in ("--detach", "-f"):
            j += 1
        elif w[j].startswith("-"):
            return "option %s" % w[j]
        else:
            pos.append(w[j])
            j += 1
    if not 1 <= len(pos) <= 2 or len(pos) == 2 and re.search(r"[$`]", pos[1]):
        return "the words after the options are not <path> [<commit>]"
    path = pos[0]
    m = WT_PREFIX.match(path)
    prefix, tail = (m.group(1), path[m.end():]) if m else ("", path)
    if re.search(r"[$`*?\[{]", tail) or path.startswith("~") and not prefix:
        return "the path %s holds an expansion" % path
    if any(os.path.basename(x) == "ln" for x in earlier):
        return "an ln earlier on the line"
    if "TMPDIR" in prefix:
        if any(re.fullmatch(r"TMPDIR(\+?=.*)?", x) for x in earlier):
            return "TMPDIR is changed earlier on the line"
        return "the path leaves the temporary folder" if ".." in tail.split("/") else None
    if not prefix and not path.startswith("/") and any(x in ("cd", "pushd", "popd") for x in earlier):
        return "a relative path after a folder change earlier on the line"
    full = HOME + tail if prefix else os.path.join(cwd, path)
    if not any(under(full, r) for r in TMP_ROOTS):
        return "the path %s is outside the temporary folder" % path
    return None


def guard_worktree(cmd, cwd):
    """git worktree add passes only in the plain form under a temporary root (Worktree add by shell words, Worktree
    path line state). A guard against accidents by the forms it reads, not a boundary."""
    text = strip_heredocs(cmd)
    bare = re.sub(r"\$(?=['\"])|[\"'\\]", "", text)
    if UNCUT.search(text) and re.search(r"\bworktree\s+add\b", bare):
        deny("git worktree add refused: the line holds $'…', =(…), a # word or a ${…} the hook cannot read. %s. %s" % (WT_PLAIN, WT_RULE))
    earlier = []
    for part in split_cmd(text)[::2]:
        w = split_words(part)
        why = wt_plain_problem(w, earlier, cwd) if wt_add(w) else "inside eval or a shell -c string" if wt_nested(w) else None
        if why:
            deny("git worktree add refused: %s. %s. %s" % (why, WT_PLAIN, WT_RULE))
        earlier += [x.lstrip("({!") for x in w]
    if any(wt_add(split_words(p)) for s in substituted(text) for p in split_cmd(s)[::2]):
        deny("git worktree add refused: inside a substitution. %s. %s" % (WT_PLAIN, WT_RULE))
    why = codex_worktree_cli(cmd)
    if why:
        deny("%s. For Codex a copy goes only into a temporary folder: git worktree add, then codex exec -C <worktree>. %s" % (why, WT_RULE))


# the forms strip_patterns leaves uncut and every ${, a plain parameter expansion too: read again with quotes ignored
UNREADABLE = re.compile(UNCUT.pattern + r"|\$\{")
MERGE_API = re.compile(r"(?:^|/)pulls/[^/\s?#]+/merge/?(?:[?#].*)?$")  # gh api sends a query string with the path
MERGE_RULE = ("A direct merge (gh pr merge, gh api .../pulls/<n>/merge) in a project with a solo-sdd/ tree skips the gates of "
              "sdd-pr.py merge: human merge, behind, code scanning, «Owner only:» paths and checklists. Merge by the /ship skill: "
              "python3 ~/.local/bin/sdd-pr.py open <worktree> <main> <title>, then wait <url>, then "
              "sdd-pr.py merge <url> <squash|merge|rebase> <hash>.")


def gh_merge_words(w):
    """The words of one command, quotes removed, run gh pr merge or gh api …/pulls/<n>/merge."""
    i = cmd_start(w)
    if i >= len(w) or os.path.basename(w[i]) != "gh":
        return False
    pos, j = [], i + 1
    while j < len(w):
        if w[j] in ("-R", "--repo"):
            j += 2
            continue
        if not w[j].startswith("-"):
            pos.append(w[j])
        j += 1
    return pos[:2] == ["pr", "merge"] or pos[:1] == ["api"] and any(MERGE_API.search(x) for x in pos[1:])


def gh_merges(cmd, depth=0, subs=None):
    """A gh pr merge or gh api …/pulls/<n>/merge run, read as archive_runs reads an archive: the program word after
    wrappers and assignments; substitutions (each a command list again), eval and a shell's -c string are parsed again;
    an argument of another program is not a run. subs: the substitutions to read instead of those of cmd."""
    if depth < 3 and any(gh_merges(command_text(x), depth + 1) for x in (substituted(cmd) if subs is None else subs)):  # its heredocs and messages are text too
        return True
    for part in split_cmd(cmd)[::2]:
        raw = split_words(part)
        w = [os.path.basename(x) if os.path.basename(x) in WRAPPERS else x for x in (re.split(r"[<>)&]", y, 1)[0] for y in raw)]
        # an assignment with a quoted value holding spaces (FOO='a b') is unquoted here, cmd_start would take it for the program
        w = ["A=x" if re.fullmatch(r"[A-Za-z_]\w*=[\s\S]*", x) else x for x in w]
        i = cmd_start(w)
        prog = os.path.basename(w[i]) if i < len(w) else ""
        if depth < 3 and prog == "eval":
            if gh_merges(" ".join(raw[i + 1:]), depth + 1):
                return True
        elif depth < 3 and prog in SHELLS:
            c = next((k for k in range(i + 1, len(w)) if re.fullmatch(r"-\w*c\w*", w[k])), None)
            if c is not None and c + 1 < len(w) and gh_merges(raw[c + 1], depth + 1):
                return True
        elif gh_merge_words(w):
            return True
    return False


def gh_merges_unquoted(cmd):
    """For a form whose quotes this reader cannot follow (UNREADABLE): every stretch between shell separators, quotes
    ignored, is read as a command, so a gh merge hidden by a moved quote boundary is found; a message or comment that
    does not start a stretch with gh is still text. Words are read as gh_merges reads them: no backslash, a wrapper by
    its name."""
    def word(x):
        x = x.replace("\\", "").strip("'\"")
        return os.path.basename(x) if os.path.basename(x) in WRAPPERS else x
    return any(gh_merge_words([word(x) for x in seg.split()]) for seg in re.split(r"&&|\|\||[;&|\n()`]|\$\(", cmd))


def guard_merge(text, cwd, raw):
    """text is command_text: messages, patterns and heredoc bodies for text readers are cut. Its substitutions are taken
    from raw: strip_message requotes a part, which hides a heredoc marker inside its substitution. A form it cannot cut
    (UNREADABLE) is read once more with quotes ignored."""
    if not (gh_merges(text, subs=substituted(strip_heredocs(raw))) or UNREADABLE.search(text) and gh_merges_unquoted(text)):
        return
    root = git_root(cwd)
    if root and os.path.isdir(os.path.join(root, "solo-sdd")):
        deny(MERGE_RULE)


STATUS_FIELDS = ("STATUS", "CHANGE", "BRANCH", "WORKTREE", "COMMIT", "ARCHIVE", "VALIDATE", "TESTS", "LIVE",
                 "REVIEW", "AGENTS", "HOOKS", "NOT_VERIFIED", "NOTES")
STATUS_VALUES = ("archived", "not_ready", "blocked")


def parse_status(message):
    """Fields of the status block, or None if the message has no line starting with STATUS:."""
    lines = [l.lstrip() for l in message.splitlines()]
    if not any(l.startswith("STATUS:") for l in lines):
        return None
    fields = {}
    for l in lines:
        m = re.match(r"(%s):(.*)" % "|".join(STATUS_FIELDS), l)
        if m:
            fields.setdefault(m.group(1), m.group(2).strip())
    return fields


EXIT_0 = r"(?i)exit\s+0(?:[\s;,)]|$)"


def exit_zero(value):
    """The code after the first " -> " (without an arrow, at the start) is exit 0; notes and other commands after it
    are allowed (`npm test -> exit 0 (250 files); npm run typecheck -> exit 0`), a non-zero exit after the arrow is not."""
    arrows = [x.strip() for x in re.split(r"\s*->\s*", value)]
    head = arrows[1] if len(arrows) > 1 else value.strip()
    # a non-zero exit anywhere after the arrow: `-> exit 1`, `-> exit: 1`, `build -> failed (exit 1)`
    bad = r"(?i)\bexit\b(?!\s+0(?:[\s;,)]|$))"
    return bool(re.match(EXIT_0, head)) and not any(re.match(bad, a) or re.search(bad + r"\W*[1-9]", a) for a in arrows[1:])


def live_problems(value):
    """LIVE is one command: outside quotes and without `\\` there is no `&&`, `||`, `;`, `|` and no leading `cd ` (the text before the first arrow is checked).
    An unclosed quote: the rest counts as quoted, no refusal."""
    cmd, sign, q, i = re.split(r"\s*->\s*", value)[0], None, None, 0
    if cmd.lstrip().startswith("cd "):
        sign = "cd "
    while sign is None and i < len(cmd):
        c = cmd[i]
        if q:
            q = None if c == q else q
            i += 1 if c == "\\" and q == '"' else 0
        elif c == "\\":
            i += 1
        elif c in "'\"":
            q = c
        else:
            sign = next((s for s in ("&&", "||", ";", "|") if cmd.startswith(s, i)), None)
        i += 1
    return [] if sign is None else ["LIVE: the command has «%s» outside quotes: one command from the WORKTREE root is needed; make a multi-step scenario "
                                    "a stand (a script in the repository) and give its call in LIVE, the dispatcher shortens the output" % sign]


def archived_problems(f, cwd):
    problems = ["field missing or empty: %s" % n for n in STATUS_FIELDS if not f.get(n)]
    wt = os.path.join(cwd, os.path.expanduser(f["WORKTREE"])) if f.get("WORKTREE") else git_root(cwd)
    if not wt or not os.path.exists(os.path.join(wt, ".git")):
        return problems + ["WORKTREE is not a git working copy (no folder or no .git in it): %s" % (wt or "git root for cwd not found")]
    wt = nfc(os.path.realpath(wt))
    head = git_strict(["git", "rev-parse", "HEAD"], cwd=wt).strip()
    commit = f.get("COMMIT", "")
    if commit and not (re.fullmatch(r"[0-9a-fA-F]{7,}", commit) and head.startswith(commit.lower())):
        problems.append("COMMIT %s is not the start of the last commit HEAD %s (at least 7 hex digits needed)" % (commit, head))
    name = f.get("CHANGE", "")
    arch = f.get("ARCHIVE", "")
    tree = process_root(wt)
    if arch:
        a = nfc(os.path.realpath(os.path.join(wt, arch)))
        if not (os.path.isdir(a) and a.startswith(os.path.join(wt, tree, "changes", "archive") + "/")):
            problems.append("ARCHIVE %s is not an existing folder inside %s/changes/archive/ in %s" % (arch, tree, wt))
    if name and os.path.exists(os.path.join(wt, tree, "changes", name)):
        problems.append("%s/changes/%s is still in %s: the change was not moved to the archive" % (tree, name, wt))
    main = main_checkout(wt, run=git_strict)
    if name and os.path.exists(os.path.join(main, process_root(main), "changes", name, "CLAIM")):
        problems.append("the CLAIM of change %s is still in the main folder %s: remove it" % (name, main))
    problems += ["%s: after the first « -> » there must be «exit 0», and no « -> exit » with another code; now: %s" % (n, f[n])
                 for n in ("VALIDATE", "TESTS") if f.get(n) and not exit_zero(f[n])]
    return problems + live_problems(f.get("LIVE", ""))


def status_problems(message, cwd):
    """Mismatches of the orchestrator status with git and files; an empty list means all is right or this is not a status."""
    f = parse_status(message)
    if f is None:
        return []
    if f.get("STATUS") not in STATUS_VALUES:
        return ["STATUS «%s» is not one of: %s" % (f.get("STATUS", ""), ", ".join(STATUS_VALUES))]
    if f["STATUS"] != "archived":
        return ["field missing or empty: %s" % n for n in ("CHANGE", "NOTES") if not f.get(n)]
    return archived_problems(f, cwd)


def cmd_guard(inp):
    tool, ti = inp.get("tool_name"), inp.get("tool_input") or {}
    sid, cwd = inp.get("session_id", ""), os.path.realpath(inp.get("cwd") or os.getcwd())
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = ti.get("file_path") or ti.get("notebook_path")
        if not path:
            return
        path = os.path.join(cwd, os.path.expanduser(path))
        guard_env_write(tool, path, cwd)
        guard_override_write(tool, ti, path)
        guard_scope(sid, cwd, path)
        guard_claim(sid, path, tool, ti)
    elif tool in ("Read", "Grep"):
        guard_env_read(ti, cwd)
    elif tool == "Bash":
        cmd = ti.get("command") or ""
        text = command_text(cmd)
        guard_secrets_bash(text, cwd, cmd)
        guard_override_bash(cmd)
        guard_models_bash(text, cmd)
        guard_worktree(cmd, cwd)
        guard_merge(text, cwd, cmd)
        guard_archive(sid, text, cwd, inp)
        note_claim_cmd(inp, cmd)
    elif tool == "Agent":
        guard_models_agent(ti, bool(inp.get("agent_id")))
    elif tool == "SubagentHandback":
        problems = status_problems(ti.get("message") or "", cwd)
        if problems:
            deny("Status not accepted by the hook, mismatches:\n- " + "\n- ".join(problems) +
                 "\nIf they cannot be fixed, hand in `STATUS: not_ready` with the reason in `NOTES`.")


# ---------- stop: Stop ----------

def transcript_events(f):
    """Edits and tool calls of a transcript in order: ("edit", path) for a tool or Bash edit, ("tool", name, input)."""
    for raw in f:
        if b'"tool_use"' not in raw and b"bashEditDiff" not in raw:
            continue
        try:
            d = json.loads(raw)
        except Exception:
            continue
        r = d.get("toolUseResult")
        if isinstance(r, dict) and isinstance(r.get("bashEditDiff"), dict):
            for fp in r["bashEditDiff"].get("changedFiles") or []:
                yield "edit", fp
        if d.get("type") != "assistant":
            continue
        for p in (d.get("message") or {}).get("content") or []:
            if not isinstance(p, dict) or p.get("type") != "tool_use":
                continue
            name, ti = p.get("name", ""), p.get("input") or {}
            if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
                fp = ti.get("file_path") or ti.get("notebook_path")
                if fp:
                    yield "edit", fp
            else:
                yield "tool", name, ti


def browser_signs():
    """{"tools", "skills", "bash"}: the built-in browser signs plus the lists of non-empty strings of the policy's
    `browser` key. A missing key or part adds nothing; a broken one, or a file that cannot be read or parsed, adds
    nothing and writes one errors.log line naming it, so the rest of `stop` still runs."""
    signs = {"tools": BROWSER_TOOLS, "skills": BROWSER_SKILLS, "bash": BROWSER_BASH}
    try:
        doc = policy()
        if not isinstance(doc, dict):
            raise ValueError("not a JSON object")
    except Exception as e:
        log_error("stop model-policy.json", e)
        return signs
    key = doc.get("browser", {})
    if not isinstance(key, dict):
        log_error("stop browser", ValueError("not an object"))
        return signs
    for part in signs:
        extra = key.get(part, [])
        if isinstance(extra, list) and all(isinstance(x, str) and x for x in extra):
            signs[part] = signs[part] + tuple(extra)
        else:
            log_error("stop browser.%s" % part, ValueError("not a list of non-empty strings"))
    return signs


def scan_transcript(path, signs):
    edited, browser, pushed = set(), False, False
    try:
        f = open(path, "rb")
    except Exception:
        return edited, browser, pushed
    with f:
        for ev in transcript_events(f):
            if ev[0] == "edit":
                edited.add(ev[1])
                continue
            name, ti = ev[1], ev[2]
            if name.startswith(signs["tools"]):
                browser = True
            elif name == "Skill" and str(ti.get("skill", "")).split(":")[-1] in signs["skills"]:
                browser = True
            elif name == "Bash":
                c = ti.get("command") or ""
                browser = browser or any(b in c for b in signs["bash"])
                pushed = pushed or bool(re.search(r"\bgit\b[^;&|\n]*\bpush\b|gh pr create", c))
    return edited, browser, pushed


def last_text(inp):
    if inp.get("last_assistant_message"):
        return inp["last_assistant_message"]
    try:
        with open(inp["transcript_path"], "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 3000000))
            lines = f.read().splitlines()
    except Exception:
        return ""
    for raw in reversed(lines):
        try:
            d = json.loads(raw)
        except Exception:
            continue
        if d.get("type") == "assistant":
            texts = [p.get("text", "") for p in (d.get("message") or {}).get("content") or []
                     if isinstance(p, dict) and p.get("type") == "text"]
            if texts:
                return "\n".join(texts)
    return ""


CYRILLIC = "[\u0430-\u044f\u0451\u0410-\u042f\u0401]"
REPLY_LANGS = {"ru": ("Russian", CYRILLIC, 0.3), "en": ("English", "[A-Za-z]", 0.7)}


def wrong_language(text, lang):
    """Language name when the reply is not in lang (ru, en), else None; other values (off): no check."""
    if lang not in REPLY_LANGS:
        return None
    name, letters, share = REPLY_LANGS[lang]
    t = re.sub(r"```.*?```|`[^`]*`|https?://\S+|(?:~|\.{0,2})?/[\w./-]+", " ", text, flags=re.S)
    cyr, lat = len(re.findall(CYRILLIC, t)), len(re.findall(r"[A-Za-z]", t))
    own = len(re.findall(letters, t))
    return name if cyr + lat >= 80 and own / float(cyr + lat) < share else None


def dirty_paths(root):
    out = sh(["git", "status", "--porcelain", "-z"], cwd=root)
    paths, items, i = set(), out.split("\0"), 0
    while i < len(items):
        e = items[i]
        if len(e) > 3:
            paths.add(nfc(os.path.realpath(os.path.join(root, e[3:]))))
            if e[0] in "RC":
                i += 1
        i += 1
    return paths


INTEGRATION_RUN = "solo-sdd check --point checks --changed"


def integration_reasons(by_root):
    """A reason per repository (by_root: {git root: files of it the session edited}) with a solo-sdd/ tree where an
    enabled integration of the point checks has an `applies` matching an edited file that `check --changed` sees (one
    changed_files lists) and no record of the point checks exists for the current tree. Each repository is read under
    its own guard: a broken description is logged and gives no reason, a broken config or record read is logged and
    the repository gives no reason."""
    out = []
    for root, files in sorted(by_root.items()):
        if process_root(root) != "solo-sdd":
            continue
        try:
            listed = listed_names(parse_settings(read_settings_text(root)).get(LISTED, ""))
            found = {e["name"]: e for e in find_integrations(root, HOME) if e["name"] and not e["shadowed"]} if listed else {}
            rel = [os.path.relpath(p, root).replace(os.sep, "/") for p in sorted(files)]
            hits = []
            for name in listed:
                e = found.get(name)
                if e and e["error"]:
                    log_error("stop integration %s" % name, ValueError(e["error"]))
                elif e and "checks" in e["fields"]["points"] and any(
                        fnmatch.fnmatchcase(p, g) for p in rel for g in (e["fields"]["applies"] or ["*"])):
                    hits.append(name)
            if hits:  # only edits `check --changed` sees: committed on the base, ignored or reverted ones are not
                rel = sorted(set(rel) & {nfc(p) for p in changed_files(root)})
                hits = [n for n in hits if any(fnmatch.fnmatchcase(p, g) for p in rel
                                               for g in (found[n]["fields"]["applies"] or ["*"]))]
            if not hits:
                continue
            points = read_json(os.path.join(repo_dir(root, HOME), tree_hash(root) + ".json")).get("points")
            if not (isinstance(points, dict) and isinstance(points.get("checks"), dict)):
                out.append("%s: the integrations %s apply to this session's edits and no run is recorded for the "
                           "current tree. Run `%s` (in a change: `--change <id>`) or say why not." %
                           (root, ", ".join(hits), INTEGRATION_RUN))
        except Exception as e:
            log_error("stop integrations", e)
    return out


def cmd_stop(inp):
    if inp.get("stop_hook_active"):
        return
    if any(isinstance(t, dict) and t.get("status") == "running" for t in inp.get("background_tasks") or []):
        return  # background agents are still running: the dispatcher waits for them, the gate is not needed
    sid, cwd = inp.get("session_id", ""), os.path.realpath(inp.get("cwd") or os.getcwd())
    tp = inp.get("transcript_path") or ""
    signs = browser_signs()
    edited, browser, pushed = scan_transcript(tp, signs)
    # a browser check counts for the session's subagents too; edits and push are taken only from the main transcript
    for sub in glob.glob(glob.escape(re.sub(r"\.jsonl$", "", tp)) + "/subagents/agent-*.jsonl") if tp else []:
        browser = browser or scan_transcript(sub, signs)[1]
    edited = {nfc(os.path.realpath(os.path.join(cwd, p))) for p in edited}
    edited = {p for p in edited if "/scratchpad/" not in p}
    reasons = []

    by_root = {}
    for p in edited:
        r = git_root(p)
        if r:
            by_root.setdefault(r, set()).add(p)
    for root, files in sorted(by_root.items()):
        dirty = sorted(files & dirty_paths(root))
        if dirty:
            names = ", ".join(os.path.relpath(p, root) for p in dirty[:5]) + (" …" if len(dirty) > 5 else "")
            reasons.append("%s has uncommitted edits of this session (%d: %s). Commit and push (/ship) "
                           "or say «not ready» and why." % (root, len(dirty), names))

    for cdir in sorted({c[0] for c in map(change_file, edited) if c and c[1] != "archive"}):
        tasks = read_head(os.path.join(cdir, "tasks.md"), 200000)
        if tasks and os.path.isdir(cdir) and re.search(r"^\s*- \[[xX]\]", tasks, re.M) and not re.search(r"^\s*- \[ \]", tasks, re.M):
            reasons.append("Change %s: every task is checked but it is not archived. Run verify, sync, archive and remove the CLAIM, "
                           "or say what is missing." % os.path.basename(cdir))

    root = git_root(cwd)
    if pushed and root and not human_merge(main_checkout(root)):  # a person merges: an open PR is the expected end
        pr = sh(["gh", "pr", "view", "--json", "state,url"], cwd=root, timeout=10)
        try:
            pr = json.loads(pr) if pr else {}
        except Exception:
            pr = {}
        if pr.get("state") == "OPEN":
            reasons.append("PR %s is open and not merged. Merge it and update the main branch (/ship) if the merge does not start "
                           "a production deploy. If it does, ask the user." % pr.get("url"))

    ui = sorted(p for p in edited if p.endswith(UI_EXT) and not re.search(r"\.(test|spec)\.", p))
    if ui and not browser:
        reasons.append("The interface changed (%s) but the session had no browser check. Check on desktop and phone "
                       "(/ui-check) or say why the check is impossible." % ", ".join(os.path.basename(p) for p in ui[:4]))

    reasons += integration_reasons(by_root)

    text = last_text(inp)
    lang = wrong_language(text, reply_language(root or cwd))
    if lang:
        reasons.append("The final reply is not in %s. Rewrite it in %s." % (lang, lang))

    if not reasons:
        return
    key = hashlib.sha1(("\n".join(reasons) + (text if reasons[-1].startswith("The final reply") else "")).encode()).hexdigest()
    p = state_path(sid, "stop")
    if (read_head(p, 100) or "").strip() == key:
        return
    with open(p, "w") as f:
        f.write(key)
    emit({"decision": "block", "reason": "Readiness gate (Stop hook):\n- " + "\n- ".join(reasons) +
          "\nIf an item is deliberately not done, say so in the reply in one line. With the same set of items the hook does not fire again."})


# ---------- beat / end / status ----------

def cmd_beat(inp):
    sid, ev = inp.get("session_id", ""), inp.get("hook_event_name", "")
    st = load_state(sid)
    now = time.time()
    st["cwd"] = inp.get("cwd") or st.get("cwd")
    if ev == "PreToolUse":
        ti, tool = inp.get("tool_input") or {}, inp.get("tool_name", "")
        detail = ti.get("description") or ti.get("command") or ti.get("file_path") or ti.get("skill") or ti.get("prompt") or ""
        if ti.get("file_path"):
            detail = os.path.basename(ti["file_path"])
        st.update(phase="run", tool=tool, detail=re.sub(r"\s+", " ", str(detail))[:60], since=now)
    elif ev == "PostToolUse":
        st.update(phase="done", since=now)
    elif ev == "SubagentStart" and inp.get("agent_id"):
        st.setdefault("subagents", {})[inp["agent_id"]] = inp.get("agent_type", "")
    elif ev == "SubagentStop":
        st.setdefault("subagents", {}).pop(inp.get("agent_id", ""), None)
    elif ev == "UserPromptSubmit":
        st.update(phase="think", since=now)
    elif ev == "Stop":
        st.update(phase="idle", since=now)
    save_state(sid, st)


ERROR_LINES = 1000


def cmd_end(inp):
    sid = inp.get("session_id", "")
    # the trim first: a failure of the cleanup below must not keep the log growing
    log = os.path.join(STATE, "errors.log")
    if os.path.exists(log):
        with open(log, "rb") as f:
            lines = f.readlines()
        if len(lines) > ERROR_LINES:
            # ponytail: a line another hook appends between the read and the write is lost; a lock if that is ever seen
            with open(log, "wb") as f:
                f.writelines(lines[-ERROR_LINES:])
    st = load_state(sid)
    for claim in st.get("claims", []) + [l for l in claim_log(sid) if l.startswith("/")]:
        body = read_head(claim, 300) or ""
        if sid and sid in body:
            os.remove(claim)
    for p in (state_path(sid), state_path(sid, "claims"), state_path(sid, "cmds"), state_path(sid, "scope"), state_path(sid, "stop")):
        if os.path.exists(p):
            os.remove(p)
    for n in os.listdir(STATE):
        p = os.path.join(STATE, n)
        if n.endswith((".json", ".claims", ".cmds", ".scope", ".stop")) and time.time() - os.path.getmtime(p) > 7 * 86400:
            os.remove(p)


def fmt_age(sec):
    sec = int(sec)
    return "%ds" % sec if sec < 60 else "%dm%02ds" % (sec // 60, sec % 60) if sec < 3600 else "%dh%02dm" % (sec // 3600, sec % 3600 // 60)


def cmd_status(inp):
    st = load_state(inp.get("session_id", ""))
    model = (inp.get("model") or {}).get("display_name", "")
    folder = os.path.basename((inp.get("workspace") or {}).get("current_dir") or inp.get("cwd") or "")
    age = fmt_age(time.time() - st.get("since", time.time()))
    phase = st.get("phase")
    if phase == "run":
        now = "▶ %s: %s · %s" % (st.get("tool"), st.get("detail"), age)
    elif phase == "done":
        now = "✓ last action %s ago: %s" % (age, st.get("tool"))
    elif phase == "think":
        now = "… thinking %s" % age
    elif phase == "idle":
        now = "⏸ waiting for you %s" % age
    else:
        now = ""
    subs = len(st.get("subagents") or {})
    print(" · ".join(x for x in (model, folder, now, ("subagents: %d" % subs) if subs else "") if x))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        inp = json.load(sys.stdin)
        {"context": cmd_context, "subagent-context": cmd_subagent_context, "guard": cmd_guard, "stop": cmd_stop, "beat": cmd_beat,
         "end": cmd_end, "status": cmd_status, "claims": cmd_claims}[cmd](inp)
    except SystemExit:
        raise
    except Exception as e:
        log_error(cmd, e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
