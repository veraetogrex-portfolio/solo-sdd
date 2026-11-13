#!/usr/bin/env python3
"""Stand of change vendor-targets: vendor files listed per skill in targets.json, laid out per agent.

Temporary homes only; the previous map is tests/targets-before.json in a temporary copy of the repository.
  1. a home laid out by the previous map, one copy edited, one deleted: status by the previous map and
     by targets.json lists the same paths and states;
  2. install --agents claude: vendor copies under ~/.claude/skills and ~/.agents/skills (`other`), none under ~/.codex;
     install --agents codex: under ~/.codex/skills and ~/.agents/skills, none under ~/.claude;
  3. targets.json names no agent skill folder.
"""
import os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
checks = []


def check(name, good, detail=""):
    checks.append(good)
    print(("ok   " if good else "FAIL ") + name + ("" if good or not detail else ": " + detail.strip()[-600:]))


def run(home, cwd, repo, *args):
    p = subprocess.run([sys.executable, *args], cwd=cwd, env=dict(os.environ, HOME=home, PYTHONPATH=repo),
                       capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)
    return p.returncode, p.stdout + p.stderr


def rows(out):
    return sorted(" ".join(line.split()) for line in out.splitlines())


def vendor_copies(home):
    """Files under a skill folder's antislop/ or security/: the vendor copies, as paths from home."""
    out = []
    for dp, _, names in os.walk(home):
        rel = os.path.relpath(dp, home)
        if re.search(r"/skills/[^/]+/(antislop|security)(/|$)", "/" + rel):
            out += [os.path.join(rel, n) for n in names]
    return out


def main():
    tmp = tempfile.mkdtemp(prefix="vendor-targets-")
    try:
        before = os.path.join(tmp, "before")
        for d in ("solo_sdd", "global", "skills", "templates", "integrations"):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(before, d), ignore=shutil.ignore_patterns("__pycache__"))
        for f in ("sync.py", "ALGORITHM.md"):
            shutil.copy(os.path.join(ROOT, f), before)
        shutil.copy(os.path.join(ROOT, "tests", "targets-before.json"), os.path.join(before, "targets.json"))

        home = os.path.join(tmp, "home1")
        for d in (".claude", ".codex"):
            os.makedirs(os.path.join(home, d))
        code, out = run(home, tmp, before, os.path.join(before, "sync.py"), "push")
        check("1 push by the previous map", code == 0, out)
        with open(os.path.join(home, ".codex/skills/copy-check/antislop/core.md"), "a") as f:
            f.write("edited in place\n")
        os.remove(os.path.join(home, ".claude/skills/spec-audit/security/HUNTING.md"))
        c1, old = run(home, tmp, before, os.path.join(before, "sync.py"), "status")
        c2, new = run(home, tmp, ROOT, os.path.join(ROOT, "sync.py"), "status")
        kinds = sorted({r.split()[0] for r in rows(new)})
        check("1 status: same %d paths and states (%s)" % (len(rows(new)), ", ".join(kinds)),
              c1 == c2 == 0 and rows(old) == rows(new) and kinds == ["drift", "missing", "ok"],
              "\n".join(sorted(set(rows(old)) ^ set(rows(new)))) or new)

        for agent, other in (("claude", ".codex"), ("codex", ".claude")):
            home = os.path.join(tmp, "home-" + agent)
            os.makedirs(home)
            code, out = run(home, tmp, ROOT, "-m", "solo_sdd", "install", "--agents", agent)
            laid = vendor_copies(home)
            own = [p for p in laid if p.startswith(".%s/skills/" % agent)]
            shared = [p for p in laid if p.startswith(".agents/skills/")]
            check("2 install --agents %s: %d vendor copies in ~/.%s/skills, %d in ~/.agents/skills, none in ~/%s"
                  % (agent, len(own), agent, len(shared), other),
                  code == 0 and own and len(own) == len(shared) and len(own) + len(shared) == len(laid)
                  and not os.path.exists(os.path.join(home, other)), out + "\n".join(laid))

        with open(os.path.join(ROOT, "targets.json")) as f:
            found = re.findall(r"~/\.(?:claude|codex|agents)/skills", f.read())
        check("3 targets.json names agent skill folders: %d times" % len(found), not found)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("vendor-targets: %d/%d checks passed" % (sum(checks), len(checks)))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
