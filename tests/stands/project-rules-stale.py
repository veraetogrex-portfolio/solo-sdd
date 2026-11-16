#!/usr/bin/env python3
"""Stand of change project-rules-stale: doctor names a project rules block left by an older solo-sdd.

A temporary home and git project only, removed at the end:
  1. init --yes, then doctor: `ok project-rules:`;
  2. an older block (one line replaced, its digest recorded): `warn project-rules:` naming solo-sdd init,
     AGENTS.md keeps its bytes;
  3. init again, then doctor: `ok project-rules:`;
  4. a line edited inside the block: `warn project-rules:` naming the edit and the rules path, not solo-sdd init;
  5. config set rules.scope global: no project-rules line.
"""
import hashlib, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from solo_sdd import rules_block  # noqa: E402

RULES = os.path.join(ROOT, "global", "AGENTS.md")
checks = []


def check(name, good, detail=""):
    checks.append(good)
    print(("ok   " if good else "FAIL ") + name + ("" if good or not detail else ": " + detail.strip()[-600:]))


def sdd(home, cwd, *args):
    env = dict(os.environ, HOME=home, PYTHONPATH=ROOT, GIT_CONFIG_NOSYSTEM="1")
    p = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=cwd, env=env, capture_output=True,
                       text=True, stdin=subprocess.DEVNULL, timeout=300)
    return p.returncode, p.stdout + p.stderr


def line(home, project):
    out = sdd(home, project, "doctor")[1]
    found = [l for l in out.splitlines() if " project-rules: " in l]
    return found[0] if len(found) == 1 else "%d lines: %s" % (len(found), out)


def read(path):
    with open(path, "rb") as f:
        return f.read()


with tempfile.TemporaryDirectory(prefix="project-rules-stale-") as tmp:
    home, project = os.path.join(tmp, "home"), os.path.join(tmp, "p")
    for d in (".claude", ".codex"):
        os.makedirs(os.path.join(home, d))
    subprocess.run(["git", "-c", "init.defaultBranch=main", "init", "-q", project], check=True,
                   stdin=subprocess.DEVNULL, env=dict(os.environ, HOME=home, GIT_CONFIG_NOSYSTEM="1"))
    agents = os.path.join(project, "AGENTS.md")
    code, out = sdd(home, project, "init", "--yes")
    check("init --yes exits 0", code == 0, out)
    got = line(home, project)
    check("1. after init: ok project-rules", got.startswith("ok project-rules: "), got)

    text = read(agents).decode()
    before, body, after = rules_block.parse(text)
    old = body.replace("\n", "\nan older rule line\n", 1)
    with open(agents, "w", encoding="utf-8", newline="") as f:
        f.write(before + rules_block.block(old) + after)
    with open(os.path.join(project, "solo-sdd/rules-block"), "w") as f:
        f.write(hashlib.sha256(old.encode()).hexdigest() + "\n")
    held = read(agents)
    got = line(home, project)
    check("2. older block: warn project-rules naming solo-sdd init",
          got.startswith("warn project-rules: ") and "solo-sdd init" in got, got)
    check("2. doctor keeps AGENTS.md byte for byte", read(agents) == held)

    code, out = sdd(home, project, "init")
    check("3. init refreshes the block", code == 0 and "updated the solo-sdd rules block" in out, out)
    got = line(home, project)
    check("3. after refresh: ok project-rules", got.startswith("ok project-rules: "), got)

    text = read(agents).decode().replace(rules_block.BEGIN + "\n", rules_block.BEGIN + "\nmy own line\n", 1)
    with open(agents, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    got = line(home, project)
    check("4. edited block: warn naming the edit and the rules path, not solo-sdd init",
          got.startswith("warn project-rules: ") and "edited in place" in got and RULES in got
          and "solo-sdd init" not in got, got)

    code, out = sdd(home, project, "config", "set", "rules.scope", "global")
    check("5. config set rules.scope global exits 0", code == 0, out)
    out = sdd(home, project, "doctor")[1]
    check("5. global scope: no project-rules line", " project-rules: " not in out, out)

fails = checks.count(False)
print("project-rules-stale: %d of %d checks passed" % (len(checks) - fails, len(checks)))
sys.exit(1 if fails else 0)
