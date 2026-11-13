"""rules-audit stand: checks docs/rules-audit.md against the rules files.

A fixed finding is no longer quoted in its file, an amended one has the added text in the file,
a kept one has a reason, signals of outdated
prompting are not found in the rules. Then the same on a temporary copy where the quote of a fixed
finding is returned: the stand must catch it.
Run from the repository root: python3 tests/stands/rules-audit.py. Creates and removes its temporary folder itself."""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SURFACE = ["skills/*/SKILL.md", "global/AGENTS.md", "ALGORITHM.md", "templates/**/*.*"]
SIGNALS = re.compile(
    r"step by step|deep breath|scratchpad|take your time|double-check|"
    r"claude-(2|3|instant)|(sonnet|opus|haiku) 4\b", re.I)


def rows(root):
    for line in (root / "docs/rules-audit.md").read_text().splitlines():
        if line.startswith("| A-"):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            yield c[0], re.split(r"[: ]", c[1], maxsplit=1)[0], c[2].strip('"'), c[-1]


def check(root):
    problems, fixed, kept = [], 0, 0
    # personal skills of a working copy lie on disk outside git: only tracked files are audited
    tracked = set(subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True).stdout.split())
    for fid, path, quote, status in rows(root):
        if status == "fixed":
            fixed += 1
            f = root / path
            if not f.is_file():
                problems.append("%s: no file %s" % (fid, path))
            elif quote in f.read_text():
                problems.append("%s: quote remained in %s" % (fid, path))
        elif status.startswith("amended:"):
            fixed += 1
            added = status[len("amended:"):].strip().strip('"')
            f = root / path
            if not added or not f.is_file() or added not in f.read_text():
                problems.append("%s: no addition in %s" % (fid, path))
        elif status.startswith("kept:") and status[len("kept:"):].strip():
            kept += 1
        else:
            problems.append("%s: status without a reason: %s" % (fid, status))
    for pattern in SURFACE:
        for f in sorted(root.glob(pattern)):
            if str(f.relative_to(root)) not in tracked:
                continue
            for n, line in enumerate(f.read_text().splitlines(), 1):
                if SIGNALS.search(line):
                    problems.append("signal: %s:%d" % (f.relative_to(root), n))
    return fixed, kept, problems


fixed, kept, problems = check(ROOT)
for p in problems:
    print("FAILED", p)
print("repository: findings %d, fixed %d, kept with a reason %d, open %d"
      % (fixed + kept, fixed, kept, len(problems)))

with tempfile.TemporaryDirectory() as d:
    tmp = pathlib.Path(d)
    (tmp / "docs").mkdir()
    shutil.copy(ROOT / "docs/rules-audit.md", tmp / "docs/rules-audit.md")
    fid, path, quote, _ = next(r for r in rows(ROOT) if r[3] == "fixed")
    (tmp / path).parent.mkdir(parents=True, exist_ok=True)
    (tmp / path).write_text((ROOT / path).read_text() + "\n" + quote + "\n")
    caught = any(p.startswith(fid + ": quote remained") for p in check(tmp)[2])
    print("copy with the returned quote %s: %s" % (fid, "caught" if caught else "NOT caught"))
    fid, path, _, _ = next(r for r in rows(ROOT) if r[3].startswith("amended:"))
    (tmp / path).parent.mkdir(parents=True, exist_ok=True)
    (tmp / path).write_text("")
    missed = any(p.startswith(fid + ": no addition") for p in check(tmp)[2])
    print("copy without the addition %s: %s" % (fid, "caught" if missed else "NOT caught"))
    caught = caught and missed

ok = not problems and caught
print("total: %s" % ("open findings 0" if ok else "there are open findings"))
sys.exit(0 if ok else 1)
