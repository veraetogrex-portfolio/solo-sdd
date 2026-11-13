#!/usr/bin/env python3
"""Live Scenario of dispatch-eval-replay without a subscription: the real global/sdd_eval.py on a toy project
of 8 changes; instead of claude a fake first in PATH merges the oracle commit and archives the change.

Usage: python3 tests/stands/eval-replay.py
Code 0 means every check matched. The stand creates and removes its temporary folder and HOME itself."""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL, PLAN = ROOT / "global/sdd_eval.py", ROOT / "global/sdd_dispatch_plan.py"
IDS = ["20%d-feat" % i for i in range(8)]
DEPS = {"201-feat": "- `100-dep`\n", "202-feat": "- `999-ghost`\n", "203-feat": "none\n"}
ASKED, BROKEN = "203-feat", "204-feat"
RUNNER = 'rc=0\nfor f in "$@"; do sh "$f" || { echo "FAIL $f"; rc=1; }; done\nexit $rc\n'
AGENTS = "# P\n\n## Commands\n\n| What | Command |\n|---|---|\n| Tests | `sh run-tests.sh` |\n\n## Delivery\n\n- Mode: pr\n"
FAKE = """#!%s
import json, os, subprocess, sys
meta = json.load(open(".sdd-eval"))
open(os.environ["STAND_ARGV"], "a").write(json.dumps(sys.argv[1:]) + "\\n")
subprocess.run(["git", "merge", "-q", "--ff-only", meta["oracle"]], check=True)
os.makedirs("openspec/changes/archive", exist_ok=True)
os.rename("openspec/changes/" + meta["id"], "openspec/changes/archive/2026-01-01-" + meta["id"])
if meta["id"] == "%s" and os.environ["STAND_ASK"] == "1":
    d = os.path.expanduser("~/.claude/projects/p")
    os.makedirs(d, exist_ok=True)
    sid = sys.argv[sys.argv.index("--session-id") + 1]
    msg = {"type": "assistant", "message": {"content": [{"type": "text", "text": "Needs from you: pick a mode"}]}}
    open(os.path.join(d, sid + ".jsonl"), "w").write(json.dumps(msg) + "\\n")
""" % (sys.executable, ASKED)

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("ok: " if ok else "FAIL: ") + name + ("" if ok else " — " + detail[-400:]))


