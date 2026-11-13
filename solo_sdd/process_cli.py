"""`solo-sdd list`, `new` and `archive`: the change cycle in the `solo-sdd/` tree; standard library only.

Archive applies a change's deltas the way OpenSpec does (RENAMED, REMOVED, MODIFIED, ADDED, then the spec is
rebuilt with blocks joined by one blank line), but refuses where OpenSpec warns: a missing name is an error."""
import datetime, json, os, pathlib, re, sys

from solo_sdd import process_format as pf, resources

KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATED = re.compile(r"^\d{4}-\d{2}-\d{2}-(.+)$")
REQUIREMENTS = re.compile(r"^##\s+Requirements\s*$", re.I)
REMOVED_BULLET = re.compile(r"^\s*[-*+]\s*`?###\s*Requirement:\s*(.+?)`?\s*$", re.I)
# a rename entry is a bullet (the header optional, as validate reads it) or an unbulleted line with the header
RENAME = (re.compile(r"^\s*[-*+]\s*(FROM|TO):\s*`?(?:###\s*Requirement:\s*)?(.+?)`?\s*$", re.I),
          re.compile(r"^\s*(FROM|TO):\s*`?###\s*Requirement:\s*(.+?)`?\s*$", re.I))
DONE = re.compile(r"^\s*- \[[xX]\]")
TEMPLATES = pathlib.Path(resources.ROOT) / "templates" / "solo-sdd" / "change"


class Refused(Exception):
    pass


def norm(name):
    return re.sub(r"[ \t]+#+[ \t]*$", "", name).strip()


def read(path):
    return "\n".join(pf.read_lines(path))


def read_delta(path):
    """A delta with its HTML comments blanked: template guidance never reaches a main spec."""
    return "\n".join(pf.read_doc(path))


def blocks(lines, mask):
    """(preamble lines, [[name, raw]]) of a section body: a block runs from `### Requirement:` to the next one or `##`."""
    pre, out = [], []
    for line, m in zip(lines, mask):
        req = None if m else pf.DELTA_REQ.match(line)
        if req:
            out.append([norm(req.group(1)), [line]])
        elif not m and pf.H2.match(line):
            break
        elif out:
            out[-1][1].append(line)
        else:
            pre.append(line)
    return pre, [[n, "\n".join(b).rstrip()] for n, b in out]


def split_main(text):
    """(before, header, preamble, blocks, after) of a main spec around its `## Requirements` section."""
    lines = text.split("\n")
    mask = pf.fence_mask(lines)
    h = next((i for i, l in enumerate(lines) if not mask[i] and REQUIREMENTS.match(l)), None)
    if h is None:
        return text, "## Requirements", "", [], ""
    end = next((i for i in range(h + 1, len(lines)) if not mask[i] and pf.H2.match(lines[i])), len(lines))
    pre, found = blocks(lines[h + 1:end], mask[h + 1:end])
    return "\n".join(lines[:h]), lines[h], "\n".join(pre), found, "\n".join(lines[end:])


def collapse(text):
    """Runs of blank lines outside code blocks become one blank line."""
    lines = text.split("\n")
    out = []
    for line, m in zip(lines, pf.fence_mask(lines)):
        if not m and line == "" and out and out[-1] == "":
            continue
        out.append(line)
    return "\n".join(out)


