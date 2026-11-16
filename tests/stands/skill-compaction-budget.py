#!/usr/bin/env python3
"""Stand of change skill-compaction-budget: steps 2 to 4 of its Live Scenario.

  2. the size budget on a copy of the base commit (pinned by hash, read with `git show`, apart from the working
     folder) fails naming spec-dispatch, spec-next and spec-plan; on this tree it holds and the step files are named;
  3. `sync.py push` of this tree into a temporary home lays every step file next to each deployed SKILL.md of its
     skill with the same bytes;
  4. every non-empty line of each base SKILL.md is in that skill's SKILL.md joined with its step files.
The real home is never touched; the temporary folder is removed at the end. Exit 0 only when every step holds.
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import skill_text  # noqa: E402

BASE = "2cf3a4999fcac0935f28805ea1e144f0a6a05791"
SPLIT = ("spec-dispatch", "spec-next", "spec-plan")
GIT = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
failed = []


def git(*args, cwd=ROOT, binary=False):
    return subprocess.run(["git", *args], cwd=cwd, env=GIT, capture_output=True, check=True, text=not binary,
                          stdin=subprocess.DEVNULL).stdout


def check(good, line):
    print(line)
    if not good:
        failed.append(line)


def flat(text):
    return {" ".join(l.split()) for l in text.splitlines() if l.strip()}


def main():
    tmp = tempfile.mkdtemp(prefix="skill-compaction-budget-")
    try:
        # 2: the budget fails on the base commit and holds on this tree
        base = os.path.join(tmp, "base")
        os.makedirs(base)
        for rel in git("ls-tree", "-r", "--name-only", BASE, "skills").split():
            os.makedirs(os.path.dirname(os.path.join(base, rel)), exist_ok=True)
            with open(os.path.join(base, rel), "wb") as f:
                f.write(git("show", "%s:%s" % (BASE, rel), binary=True))
        git("init", "-q", cwd=base)
        git("add", "skills", cwd=base)
        over = skill_text.over_budget(base)
        for line in over:
            print("over budget: " + line)
        check(any(l.startswith("skills/spec-dispatch/SKILL.md ") for l in over),
              "base %s: the budget check fails (%d over)" % (BASE[:7], len(over)))
        now, steps = skill_text.over_budget(ROOT), skill_text.step_errors(ROOT)
        for line in now + steps:
            print("FAIL " + line)
        check(not now and not steps, "ok: %d skills within %d bytes, step files named and present"
              % (len(skill_text.tracked_skills(ROOT)), skill_text.BUDGET) if not now and not steps
              else "FAIL: this tree is over budget or a step file is missing or orphan")

        # 3: sync.py push lays the step files next to each deployed SKILL.md
        home, bindir = os.path.join(tmp, "home"), os.path.join(tmp, "bin")
        for d in (".claude", ".codex", ".agents"):
            os.makedirs(os.path.join(home, d))
        os.makedirs(bindir)
        env = {"HOME": home, "PATH": bindir, "LANG": "C.UTF-8", "PYTHONPATH": ROOT}
        p = subprocess.run([sys.executable, os.path.join(ROOT, "sync.py"), "push"], cwd=tmp, env=env,
                           capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
        bad, laid = [], 0
        for name in SPLIT:
            files = sorted(f for f in os.listdir(os.path.join(ROOT, "skills", name)) if f != "SKILL.md")
            roots = sorted(os.path.dirname(s) for s in glob.glob(os.path.join(home, ".*", "skills", name, "SKILL.md")))
            if not roots:
                bad.append("%s: no deployed SKILL.md" % name)
            for root in roots:
                for f in files:
                    with open(os.path.join(ROOT, "skills", name, f), "rb") as a:
                        want = a.read()
                    there = os.path.join(root, f)
                    got = open(there, "rb").read() if os.path.isfile(there) else None
                    laid += got == want
                    if got != want:
                        bad.append("%s %s" % ("missing" if got is None else "differs", os.path.relpath(there, home)))
        for line in bad:
            print("FAIL " + line)
        check(p.returncode == 0 and not bad and laid, "ok: step files deployed (%d copies)" % laid
              if p.returncode == 0 and not bad and laid else "FAIL: push exit %d, %d bad" % (p.returncode, len(bad)))

        # 4: every base line of a split skill is in its joined text
        lost = []
        for name in SPLIT:
            joined = flat(skill_text.skill(name))
            lost += ["%s: %s" % (name, l[:100]) for l in sorted(flat(git("show", "%s:skills/%s/SKILL.md" % (BASE, name))))
                     if l not in joined]
        for line in lost:
            print("lost " + line)
        check(not lost, "ok: no rule lost" if not lost else "FAIL: %d base lines lost" % len(lost))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("skill-compaction-budget: %s" % ("all checks passed" if not failed else "%d checks failed" % len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
