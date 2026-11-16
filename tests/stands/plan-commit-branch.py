#!/usr/bin/python3
"""Live scenario of change plan-commit-branch-fix (Fallback: step 9 followed by hand, no model call).

1. The step 9 text of the base commit af6bd62 (read with `git show`, apart from the working folder) misses the words
   of Requirement: Plan committed; the text of this tree has them.
2. A temporary repository with a bare remote, `## Delivery` `- Mode: pr`, `main` pushed, a new change `csv-export`,
   an edited tracked change `old` and someone else's edit `src/x.py`; and a fresh one with no tracked change. The
   commands of step 9, each checked to be named in its text, leave `main` where it was, put `change: csv-export, old`
   with only the plan folders on `plan/csv-export`, and leave no untracked copy, so the pull after the merge passes and
   the worktree and the local branch go; a folder origin/main changed since the fork point stops the step; a control copy instead of a move makes git refuse that pull.
3. The same repository with `- Mode: local`: the plan commit is the last commit of `main`.
Run from the repository root: python3 tests/stands/plan-commit-branch.py. The temporary folder is removed; the last
line is the summary."""
import os, pathlib, re, subprocess, sys, tempfile

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


def project(t, name, tracked=True, mode="pr"):
    """A pushed `main` with (or without) a tracked change `old`, then a new change, an edit of `old` and someone else's
    edit."""
    remote, work = t / ("%s.git" % name), t / name
    git(t, "init", "-q", "--bare", str(remote))
    git(t, "clone", "-q", str(remote), str(work))
    put(work, "AGENTS.md", "# p\n\n## Delivery\n\n- Mode: %s\n" % mode)
    put(work, "solo-sdd/project.md", "# Project\n\nLanguage: en\n\nIntent: a toy.\n")
    if tracked:
        put(work, "solo-sdd/changes/old/proposal.md", "# Proposal\n\nv1\n")
    put(work, "src/x.py", "x = 1\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "init")
    git(work, "push", "-q", "origin", "main")
    put(work, "solo-sdd/changes/csv-export/proposal.md", "# Proposal\n\nadd a CSV export\n")
    if tracked:
        put(work, "solo-sdd/changes/old/proposal.md", "# Proposal\n\nv2\n")
    put(work, "src/x.py", "x = 2\n")
    return work


FOLDERS = ["solo-sdd/changes/csv-export", "solo-sdd/changes/old"]
MSG = "change: csv-export, old"
text = run(ROOT, "git", "show", "%s:skills/spec-plan/SKILL.md" % BASE)[1]
base, now = plan_commit_misses(text), plan_commit_misses((ROOT / "skills/spec-plan/SKILL.md").read_text("utf-8"))
step("1 step 9 text", bool(base) and now == [], "base %s misses %d words; this tree misses %s" % (BASE, len(base), now))

STEP = re.sub(r"\s+", " ", (ROOT / "skills/spec-plan/SKILL.md").read_text("utf-8")).split("9. **Plan commit.**")[1]
STEP = STEP.split(" More than five changes")[0]
NAMED = ("`git fetch origin`", "`git diff --quiet HEAD...origin/<main branch> -- <folder>`", "`git worktree add -b plan/<first id> ${TMPDIR:-/tmp}/plan-<first id> origin/<main branch>`",
         "`mkdir -p <worktree>/solo-sdd/changes`", "`rm -rf <worktree>/<folder>`", "`mv <folder> <worktree>/<folder>`",
         "`git restore --source=HEAD --staged --worktree -- <folder>`", "run with `git -C <worktree>`",
         "`git worktree remove <worktree>`", "`git branch -D plan/<first id>`")
step("2 commands named in step 9", all(c in STEP for c in NAMED), "%d of %d" % (sum(c in STEP for c in NAMED), len(NAMED)))


def plan_pr(t, name, tracked):
    """Step 9 under pr in a project with (or without) a tracked change; the merge as a fast-forward push."""
    work = project(t, name, tracked)
    folders = FOLDERS if tracked else FOLDERS[:1]
    mode = run(work, sys.executable, "-m", "solo_sdd", "config", "get", "delivery.mode")[1].splitlines()[0]
    main = git(work, "rev-parse", "main")[1]
    wt = str(t / ("plan-csv-export-" + name))
    git(work, "fetch", "origin")
    stale = [git(work, "diff", "--quiet", "HEAD...origin/main", "--", rel)[0] for rel in folders]
    added = git(work, "worktree", "add", "-b", "plan/csv-export", wt, "origin/main")[0]
    moved = [run(work, "mkdir", "-p", wt + "/solo-sdd/changes")[0]]
    for rel in folders:
        moved += [run(work, "rm", "-rf", wt + "/" + rel)[0], run(work, "mv", rel, wt + "/" + rel)[0]]
        if tracked and rel.endswith("/old"):
            moved.append(git(work, "restore", "--source=HEAD", "--staged", "--worktree", "--", rel)[0])
    git(wt, "add", "--", *folders)
    git(wt, "commit", "-qm", "change: " + ", ".join(f.rsplit("/", 1)[1] for f in folders), "--", *folders)
    subject = git(work, "log", "-1", "--format=%s", "plan/csv-export")[1]
    files = git(work, "show", "--name-only", "--format=", "plan/csv-export")[1].split()
    status = git(work, "status", "--porcelain")[1]
    step("2 plan branch (%s)" % name, mode == "pr" and added == 0 and stale == [0] * len(folders) and moved == [0] * len(moved)
         and git(work, "rev-parse", "main")[1] == main and subject == "change: " + ", ".join(
             f.rsplit("/", 1)[1] for f in folders) and all(f.startswith(tuple(folders)) for f in files)
         and status == "M src/x.py", "config %s; main kept %s; plan/csv-export: %r, %d files under the plan folders; "
         "working folder status: %r" % (mode, main[:7], subject, len(files), status))
    git(wt, "push", "-q", "origin", "plan/csv-export:main")
    gone = git(work, "worktree", "remove", wt)[0] + git(work, "branch", "-D", "plan/csv-export")[0]
    pulled = git(work, "pull", "-q", "--ff-only")[0]
    got = (work / "solo-sdd/changes/old/proposal.md").read_text("utf-8").split()[-1] if tracked else "-"
    step("2 pull after merge (%s)" % name, pulled == 0 and gone == 0 and got in ("v2", "-") and (work / FOLDERS[0]).is_dir(),
         "pull exit %d; worktree and branch removed %s; old holds %s" % (pulled, gone == 0, got))


with tempfile.TemporaryDirectory() as t:
    t = pathlib.Path(t)
    plan_pr(t, "pr", True)
    plan_pr(t, "fresh", False)

    old = project(t, "stale")
    other = t / "other"
    git(t, "clone", "-q", str(t / "stale.git"), str(other))
    put(other, "solo-sdd/changes/old/proposal.md", "# Proposal\n\nv3, merged elsewhere\n")
    git(other, "commit", "-qam", "tick")
    git(other, "push", "-q", "origin", "main")
    git(old, "fetch", "origin")
    stop = git(old, "diff", "--quiet", "HEAD...origin/main", "--", "solo-sdd/changes/old")[0]
    step("2 stale tracked folder", stop == 1, "origin/main changed old since the fork point: the check exits %d, step 9 stops" % stop)

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

    loc = project(t, "local", mode="local")
    lmode = run(loc, sys.executable, "-m", "solo_sdd", "config", "get", "delivery.mode")[1].splitlines()[0]
    git(loc, "add", "--", *FOLDERS)
    git(loc, "commit", "-qm", MSG, "--", *FOLDERS)
    last = git(loc, "log", "-1", "--format=%s", "main")[1]
    step("3 local", lmode == "local" and last == MSG and git(loc, "status", "--porcelain")[1] == "M src/x.py",
         "config %s; last commit of main: %r" % (lmode, last))

print("plan-commit-branch: %d of %d steps passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