def parse_delta(text, lenient=False):
    """{section: data} of a delta: added/modified [[name, raw]], removed [names], renamed [(from, to)];
    lenient skips an unpaired RENAMED line instead of refusing."""
    lines = text.split("\n")
    mask = pf.fence_mask(lines)
    plan = {"added": [], "modified": [], "removed": [], "renamed": [], "purpose": None}
    heads = [i for i, l in enumerate(lines) if not mask[i] and pf.H2.match(l)]
    for k, i in enumerate(heads):
        end = heads[k + 1] if k + 1 < len(heads) else len(lines)
        title = pf.H2.match(lines[i]).group(1).lower()
        body, bmask = lines[i + 1:end], mask[i + 1:end]
        kind = title.split()[0] if title in pf.DELTA_SECTIONS else None
        if title == "purpose" and plan["purpose"] is None:
            plan["purpose"] = "\n".join(body).strip()
        elif kind in ("added", "modified"):
            plan[kind] += blocks(body, bmask)[1]
        elif kind == "removed":
            for line, m in zip(body, bmask):
                r = None if m else (pf.DELTA_REQ.match(line) or REMOVED_BULLET.match(line))
                if r:
                    plan["removed"].append(norm(r.group(1)))
        elif kind == "renamed":
            pending = None
            for line, m in zip(body, bmask):
                r = None if m else (RENAME[0].match(line) or RENAME[1].match(line))
                if not r:
                    continue
                if r.group(1).upper() == "FROM" and pending is None:
                    pending = norm(r.group(2))
                elif r.group(1).upper() == "TO" and pending is not None:
                    plan["renamed"].append((pending, norm(r.group(2))))
                    pending = None
                elif not lenient:
                    raise Refused("RENAMED: unpaired %s line: %s" % (r.group(1).upper(), line.strip()))
            if pending is not None and not lenient:
                raise Refused("RENAMED: FROM %s has no TO line" % pending)
    return plan


def apply(main, delta, cap):
    """The new main spec text (main is None for a new capability); raises Refused naming the requirement."""
    plan = parse_delta(delta)
    seen = {}
    for kind, names in (("ADDED", [n for n, _ in plan["added"]]), ("MODIFIED", [n for n, _ in plan["modified"]]),
                        ("REMOVED", plan["removed"]), ("RENAMED", [f for f, _ in plan["renamed"]])):
        for n in names:
            if n in seen:
                raise Refused("%s in %s and %s" % (n, seen[n], kind))
            seen[n] = kind
    for _, to in plan["renamed"]:
        if seen.get(to) == "ADDED":
            raise Refused("RENAMED to %s collides with ADDED" % to)
    if main is None:
        if not plan["purpose"]:
            raise Refused("new capability %s has no ## Purpose" % cap)
        main = "# %s Specification\n\n## Purpose\n%s\n\n## Requirements\n" % (cap, plan["purpose"])
    before, header, pre, found, after = split_main(main)
    index = {b[0]: b for b in found}

    def get(n, kind):
        if n not in index:
            raise Refused("%s %s: not in the main spec" % (kind, n))
        return index[n]

    for old, new in plan["renamed"]:
        b = get(old, "RENAMED")
        if new in index:
            raise Refused("RENAMED %s: %s already exists" % (old, new))
        b[0], b[1] = new, "\n".join(["### Requirement: %s" % new] + b[1].split("\n")[1:])
        index[new] = index.pop(old)
    for n in plan["removed"]:
        found.remove(get(n, "REMOVED"))
        del index[n]
    for n, raw in plan["modified"]:
        get(n, "MODIFIED")[1] = raw
    for n, raw in plan["added"]:
        if n in index:
            raise Refused("ADDED %s: already in the main spec" % n)
        found.append([n, raw])
        index[n] = found[-1]
    body = "\n\n".join(([pre.rstrip()] if pre.strip() else []) + [raw for _, raw in found]).rstrip()
    return collapse("\n\n".join(s for s in (before.rstrip(), header, body, after.strip()) if s)).rstrip() + "\n"


def tasks(path):
    try:
        lines = pf.read_doc(path)
    except (OSError, UnicodeDecodeError):
        return 0, 0
    marks = [l for l, m in zip(lines, pf.fence_mask(lines)) if not m and pf.TASK.match(l)]
    return sum(1 for l in marks if DONE.match(l)), len(marks)


def unfinished(change):
    """What is open: each unticked task above the last group of tasks.md (its number, else its text) and an empty
    `## Result`."""
    lines = pf.read_doc(change / "tasks.md")
    mask = pf.fence_mask(lines)
    last = max((i for i, l in enumerate(lines) if not mask[i] and pf.H2.match(l)), default=len(lines))
    out = []
    for l, m in zip(lines[:last], mask):
        if not m and pf.TASK.match(l) and not DONE.match(l):
            text = pf.TASK.sub("", l, 1).strip()
            num = re.match(r"\d+(?:\.\d+)*", text)
            out.append(num.group() if num else text)
    lines = pf.read_doc(change / "verification.md")
    found = {n: body for n, body, _ in pf.sections(lines, pf.fence_mask(lines))}
    return out + (["Result"] if pf.empty(found.get("Result", [])) else [])


