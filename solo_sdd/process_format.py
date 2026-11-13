"""The solo-sdd process tree and the rules `solo-sdd validate` enforces; standard library only, no external program.

Tree: `solo-sdd/` with `project.md`, main specs `specs/<capability>/spec.md`, open changes `changes/<id>/`
and the archive `changes/archive/` (history, not checked). The spec format rules are the ones the
removed OpenSpec-tree tests enforced. An error is `(file, rule, item)`."""
import json, pathlib, re, stat

TREE = "solo-sdd"
MAX_LEN = 500
MAX_TASKS = 10
MIN_PURPOSE = 50
ARTIFACTS = ("proposal.md", "verification.md", "tasks.md")
PROPOSAL = ("Why", "What Changes", "Impact", "Out of Scope", "Depends On", "Source")
VERIFICATION = ("Live Scenario", "Needs", "Fallback")

DELTA_REQ = re.compile(r"^###\s*Requirement:\s*(.+?)\s*$", re.I)
NO_SPACE = re.compile(r"^###Requirement:", re.I)
MAIN_REQ = re.compile(r"^###\s+(.+?)\s*$")
ANY_HEAD = re.compile(r"^#{1,6}\s")
META = re.compile(r"^\*\*[^*]+\*\*:")
SCENARIO = re.compile(r"^####\s+Scenario:\s*(.*?)\s*$", re.I)
SCENARIO_END = re.compile(r"^#{1,4}\s")
TRIGGER = (re.compile(r"(?:\*\*|__)(?:WHEN|GIVEN):?(?:\*\*|__)", re.I), re.compile(r"\b(?:WHEN|GIVEN)\b"))
OUTCOME = (re.compile(r"(?:\*\*|__)THEN:?(?:\*\*|__)", re.I), re.compile(r"\bTHEN\b"))
TASK = re.compile(r"^\s*- \[[ xX]\]")
CHANGE_ID = re.compile(r"^[A-Za-z0-9_][\w.-]*$")
RENAMED_FROM = re.compile(r"^\s*-\s*FROM:", re.I)
DELTA_SECTIONS = {"added requirements", "modified requirements", "removed requirements", "renamed requirements"}
CHECKED = ("added requirements", "modified requirements")
CHANGED = ("modified requirements", "removed requirements")


def _is_file(path):
    """Path.is_file that lets PermissionError through, as before Python 3.14: an unreadable folder is not a missing file."""
    try:
        return stat.S_ISREG(path.stat().st_mode)
    except (FileNotFoundError, NotADirectoryError):
        return False


def _is_dir(path):
    try:
        return stat.S_ISDIR(path.stat().st_mode)
    except (FileNotFoundError, NotADirectoryError):
        return False


def find_tree(start):
    """The nearest `solo-sdd/` upward from start that holds project.md, specs/ or changes/; else None."""
    for d in [pathlib.Path(start).resolve(), *pathlib.Path(start).resolve().parents]:
        t = d / TREE
        try:
            if _is_dir(t) and any(_is_file(t / n) or _is_dir(t / n) for n in ("project.md", "specs", "changes")):
                return t
        except OSError:  # a solo-sdd/ that cannot be read: validate reports it as unreadable
            return t
    return None


# The document reader below is copied into global/sdd_dispatch.py (deployed alone): edit it here, then run
# python3 scripts/sync_blocks.py.
# doc-reader:begin
FENCE_OPEN = re.compile(r"^\s*(`{3,}|~{3,})")
FENCE_CLOSE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")
H2 = re.compile(r"^##\s+(.+?)\s*$")
CODE_OR_COMMENT = re.compile(r"(`+).*?\1|<!--")


def read_lines(path):
    text = path.read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def read_doc(path):
    """Lines of a process document with HTML comments blanked: a comment never counts as a header, task or text.
    `<!--` inside a code block or an inline code span is code, not a comment; an unclosed comment runs to the end."""
    out, comment, fence = [], False, None
    for line in read_lines(path):
        if fence:
            out.append(line)
            m = FENCE_CLOSE.match(line)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
            continue
        m = None if comment else FENCE_OPEN.match(line)
        if m:
            fence = m.group(1)
            out.append(line)
            continue
        kept, pos = "", 0
        while pos < len(line):
            if comment:
                end = line.find("-->", pos)
                comment, pos = (True, len(line)) if end < 0 else (False, end + 3)
                continue
            t = CODE_OR_COMMENT.search(line, pos)
            if not t:
                kept += line[pos:]
                break
            kept += line[pos:t.start()] if t.group() == "<!--" else line[pos:t.end()]
            comment, pos = t.group() == "<!--", t.end()
        out.append(kept)
    return out


