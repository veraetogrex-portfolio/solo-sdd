#!/usr/bin/python3
"""Live scenario of change integration-skills, steps 1-5: the skill of the fictional owner integration dup-scan laid
out by `solo-sdd install --agents claude,codex` into every skill root, its `integration:dup-scan` status rows, an
edited copy kept as drift, the taken name `ship` refused, and the copies removed when the folder is deleted, on a
temporary HOME. Step 6 of the scenario (the whole suite) is the suite command itself, not run here.
Run from the repository root: python3 tests/stands/integration-skills.py. The temporary folder is removed; the last
line is the summary."""
import os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
ROOTS = (".claude/skills", ".codex/skills", ".agents/skills")
SKILL = "---\nname: dup-scan-review\ndescription: Use when reviewing duplicate code.\n---\nLook for repeated blocks.\n"
passed, total = 0, 0


def step(name, good, detail):
    global passed, total
    total += 1
    passed += bool(good)
    print("%s %s: %s" % ("ok" if good else "FAIL", name, str(detail).strip().replace("\n", " | ")[:300]))


def main():
    tmp = tempfile.mkdtemp(prefix="integration-skills-")
    try:
        home = os.path.join(tmp, "home")
        for d in (".claude", ".codex"):
            os.makedirs(os.path.join(home, d))
        env = {"PATH": "/usr/bin:/bin", "HOME": home, "LANG": "C.UTF-8", "PYTHONPATH": str(ROOT)}
        owner = os.path.join(home, ".local/share/solo-sdd/integrations/dup-scan")

        def put(path, text):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

        def read(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                return None

        def sdd(*args):
            p = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=tmp, env=env, capture_output=True,
                               text=True, timeout=120, stdin=subprocess.DEVNULL)
            return p.returncode, p.stdout + p.stderr

        def copy(root, skill="dup-scan-review"):
            return os.path.join(home, root, skill, "SKILL.md")

        put(os.path.join(owner, "integration"), "name: dup-scan\nabout: finds duplicate code\npoints: checks\ncommand: true\n")
        put(os.path.join(owner, "skills/dup-scan-review/SKILL.md"), SKILL)
        code, out = sdd("install", "--agents", "claude,codex")
        laid = [r for r in ROOTS if read(copy(r)) == SKILL]
        step("1 install lays the skill out", code == 0 and len(laid) == 3, "code %d; in %s" % (code, ", ".join(laid)))

        code, out = sdd("status")
        rows = [line.split() for line in out.splitlines() if "integration:dup-scan" in line]
        step("2 status rows", len(rows) == 3 and all(r[0] == "ok" for r in rows),
             "; ".join(" ".join(r) for r in rows) or out)

        ship = {r: read(copy(r, "ship")) for r in ROOTS}
        put(copy(".claude/skills"), SKILL + "my own line\n")
        code, out = sdd("update")
        _, status = sdd("status")
        drift = [line for line in status.splitlines() if line.split()[:1] == ["drift"] and "integration:dup-scan" in line]
        step("3 an edited copy is drift", read(copy(".claude/skills")).endswith("my own line\n") and len(drift) == 1,
             "kept: %s; %s" % (read(copy(".claude/skills")).endswith("my own line\n"), drift))

        put(os.path.join(owner, "skills/ship/SKILL.md"), "an integration's ship\n")
        code, out = sdd("update")
        named = [line for line in out.splitlines() if "taken by solo-sdd" in line]
        same = all(read(copy(r, "ship")) == ship[r] for r in ROOTS)
        step("4 ship is taken by solo-sdd", named and same, "%s; solo-sdd ship copies unchanged: %s" % (named, same))

        def raw(path):
            try:
                with open(path, "rb") as f:
                    return f.read()
            except FileNotFoundError:
                return None

        before = {}  # the agents' copies only: an interpreter may cache bytecode under ~/Library
        for top in (".claude", ".codex", ".agents"):
            for d, _, files in os.walk(os.path.join(home, top)):
                for f in files:
                    p = os.path.join(d, f)
                    if "dup-scan-review" not in p:
                        before[p] = raw(p)
        shutil.rmtree(owner)
        code, out = sdd("update")
        removed = [line for line in out.splitlines() if line.startswith("removed") and "dup-scan-review" in line]
        gone = all(read(copy(r)) is None for r in (".codex/skills", ".agents/skills"))
        kept = (read(copy(".claude/skills")) or "").endswith("my own line\n") and "drift" in out
        after = {p: raw(p) for p in before}
        step("5 the folder deleted", len(removed) == 2 and gone and kept and after == before,
             "removed: %s; kept as drift: %s; other copies unchanged: %s" % (removed, kept, after == before))
    finally:
        shutil.rmtree(tmp, True)
    print("integration-skills: %d of %d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
