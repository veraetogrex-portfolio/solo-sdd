"""Skill texts with their step files, the size budget and the step-file names (Requirements: Skill size budget,
Step files).

A step file is named by a `SKILL.md` line that holds its bare name in backquotes followed by `each time` (the read
instruction); read() replaces that line with the file's text, which gives back the skill as one text.
"""
import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[1]
BUDGET = 16000  # 5,000 re-attached tokens at 3.2 bytes per token
STEP = re.compile(r"`([A-Za-z0-9._-]+\.md)` each time")


def read(path):
    """The text of a SKILL.md path with each line that names an existing step file replaced by that file's text."""
    path = pathlib.Path(path)
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = STEP.search(line)
        step = path.parent / m.group(1) if m else None
        out.append(step.read_text(encoding="utf-8").rstrip("\n") if step and step.is_file() else line)
    return "\n".join(out) + "\n"


def skill(name, root=REPO):
    return read(pathlib.Path(root) / "skills" / name / "SKILL.md")


def tracked_skills(root=REPO):
    run = subprocess.run(["git", "ls-files", "-z", "--", "skills/*/SKILL.md"], cwd=root, capture_output=True,
                         text=True, check=True, stdin=subprocess.DEVNULL)
    return sorted(filter(None, run.stdout.split("\0")))


def over_budget(root=REPO):
    """'<path> <n> bytes' for every tracked skills/*/SKILL.md larger than BUDGET."""
    sizes = ((rel, (pathlib.Path(root) / rel).stat().st_size) for rel in tracked_skills(root))
    return ["%s %d bytes" % (rel, n) for rel, n in sizes if n > BUDGET]


def step_errors(root=REPO):
    """'skills/<name>: missing <file>' for a named step file that does not exist, 'skills/<name>: orphan <file>' for a
    .md file of the skill folder (other than SKILL.md) that no line of its SKILL.md names."""
    errors = []
    for md in sorted(pathlib.Path(root).glob("skills/*/SKILL.md")):
        named = set(STEP.findall(md.read_text(encoding="utf-8")))
        here = {p.name for p in md.parent.glob("*.md")} - {"SKILL.md"}
        errors += ["skills/%s: missing %s" % (md.parent.name, f) for f in sorted(named - here)]
        errors += ["skills/%s: orphan %s" % (md.parent.name, f) for f in sorted(here - named)]
    return errors