def fence_mask(lines):
    """True for lines inside code blocks and for the fences themselves."""
    mask, ch, n = [], None, 0
    for line in lines:
        if ch is None:
            m = FENCE_OPEN.match(line)
            if m:
                ch, n = m.group(1)[0], len(m.group(1))
            mask.append(bool(m))
        else:
            mask.append(True)
            m = FENCE_CLOSE.match(line)
            if m and m.group(1)[0] == ch and len(m.group(1)) >= n:
                ch = None
    return mask


def sections(lines, mask):
    """[(## name, body lines, body lines outside code blocks)] in file order."""
    out = []
    for line, masked in zip(lines, mask):
        m = None if masked else H2.match(line)
        if m:
            out.append((m.group(1), [], []))
        elif out:
            out[-1][1].append(line)
            if not masked:
                out[-1][2].append(line)
    return out
# doc-reader:end


def empty(body):
    return not "\n".join(body).strip()  # read_doc has blanked the comments


def req_length(lines, mask, name):
    """Length of the requirement text in UTF-16 units (the count of OpenSpec 1.14.3)."""
    captured, meta = [], []
    for line, masked in zip(lines, mask):
        if masked:
            continue
        if ANY_HEAD.match(line):
            break
        t = line.strip()
        if t:
            (meta if META.match(t) else captured).append(t)
    text = "\n".join(captured) if captured else ("\n".join(meta) if meta else name)
    return len(text.encode("utf-16-le")) // 2


def delta_blocks(lines, mask, kinds=CHECKED):
    """(name, body start, end) of delta requirements under the sections `kinds`."""
    out, in_sec, cur = [], False, None
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        sec, req = H2.match(line), DELTA_REQ.match(line)
        if (sec or req) and cur:
            out.append((cur[0], cur[1], i))
            cur = None
        if sec:
            in_sec = sec.group(1).lower() in kinds
        elif req and in_sec:
            cur = (req.group(1), i + 1)
    if cur:
        out.append((cur[0], cur[1], len(lines)))
    return out


def main_blocks(lines, mask):
    """(name, body start, end) of the requirements under `## Requirements` of a main spec."""
    out, in_sec, cur = [], False, None
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        if re.match(r"^#{1,3}\s", line) and cur:
            out.append((cur[0], cur[1], i))
            cur = None
        if re.match(r"^#{1,2}\s", line):
            in_sec = bool(re.match(r"^##\s+requirements\s*$", line, re.I))
        elif in_sec:
            m = MAIN_REQ.match(line)
            if m:
                cur = (re.sub(r"^Requirement:\s*", "", m.group(1), flags=re.I), i + 1)
    if cur:
        out.append((cur[0], cur[1], len(lines)))
    return out


def has_step(lines, mask, patterns):
    return any(not m and any(p.search(line) for p in patterns) for line, m in zip(lines, mask))


def check_spec(path, rel, is_delta, skip=frozenset()):
    """Errors of one main spec or delta: length, scenario presence and steps, delta section, header space."""
    lines = read_lines(path)
    mask = fence_mask(lines)
    errs = []
    blocks = delta_blocks(lines, mask) if is_delta else main_blocks(lines, mask)
    for name, a, b in blocks:
        if name not in skip:
            n = req_length(lines[a:b], mask[a:b], name)
            if n > MAX_LEN:
                errs.append((rel, "requirement too long", "%s: %d > %d" % (name, n, MAX_LEN)))
        if not any(not m and SCENARIO.match(l) for l, m in zip(lines[a:b], mask[a:b])):
            errs.append((rel, "no scenario", name))
    section, req = None, ""
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        sec = H2.match(line)
        if sec:
            section = sec.group(1)
            continue
        m = DELTA_REQ.match(line)
        if m:
            req = m.group(1)
            if NO_SPACE.match(line):
                errs.append((rel, "header without a space after ###", req))
            if is_delta and (section is None or section.lower() not in DELTA_SECTIONS):
                where = 'under "## %s"' % section if section else "above the first ## section"
                errs.append((rel, "not a delta section", "%s: %s" % (req, where)))
            continue
        s = SCENARIO.match(line)
        if not s:
            continue
        end = i + 1
        while end < len(lines) and (mask[end] or not SCENARIO_END.match(lines[end])):
            end += 1
        if not "\n".join(lines[i + 1:end]).strip():
            continue  # an empty scenario: OpenSpec 1.16.1 does not count its steps either
        missing = [k for k, pats in (("WHEN/GIVEN", TRIGGER), ("THEN", OUTCOME))
                   if not has_step(lines[i + 1:end], mask[i + 1:end], pats)]
        if missing:
            errs.append((rel, "scenario step", '%s: scenario "%s" has no %s' % (req, s.group(1), " and no ".join(missing))))
    return errs


