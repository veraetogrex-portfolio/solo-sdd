#!/usr/bin/python3
"""Live scenario of change hook-failure-signal, steps 1-4.

1-3 on a temporary HOME after `solo-sdd install --hooks`: a truncated model policy, the test model allowlist, the
errors.log trim. 4 runs `solo-sdd doctor` on this machine's HOME (read only) and shows its hook errors line.
Run from the repository root: python3 tests/stands/hook-failure-signal.py. The temporary folder is removed; the last
line is the summary."""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
results = []


def step(name, good, detail):
    results.append(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def call(env, *args, inp=None):
    p = subprocess.run(list(args), cwd=ROOT, env=env, capture_output=True, text=True, timeout=300, input=inp,
                       stdin=None if inp is not None else subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


tmp = tempfile.mkdtemp(prefix="hook-failure-signal-")
try:
    home = os.path.join(tmp, "home")
    for d in (".claude", ".codex"):
        os.makedirs(os.path.join(home, d))
    env = dict(os.environ, HOME=home, PATH="/usr/bin:/bin")
    env.pop("SOLO_SDD_EXPENSIVE_OK", None)
    hook = os.path.join(home, ".claude/hooks/work_hooks.py")
    pol = os.path.join(home, ".claude/hooks/model-policy.json")
    elog = os.path.join(home, ".claude/hook-state/errors.log")

    def hook_run(name, inp):
        code, out = call(env, PY, hook, name, inp=json.dumps(dict({"session_id": "stand", "cwd": home}, **inp)))
        return json.loads(out)["hookSpecificOutput"] if code == 0 and out.strip() else {}

    def guard(command):
        return hook_run("guard", {"tool_name": "Bash", "tool_input": {"command": command}})

    code, out = call(env, PY, "-m", "solo_sdd", "install", "--hooks")
    installed = code == 0 and os.path.exists(hook) and os.path.exists(pol)
    if not installed:
        raise SystemExit("FAILED install --hooks: exit %d\n%s" % (code, out[-600:]))

    # 1: a truncated policy
    text = open(pol).read()
    open(pol, "w").write(text[:len(text) // 2])
    # from a session folder outside the temporary roots (the real home), where ../wt is not temporary
    wt = hook_run("guard", {"tool_name": "Bash", "tool_input": {"command": "git worktree add ../wt"}, "cwd": os.path.expanduser("~")})
    refused = wt.get("permissionDecision") == "deny"
    log = open(elog).read() if os.path.exists(elog) else ""
    dcode, dout = call(env, PY, "-m", "solo_sdd", "doctor")
    prow = [l for l in dout.splitlines() if l.startswith("fail model policy:")]
    ctx = hook_run("context", {}).get("additionalContext", "")
    good = refused and "model-policy.json" in log and prow and dcode == 1 and "hook errors: 1 in the last 7 days" in ctx
    step("1 broken policy", bool(good), "worktree refused %s, policy line in errors.log %s, doctor exit %d %s, context %r"
         % (refused, "model-policy.json" in log, dcode, (prow or ["no fail model policy row"])[0][:90],
            re.findall(r"hook errors: \d+ in the last 7 days", ctx)))

    # 2: a valid policy, the --model allowlist
    open(pol, "w").write(text)
    cheap = json.loads(text)["cheap"]
    r = guard("pytest --model gpt-9-ultra")
    ultra = r.get("permissionDecision") == "deny" and all(c in r.get("permissionDecisionReason", "") for c in cheap)
    cheap_ok = not guard("pytest --model=gpt-6-%s" % cheap[0])
    marker_ok = not guard("python3 -m pytest -m slow tests")
    step("2 test model allowlist", ultra and cheap_ok and marker_ok,
         "gpt-9-ultra refused naming %s: %s; --model=gpt-6-%s passes: %s; python3 -m pytest -m slow passes: %s"
         % (", ".join(cheap), ultra, cheap[0], cheap_ok, marker_ok))

    # 3: the trim at SessionEnd
    lines = ["2026-11-11T00:00:00 stand line %d" % i for i in range(1500)]
    open(elog, "w").write("".join(l + "\n" for l in lines))
    hook_run("end", {})
    left = open(elog).read().splitlines()
    step("3 errors.log trim", left == lines[500:], "%d lines left, first %r" % (len(left), left[0] if left else None))
finally:
    shutil.rmtree(tmp, True)

# 4: this machine, read only
code, out = call(dict(os.environ), PY, "-m", "solo_sdd", "doctor")
row = [l for l in out.splitlines() if re.match(r"(ok|warn) hook errors: ", l)]
step("4 doctor on this machine", len(row) == 1, (row or ["no hook errors row"])[0][:200])

print("hook-failure-signal stand: %d of %d steps passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
