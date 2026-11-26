#!/usr/bin/python3
"""Live scenario of change guard-fails-closed, steps 1-3, against the base commit e262b7e.

1 `solo-sdd install --hooks` in a temporary HOME from the base tree and from this tree: the `guard` entry. 2 the
installed entry's command through `sh -c` with a `work_hooks.py` that does not compile. 3 a driver in the temporary
folder imports `work_hooks.py` of each tree, makes a check raise and feeds `main()`; the installed hook gets `[1]`.
Run from the repository root: python3 tests/stands/guard-fails-closed.py. The temporary folder is removed; the last line
is the summary."""
import io, json, os, pathlib, shutil, subprocess, sys, tarfile, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = "e262b7e"
PY = "/usr/bin/python3"
results = []

DRIVER = r'''
import importlib.util, io, json, sys
path, check, inp = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
spec = importlib.util.spec_from_file_location("work_hooks", path)
wh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wh)
def boom(*a, **k):
    raise RuntimeError("stand fault")
setattr(wh, check, boom)
sys.argv = [path, "guard"]
sys.stdin = io.StringIO(json.dumps(inp))
try:
    wh.main()
except SystemExit:
    pass
'''


def step(name, good, detail):
    results.append(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def call(args, env, cwd=ROOT, inp=None):
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=300, input=inp,
                       stdin=None if inp is not None else subprocess.DEVNULL)
    return p.returncode, p.stdout, p.stderr


def answer(out):
    """(decision, reason) of a hook answer, ("pass", "") for none."""
    if not out.strip():
        return "pass", ""
    o = json.loads(out)["hookSpecificOutput"]
    return o["permissionDecision"], o.get("permissionDecisionReason", "")


tmp = tempfile.mkdtemp(prefix="guard-fails-closed-")
try:
    base = os.path.join(tmp, "base")
    archive = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", BASE], capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as t:
        t.extractall(base)
    trees = {"base": base, "branch": str(ROOT)}
    homes, envs, entries = {}, {}, {}
    for name, tree in trees.items():
        home = homes[name] = os.path.join(tmp, "home-" + name)
        for d in (".claude", ".codex"):
            os.makedirs(os.path.join(home, d))
        env = envs[name] = {"HOME": home, "PATH": "/usr/bin:/bin"}
        code, out, err = call([PY, "-m", "solo_sdd", "install", "--hooks"], env, cwd=tree)
        if code:
            raise SystemExit("FAILED install --hooks from %s: exit %d\n%s" % (name, code, (out + err)[-600:]))
        with open(os.path.join(home, ".claude", "settings.json")) as f:
            s = json.load(f)
        entries[name] = [h for g in s["hooks"]["PreToolUse"] for h in g["hooks"] if h["command"].endswith('"$f" guard')]

    # 1: the guard entry
    b, n = entries["base"], entries["branch"]
    probe = '/usr/bin/python3 -c "" >/dev/null 2>&1 || exit 0; exec '
    good = (len(b) == 1 and "onFailure" not in b[0] and len(n) == 1 and n[0].get("onFailure") == "block"
            and n[0].get("timeout") == 10 and probe in n[0]["command"])
    step("1 guard entry", good, "base onFailure %s; branch onFailure %s, timeout %s, interpreter check %s"
         % (b[0].get("onFailure", "absent") if b else "no entry", n[0].get("onFailure") if n else None,
            n[0].get("timeout") if n else None, bool(n) and probe in n[0]["command"]))

    # 2: a work_hooks.py that does not compile, run by the entry's command
    hook = os.path.join(homes["branch"], ".claude", "hooks", "work_hooks.py")
    with open(hook) as f:
        kept = f.read()
    with open(hook, "w") as f:
        f.write(kept + "\n)(\n")
    read = json.dumps({"session_id": "stand", "cwd": homes["branch"], "tool_name": "Read", "tool_input": {"file_path": "README.md"}})
    code, out, err = call(["sh", "-c", n[0]["command"]], envs["branch"], inp=read)
    with open(hook, "w") as f:
        f.write(kept)
    step("2 broken work_hooks.py", code not in (0, 2), "exit %d (Claude Code refuses an exit other than 0 and 2 under onFailure block)" % code)

    # 3: a raising check through main(), and unreadable input through the installed hook
    driver = os.path.join(tmp, "driver.py")
    with open(driver, "w") as f:
        f.write(DRIVER)
    cases = (("guard_secrets_bash", {"tool_name": "Bash", "tool_input": {"command": "cat .env.local"}}),
             ("guard_models_agent", {"tool_name": "Agent", "tool_input": {"description": "Explore a", "prompt": "x"}}))
    seen = {}
    for name, tree in trees.items():
        for check, inp in cases:
            inp = dict({"session_id": "stand", "cwd": homes[name]}, **inp)
            code, out, err = call([PY, driver, os.path.join(tree, "global", "work_hooks.py"), check, json.dumps(inp)], envs[name], cwd=tmp)
            seen[name, check] = answer(out) if code == 0 else ("exit %d" % code, err[-200:])
        installed = os.path.join(homes[name], ".claude", "hooks", "work_hooks.py")
        code, out, err = call([PY, installed, "guard"], envs[name], cwd=tmp, inp="[1]")
        seen[name, "input"] = answer(out) if code == 0 else ("exit %d" % code, err[-200:])
    nb, na, ni = seen["branch", "guard_secrets_bash"], seen["branch", "guard_models_agent"], seen["branch", "input"]
    good = (nb[0] == "deny" and "`guard_secrets_bash`" in nb[1] and "errors.log" in nb[1] and na == ("pass", "")
            and ni[0] == "deny" and "`guard input`" in ni[1]
            and all(seen["base", k] == ("pass", "") for k in ("guard_secrets_bash", "guard_models_agent", "input")))
    step("3 raising checks", good, "branch: secret check %s, agent check %s, [1] on stdin %s; base: %s, %s, %s"
         % (nb[0], na[0], ni[0], seen["base", "guard_secrets_bash"][0], seen["base", "guard_models_agent"][0], seen["base", "input"][0]))
finally:
    shutil.rmtree(tmp, True)

print("guard-fails-closed: %d of %d steps ok" % (sum(results), len(results)))
sys.exit(0 if results and all(results) else 1)