def check_sections(path, rel, names):
    lines = read_doc(path)
    found = {name: body for name, body, _ in sections(lines, fence_mask(lines))}
    errs = []
    for n in names:
        if n not in found:
            errs.append((rel, "missing section", n))
        elif empty(found[n]):
            errs.append((rel, "empty section", n))
    return errs, found


def check_tasks(path, rel):
    lines = read_doc(path)
    mask = fence_mask(lines)
    count = sum(1 for l, m in zip(lines, mask) if not m and TASK.match(l))
    errs = [(rel, "too many tasks", "%d > %d" % (count, MAX_TASKS))] if count > MAX_TASKS else []
    groups = [name for name, _, _ in sections(lines, mask)]
    last = groups[-1] if groups else ""
    if re.sub(r"^\d+(\.\d+)*\.?\s*", "", last) != "Acceptance":
        errs.append((rel, "no Acceptance group", "last group: %s" % (last or "none")))
    return errs


def guarded(fn, path, root, *args):
    """fn's errors, or one `unreadable` error for a file or folder that cannot be read (as UTF-8)."""
    rel = path.relative_to(root).as_posix()
    try:
        return fn(path, rel, *args)
    except (OSError, UnicodeDecodeError) as e:
        return [(rel, "unreadable", type(e).__name__)]


def has_delta(path):
    """True when a delta file holds a requirement or a RENAMED entry; an unreadable one counts (check_spec reports it)."""
    try:
        lines = read_lines(path)
    except (OSError, UnicodeDecodeError):
        return True
    return any(not m and (DELTA_REQ.match(l) or RENAMED_FROM.match(l)) for l, m in zip(lines, fence_mask(lines)))


def check_change(change, tree):
    root = tree.parent
    errs = []
    for name in ARTIFACTS:
        if not _is_file(change / name):
            errs.append(((change / name).relative_to(root).as_posix(), "missing file", name))
    deltas = sorted(change.glob("specs/*/spec.md"))
    def proposal(path, rel):
        e, _ = check_sections(path, rel, PROPOSAL)
        lines = read_doc(path)
        plain = {name: text for name, _, text in sections(lines, fence_mask(lines))}
        if not any(has_delta(d) for d in deltas) and not any(
                re.match(r"^\s*Specs:\s*none\s*$", l, re.I) for l in plain.get("Capabilities", [])):
            e.append((rel, "no deltas", "no delta requirement in specs/*/spec.md and no `Specs: none` under ## Capabilities"))
        return e

    if _is_file(change / "proposal.md"):
        errs += guarded(proposal, change / "proposal.md", root)
    if _is_file(change / "verification.md"):
        errs += guarded(lambda p, r: check_sections(p, r, VERIFICATION)[0], change / "verification.md", root)
    if _is_file(change / "tasks.md"):
        errs += guarded(check_tasks, change / "tasks.md", root)
    deps = dependencies(change, tree)  # archived before this change
    provided = {p.parent.name for dep in deps for p in dep.glob("specs/*/spec.md")}
    for d in deltas:
        found = guarded(check_spec, d, root, True)
        errs += found
        cap = d.parent.name
        if any(r == "unreadable" for _, r, _ in found):
            continue
        purpose = guarded(check_purpose, d, root) \
            if not _is_file(tree / "specs" / cap / "spec.md") and cap not in provided else []
        errs += purpose or dry_run(d, tree, deps)  # a missing Purpose is reported once, by its own rule
    return errs


def dependencies(change, tree, seen=None):
    """The open changes `Depends On` names, each after its own open dependencies, in order, each once, never itself."""
    seen = {change} if seen is None else seen
    out = []
    try:
        lines = read_doc(change / "proposal.md")
    except (OSError, UnicodeDecodeError):
        return out  # validate reports the proposal
    plain = {name: text for name, _, text in sections(lines, fence_mask(lines))}
    for dep in re.findall(r"[\w.-]+", "\n".join(plain.get("Depends On", []))):
        d = tree / "changes" / dep
        if CHANGE_ID.match(dep) and dep != "archive" and _is_dir(d) and d not in seen:
            seen.add(d)
            out += dependencies(d, tree, seen) + [d]
    return out


