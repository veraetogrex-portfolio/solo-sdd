#!/usr/bin/python3
"""Live scenario of change archive-gates, steps 1-5, on copies of examples/demo (solo-sdd from this repository).

1. `split-bill` with its tasks unticked: `archive split-bill --yes` exits 1 naming the open tasks and Result,
   `git status` of the copy is clean.
2. The same with `--yes --force`: archived, the output has `forced:`.
3. A fresh copy, the delta of `split-bill` gets MODIFIED `No such requirement`: `validate split-bill` exits 1 naming
   the file and the name.
4. A fresh copy with two open changes modifying "Tip and total", the first ticked and with a Result:
   archiving it prints `sibling: <second> MODIFIED Tip and total`.
5. `validate --all` on this repository: 0 errors.
Run from the repository root: python3 tests/stands/archive-gates.py. Temporary folders are removed; the last line is
the summary."""
import os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEMO = ROOT / "examples" / "demo"
ENV = dict(os.environ, PYTHONPATH=str(ROOT))
CHANGE = "solo-sdd/changes/split-bill"
REQ = "### Requirement: %s\nThe system SHALL %s.\n\n#### Scenario: S\n- **WHEN** a\n- **THEN** b\n"
ok = True


def step(name, good, detail):
    global ok
    ok &= good
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def sdd(cwd, *args):
    p = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=cwd, env=ENV, capture_output=True,
                       text=True, stdin=subprocess.DEVNULL, timeout=120)
    return p.returncode, p.stdout


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, capture_output=True,
                          text=True, stdin=subprocess.DEVNULL, timeout=60).stdout


def copy(t, name):
    d = pathlib.Path(t) / name
    shutil.copytree(DEMO, d)
    git(d, "init", "-q", "-b", "main")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "demo")
    return d


def finish(d, cid):
    """Ticks every task before the Acceptance group and writes a Result."""
    tasks = d / "solo-sdd/changes" / cid / "tasks.md"
    head, acc = tasks.read_text(encoding="utf-8").split("## 2. Acceptance")
    tasks.write_text(head.replace("- [ ]", "- [x]") + "## 2. Acceptance" + acc, encoding="utf-8")
    v = d / "solo-sdd/changes" / cid / "verification.md"
    text = v.read_text(encoding="utf-8")
    start = text.index("## Result")
    end = text.index("\n## ", start + 1)
    v.write_text(text[:start] + "## Result\n\nRan the stand.\n" + text[end:], encoding="utf-8")


with tempfile.TemporaryDirectory() as t:
    d = copy(t, "one")
    code, out = sdd(d, "archive", "split-bill", "--yes")
    clean = git(d, "status", "--porcelain") == ""
    step("1 refused", code == 1 and "open task: 1.1" in out and "open task: 1.2" in out
         and "empty section: Result" in out and clean,
         "exit %d, %s, git status %s" % (code, " | ".join(l for l in out.splitlines() if l.startswith(("open", "empty"))),
                                         "clean" if clean else "dirty"))
    code, out = sdd(d, "archive", "split-bill", "--yes", "--force")
    forced = [l for l in out.splitlines() if l.startswith("forced:")]
    step("2 forced", code == 0 and forced == ["forced: 1.1, 1.2, Result"] and not (d / CHANGE).exists(),
         "exit %d, %s" % (code, forced))

    d = copy(t, "two")
    delta = d / CHANGE / "specs/tip/spec.md"
    delta.write_text(delta.read_text(encoding="utf-8") + "\n## MODIFIED Requirements\n\n"
                     + REQ % ("No such requirement", "do it"), encoding="utf-8")
    code, out = sdd(d, "validate", "split-bill")
    errs = [l for l in out.splitlines() if ": delta: " in l]
    step("3 dry run", code == 1 and len(errs) == 1 and errs[0].startswith(CHANGE + "/specs/tip/spec.md: delta: ")
         and "No such requirement" in errs[0] and git(d, "status", "--porcelain") == " M %s/specs/tip/spec.md\n" % CHANGE,
         "exit %d, %s" % (code, errs))

    d = copy(t, "three")
    for cid in ("tip-round", "tip-cents"):
        shutil.copytree(d / CHANGE, d / "solo-sdd/changes" / cid)
        (d / "solo-sdd/changes" / cid / "specs/tip/spec.md").write_text(
            "## MODIFIED Requirements\n\n" + REQ % ("Tip and total", "print the tip and the total of " + cid),
            encoding="utf-8")
    finish(d, "tip-round")
    code, out = sdd(d, "archive", "tip-round", "--yes")
    sib = [l for l in out.splitlines() if l.startswith("sibling:")]
    step("4 sibling", code == 0 and sib == ["sibling: tip-cents MODIFIED Tip and total"], "exit %d, %s" % (code, sib))

code, out = sdd(ROOT, "validate", "--all")
step("5 validate --all", code == 0 and out.strip().endswith("0 errors"), "exit %d, %s" % (code, out.strip().splitlines()[-1]))
print("archive-gates stand: %s" % ("all steps passed" if ok else "FAILED"))
sys.exit(0 if ok else 1)
