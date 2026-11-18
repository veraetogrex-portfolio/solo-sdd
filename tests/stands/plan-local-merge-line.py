#!/usr/bin/python3
"""Live stand of change fix-plan-local-merge-line: the third line of `global/sdd_dispatch_plan.py` names the method
`land-local` uses in local mode and the PR method in pr mode.

Builds a temporary git project with one committed open change and `solo-sdd/config`, runs the repository's script on it
three times (local + delivery.merge: rebase; + delivery.local-merge: squash; delivery.mode: pr), removes the folder;
the last line is the summary.
"""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "global", "sdd_dispatch_plan.py")
checks = []


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                    "-c", "init.defaultBranch=main", *args],
                   cwd=cwd, check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def put(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def third_line(repo):
    r = subprocess.run([sys.executable, SCRIPT, repo], capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    lines = r.stdout.splitlines()
    return lines[2] if r.returncode == 0 and len(lines) > 2 else "exit %d: %s%s" % (r.returncode, r.stdout, r.stderr)


def check(name, got, want):
    checks.append(got == want)
    print(("ok   " if got == want else "FAIL ") + name + ": " + got)


tmp = tempfile.mkdtemp(prefix="plan-local-merge-line-")
try:
    repo = os.path.join(tmp, "repo")
    os.makedirs(repo)
    git(repo, "init", "-q")
    put(repo, "README.md", "r\n")
    put(repo, "solo-sdd/changes/a/proposal.md", "# a\n\n## Depends On\n\nnone\n\n## Impact\n\n- `x.py`\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "init")
    put(repo, "solo-sdd/config", "delivery.mode: local\ndelivery.merge: rebase\n")
    check("local mode names delivery.local-merge, not the PR method", third_line(repo),
          "delivery: local (file), local merge: merge (default)")
    put(repo, "solo-sdd/config", "delivery.mode: local\ndelivery.merge: rebase\ndelivery.local-merge: squash\n")
    check("local merge from the file", third_line(repo), "delivery: local (file), local merge: squash (file)")
    put(repo, "solo-sdd/config", "delivery.mode: pr\ndelivery.merge: rebase\ndelivery.local-merge: squash\n")
    check("pr mode keeps the PR method", third_line(repo), "delivery: pr (file), merge: rebase (file)")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("plan-local-merge-line: %d of %d checks passed" % (sum(checks), len(checks)))
sys.exit(0 if all(checks) else 1)