def touched(path):
    """{section: requirement names} a delta modifies, removes or renames (both names) and adds; {} if unreadable."""
    try:
        plan = parse_delta(read_delta(path), lenient=True)  # a broken RENAMED section: the other blocks still count
    except (OSError, UnicodeDecodeError):
        return {}  # validate --all reports it
    return {"MODIFIED": [n for n, _ in plan["modified"]], "REMOVED": plan["removed"],
            "RENAMED": [f for f, _ in plan["renamed"]], "ADDED": [n for n, _ in plan["added"]] +
            [t for _, t in plan["renamed"]]}


def siblings(tree, archived):
    """`sibling:` lines: open changes with a MODIFIED, REMOVED or RENAMED block of a requirement the archive touched."""
    mine = {d.parent.name: {n for names in touched(d).values() for n in names}
            for d in archived.glob("specs/*/spec.md")}
    out = []
    for c in pf.open_changes(tree):
        for d in sorted(c.glob("specs/*/spec.md")):
            theirs = touched(d)
            out += ["sibling: %s %s %s" % (c.name, k, n) for k in ("MODIFIED", "REMOVED", "RENAMED")
                    for n in theirs.get(k, []) if n in mine.get(d.parent.name, ())]
    return out


def list_cmd(tree, specs, as_json):
    rows, text = [], []
    if specs:
        for p in sorted((tree / "specs").glob("*/spec.md")):
            try:
                n = len(split_main(read(p))[3])
            except (OSError, UnicodeDecodeError):
                n = None
            rows.append({"id": p.parent.name, "requirements": n})
            text.append("%s %s" % (p.parent.name, "unreadable" if n is None else n))
    else:
        for c in pf.open_changes(tree):
            done, total = tasks(c / "tasks.md")
            row = {"id": c.name, "done": done, "total": total,
                   "claim": (c / "CLAIM").exists(), "waiting": (c / "WAITING").exists()}
            rows.append(row)
            text.append(" ".join([c.name, "%d/%d" % (done, total)] + [k.upper() for k in ("claim", "waiting") if row[k]]))
    if as_json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        print("\n".join(text) if text else ("no specs" if specs else "no open changes"))
    return 0


def new(tree, cid):
    root = tree.parent
    if not KEBAB.match(cid) or cid == "archive":
        print("not a kebab-case id or reserved: %s" % cid)
        return 1
    change = tree / "changes" / cid
    if change.exists():
        print("change exists: %s" % change.relative_to(root).as_posix())
        return 1
    archive = tree / "changes" / "archive"
    old = [p for p in (sorted(archive.iterdir()) if archive.is_dir() else [])
           if DATED.match(p.name) and DATED.match(p.name).group(1) == cid]
    if old:
        print("archived change exists: %s" % old[0].relative_to(root).as_posix())
        return 1
    texts = {n: (TEMPLATES / n).read_text(encoding="utf-8").replace("<id>", cid) for n in pf.ARTIFACTS}
    change.mkdir(parents=True)
    for n, t in texts.items():
        (change / n).write_text(t, encoding="utf-8")
        print((change / n).relative_to(root).as_posix())
    print("delta spec template: %s" % (TEMPLATES / "spec.md"))
    return 0