def put(base, rel, text):
    p = Path(base, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def sh(args, cwd=None, env=None):
    return subprocess.run([str(a) for a in args], cwd=cwd, env=env, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)


def git(repo, *args):
    r = sh(["git", "-C", repo] + list(args))
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def build(tmp):
    proj = tmp / "proj"
    proj.mkdir()
    git(proj, "init", "-q", "-b", "main")
    put(proj, ".gitignore", "openspec/\nAGENTS.md\nCLAUDE.md\n")
    put(proj, "run-tests.sh", RUNNER)
    git(proj, "add", "-A")
    git(proj, "commit", "-qm", "base")
    changes = []
    for cid in IDS:
        n = cid[:3]
        put(proj, "code_%s.sh" % n, "f_%s() { :; }\n" % n)
        put(proj, "t%s.test.sh" % n, ". ./code_%s.sh\ntype f_%s >/dev/null 2>&1\n" % (n, n))
        git(proj, "add", "-A")
        git(proj, "commit", "-qm", cid)
        changes.append({"id": cid, "oracle": git(proj, "rev-parse", "HEAD")})
        d = "openspec/changes/archive/2025-12-01-" + cid
        put(proj, d + "/proposal.md", "## Why\nw\n\n## Depends On\n\n" + DEPS.get(cid, "none\n"))
        put(proj, d + "/tasks.md", "- [x] a\n- [ ] b\n")
        put(proj, d + "/verification.md", "## Live Scenario\n\nstep\n\n## Result\n\nOK\n\n## Not Verified\n\nnothing\n")
        put(proj, d + "/CLAIM", "c\n")
    put(proj, "AGENTS.md", AGENTS)
    put(proj, "openspec/config.yaml", "schema: solo\n")
    put(proj, "openspec/changes/archive/2025-11-01-100-dep/proposal.md", "## Why\nd\n")
    put(tmp, "set.json", json.dumps({"project": str(proj), "prepare": "true", "tests": ["*.test.sh"], "changes": changes,
                                     "answers": {"Delivery mode": "local"}}))
    put(tmp, "cfg.json", json.dumps({"name": "base", "working_copy": []}))


def main():
    tmp = Path(tempfile.mkdtemp()).resolve()
    try:
        return stand(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def stand(tmp):
    build(tmp)
    home, fake, E = tmp / "home", tmp / "bin", tmp / "E"
    home.mkdir()
    fake.mkdir()
    E.mkdir()
    (fake / "claude").write_text(FAKE)
    (fake / "claude").chmod(stat.S_IRWXU)
    env = dict(os.environ, HOME=str(home), PATH="%s:%s" % (fake, os.environ["PATH"]), STAND_ARGV=str(tmp / "argv"),
               GIT_AUTHOR_NAME="s", GIT_AUTHOR_EMAIL="s@s", GIT_COMMITTER_NAME="s", GIT_COMMITTER_EMAIL="s@s")

    def ev(*args, ask="0"):
        return sh([sys.executable, EVAL] + list(args), cwd=ROOT, env=dict(env, STAND_ASK=ask))

    a, b = ev("setup", tmp / "set.json", "--config", tmp / "cfg.json", "--out", E / "a"), \
        ev("setup", tmp / "set.json", "--config", tmp / "cfg.json", "--out", E / "b")
    check("setup twice: 8 copies, HEAD and the openspec hash match", a.returncode == 0 and a.stdout == b.stdout
          and len(os.listdir(E / "a")) == 8, a.stdout + a.stderr)
    check("dependency not archived: line and copy", "dependency not archived: 202-feat 999-ghost" in a.stdout
          and (E / "a/202-feat").is_dir() and "not archived: 203-feat" not in a.stdout, a.stdout)
    c = E / "a/201-feat"
    ch = c / "openspec/changes/201-feat"
    tasks, ver, agents = (ch / "tasks.md").read_text(), (ch / "verification.md").read_text(), (c / "AGENTS.md").read_text()
    check("copy before code: tasks reset, no CLAIM, no remote, mode local",
          "[x]" not in tasks and "OK" not in ver and not (ch / "CLAIM").exists() and not git(c, "remote")
          and "Mode: local" in agents and "Mode: pr" not in agents, tasks + ver + agents)
    plan = sh([sys.executable, PLAN, c], env=env)
    check("plan of a copy with an archived dependency: launch, no unknown dependency",
          (c / "openspec/changes/archive/2025-11-01-100-dep").is_dir() and "launch: 201-feat" in plan.stdout
          and "unknown dependency" not in plan.stdout, plan.stdout + plan.stderr)

    ra, rb = ev("run", E / "a", "--label", "a1", ask="1"), ev("run", E / "b", "--label", "b1")
    argv = json.loads((tmp / "argv").read_text().splitlines()[0])
    check("run: prompt /spec-dispatch, answers in --append-system-prompt, all merged",
          argv[:2] == ["-p", "/spec-dispatch"] and "Delivery mode → local" in argv[argv.index("--append-system-prompt") + 1]
          and "finished 8 of 8" in ra.stdout and "finished 8 of 8" in rb.stdout, ra.stdout + ra.stderr + rb.stdout)
    check("run: question mark from the \"Needs from you\" line", "%s merged question: pick a mode" % ASKED in ra.stdout, ra.stdout)
    for f, x, y in ((E / "a", "a1", "a2"), (E / "b", "b1", "b2")):
        shutil.copy(f / "runs" / (x + ".json"), f / "runs" / (y + ".json"))

    same = ev("compare", E, "--a", "a1", "a2", "--b", "a1", "a2")
    check("self-comparison: no flips", same.returncode == 0 and "Flipped: none" in same.stdout, same.stdout + same.stderr)
    for cid in (ASKED, BROKEN):
        n = cid[:3]
        put(E / "a" / cid, "code_%s.sh" % n, "x=1\n")
        git(E / "a" / cid, "-c", "user.name=s", "-c", "user.email=s@s", "commit", "-qam", "export removed")
    r = ev("compare", E, "--a", "a1", "a2", "--b", "b1", "b2")
    flips = r.stdout.split("Flipped:")[1].split("With a question:")[0]
    check("export removed: merged, oracle red with the test name", r.returncode == 0 and
          "merged, oracle red: t204.test.sh" in r.stdout, r.stdout + r.stderr)
    check("only the change without a question flipped", BROKEN in flips and ASKED not in flips, r.stdout)
    check("question: the \"With a question\" section and a mark in the table, the count by oracle",
          "- %s: a1: question: pick a mode" % ASKED in r.stdout and "oracle red: t203.test.sh (question)" in r.stdout
          and "| a | 6, 6 of 8 |" in r.stdout and "| b | 8, 8 of 8 |" in r.stdout, r.stdout)

    proj = home / ".claude/projects/fx"
    shutil.copytree(ROOT / "tests/eval/fixtures", proj)
    m = ev("metrics", "--session", "fixture-session", "--prices", ROOT / "tests/eval/prices.json")
    check("metrics --session on the fixture", m.returncode == 0 and "merged: 1" in m.stdout and "time: 0.47 h" in m.stdout, m.stdout + m.stderr)

    print("total: %d of %d" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
