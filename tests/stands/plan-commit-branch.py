#!/usr/bin/python3
"""Live scenario of change plan-commit-branch-fix (Fallback: step 9 followed by hand, no model call).

1. The step 9 text of the base commit af6bd62 (read with `git show`, apart from the working folder) misses the words
   of Requirement: Plan committed; the text of this tree has them.
2. A temporary repository with a bare remote, `## Delivery` `- Mode: pr`, `main` pushed, a new change `csv-export`,
   an edited tracked change `old` and someone else's edit `src/x.py`: the commands of step 9 (each named in its text)
   leave `main` where it was, put `change: csv-export, old` on `plan/csv-export`, and leave no untracked copy, so the
   pull after the merge passes; a control copy instead of a move makes git refuse that pull.
3. The same repository with `- Mode: local`: the plan commit is the last commit of `main`.
Run from the repository root: python3 tests/stands/plan-commit-branch.py. The temporary folder is removed; the last
line is the summary."""
import os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from test_skill_commands import plan_commit_misses  # noqa: E402

BASE = "af6bd62"
ENV = {**os.environ, "PYTHONPATH": str(ROOT), "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
results = []


def step(name, good, detail):
    results.append(good)
    print("%s %s: %s" % ("ok" if good else "FAILED", name, detail))


def run(cwd, *cmd):
    p = subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
    return p.returncode, (p.stdout + p.stderr).strip()


def git(cwd, *args):
    return run(cwd, "git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main", *args)


def put(root, rel, text):
    p = pathlib.Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def project(t, mode):
    """A pushed `main` with a tracked change `old`, then a new change, an edit of `old` and someone else's edit."""
    remote, work = t / ("%s.git" % mode), t / mode
    git(t, "init", "-q", "--bare", str(remote))
    git(t, "clone", "-q", str(remote), str(work))
    put(work, "AGENTS.md", "# p\n\n## Delivery\n\n- Mode: %s\n" % mode)
    put(work, "solo-sdd/project.md", "# Project\n\nLanguage: en\n\nIntent: a toy.\n")
    put(work, "solo-sdd/changes/old/proposal.md", "# Proposal\n\nv1\n")
    put(work, "src/x.py", "x = 1\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "init")
    git(work, "push", "-q", "origin", "main")
    put(work, "solo-sdd/changes/csv-export/proposal.md", "# Proposal\n\nadd a CSV export\n")
    put(work, "solo-sdd/changes/old/proposal.md", "# Proposal\n\nv2\n")
    put(work, "src/x.py", "x = 2\n")
    return work


FOLDERS = ["solo-sdd/changes/csv-export", "solo-sdd/changes/old"]
MSG = "change: csv-export, old"
text = run(ROOT, "git", "show", "%s:skills/spec-plan/SKILL.md" % BASE)[1]
base, now = plan_commit_misses(text), plan_commit_misses((ROOT / "skills/spec-plan/SKILL.md").read_text("utf-8"))
step("1 step 9 text", bool(base) and now == [], "base %s misses %d words; this tree misses %s" % (BASE, len(base), now))

with tempfile.TemporaryDirectory() as t:
    t = pathlib.Path(t)
    work = project(t, "pr")
    mode = run(work, sys.executable, "-m", "solo_sdd", "config", "get", "delivery.mode")[1].splitlines()[0]
    main = git(work, "rev-parse", "main")[1]
    wt = t / "plan-csv-export"
    git(work, "fetch", "origin")
    added = git(work, "worktree", "add", "-b", "plan/csv-export", str(wt), "origin/main")[0]
    for rel in FOLDERS:  # step 9: mv replacing the worktree's copy, then git restore a tracked one
        shutil.rmtree(wt / rel, ignore_errors=True)
        shutil.move(str(work / rel), str(wt / rel))
    git(work, "restore", "--", "solo-sdd/changes/old")
    git(wt, "add", "--", *FOLDERS)
    git(wt, "commit", "-qm", MSG, "--", *FOLDERS)
    subject = git(work, "log", "-1", "--format=%s", "plan/csv-export")[1]
    status = git(work, "status", "--porcelain")[1]
    step("2 plan branch", mode == "pr" and added == 0 and git(work, "rev-parse", "main")[1] == main and subject == MSG
         and status == "M src/x.py", "config %s; main kept %s; plan/csv-export: %r; working folder status: %r"
         % (mode, main[:7], subject, status))
    git(wt, "push", "-q", "origin", "plan/csv-export:main")  # the PR merge, fast-forward
    git(work, "worktree", "remove", str(wt))
    pulled = git(work, "pull", "-q", "--ff-only")
    got = (work / "solo-sdd/changes/old/proposal.md").read_text("utf-8")
    step("2 pull after merge", pulled[0] == 0 and "v2" in got and (work / FOLDERS[0]).is_dir(),
         "pull exit %d; old holds %s; csv-export %s" % (pulled[0], got.split()[-1], (work / FOLDERS[0]).is_dir()))

    ctl = project(t, "control")
    git(ctl, "switch", "-q", "-c", "plan/x")
    git(ctl, "add", "--", *FOLDERS)
    git(ctl, "commit", "-qm", MSG, "--", *FOLDERS)
    git(ctl, "push", "-q", "origin", "plan/x:main")
    git(ctl, "switch", "-q", "main")
    put(ctl, "solo-sdd/changes/csv-export/proposal.md", "# Proposal\n\nadd a CSV export\n")  # a copy, not a move
    refused = git(ctl, "pull", "-q", "--ff-only")
    step("2 control copy", refused[0] != 0 and "untracked working tree files" in refused[1],
         "an untracked copy: pull exit %d" % refused[0])

    loc = project(t, "local")
    lmode = run(loc, sys.executable, "-m", "solo_sdd", "config", "get", "delivery.mode")[1].splitlines()[0]
    git(loc, "add", "--", *FOLDERS)
    git(loc, "commit", "-qm", MSG, "--", *FOLDERS)
    last = git(loc, "log", "-1", "--format=%s", "main")[1]
    step("3 local", lmode == "local" and last == MSG and git(loc, "status", "--porcelain")[1] == "M src/x.py",
         "config %s; last commit of main: %r" % (lmode, last))

print("plan-commit-branch: %d of %d steps passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
