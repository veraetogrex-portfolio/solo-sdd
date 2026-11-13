#!/usr/bin/env python3
"""Stand of change vendor-to-integrations: the two pinned copies as bundled integrations.

Steps 1 to 6 of its Live Scenario, on a temporary home and a temporary project with no settings:
  1. sync.py status after a push of the layout before the move (a copy of the repository with integrations/ put back
     as vendor/ and the targets.json keys with it) lists the same targets in the same states with the moved tree;
  2. `solo-sdd integrations list` shows antislop and security-audit as bundled and enabled;
  3. `check --point review --tag ui` and `check --point audit --tag security` name their material files;
  4. `integrations disable antislop` writes integrations.off, the ui material is gone, `enable` removes the line;
  5. the wheel and the npm tarball scripts/release_check.py builds from a copy of the tree hold integrations/ and no
     vendor/ (the build runs on the first of sys.executable and /usr/bin/python3 that has the build module);
  6. after sync.py push of this tree the laid-out ui-check, copy-check, spec-next and spec-audit name
     `check --point ... --tag ...` and no copy path.
The real home is never touched; the temporary folder is removed at the end. The last line is the summary.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COPY_DIRS = ("solo_sdd", "global", "skills", "templates")
SKILLS = {"ui-check": "--point review --tag ui", "copy-check": "--point review --tag copy",
          "spec-next": "--point review --tag ui", "spec-audit": "--point audit --tag security"}
COPY_PATHS = ("vendor/", "integrations/antislop", "integrations/security-audit")
passed = total = 0


def step(name, good, detail):
    global passed, total
    total += 1
    passed += bool(good)
    print("%s %s: %s" % ("ok" if good else "FAIL", name, " | ".join(str(detail).strip().splitlines())[:600]))


def run(args, cwd, env):
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def rows(out):
    """{target: state} of `sync.py status` rows `<state> <source> <target>`."""
    got = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2].startswith("~/"):
            got[parts[2]] = parts[0]
    return got


def before_tree(dest):
    """This tree as it was before the move: integrations/ back as vendor/, the targets.json keys with it."""
    for d in COPY_DIRS:
        shutil.copytree(os.path.join(ROOT, d), os.path.join(dest, d), ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(ROOT, "integrations"), os.path.join(dest, "vendor"))
    for f in ("sync.py", "ALGORITHM.md"):
        shutil.copy(os.path.join(ROOT, f), dest)
    with open(os.path.join(ROOT, "targets.json"), encoding="utf-8") as f:
        text = f.read()
    with open(os.path.join(dest, "targets.json"), "w", encoding="utf-8") as f:
        f.write(text.replace('"integrations/', '"vendor/'))


def git_copy(dest):
    """The tracked files plus untracked not ignored ones, committed into a new repository (release_check builds from
    what is committed)."""
    files = subprocess.run(["git", "-C", ROOT, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                           capture_output=True, text=True, check=True).stdout.split("\0")
    for rel in filter(None, files):
        src = os.path.join(ROOT, rel)
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(os.path.join(dest, rel)) or dest, exist_ok=True)
            shutil.copy2(src, os.path.join(dest, rel))
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "tree"]):
        subprocess.run(["git", "-C", dest] + args, check=True, env=env, capture_output=True, stdin=subprocess.DEVNULL)


def builder():
    for py in (sys.executable, "/usr/bin/python3"):
        if os.path.exists(py) and subprocess.run([py, "-c", "import build"], capture_output=True,
                                                 stdin=subprocess.DEVNULL).returncode == 0:
            return py
    return None


def main():
    tmp = tempfile.mkdtemp(prefix="vendor-to-integrations-")
    try:
        home, bindir, proj, before = (os.path.join(tmp, n) for n in ("home", "bin", "proj", "before"))
        for d in (os.path.join(home, ".claude"), bindir, os.path.join(proj, "solo-sdd", "changes"), before):
            os.makedirs(d, exist_ok=True)
        env = {"HOME": home, "PATH": bindir, "LANG": "C.UTF-8"}

        # 1: the same targets in the same states before and after the move
        before_tree(before)
        code, out = run([sys.executable, os.path.join(before, "sync.py"), "push"], tmp, dict(env, PYTHONPATH=before))
        old = rows(run([sys.executable, os.path.join(before, "sync.py"), "status"], tmp, dict(env, PYTHONPATH=before))[1])
        new = rows(run([sys.executable, os.path.join(ROOT, "sync.py"), "status"], tmp, dict(env, PYTHONPATH=ROOT))[1])
        moved = {t: s for t, s in new.items() if "/antislop/" in t or "/spec-audit/security/" in t}
        folders = {f for f in ("ui-check/antislop/", "copy-check/antislop/", "spec-audit/security/")
                   if any(f in t for t in moved)}
        step("1 same targets", code == 0 and old == new and len(folders) == 3 and set(moved.values()) == {"ok"},
             "push exit %d, %d targets before, %d after, equal: %s, copy targets: %d, states: %s"
             % (code, len(old), len(new), old == new, len(moved), sorted(set(moved.values()))))

        sdd_env = dict(env, PYTHONPATH=ROOT)

        def sdd(*args):
            return run([sys.executable, "-m", "solo_sdd", *args], proj, sdd_env)

        # 2: bundled and enabled in a project with no settings
        code, out = sdd("integrations", "list")
        heads = [" ".join(ln.split(":")[0].split()) for ln in out.splitlines()]
        step("2 list", code == 0 and "antislop bundled enabled review" in heads
             and "security-audit bundled enabled audit" in heads, "exit %d: %s" % (code, out))

        # 3: the material of a point and a tag
        code, ui = sdd("check", "--point", "review", "--tag", "ui")
        code2, sec = sdd("check", "--point", "audit", "--tag", "security")
        core = os.path.join(ROOT, "integrations", "antislop", "antislop.md")
        step("3 material", (code, code2) == (0, 0) and ui == "MATERIAL antislop: %s\n" % core
             and sec.startswith("MATERIAL security-audit: ") and sec.strip().endswith("skills/security-audit/SKILL.md"),
             "%s %s" % (ui, sec))

        # 4: switched off and on again
        cfg = os.path.join(proj, "solo-sdd", "config")
        code, out = sdd("integrations", "disable", "antislop")
        value = sdd("config", "get", "integrations.off")[1].splitlines()[:1]
        listed = sdd("integrations", "list")[1]
        off = sdd("check", "--point", "review", "--tag", "ui")[1]
        code2, out2 = sdd("integrations", "enable", "antislop")
        left = open(cfg, encoding="utf-8").read() if os.path.exists(cfg) else ""
        step("4 disable and enable", code == 0 and value == ["antislop"] and "antislop bundled disabled" in listed
             and off.startswith("no integrations enabled") and code2 == 0 and "integrations.off" not in left,
             "disable: %s; config get: %s; check: %s; enable: %s; config after: %r" % (out, value, off, out2, left))

        # 5: the built packages hold integrations/ and no vendor/
        py = builder()
        if py is None:
            step("5 packages", False, "no interpreter with the build module (python3 -m pip install build)")
        else:
            repo, dist = os.path.join(tmp, "repo"), os.path.join(tmp, "dist")
            git_copy(repo)
            with open(os.path.join(repo, "package.json"), encoding="utf-8") as f:
                version = json.load(f)["version"]
            # a temporary home for the caches of pip and npm; the user site of py (where build may lie) stays readable
            base = subprocess.run([py, "-c", "import site; print(site.getuserbase())"], capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL).stdout.strip()
            code, out = run([py, os.path.join(repo, "scripts", "release_check.py"), "v" + version, "--out", dist], tmp,
                            dict(os.environ, HOME=os.path.join(tmp, "build-home"), PYTHONUSERBASE=base))
            names = {}
            for path in glob.glob(os.path.join(dist, "*.whl")):
                with zipfile.ZipFile(path) as z:
                    names["wheel"] = z.namelist()
            for path in glob.glob(os.path.join(dist, "*.tgz")):
                with tarfile.open(path) as t:
                    names["npm"] = t.getnames()
            want = {"wheel": "solo_sdd/data/", "npm": "package/"}
            good = all(any(n.startswith(want[k] + "integrations/" + c + "/") for n in names.get(k, ()))
                       for k in want for c in ("antislop", "security-audit")) and not any(
                n.startswith(want[k] + "vendor/") for k in want for n in names.get(k, ()))
            step("5 packages", code == 0 and set(names) == set(want) and good,
                 "release_check exit %d, packages %s, integrations/ in both and no vendor/: %s; %s"
                 % (code, sorted(names), good, out.strip().splitlines()[-1:] if out.strip() else ""))

        # 6: the laid-out skills ask the CLI and name no copy path
        code, out = run([sys.executable, os.path.join(ROOT, "sync.py"), "push"], tmp, dict(env, PYTHONPATH=ROOT))
        bad = []
        for skill, args in SKILLS.items():
            path = os.path.join(home, ".claude", "skills", skill, "SKILL.md")
            text = open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
            if "solo-sdd check " + args not in text:
                bad.append("%s: no `check %s`" % (skill, args))
            bad += ["%s: names %s" % (skill, p) for p in COPY_PATHS + ("ui-check/antislop/core.md",) if p in text]
        security = os.path.join(home, ".claude", "skills", "spec-audit", "security")
        if not os.path.isfile(os.path.join(security, "METHOD.md")) or glob.glob(os.path.join(security, "**", "SKILL.md"),
                                                                                 recursive=True):
            bad.append("spec-audit/security: METHOD.md missing or a SKILL.md under it")
        with open(core, "rb") as a, open(os.path.join(home, ".claude", "skills", "ui-check", "antislop", "core.md"),
                                         "rb") as b:
            if a.read() != b.read():
                bad.append("ui-check/antislop/core.md differs from integrations/antislop/antislop.md")
        step("6 laid-out skills", code == 0 and not bad, "push exit %d; %s" % (code, "; ".join(bad) or "all four"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("vendor-to-integrations: %d of %d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
