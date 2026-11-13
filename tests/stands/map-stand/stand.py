#!/usr/bin/python3
"""Live stand of change codebase-map: the shell commands of `skills/project-init/SKILL.md` step 4a on real repositories.

Takes from the skill text the existing-project condition, the stamp command and the lead's existence check, and runs them:
the condition in an empty repository, in one holding only process artifacts and a non-ASCII doc, and in a clone of this checkout;
a map stamped by the skill's command in the clone passes `check.py`; an invented path fails it; after an empty
commit the restamped map names the new HEAD; the lead check names a missing file. Writes only to a temporary
folder it removes; the last line is the summary.
"""
import os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CHECK = os.path.join(HERE, "check.py")
FILES = ("STACK", "ARCHITECTURE", "CONVENTIONS", "CONCERNS")
checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else "\n" + str(detail)))


def sh(cmd, cwd):
    return subprocess.run(["sh", "-c", cmd], cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                          capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout.strip()


skill = open(os.path.join(ROOT, "skills", "project-init", "SKILL.md"), encoding="utf-8").read()
step = re.search(r"^4a\. .*?(?=^5\. )", skill, re.S | re.M).group(0)
cond = re.search(r"`(git [^`]*ls-tree [^`]+)`", step).group(1)
stamp_cmd = re.search(r"`(git log -1 --format='Commit: [^`]+)`", step).group(1)
lead_cmd = re.search(r"`(for f in [^`]+)`", step).group(1)

tmp = tempfile.mkdtemp(prefix="map-stand-")
try:
    empty, bare, clone = (os.path.join(tmp, n) for n in ("empty", "artifacts", "clone"))
    os.makedirs(empty)
    git(empty, "init", "-q")
    check("empty repository: condition says no map", sh(cond, empty).returncode != 0)

    os.makedirs(os.path.join(bare, "openspec"))
    git(bare, "init", "-q")
    os.makedirs(os.path.join(bare, "docs"))
    for f in ("AGENTS.md", "CLAUDE.md", ".gitignore", "openspec/config.yaml", "docs/\u0437\u0430\u043c.md"):
        open(os.path.join(bare, f), "w").close()
    git(bare, "add", "-A")
    git(bare, "commit", "-qm", "project-init: rules and specs")
    check("only process artifacts and a non-ASCII doc committed: condition says no map", sh(cond, bare).returncode != 0)

    git(tmp, "clone", "-q", "--shared", ROOT, clone)
    check("clone of this checkout: condition says map", sh(cond, clone).returncode == 0)

    def write_map(extra=""):
        stamp = sh(stamp_cmd, clone).stdout.strip()
        top = git(clone, "ls-tree", "--name-only", "HEAD").splitlines()[:5]
        os.makedirs(os.path.join(clone, "docs", "codebase"), exist_ok=True)
        for f in FILES:
            body = "".join("- Part of the tree: `%s`\n" % p for p in top) + extra
            open(os.path.join(clone, "docs", "codebase", f + ".md"), "w").write(stamp + "\n\n## Items\n\n" + body)
        return stamp

    def run_check():
        return subprocess.run([sys.executable, CHECK, clone], capture_output=True, text=True, stdin=subprocess.DEVNULL)

    stamp = write_map()
    head = git(clone, "rev-parse", "HEAD")
    p = run_check()
    check("map stamped by the skill command passes check.py", p.returncode == 0 and stamp.split()[1] == head,
          stamp + "\n" + p.stdout)
    print(p.stdout.strip().splitlines()[-1])

    write_map("- Errors are logged centrally in `src/logger.py`\n")
    p = run_check()
    check("invented path fails check.py and is printed",
          p.returncode == 1 and "no existing path: Errors are logged centrally in `src/logger.py`" in p.stdout, p.stdout)

    git(clone, "commit", "-q", "--allow-empty", "-m", "map-test")
    write_map()
    new_head = git(clone, "rev-parse", "HEAD")
    first = open(os.path.join(clone, "docs", "codebase", "STACK.md")).readline()
    check("refresh after a new commit stamps the new HEAD", new_head != head and new_head in first
          and run_check().returncode == 0, first)
    out = sh(lead_cmd, clone).stdout.split()
    os.remove(os.path.join(clone, "docs", "codebase", "CONCERNS.md"))
    out2 = sh(lead_cmd, clone).stdout
    check("lead check prints line counts and names a missing file",
          len(out) == 4 and all(x.isdigit() for x in out) and "CONCERNS missing or empty" in out2, (out, out2))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("map-stand: %d of %d checks passed" % (sum(checks), len(checks)))
sys.exit(0 if all(checks) else 1)
