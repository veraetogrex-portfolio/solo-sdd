#!/usr/bin/python3
"""Readiness of the security-pass stand, without models: steps 1 and 2 of its Live Scenario and the planted places.

Step 1: tests/test_vendor_security_audit.py passes, an edited file of a temporary copy is named. Step 2: sync.py push
into a temporary HOME puts METHOD.md into <root>/spec-audit/security/ of the three roots, with no SKILL.md under it and
no security-audit skill. The stand: bad/notes.py has the three planted places and bad/bin/check-archive is a binary without source, good/notes.py none of them, the change in
analyze/ has no rule on who may delete. Temporary folders are removed at the end. The last line is the summary.
"""
import os, re, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STAND = os.path.join(REPO, "tests", "stands", "security-pass")
sys.path.insert(0, os.path.join(REPO, "tests"))
from test_vendor_security_audit import VENDOR, changed_files  # noqa: E402

checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else "\n" + detail))


def run(cmd, env=None):
    p = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


tmp = tempfile.mkdtemp(prefix="security-pass-")
try:
    code, out = run([sys.executable, "tests/test_vendor_security_audit.py"])
    check("step 1: test_vendor_security_audit.py passes", code == 0, out)
    shutil.copytree(os.path.join(REPO, VENDOR), os.path.join(tmp, VENDOR))
    with open(os.path.join(tmp, VENDOR, "skills", "security-audit", "ATTACK-CLASSES.md"), "a") as f:
        f.write("\nedited\n")
    got = changed_files(tmp)
    check("step 1: an edited file is named: " + "; ".join(got),
          got == ["skills/security-audit/ATTACK-CLASSES.md: hash differs from VERSION"])

    home = os.path.join(tmp, "home")
    os.makedirs(home)
    code, out = run([sys.executable, "sync.py", "push"], env=dict(os.environ, HOME=home))
    check("step 2: sync.py push into a temporary HOME", code == 0, out)
    for root in (".claude/skills", ".codex/skills", ".agents/skills"):
        sec = os.path.join(home, root, "spec-audit", "security")
        nested = [n for _, _, ns in os.walk(sec) for n in ns if n == "SKILL.md"]
        check("step 2: %s/spec-audit/security/METHOD.md, %d files, no SKILL.md under it, no security-audit skill"
              % (root, len(os.listdir(sec)) if os.path.isdir(sec) else 0),
              os.path.isfile(os.path.join(sec, "METHOD.md")) and not nested
              and not os.path.exists(os.path.join(home, root, "security-audit")))

    with open(os.path.join(STAND, "bad", "notes.py")) as f:
        bad = f.read().splitlines()
    with open(os.path.join(STAND, "good", "notes.py")) as f:
        good = f.read()
    planted = {12: "os.path.join(NOTES_DIR, name)", 18: "shell=True", 23: "[CHECKER, archive]",
               26: 'filter="fully_trusted"'}
    check("stand: bad/notes.py planted at lines 12, 18, 23-26", all(s in bad[n - 1] for n, s in planted.items()))
    checker = os.path.join(STAND, "bad", "bin", "check-archive")
    check("stand: bad/bin/check-archive is an executable binary without source in bad/",
          os.access(checker, os.X_OK) and not any(n.endswith(".c") for _, _, ns in os.walk(os.path.join(STAND, "bad"))
                                                    for n in ns))
    check("stand: good/notes.py has containment, no shell, a tar filter",
          "commonpath" in good and "subprocess" not in good and 'filter="data"' in good)
    with open(os.path.join(STAND, "analyze", "openspec", "changes", "add-project-delete", "specs", "projects",
                           "spec.md")) as f:
        delta = f.read()
    check("stand: add-project-delete adds DELETE /projects/{id} with no rule on who may delete",
          "DELETE /projects/{id}" in delta and not re.search(r"owner|authori|403|who may", delta, re.I))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("%d of %d checks passed" % (sum(checks), len(checks)))
sys.exit(0 if all(checks) else 1)
