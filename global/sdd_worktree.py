#!/usr/bin/env python3
"""Working copy of a change: git-ignored artifacts between the main folder and a worktree.

Run: sdd_worktree.py <setup|refresh|transport|undo|remove|discard> <MAIN> <WORKTREE>

Artifact set: everything under the process root (solo-sdd/ if it holds project.md, specs/ or changes/, else
openspec/), the files AGENTS.md and CLAUDE.md at the root and the paths
of the AGENTS.md section «Working copy» (optional) that git ignores in MAIN.
Section format (up to the next «## » heading), values in backticks:

    ## Working copy

    - Paths: `docs/architecture.md`, `docs/waiting.md`
    - Prepare: `npm ci --prefer-offline`
    - After refresh: `npm run build:ocr`

Paths are relative to the root, files or folders. The prepare command and the after-refresh command run
through sh -c in WORKTREE; setup runs the prepare command, refresh runs the after-refresh command.

Besides, setup adds to the set the documents MAIN ignores one by one (not as a whole ignored
folder): .md, .txt, .rst, .adoc up to 1 MiB, no links, node_modules, .venv or .env*. Their list
lives in the snapshot (<WORKTREE>.base/.sdd-ignored); after that they are handled like the whole set.

setup      copies what is needed into WORKTREE, puts the snapshot into <WORKTREE>.base/, links
           node_modules and .venv, adds them to info/exclude, runs the prepare command.
           With `delivery.base` in solo-sdd/config it first moves a worktree without own commits to
           origin/<base> (no such ref: the local <base>) unless HEAD already contains it or a local <base>
           ahead of it, and then prints «start: <ref>»; own commits or broken settings: code 1.
refresh    brings MAIN edits made after setup into WORKTREE (three-way merge: base = snapshot);
           on conflict the WORKTREE file gets markers, code 3; the snapshot is updated to MAIN.
           Without conflicts it then runs the «After refresh:» command (stdin closed, limit 600 s):
           success is the line «after refresh: <command> — code 0» without the command output; a non-zero
           code or a timeout prints at most the last 20 lines of its output, then a line with the command and
           the code or «timeout», code 4. The transfer and the snapshot are already updated by then. No item or
           a conflict (code 3): the command does not run.
transport  brings artifact edits into MAIN (three-way merge: base = snapshot);
           on conflict MAIN is not changed (code 3). The previous state lives in <WORKTREE>.undo/.
           Files ignored one by one outside the set that differ between MAIN and WORKTREE are named
           in the line «not transported: ...»; the exit code does not change because of them.
undo       returns MAIN to the state before the last transport.
remove     removes the links, the snapshot, .undo, the .start record and the worktree itself.
discard    removes a worktree without its own commits (HEAD equals the <WORKTREE>.start record made by setup,
           the commit is not only in the branch being removed) together with its branch; otherwise code 1, nothing changes.
"""
import filecmp
import os
import re
import shutil
import signal
import subprocess
import sys

ROOTS = ["AGENTS.md", "CLAUDE.md"]
LINKED = ["node_modules", ".venv"]
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
    """Paths, the prepare command and the after-refresh command from the «Working copy» section."""
    paths, cmd, after, inside = [], None, None, False
    agents = os.path.join(main, "AGENTS.md")
    try:
        src = read(agents).decode("utf-8")
    except OSError:
        return paths, cmd, after
    found = migrate_agents(src)[1]
    if found and agents not in WARNED:
        WARNED.add(agents)
        print(migrate_hint(agents, found), file=sys.stderr)
    for ln in src.splitlines():
        if ln.startswith("## "):
            inside = ln.strip() == "## Working copy"
            continue
        if not inside:
            continue
        s = ln.strip().lstrip("-* ").strip()
        parts = s.split("`")
        vals = parts[1::2]
        if s.startswith("Paths:"):
            paths += [v.strip("/") for v in vals if v and not os.path.isabs(v) and ".." not in v.split("/")]
        elif s.startswith("Prepare:") and vals:
            cmd = vals[0]
        elif s.startswith("After refresh:") and vals:
            after = vals[0]
    return paths, cmd, after


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
    return sorted(f for f in names if regular(os.path.join(main, f)) and os.path.dirname(f) not in hidden
                  and not set(f.split("/")) & set(LINKED))


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


def find_links(main):
    """node_modules no deeper than three levels (not entering them or .git) and .venv at the root."""
    found = []
    for d, dirs, _ in os.walk(main):
        rel = os.path.relpath(d, main)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if ".git" in dirs:
            dirs.remove(".git")
        if "node_modules" in dirs:
            dirs.remove("node_modules")
            found.append(os.path.normpath(os.path.join(rel, "node_modules")))
        if depth >= 2:
            dirs[:] = []
    if os.path.isdir(os.path.join(main, ".venv")):
        found.append(".venv")
    return found


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


def add_exclude(main):
    r = git(main, "rev-parse", "--git-common-dir")
    if r.returncode:
        raise RuntimeError("git rev-parse: " + r.stderr.decode("utf-8", "replace").strip())
    p = os.path.join(main, r.stdout.decode().strip(), "info", "exclude")
    have = read(p).decode("utf-8").splitlines() if os.path.exists(p) else []
    add = [x for x in LINKED if x not in have]
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
    paths, cmd, _ = section(main)
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
    links = 0
    for rel in find_links(main):
        dst = os.path.join(wt, rel)
        if os.path.lexists(dst) or not os.path.isdir(os.path.dirname(dst)):
            continue
        if os.path.basename(rel) == "node_modules":
            link_modules(os.path.join(main, rel), dst)
        else:
            os.symlink(os.path.abspath(os.path.join(main, rel)), dst)
        links += 1
    add_exclude(main)
    if cmd:
        r = subprocess.run(["sh", "-c", cmd], cwd=wt, stdin=subprocess.DEVNULL)
        if r.returncode:
            raise RuntimeError("prepare command exited with code %d: %s" % (r.returncode, cmd))
    if start:
        print("start: " + start)
    print("copied files %d, link folders %d, command: %s" % (len(copied), links, cmd or "none"))
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


def unlink_links(wt):
    for rel in find_links(wt):
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
