#!/usr/bin/python3
"""Live scenario of change secret-sandbox-read, steps 1, 2, 4 and 5 (the Fallback), on a temporary HOME; no Claude Code session.

1. ~/.claude/settings.json with the sandbox on, a project with `.env` holding API_KEY=x.
2. `solo-sdd install --hooks`: permissions.deny holds Read(**/.env), `_hooks` records it, the sandbox key is unchanged,
   the output says the read deny is expected active (on macOS).
4. `solo-sdd uninstall`: settings.json is byte for byte as before step 2.
5. No sandbox key: `install --hooks` writes none and says the read deny needs the sandbox.
Step 3 (a sandboxed `cat .e{n,}v` in a session) is not run here: it needs a logged-in session in the temporary HOME.
Run from the repository root: python3 tests/stands/secret-sandbox-read.py. The temporary folder is removed; the last line is the summary."""
import json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
RULE = "Read(**/.env)"
ok = True


def step(name, good, detail):
    global ok
    ok &= good
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def call(env, *args):
    p = subprocess.run([PY, "-m", "solo_sdd", *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
                       stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def line(out):
    return next((x for x in out.splitlines() if x.startswith("sandbox read deny:")), None)


tmp = tempfile.mkdtemp(prefix="secret-sandbox-read-")
try:
    home, proj = os.path.join(tmp, "home"), os.path.join(tmp, "proj")
    os.makedirs(os.path.join(home, ".claude"))
    os.makedirs(proj)
    pathlib.Path(proj, ".env").write_text("API_KEY=x\n")
    env = dict(os.environ, HOME=home, PATH="/usr/bin:/bin")
    settings = os.path.join(home, ".claude", "settings.json")
    state = os.path.join(home, ".local", "share", "solo-sdd", "state.json")
    raw = json.dumps({"sandbox": {"enabled": True}}, indent=2).encode()
    pathlib.Path(settings).write_bytes(raw)
    step("1 sandbox on", True, "settings %s, project .env" % raw.decode().replace("\n", "").replace("  ", ""))

    code, out = call(env, "install", "--agents", "claude", "--hooks")
    s = json.load(open(settings))
    recorded = any(RULE in x.get("deny", []) for x in json.load(open(state)).get("_hooks", []))
    want = "expected active" if sys.platform == "darwin" else "not active"
    got = line(out)
    step("2 install --hooks", code == 0 and s.get("sandbox") == {"enabled": True} and s["permissions"]["deny"].count(RULE) == 1
         and recorded and got is not None and got.startswith("sandbox read deny: " + want),
         "exit %d, %s in deny and _hooks: %s, sandbox key %s, %s" % (code, RULE, recorded, s.get("sandbox"), got))

    code, out = call(env, "uninstall")
    same = os.path.exists(settings) and pathlib.Path(settings).read_bytes() == raw
    step("4 uninstall", code == 0 and same, "exit %d, settings as before step 2: %s" % (code, same))

    os.remove(settings)
    code, out = call(env, "install", "--agents", "claude", "--hooks")
    s = json.load(open(settings))
    got = line(out)
    step("5 no sandbox key", code == 0 and "sandbox" not in s and got is not None and "needs the sandbox" in got,
         "exit %d, sandbox key written: %s, %s" % (code, "sandbox" in s, got))
    call(env, "uninstall")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("3 not run: a sandboxed session needs a logged-in Claude Code in the temporary HOME")
print("SUMMARY: %s" % ("steps 1, 2, 4, 5 passed" if ok else "a step failed"))
sys.exit(0 if ok else 1)
