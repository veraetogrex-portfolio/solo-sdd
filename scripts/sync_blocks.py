#!/usr/bin/env python3
"""Keeps the marked code blocks of the single-file scripts equal to their source.

python3 scripts/sync_blocks.py [--check]

The scripts in global/ are deployed one file each, so they hold copies of blocks the package keeps too. A block is
the text between the whole lines `# <name>:begin` and `# <name>:end` (a name of lowercase ASCII letters, digits and
hyphens) in a .py file under solo_sdd/ or global/; a lone CR line break, a link or a folder it cannot list is refused. A run copies each block from its source in SOURCES into every
other file with its markers and names each rewritten copy; --check writes nothing and names each differing copy.
A begin without its end, an end without its begin, a block twice in a file, a name without a source, or a source
without its block: nothing is written in any mode. Codes: 0 in sync (or synced), 1 a differing copy under --check
or broken markers, 2 a usage error.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCANNED = ("solo_sdd", "global")
SOURCES = {
    "settings": "solo_sdd/settings.py",
    "keywords": "solo_sdd/keywords.py",
    "integration-reader": "solo_sdd/integrations.py",
    "tree-hash": "solo_sdd/integration_run.py",
    "doc-reader": "solo_sdd/process_format.py",
    "errors": "solo_sdd/doctor.py",
    "shell": "global/work_hooks.py",
    "process-root": "global/work_hooks.py",
}
# re.M: ^ and $ stand only at "\n", so a line is what Python's universal newlines off would give
MARKER = re.compile(r"^# ([a-z0-9-]+):(begin|end)\r?$", re.M)


def parse(text):
    """{name: (start, end)} of each block's text, or (name, why) for the first broken marker."""
    found, open_ = {}, None
    for m in MARKER.finditer(text):
        name, kind = m.groups()
        if kind == "begin":
            if open_:
                return {}, (open_[0], "begin before its end")
            if name in found:
                return {}, (name, "the block twice")
            open_ = (name, m.end() + (text[m.end():m.end() + 1] == "\n"))
        elif not open_:
            return {}, (name, "end without its begin")
        elif open_[0] != name:
            return {}, (open_[0], "begin without its end (%s:end before it)" % name)
        else:
            found[name], open_ = (open_[1], m.start()), None
    if open_:
        return {}, (open_[0], "begin without its end")
    return found, None


def fail(e):
    raise e


def scan(root):
    """[(rel, text)] of the scanned .py files, sorted. Raises OSError for a scanned folder that is missing, cannot
    be listed or is a link, and ValueError for a file Python would read with other line breaks than the script."""
    out = []
    for d in SCANNED:
        if not os.path.isdir(os.path.join(root, d)) or os.path.islink(os.path.join(root, d)):
            raise OSError("%s/ is missing or a link" % d)
        for base, dirs, names in os.walk(os.path.join(root, d), onerror=fail):
            dirs.sort()
            for n in sorted(dirs + names):
                path = os.path.join(base, n)
                rel = os.path.relpath(path, root).replace(os.sep, "/")
                if os.path.islink(path) and (n in dirs or n.endswith(".py")):  # a write would land outside the tree
                    raise OSError("%s is a link" % rel)
                if n in names and n.endswith(".py"):
                    with open(path, encoding="utf-8", newline="") as f:
                        text = f.read()
                    if re.search(r"\r(?!\n)", text):  # Python reads a lone CR as a line break, MARKER does not
                        raise ValueError("%s holds a line break that is a lone CR" % rel)
                    out.append((rel, text))
    return out


def sync(root=ROOT, check=False):
    try:
        files = scan(root)
    except (OSError, ValueError) as e:
        print("cannot read the tree: %s" % e)
        return 1
    parsed, errors, broken = {}, [], set()
    for rel, text in files:
        blocks, bad = parse(text)
        if bad:
            errors.append("%s: %s: %s" % (rel, bad[0], bad[1]))
            broken.add(rel)
            continue
        errors += ["%s: %s: no source for this block" % (rel, n) for n in blocks if n not in SOURCES]
        parsed[rel] = (text, blocks)
    for name, src in SOURCES.items():
        users = [rel for rel, (_, b) in parsed.items() if name in b]
        if users and name not in parsed.get(src, ("", {}))[1] and src not in broken:
            errors.append("%s: %s: the source holds no such block" % (src, name))
    if errors:
        print("\n".join(errors))
        return 1
    stale, writes, lines = 0, [], []
    for rel, (text, blocks) in parsed.items():
        new, names = text, []
        for name, (start, end) in sorted(blocks.items(), key=lambda kv: -kv[1][0]):
            stext, sb = parsed[SOURCES[name]]
            want = stext[sb[name][0]:sb[name][1]]
            if rel != SOURCES[name] and text[start:end] != want:
                new, names = new[:start] + want + new[end:], [name] + names
        lines += ["%s: %s: %s" % (rel, n, ("differs from " if check else "copied from ") + SOURCES[n]) for n in names]
        stale += bool(names)
        if names and not check:
            writes.append((os.path.join(root, rel), new))
    locked = [p for p, _ in writes if not os.access(p, os.W_OK)]
    if locked:  # checked before the first write: a run never leaves some copies rewritten and others not
        print("\n".join("%s: cannot be written" % os.path.relpath(p, root) for p in locked))
        return 1
    # ponytail: plain writes; a disk error midway leaves earlier copies rewritten, a rerun finishes the job
    for path, new in writes:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new)
    if lines:
        print("\n".join(lines))
    return 1 if check and stale else 0


def main(argv):
    if argv not in ([], ["--check"]):
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    return sync(ROOT, argv == ["--check"])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
