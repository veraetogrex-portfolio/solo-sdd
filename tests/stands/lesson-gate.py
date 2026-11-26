#!/usr/bin/env python3
"""Step 0 of the live scenario of change lesson-gate, without model calls.

1. `sync.py push --global-rules` of this tree into a temporary HOME: the installed ~/.claude/CLAUDE.md and
   ~/.codex/AGENTS.md (section 15) name `Lesson gate:`, `Held by:` and `Lesson held:`; the installed spec-next names
   `Lesson gate:` and `Lesson held:`.
2. global/AGENTS.md of base commit e262b7e (main when the change was planned) names none of the three.
3. A copy of tests/stands/lesson-stand with ui/strings.json and ui/labels.txt committed in its own git: check.sh
   prints "## Lessons: missing", the UI files are tracked, and no stand test reads ui/.
With --prepare <dir> the HOME, the base rules (base-AGENTS.md) and fresh copies c1 to c5 are left in <dir> for the
model steps, and the caller removes <dir>; otherwise the temporary folder is removed. Run from the repository root:
python3 tests/stands/lesson-gate.py [--prepare <dir>]. The last line is "SUMMARY: all steps passed" (code 0) or
"SUMMARY: N of M steps failed" (code 1)."""
import os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
STAND = ROOT / "tests/stands/lesson-stand"
BASE = "e262b7e"  # main when the change was planned: pinned, so the stand runs the same after the merge
ENV = {k: v for k, v in os.environ.items() if k not in ("HOME", "SOLO_SDD_TESTS")}
GIT = ["git", "-c", "user.name=stand", "-c", "user.email=stand@example.invalid", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null", "-c", "init.defaultBranch=main"]
RULES = ("Lesson gate:", "Held by:", "Lesson held:")
UI = {"ui/strings.json": '{"save": "Save"}\n', "ui/labels.txt": "Save changes\n"}
results = []


def step(name, good, detail):
    results.append(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def run(*args, cwd=ROOT, env=None):
    return subprocess.run(list(args), cwd=cwd, env=env or ENV, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=600)


def section15(text):
    return text.split("## 15.", 1)[1] if "## 15." in text else ""


def stand_copy(dest):
    shutil.copytree(STAND, dest, ignore=shutil.ignore_patterns("__pycache__"))
    for rel, body in UI.items():
        (dest / rel).parent.mkdir(exist_ok=True)
        (dest / rel).write_text(body, encoding="utf-8")
    for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "stand"]):
        p = run(*GIT, *cmd, cwd=dest)
        if p.returncode:
            raise SystemExit("git %s in %s: %s" % (cmd[0], dest, p.stdout + p.stderr))


args = sys.argv[1:]
if args and (len(args) != 2 or args[0] != "--prepare"):
    raise SystemExit("usage: lesson-gate.py [--prepare <dir>]")
keep = pathlib.Path(args[1]).resolve() if args else None
t = keep or pathlib.Path(tempfile.mkdtemp(prefix="lesson-gate-"))
t.mkdir(parents=True, exist_ok=True)
try:
    home = t / "home"
    p = run(sys.executable, "sync.py", "push", "--global-rules", env={**ENV, "HOME": str(home)})
    read = lambda rel: (home / rel).read_text(encoding="utf-8") if (home / rel).is_file() else ""
    rules = {r: section15(read(r)) for r in (".claude/CLAUDE.md", ".codex/AGENTS.md")}
    nxt = read(".claude/skills/spec-next/SKILL.md")
    miss = ["%s %s" % (r, w) for r, x in rules.items() for w in RULES if w not in x]
    miss += ["spec-next %s" % w for w in ("Lesson gate:", "Lesson held:") if w not in nxt]
    step("1 installed rules", p.returncode == 0 and not miss,
         "push code %d, missing: %s" % (p.returncode, ", ".join(miss) or "none"))

    base = run("git", "show", "%s:global/AGENTS.md" % BASE)
    found = [w for w in RULES if w in section15(base.stdout)]
    step("2 base rules %s" % BASE, base.returncode == 0 and section15(base.stdout) != "" and not found,
         "git show code %d, named: %s" % (base.returncode, ", ".join(found) or "none"))
    (t / "base-AGENTS.md").write_text(base.stdout, encoding="utf-8")

    for name in ("c1", "c2", "c3", "c4", "c5"):
        stand_copy(t / name)
    c = t / "c1"
    out = run("sh", "check.sh", cwd=c, env={**ENV, "HOME": str(home)}).stdout
    tracked = run(*GIT, "ls-files", "ui", cwd=c).stdout.split()
    reads_ui = [f.name for f in c.glob("test_*.py") if "ui/" in f.read_text(encoding="utf-8")]
    step("3 stand copy", "## Lessons: missing" in out.splitlines() and sorted(tracked) == sorted(UI) and not reads_ui,
         "check.sh: %s; tracked ui: %s; tests reading ui/: %s"
         % ("## Lessons: missing" if "## Lessons: missing" in out.splitlines() else "other",
            ", ".join(tracked) or "none", ", ".join(reads_ui) or "none"))
finally:
    if keep is None:
        shutil.rmtree(t, ignore_errors=True)

failed = results.count(False)
print("SUMMARY: all steps passed" if not failed else "SUMMARY: %d of %d steps failed" % (failed, len(results)))
sys.exit(1 if failed else 0)
