"""Project settings: `solo-sdd/config` and the `solo-sdd config list|get|set|unset` command.

The block between the settings markers is copied into the scripts of global/ that hold its markers
(they are laid out as separate files and run on /usr/bin/python3 3.9) by python3 scripts/sync_blocks.py: edit it here.
"""
import os
import sys

from solo_sdd import process_format as pf, providers

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
# The block above is copied into files that cannot import the package: the agents default is the detected ones here.
REGISTRY["agents"] = REGISTRY["agents"][:2] + (", ".join(providers.detected()), None)


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


def unknown_key(key, registry=REGISTRY):
    return None if entry(key, registry) else "unknown key %s; known: %s" % (key, ", ".join(list(registry) + list(PATTERNS)))


def run(args, cwd=".", registry=REGISTRY):
    """`config list | get <key> | set <key> <value> | unset <key>`; the exit code, or None on bad arguments."""
    if not args or (args[0], len(args)) not in (("list", 1), ("get", 2), ("set", 3), ("unset", 2)):
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
    if args[0] == "list":
        for key, (value, source) in values.items():
            print("%s %s %s" % (key, value, source))
        return 0
    bad = unknown_key(args[1], registry)
    if bad:
        print(bad)
        return 1
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
    if new != text:
        try:
            with open(os.path.join(root, SETTINGS_FILE), "w", encoding="utf-8", newline="") as f:
                f.write(new)
        except OSError as e:
            print(e)
            return 1
    print("%s: %s" % (args[1], value) if value is not None else "%s: removed, in effect %s" % (
        args[1], effective(parse_settings(new, registry), registry, agents).get(args[1], ("",))[0]))
    return 0

