#!/usr/bin/env python3
"""Stand of change layout-safety: broken state refused, foreign copy kept, backup retention.

Steps 1-3 run on temporary homes the stand creates and removes:
  1. install --agents claude, a truncated state.json, install: exit 1 `fail state:`, no file changed;
  2. a foreign ~/.claude/skills/ship/SKILL.md: install keeps it (exit 1, `foreign ...: kept`), the other skills
     are laid out; install --replace-foreign replaces it and the old text is in a backup;
  3. 25 backup run folders and an edited copy: sync.py push --force leaves 20, prints `pruned backups: 6`.
Step 4 reads this machine: `sync.py status` with the real home (read only), no `first` and no `fail`.
"""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
checks = []


def check(name, good, detail=""):
    checks.append(good)
    print(("ok   " if good else "FAIL ") + name + ("" if good or not detail else ": " + detail.strip()[-600:]))


def run(home, *args):
    p = subprocess.run([sys.executable, *args], cwd=ROOT, env=dict(os.environ, HOME=home, PYTHONPATH=ROOT),
                       capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)
    return p.returncode, p.stdout + p.stderr


def tree(home):
    found = {}
    for d, _, names in os.walk(home):
        for n in names:
            with open(os.path.join(d, n), "rb") as f:
                found[os.path.relpath(os.path.join(d, n), home)] = f.read()
    return found


def new_home(tmp, name):
    home = os.path.join(tmp, name)
    os.makedirs(os.path.join(home, ".claude"))
    return home


def main():
    tmp = tempfile.mkdtemp()
    try:
        home = new_home(tmp, "broken")
        code, out = run(home, "-m", "solo_sdd", "install", "--agents", "claude")
        check("1 install --agents claude", code == 0, out)
        with open(os.path.join(home, ".local/share/solo-sdd/state.json"), "w") as f:
            f.write('{"skills/ship/SKILL.md"')
        before = tree(home)
        code, out = run(home, "-m", "solo_sdd", "install")
        check("1 truncated state: exit 1, fail state:", code == 1 and "fail state: ~/.local/share/solo-sdd/state.json: " in out, out)
        check("1 no copy and no backup changed", tree(home) == before)

        home = new_home(tmp, "foreign")
        ship = os.path.join(home, ".claude/skills/ship/SKILL.md")
        os.makedirs(os.path.dirname(ship))
        with open(ship, "w") as f:
            f.write("another tool's ship\n")
        code, out = run(home, "-m", "solo_sdd", "install")
        with open(ship) as f:
            kept = f.read() == "another tool's ship\n"
        check("2 foreign ship kept, exit 1", code == 1 and kept
              and "foreign ~/.claude/skills/ship/SKILL.md: kept (install --replace-foreign replaces it)" in out, out)
        check("2 other skills laid out", os.path.exists(os.path.join(home, ".claude/skills/spec-next/SKILL.md")))
        code, out = run(home, "-m", "solo_sdd", "install", "--replace-foreign")
        with open(ship) as f, open(os.path.join(ROOT, "skills/ship/SKILL.md")) as g:
            replaced = f.read() == g.read()
        saved = [v for k, v in tree(os.path.join(home, ".local/share/solo-sdd/backup")).items()]
        check("2 --replace-foreign replaced, old text in a backup", code == 0 and replaced
              and b"another tool's ship\n" in saved, out)

        home = new_home(tmp, "retention")
        code, out = run(home, "-m", "solo_sdd", "install", "--agents", "claude")
        root = os.path.join(home, ".local/share/solo-sdd/backup")
        for n in range(1, 26):
            os.makedirs(os.path.join(root, f"20260101-000000-4242-{n}"))
        with open(os.path.join(home, ".claude/skills/spec-next/SKILL.md"), "a") as f:
            f.write("edited\n")
        code, out = run(home, "sync.py", "push", "--force")
        check("3 20 run folders left, pruned backups: 6", code == 0 and len(os.listdir(root)) == 20
              and "pruned backups: 6" in out, out)
    finally:
        shutil.rmtree(tmp)

    code, out = run(os.path.expanduser("~"), "sync.py", "status")
    kinds = [line.split()[0] for line in out.splitlines() if line.strip()]
    check("4 this machine: sync.py status without first or fail", code == 0 and "first" not in kinds
          and not any(k.startswith("fail") for k in kinds), out)
    print(f"{sum(checks)} of {len(checks)} checks passed")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
