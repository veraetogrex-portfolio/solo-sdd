#!/usr/bin/env python3
"""Stand of change sync-args-fix: the Live Scenario of its verification.md, steps 1-6.

Every step runs on a new empty temporary home, never on the real one. Step 1 runs the tree of BASE (the commit
before the fix, read with git archive into a temporary folder); steps 2-6 run this tree. Step 5 runs
`python3 -m solo_sdd sync pull ship --bogus` from this repository and reads its skills/ship/SKILL.md before and after.
The stand removes its temporary folders; the last line is the summary.
Run from the repository root: python3 tests/stands/sync-args-fix.py
"""
import io, os, subprocess, sys, tarfile, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = "67e538acee24984860b94da8a1c44d9405a6efb7"
checks = []


def check(name, good, detail=""):
    checks.append(bool(good))
    print(("ok   " if good else "FAIL ") + name + ("" if good else ": " + detail.strip()[-400:]))


def files(home):
    return sum(len(names) for _, _, names in os.walk(home))


def run(repo, home, *args, module=False):
    command = [sys.executable, "-m", "solo_sdd", *args] if module else [sys.executable, os.path.join(repo, "sync.py"), *args]
    p = subprocess.run(command, cwd=repo, env=dict(os.environ, HOME=home), capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=300)
    return p.returncode, p.stdout + p.stderr


with tempfile.TemporaryDirectory(prefix="sync-args-") as tmp:
    def home():
        return tempfile.mkdtemp(dir=tmp)

    base = os.path.join(tmp, "base")
    tar = subprocess.run(["git", "archive", BASE], cwd=ROOT, capture_output=True, check=True).stdout
    tarfile.open(fileobj=io.BytesIO(tar)).extractall(base)
    h = home()
    code, out = run(base, h, "push", "--help")
    check("1 base: push --help deploys (the bug)", code == 0 and "all laid out" in out and files(h) > 100,
          f"exit {code}, {files(h)} files: {out}")

    usage = "python3 sync.py status          what diverged"
    for args in (("push", "--help"), ("push", "-h"), ("status", "-h"), ("pull", "ship", "--help"),
                 ("push", "--bogus", "--help")):
        h = home()
        code, out = run(ROOT, h, *args)
        check("2-3 " + " ".join(args) + ": usage, exit 0, 0 files", code == 0 and usage in out and files(h) == 0,
              f"exit {code}, {files(h)} files: {out}")

    for args in (("push", "--frobnicate"), ("push", "--forc"), ("status", "--bogus"), ("push", "--quiet", "extra")):
        h = home()
        code, out = run(ROOT, h, *args)
        first = out.splitlines()[0] if out else ""
        check("4 " + " ".join(args) + ": refused, exit 2, 0 files",
              code == 2 and first == "unknown argument " + args[-1] and usage in out and files(h) == 0,
              f"exit {code}, {files(h)} files: {out}")

    h = home()
    os.makedirs(os.path.join(h, ".claude"))
    code, out = run(ROOT, h, "push")
    check("5 push before the edit: exit 0", code == 0, f"exit {code}: {out}")
    copy = os.path.join(h, ".claude", "skills", "ship", "SKILL.md")
    with open(copy, "a") as f:
        f.write("edited in place\n")
    source = os.path.join(ROOT, "skills", "ship", "SKILL.md")
    with open(source, "rb") as f:
        before = f.read()
    code, out = run(ROOT, h, "sync", "pull", "ship", "--bogus", module=True)
    with open(source, "rb") as f:
        after = f.read()
    if after != before:  # a regressed refusal pulled the edit: put the tracked source back
        with open(source, "wb") as f:
            f.write(before)
    git =subprocess.run(["git", "status", "--porcelain", "--", "skills/ship/SKILL.md"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    check("5 sync pull ship --bogus: exit 2, source unchanged", code == 2 and after == before and git == "",
          f"exit {code}, git status {git!r}: {out}")

    h = home()
    os.makedirs(os.path.join(h, ".claude"))
    code, out = run(ROOT, h, "push", "--quiet")
    check("6 push --quiet: exit 0, copies laid out", code == 0 and os.path.exists(os.path.join(h, ".claude", "skills", "ship", "SKILL.md")),
          f"exit {code}: {out}")

print(f"SUMMARY: {sum(checks)} of {len(checks)} checks passed" + ("" if all(checks) else ", FAILED"))
sys.exit(0 if all(checks) else 1)
