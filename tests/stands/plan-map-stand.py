#!/usr/bin/python3
"""Live stand of change plan-reads-map: step 2a of `skills/spec-plan/SKILL.md` on real repositories.

Takes from the skill text the type table, the map existence test and the stale-map loop, and runs them:
the table rows for a bugfix, an interface, an interface+API and an unknown unit; the existence test in a
repository without `docs/codebase/`; the stale loop after 25, 20 and 35 docs-only commits since the stamp,
for a stamp unknown to the repository, a stamp on a deleted branch and a file without a stamp. Writes only to a temporary folder it removes;
the last line is the summary.
"""
import os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REFRESH = "; refresh: /project-init map"
checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else "\n" + str(detail)))


def sh(cmd, cwd):
    return subprocess.run(["sh", "-c", cmd], cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                          cwd=cwd, check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout.strip()


skill = open(os.path.join(ROOT, "skills", "spec-plan", "SKILL.md"), encoding="utf-8").read()
step = re.search(r"^2a\. .*?(?=^3\. )", skill, re.S | re.M).group(0)
table = {}
for typ, files in re.findall(r"^\s*\| ([^|]+?) \| ([A-Z, ]+) \|$", step, re.M):
    for t in typ.split(", "):
        table[t] = [f.strip() for f in files.split(",")]
fallback = re.search(r"a type not in the table reads `([A-Z]+)\.md` only", step).group(1)
exists_cmd = re.search(r"`(test -d docs/codebase)`", step).group(1)
loop = re.search(r"`(for f in <files read>; [^`]+)`", step).group(1)


def read_for(*types):
    out = []
    for t in types:
        for f in table.get(t, [fallback]):
            if f not in out:
                out.append(f)
    return sorted(out)


check("bugfix unit reads ARCHITECTURE and CONCERNS", read_for("bugfix") == ["ARCHITECTURE", "CONCERNS"], table)
check("interface unit reads CONVENTIONS and ARCHITECTURE", read_for("interface") == ["ARCHITECTURE", "CONVENTIONS"], table)
check("interface+API unit reads the union, each once", read_for("interface", "API") == ["ARCHITECTURE", "CONVENTIONS"], table)
check("unit of a type not in the table reads ARCHITECTURE only", read_for("unknown type") == ["ARCHITECTURE"], table)

tmp = tempfile.mkdtemp(prefix="plan-map-stand-")
try:
    repo = os.path.join(tmp, "repo")
    os.makedirs(os.path.join(repo, "src"))
    git(repo, "init", "-q")
    open(os.path.join(repo, "src", "app.py"), "w").write("x = 0\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "code")
    check("no docs/codebase: existence test fails, Map: none", sh(exists_cmd, repo).returncode != 0
          and "`Map: none`" in step)

    stamp = git(repo, "rev-parse", "HEAD")
    arch = "docs/codebase/ARCHITECTURE.md"
    os.makedirs(os.path.join(repo, "docs", "codebase"))

    def stamp_map(first_line):
        open(os.path.join(repo, arch), "w").write(first_line + "\n\n- Entry: `src/app.py`\n")

    def commits(n, path):
        os.makedirs(os.path.dirname(os.path.join(repo, path)), exist_ok=True)
        for i in range(n):
            open(os.path.join(repo, path), "a").write("%d\n" % i)
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "c")

    def stale(code=None):
        p = sh(loop.replace("<files read>", arch), repo)
        if code is not None:
            codes.append(p.returncode)
        return p.stdout.strip()

    codes = []

    stamp_map("Commit: %s 2026-11-09" % stamp)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "map")
    commits(30, "docs/notes.md")
    commits(5, "openspec/changes/x/tasks.md")
    out = stale()
    check("35 commits only in docs/ and openspec/: no Map stale line", out == "", out)

    commits(20, "src/app.py")
    out = stale(code=True)
    check("exactly 20 code commits: no Map stale line, loop exits 0", out == "" and codes == [0], (out, codes))

    commits(5, "src/app.py")
    out = stale()
    check("25 code commits: Map stale line with the count", out == "Map stale: %s, 25 commits since %s%s"
          % (arch, stamp, REFRESH), out)
    print(out)

    lost = "0123456789abcdef0123456789abcdef01234567"
    stamp_map("Commit: %s 2026-01-01" % lost)
    out = stale()
    check("stamp not in history: Map stale line with that hash",
          out == "Map stale: %s, unknown commits since %s%s" % (arch, lost, REFRESH), out)

    git(repo, "checkout", "-q", "-b", "side")
    commits(1, "src/side.py")
    side = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-")
    git(repo, "branch", "-q", "-D", "side")
    stamp_map("Commit: %s 2026-11-09" % side)
    out = stale()
    check("stamp commit still in the object store but not in the history of HEAD: Map stale line",
          out == "Map stale: %s, unknown commits since %s%s" % (arch, side, REFRESH), out)

    stamp_map("# Architecture")
    out = stale()
    check("no stamp: Map stale line with none", out == "Map stale: %s, unknown commits since none%s" % (arch, REFRESH), out)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("plan-map-stand: %d of %d checks passed" % (sum(checks), len(checks)))
sys.exit(0 if all(checks) else 1)
