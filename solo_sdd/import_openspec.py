"""`solo-sdd import openspec [folder] [--write]`: an `openspec/` process tree into `solo-sdd/`; standard library only.

The plan is {path under solo-sdd/: bytes}. `--write` builds it in a sibling temporary folder and renames it into place,
so a failure leaves no half tree; a non-empty `solo-sdd/` must equal the plan exactly (a repeat) or the import refuses."""
import os, pathlib, re, shutil, tempfile

SKIP = ".openspec.yaml"
SKIP_SPECS = re.compile(r"^\s*skip_specs:\s*(['\"]?)true\1\s*(#.*)?$", re.I | re.M)
SPECS_NONE = re.compile(r"^\s*Specs:\s*none\s*$", re.I)
CAPABILITIES = re.compile(r"^##\s+Capabilities\s*$")
KEYS = re.compile(r"^(Language|Mode):\s*(.*?)\.?\s*$")


def context(config):
    """The `context` value of config.yaml: a block scalar (`|`, `>`, with chomping) or a one-line value."""
    # ponytail: a reader for the one key, not YAML; folded `>` keeps its line breaks
    lines = config.replace("\r\n", "\n").split("\n")
    for i, line in enumerate(lines):
        m = re.match(r"^context:\s*(.*?)\s*$", line)
        if not m:
            continue
        if m.group(1)[:1] not in ("|", ">"):
            return m.group(1).strip("'\"")
        body = []
        for l in lines[i + 1:]:
            if l.strip() and not l[:1].isspace():
                break
            body.append(l)
        indent = min((len(l) - len(l.lstrip()) for l in body if l.strip()), default=0)
        return "\n".join(l[indent:] for l in body).strip("\n")
    return ""


def project_text(config):
    """solo-sdd/project.md: `Language:` and `Mode:` lines first, then the rest of the context as it is."""
    keys, rest = [], []
    for line in context(config).split("\n"):
        m = KEYS.match(line)
        (keys if m else rest).append("%s: %s" % m.groups() if m else line)
    body = "\n".join(rest).strip("\n")
    return "# Project\n\n" + "".join(k + "\n" for k in keys) + ("\n" if keys and body else "") + (body + "\n" if body else "")


def mark_specs_none(proposal):
    """proposal.md with `Specs: none` under `## Capabilities` (the section added at the end when missing)."""
    lines = proposal.split("\n")  # a CRLF line keeps its \r; inserted lines take the ending of their neighbour
    head = next((i for i, l in enumerate(lines) if CAPABILITIES.match(l.rstrip("\r"))), None)
    if head is None:
        nl = "\r\n" if proposal.endswith("\r\n") else "\n"
        return proposal.rstrip("\r\n") + nl.join(["", "", "## Capabilities", "", "Specs: none", ""])
    end = next((i for i in range(head + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    if any(SPECS_NONE.match(l) for l in lines[head + 1:end]):
        return proposal
    cr = "\r" if lines[head].endswith("\r") else ""
    return "\n".join(lines[:head + 1] + [cr, "Specs: none" + cr] + lines[head + 1:])


def files(base):
    """Relative posix paths of every file under base, sorted; a linked folder is refused, not silently skipped."""
    out = []
    if not os.path.isdir(base):
        return out

    def unreadable(e):
        raise e  # a folder that cannot be listed is a refusal, never a silently missing part of the tree

    for d, dirs, names in os.walk(base, onerror=unreadable):
        dirs.sort()
        for n in dirs:
            if os.path.islink(os.path.join(d, n)):
                raise OSError("linked folder not supported, replace it with a real one: %s" % os.path.join(d, n))
        out += [pathlib.Path(d, n).relative_to(base).as_posix() for n in names]
    return sorted(out)


def plan(src):
    """({path under solo-sdd/: bytes}, counts, notes) for the openspec/ folder src."""
    out, notes = {}, []
    for part in ("specs", "changes"):
        for rel in files(src / part):
            if pathlib.PurePosixPath(rel).name != SKIP:
                out["%s/%s" % (part, rel)] = (src / part / rel).read_bytes()
    for meta in sorted((src / "changes").rglob(SKIP)):
        prop = "changes/%s/proposal.md" % meta.parent.relative_to(src / "changes").as_posix()
        if prop in out and SKIP_SPECS.search(meta.read_text(encoding="utf-8", errors="replace")):
            new = mark_specs_none(out[prop].decode("utf-8")).encode("utf-8")
            if new != out[prop]:
                out[prop] = new
                notes.append("Specs: none added to solo-sdd/%s (skip_specs: true)" % prop)
    config = src / "config.yaml"
    out["project.md"] = project_text(config.read_text(encoding="utf-8") if config.is_file() else "").encode("utf-8")
    if (src / "analyze.md").is_file():
        out["analyze.md"] = (src / "analyze.md").read_bytes()
    dirs = lambda p: [d for d in sorted(p.iterdir()) if d.is_dir()] if p.is_dir() else []
    counts = (len([d for d in dirs(src / "specs") if (d / "spec.md").is_file()]),
              len([d for d in dirs(src / "changes") if d.name != "archive"]),
              len(dirs(src / "changes" / "archive")))
    return out, counts, notes


def difference(dest, want):
    """The first path under dest that differs from the plan: a changed file, else an extra one, else a missing one."""
    have = set(files(dest))
    changed = [r for r in sorted(have & set(want)) if (dest / r).read_bytes() != want[r]]
    return next(iter(changed + sorted(have - set(want)) + sorted(set(want) - have)), None)


def run(folder=".", write=False):
    root = pathlib.Path(folder)
    src, dest = root / "openspec", root / "solo-sdd"
    if not src.is_dir():
        print("no openspec/ tree")
        return 1
    try:
        want, (specs, open_, archived), notes = plan(src)
        diff = False
        if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
            diff = difference(dest, want) if dest.is_dir() else ""
    except (OSError, UnicodeDecodeError) as e:
        print("cannot read the trees, nothing written: %s" % e)
        return 1
    if diff is not False:
        if diff is None:
            print("nothing to import: solo-sdd/ already matches openspec/")
            return 0
        print("solo-sdd/ differs from the import plan at solo-sdd/%s; nothing written" % diff)
        return 1
    print("openspec/ -> solo-sdd/: %d specs, %d open changes, %d archived changes, %d files" % (specs, open_, archived, len(want)))
    for n in notes:
        print(n)
    if not write:
        for rel in want:
            print("create solo-sdd/%s" % rel)
        print("plan only, nothing written; write with: solo-sdd import openspec %s --write" % folder)
        return 0
    tmp = None
    try:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix=".solo-sdd.import-", dir=root))
        built = tmp / "solo-sdd"  # a plain mkdir: the mode the umask gives, not the 0700 of mkdtemp
        for rel, data in want.items():
            (built / rel).parent.mkdir(parents=True, exist_ok=True)
            (built / rel).write_bytes(data)
        if dest.is_dir():
            dest.rmdir()
        os.rename(built, dest)
    except OSError as e:
        print("import failed, nothing written: %s" % e)
        return 1
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    for rel in want:
        print("created solo-sdd/%s" % rel)
    print("next: check solo-sdd/ (solo-sdd validate --all), then delete openspec/ yourself")
    return 0


def main(args):
    """`import openspec [folder] [--write]`; the exit code, or None on bad arguments."""
    rest = [a for a in args if a != "--write"]
    if rest[:1] != ["openspec"] or len(rest) > 2 or len(args) - len(rest) > 1 or any(a.startswith("-") for a in rest):
        return None
    return run(*rest[1:], write="--write" in args)

