"""Integrations: outside tools and rule sets plugged in by one contract, and `solo-sdd integrations list|enable|disable`.

The block between the integration-reader markers reads the `integration` file and finds the two sources; it uses
the standard library only and runs on /usr/bin/python3 3.9, since python3 scripts/sync_blocks.py copies it into the
scripts of global/ that hold its markers: edit it here.
"""
import os
import stat
import unicodedata

from solo_sdd import process_format as pf, resources, rules_block, settings

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


BUNDLED = os.path.join(resources.ROOT, "integrations")  # the integrations shipped with the package, below the other two
OFF = "integrations.off"  # the settings key of the bundled names switched off


def all_sources():
    """The project, owner and bundled sources, in that order (BUNDLED read at the call)."""
    return INTEGRATION_SOURCES + (("bundled", BUNDLED),)


def enabled_names(entries, found):
    """The names that run, sorted: each name of `integrations` but one whose used folder is bundled, and each used
    bundled one that `integrations.off` does not name. found: the settings read from the file."""
    bundled = {e["name"] for e in entries if e["source"] == "bundled" and e["name"] and not e["shadowed"]}
    off = listed_names(found.get(OFF, ""))
    return sorted({n for n in listed_names(found.get(LISTED, "")) if n not in bundled} | (bundled - set(off)))


RULES_FILE = "rules.md"
RULES_MAX_BYTES = 8192


def rules_sections(entries, names):
    """[(name, text)] of the rules.md of each name, in name order, entries from find_integrations; a name with no
    readable description, no rules.md or a blank one gives none. IntegrationError naming the file for one that
    integration_text refuses or that holds a line the block parser reads as a solo-sdd marker."""
    used = {e["name"]: e for e in entries if e["name"] and not e["shadowed"] and not e["error"]}
    out = []
    for name in sorted(set(names) & set(used)):
        path = os.path.join(used[name]["dir"], RULES_FILE)
        if not os.path.lexists(path):
            continue
        where = used[name]["file"].rsplit("/", 1)[0] + "/" + RULES_FILE
        # a lone CR ends a line for a Markdown reader: read as LF, so no marker hides behind one and the block stays LF
        text = integration_text(path, where, RULES_MAX_BYTES).replace("\r\n", "\n").replace("\r", "\n")
        found = rules_block.marker(text)
        if found:
            raise IntegrationError("%s:%d: the solo-sdd block marker %s would end the block early" % ((where,) + found))
        if text.strip():
            out.append((name, text))
    return out


def run(args, cwd=".", home=None):
    """`integrations list | enable <name> | disable <name>`; the exit code, or None on bad arguments."""
    if not args or (args[0], len(args)) not in (("list", 1), ("enable", 2), ("disable", 2)):
        return None
    tree = pf.find_tree(cwd)
    if tree is None:
        print("no solo-sdd/ tree")
        return 1
    root = str(tree.parent)
    try:
        text = settings.read_settings_text(root)
        found = settings.parse_settings(text)
    except (OSError, ValueError) as e:
        print(e)
        return 1
    listed, off = listed_names(found.get(LISTED, "")), listed_names(found.get(OFF, ""))
    entries = find_integrations(root, home if home is not None else os.path.expanduser("~"), all_sources())
    used = {e["name"]: e for e in entries if e["name"] and not e["shadowed"]}
    on = enabled_names(entries, found)
    if args[0] == "list":
        code = 0
        for e in entries:
            if e["shadowed"]:
                print("%s %s shadowed by the %s copy" % (e["name"], e["source"], used[e["name"]]["source"]))
            elif e["error"]:
                print("%s %s broken: %s" % (e["name"] or "-", e["source"], e["error"]))
                code = 1
            else:
                print("%s %s %s %s: %s" % (e["name"], e["source"], "enabled" if e["name"] in on else "disabled",
                                           ", ".join(e["fields"]["points"]), e["fields"]["about"]))
        for name in listed:
            if name not in used:
                print("%s: listed in %s of %s, %s" % (name, LISTED, settings.SETTINGS_FILE, NOWHERE))
                code = 1
        return code
    name = integration_shown(args[1])
    key, names = (OFF, off) if name in used and used[name]["source"] == "bundled" else (LISTED, listed)
    if args[0] == "enable":
        if name not in used:
            print("%s: %s; found: %s" % (name, NOWHERE, ", ".join(sorted(used)) or "none"))
            return 1
        if used[name]["error"]:
            print(used[name]["error"])
            return 1
        new = [n for n in names if n != name] if key == OFF else names if name in names else names + [name]
    elif name in names:
        new = names if key == OFF else [n for n in names if n != name]
    elif name in used:
        new = names + [name] if key == OFF else names
    else:
        print("%s: not in %s of %s and %s" % (name, LISTED, settings.SETTINGS_FILE, NOWHERE))
        return 1
    from solo_sdd import init  # init reads the rules of this module: imported here, not at the top
    try:
        sections = rules_sections(entries, new if key == LISTED else listed)
        scope = settings.read_settings(root)["rules.scope"][0]
    except (OSError, ValueError) as e:  # IntegrationError is a ValueError
        print("%s; nothing changed" % e)
        return 1
    changed = settings.set_text(text, key, ", ".join(new) or None) if new != names else text
    cfg = os.path.join(root, settings.SETTINGS_FILE)
    if changed != text and not os.access(cfg if os.path.lexists(cfg) else os.path.dirname(cfg), os.W_OK):
        print("cannot write %s: not writable; nothing changed" % settings.SETTINGS_FILE)
        return 1
    if init.project_rules(root, scope, sections, create=False):  # a block it cannot read or write: config unchanged
        return 1
    if changed != text:
        try:
            with open(cfg, "w", encoding="utf-8", newline="") as f:
                f.write(changed)
        except OSError as e:
            print(e)
            return 1
    print("%s: %s" % (key, ", ".join(new) or "none"))
    return 0

