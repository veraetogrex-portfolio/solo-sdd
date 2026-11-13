#!/usr/bin/env python3
"""Live stand of shared-blocks: scripts/sync_blocks.py on the tree, then on a git copy of it with a stale and a broken
copy. Prints one ok/FAIL line per check and `shared-blocks: <n> of <m> checks passed`; exit 0 only when all pass.
The temporary copy is created and removed here."""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else ": " + detail.strip()[:400]))


def sync(root, *args):
    r = subprocess.run([sys.executable, os.path.join(root, "scripts", "sync_blocks.py"), *args],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout + r.stderr


def git(root, *args):
    return subprocess.run(["git", "-C", root, "-c", "user.name=stand", "-c", "user.email=stand@example.invalid",
                           "-c", "commit.gpgsign=false", *args], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL).stdout


def main():
    code, out = sync(ROOT, "--check")
    check("1 --check on the tree: code 0, nothing printed", (code, out) == (0, ""), out)
    with tempfile.TemporaryDirectory(prefix="shared-blocks-") as tmp:
        for d in ("solo_sdd", "global", "scripts"):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d), ignore=shutil.ignore_patterns("__pycache__"))
        git(tmp, "init", "-q")
        git(tmp, "add", "-A")
        git(tmp, "commit", "-qm", "clean")
        pr = os.path.join(tmp, "global", "sdd_pr.py")
        with open(pr, encoding="utf-8", newline="") as f:
            clean = f.read()
        begin, end = clean.index("# settings:begin\n"), clean.index("# settings:end")
        line = clean.index("\n", begin + len("# settings:begin\n")) + 1  # the second line of the block
        stale = clean[:line] + "# an edited line\n" + clean[clean.index("\n", line) + 1:]
        with open(pr, "w", encoding="utf-8", newline="") as f:
            f.write(stale)
        git(tmp, "commit", "-qam", "stale")
        code, out = sync(tmp, "--check")
        check("2 --check on a stale copy: code 1 naming global/sdd_pr.py and settings",
              code == 1 and "global/sdd_pr.py: settings" in out and git(tmp, "status", "--porcelain") == "", out)
        code, out = sync(tmp)
        with open(pr, encoding="utf-8", newline="") as f:
            restored = f.read()
        names = git(tmp, "diff", "--name-only").split()
        hunks = [ln for ln in git(tmp, "diff", "-U0").splitlines() if ln.startswith("@@")]
        first = int(hunks[0].split()[1].lstrip("-").split(",")[0]) if hunks else 0
        block_lines = range(stale[:begin].count("\n") + 1, stale[:stale.index("# settings:end")].count("\n") + 2)
        check("2 a run restores the copy from solo_sdd/settings.py; git diff only in that block",
              code == 0 and restored == clean and names == ["global/sdd_pr.py"] and len(hunks) == 1
              and first in block_lines, out + " ".join(names) + " ".join(hunks))
        before = git(tmp, "status", "--porcelain")
        code, out = sync(tmp)
        check("3 a second run changes no file", (code, out) == (0, "") and git(tmp, "status", "--porcelain") == before,
              out)
        git(tmp, "commit", "-qam", "synced")
        with open(pr, "w", encoding="utf-8", newline="") as f:
            f.write(clean[:end] + clean[clean.index("\n", end) + 1:])
        for args in ((), ("--check",)):
            code, out = sync(tmp, *args)
            status = git(tmp, "status", "--porcelain").splitlines()
            check("4 %s with # settings:end removed: code 1 naming global/sdd_pr.py and settings, no other change"
                  % ("sync_blocks.py " + " ".join(args)).strip(),
                  code == 1 and "global/sdd_pr.py: settings" in out and status == [" M global/sdd_pr.py"],
                  out + " ".join(status))
    print("shared-blocks: %d of %d checks passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