def dry_run(delta, tree, deps):
    """`delta` errors: what archive would refuse on applying this delta after the deltas of `deps`; writes nothing."""
    from solo_sdd import process_cli as pc  # process_cli imports this module
    root, cap = tree.parent, delta.parent.name
    main = tree / "specs" / cap / "spec.md"
    try:
        text = pc.read(main) if _is_file(main) else None
    except (OSError, UnicodeDecodeError) as e:
        return [(main.relative_to(root).as_posix(), "unreadable", type(e).__name__)]
    for dep in deps:
        try:
            text = pc.apply(text, pc.read_delta(dep / "specs" / cap / "spec.md"), cap) \
                if _is_file(dep / "specs" / cap / "spec.md") else text
        except (pc.Refused, OSError, UnicodeDecodeError):
            pass  # the dependency's own validate reports it
    try:
        pc.apply(text, pc.read_delta(delta), cap)
    except pc.Refused as e:
        return [(delta.relative_to(root).as_posix(), "delta", "%s: %s" % (main.relative_to(root).as_posix(), e))]
    except (OSError, UnicodeDecodeError):
        pass  # check_spec has reported the delta unreadable
    return []


def check_purpose(path, rel):
    lines = read_doc(path)
    secs = sections(lines, fence_mask(lines))
    cap = path.parent.name
    if not secs or secs[0][0] != "Purpose":
        return [(rel, "new capability Purpose", "%s: no ## Purpose at the start" % cap)]
    n = len("\n".join(secs[0][1]).strip())
    if n < MIN_PURPOSE:
        return [(rel, "new capability Purpose", "%s: %d < %d characters" % (cap, n, MIN_PURPOSE))]
    return []


def open_changes(tree):
    base = tree / "changes"
    return sorted(p for p in base.iterdir() if _is_dir(p) and p.name != "archive" and not p.name.startswith(".")) \
        if _is_dir(base) else []


def changed_by_open(changes):
    """{capability: requirement names} that open changes modify or remove: their main length is not checked."""
    out = {}
    for c in changes:
        for p in c.glob("specs/*/spec.md"):
            try:
                lines = read_lines(p)
            except (OSError, UnicodeDecodeError):
                continue  # check_spec reports it
            for name, _, _ in delta_blocks(lines, fence_mask(lines), CHANGED):
                out.setdefault(p.parent.name, set()).add(name)
    return out


def validate(tree, change_id=None):
    """Errors of the whole tree (project.md, main specs, open changes; not the archive) or of one change."""
    tree = pathlib.Path(tree)
    root = tree.parent

    def safe(fn, path):
        try:
            return fn()
        except OSError as e:  # a folder that cannot be listed
            return [(path.relative_to(root).as_posix(), "unreadable", type(e).__name__)]

    if change_id is not None:
        c = tree / "changes" / change_id
        found = safe(lambda: [] if CHANGE_ID.match(change_id) and change_id != "archive" and _is_dir(c) else
                     [("%s/changes/%s" % (TREE, change_id), "no change", change_id)], tree / "changes")
        return found or safe(lambda: check_change(c, tree), c)
    project = tree / "project.md"
    errs = safe(lambda: [] if _is_file(project) else [(project.relative_to(root).as_posix(), "missing file", "project.md")], tree)
    if errs and errs[0][1] == "unreadable":
        return errs
    changes = []
    errs += safe(lambda: changes.extend(open_changes(tree)) or [], tree / "changes")
    changed = changed_by_open(changes)
    errs += safe(lambda: [e for p in sorted((tree / "specs").glob("*/spec.md"))
                          for e in guarded(check_spec, p, root, False, changed.get(p.parent.name, frozenset()))],
                 tree / "specs")
    for c in changes:
        errs += safe(lambda: check_change(c, tree), c)
    return errs


def run(args, cwd="."):
    """`solo-sdd validate [<id>] [--all] [--json]`; returns the exit code, or None on bad arguments."""
    flags = [a for a in args if a.startswith("-")]
    ids = [a for a in args if not a.startswith("-")]
    if set(flags) - {"--all", "--json"} or len(ids) > 1 or (ids and "--all" in flags):
        return None
    tree = find_tree(cwd)
    if tree is None:
        print("no solo-sdd/ tree")
        return 1
    errs = validate(tree, ids[0] if ids else None)
    if "--json" in flags:
        print(json.dumps([{"file": f, "rule": r, "item": i} for f, r, i in errs], indent=2, ensure_ascii=False))
    else:
        for f, r, i in errs:
            print("%s: %s: %s" % (f, r, i))
        print("%d errors" % len(errs))
    return 1 if errs else 0
