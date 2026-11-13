#!/usr/bin/python3
"""Live scenario of change secret-guard, steps 1-5, on a temporary HOME and a project with `.env` holding API_KEY=x.

1. `solo-sdd install --hooks`: settings.json has the guard matcher with Read and Grep and permissions.deny Read(**/.env).
2-4. The installed guard hook refuses or passes each tool call and Bash command of the scenario.
5. `solo-sdd uninstall`: the deny entry is gone, an entry added by hand stays.
Run from the repository root: python3 tests/stands/secret-guard.py. The temporary folder is removed; the last line is the summary."""
import json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
ok = True


def step(name, good, detail):
    global ok
    ok &= good
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def call(env, *args, inp=None):
    p = subprocess.run(list(args), cwd=ROOT, env=env, capture_output=True, text=True, timeout=300, input=inp,
                       stdin=None if inp is not None else subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


tmp = tempfile.mkdtemp(prefix="secret-guard-")
try:
    home, proj = os.path.join(tmp, "home"), os.path.join(tmp, "proj")
    for d in (".claude", ".codex"):
        os.makedirs(os.path.join(home, d))
    os.makedirs(proj)
    pathlib.Path(proj, ".env").write_text("API_KEY=x\n")
    env = dict(os.environ, HOME=home, PATH="/usr/bin:/bin")
    settings = os.path.join(home, ".claude", "settings.json")

    code, out = call(env, PY, "-m", "solo_sdd", "install", "--hooks")
    s = json.load(open(settings)) if os.path.exists(settings) else {}
    guard = [g["matcher"] for g in s.get("hooks", {}).get("PreToolUse", []) if g["hooks"][0]["command"].endswith('"$f" guard')]
    deny = s.get("permissions", {}).get("deny", [])
    step("1 install --hooks", code == 0 and guard and {"Read", "Grep"} <= set(guard[0].split("|")) and "Read(**/.env)" in deny,
         "exit %d, guard matcher %s, Read(**/.env) in deny: %s" % (code, guard, "Read(**/.env)" in deny))

    hook = os.path.join(home, ".claude", "hooks", "work_hooks.py")

    def refused(tool, ti):
        c, o = call(env, PY, hook, "guard", inp=json.dumps({"session_id": "stand", "cwd": proj, "tool_name": tool, "tool_input": ti}))
        return c == 0 and '"deny"' in o

    cases = [("2 Read .env", "Read", {"file_path": os.path.join(proj, ".env")}, True),
             ("2 Grep path .env", "Grep", {"pattern": "KEY", "path": ".env"}, True),
             ("2 Grep glob .env*", "Grep", {"pattern": "KEY", "glob": ".env*"}, True),
             ("2 Read .env.example", "Read", {"file_path": os.path.join(proj, ".env.example")}, False)]
    for c in ("python3 -c \"print(open('.env').read())\"", "cp .env /tmp/e", "source .env && echo ok", "git diff .env",
              "while read l; do echo $l; done < .env", "set | grep -i api", 'echo "$OPENAI_API_KEY"', "echo $apiKey"):
        cases.append(("3 " + c, "Bash", {"command": c}, True))
    for c in ("test -f .env", "grep -c '^API_KEY=.' .env", "echo 'API_KEY=' >> .env", "cat .env.example", "echo $MONKEY_NAME"):
        cases.append(("4 " + c, "Bash", {"command": c}, False))
    bad = [n for n, tool, ti, want in cases if refused(tool, ti) != want]
    step("2-4 guard", os.path.exists(hook) and not bad, "%d of %d calls as expected%s" % (len(cases) - len(bad), len(cases),
                                                                                      "; wrong: " + ", ".join(bad) if bad else ""))

    s = json.load(open(settings))
    s["permissions"]["deny"].append("Read(./mine/**)")
    json.dump(s, open(settings, "w"))
    code, out = call(env, PY, "-m", "solo_sdd", "uninstall")
    left = json.load(open(settings)).get("permissions", {}).get("deny") if os.path.exists(settings) else None
    step("5 uninstall", code == 0 and left == ["Read(./mine/**)"], "exit %d, deny left: %s" % (code, left))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY: %s" % ("all steps passed" if ok else "a step failed"))
sys.exit(0 if ok else 1)