def plan_archive(tree, cid, today, force=False):
    """{main spec path: new text}, the archive folder and what was open (archived only with force),
    or raises Refused; reads only."""
    root = tree.parent
    errs = pf.validate(tree, cid)
    if errs:
        raise Refused("\n".join("%s: %s: %s" % e for e in errs) + "\n%s fails validate" % cid)
    change = tree / "changes" / cid
    opened = unfinished(change)
    if opened and not force:
        raise Refused("\n".join("%s: %s" % (("empty section", n) if n == "Result" else ("open task", n))
                                for n in opened) + "\n%s is not finished; the owner may pass --force" % cid)
    dest = tree / "changes" / "archive" / ("%s-%s" % (today, cid))
    if dest.exists():
        raise Refused("archive folder exists: %s" % dest.relative_to(root).as_posix())
    writes, problems = {}, []
    for d in sorted(change.glob("specs/*/spec.md")):
        main = tree / "specs" / d.parent.name / "spec.md"
        try:
            old = read(main) if main.is_file() else None
            text = apply(old, read_delta(d), d.parent.name)
        except Refused as e:
            problems.append("%s: %s" % (main.relative_to(root).as_posix(), e))
            continue
        except (OSError, UnicodeDecodeError) as e:
            problems.append("%s: unreadable: %s" % (main.relative_to(root).as_posix(), type(e).__name__))
            continue
        if text != old:
            writes[main] = text
    if problems:
        raise Refused("\n".join(problems))
    return writes, dest, opened


def commit(writes, change, dest):
    """Writes the specs and moves the folder; on a failure restores every file and folder it touched."""
    saved, made = {}, []
    try:
        for p, text in writes.items():
            saved[p] = p.read_bytes() if p.exists() else None
            for d in reversed(p.parents):
                if not d.exists():
                    d.mkdir()
                    made.append(d)
            tmp = p.with_name(p.name + ".tmp")
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            os.replace(tmp, p)
        if not dest.parent.exists():
            dest.parent.mkdir()
            made.append(dest.parent)
        os.rename(change, dest)
    except BaseException:
        for p, b in saved.items():
            p.with_name(p.name + ".tmp").unlink(missing_ok=True)
            if b is None:
                p.unlink(missing_ok=True)
            else:
                p.write_bytes(b)
        for d in reversed(made):
            d.rmdir()
        raise


def archive(tree, cid, yes, today=None, force=False):
    root = tree.parent
    today = today or datetime.date.today().isoformat()
    try:
        writes, dest, opened = plan_archive(tree, cid, today, force)
    except Refused as e:
        print("%s\narchive refused, no file changed" % e)
        return 1
    if not yes:
        if sys.stdin is None or not sys.stdin.isatty():
            print("archive %s needs a terminal to confirm; run: solo-sdd archive %s --yes" % (cid, cid))
            return 1
        for p in writes:
            print("%s %s" % ("update" if p.exists() else "create", p.relative_to(root).as_posix()))
        try:
            answer = input("archive %s to %s? [y/N] " % (cid, dest.relative_to(root).as_posix()))
        except (EOFError, KeyboardInterrupt):
            answer = ""
        if answer.strip().lower() not in ("y", "yes"):
            print("not archived")
            return 1
    try:
        commit(writes, tree / "changes" / cid, dest)
    except OSError as e:
        print("archive failed, every file restored: %s" % e)
        return 1
    for p in writes:
        print("synced %s" % p.relative_to(root).as_posix())
    print("archived %s" % dest.relative_to(root).as_posix())
    if opened:
        print("forced: %s" % ", ".join(opened))
    try:
        lines = siblings(tree, dest)
    except OSError as e:
        lines = ["sibling: not checked: %s" % e]
    for line in lines:
        print(line)
    return 0


def run(args, cwd="."):
    """`solo-sdd list [--specs] [--json]`, `new <id>`, `archive <id> [--yes] [--force]`; the exit code, or None on bad arguments."""
    cmd, rest = args[0], args[1:]
    flags = {a for a in rest if a.startswith("-")}
    ids = [a for a in rest if not a.startswith("-")]
    allowed = {"list": {"--specs", "--json"}, "new": set(), "archive": {"--yes", "--force"}}[cmd]
    if flags - allowed or len(ids) != (0 if cmd == "list" else 1):
        return None
    tree = pf.find_tree(cwd)
    if tree is None:
        print("no solo-sdd/ tree")
        return 1
    if cmd == "list":
        return list_cmd(tree, "--specs" in flags, "--json" in flags)
    if cmd == "new":
        return new(tree, ids[0])
    return archive(tree, ids[0], "--yes" in flags, force="--force" in flags)
