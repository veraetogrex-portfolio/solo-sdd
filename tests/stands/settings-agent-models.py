#!/usr/bin/python3
"""Live scenario of change settings-agent-models, steps 2-5, on the real guard hook.

The hook (global/work_hooks.py) and its model-policy.json are laid out into a temporary HOME as ~/.claude/hooks/ and run
as Claude Code runs them, on /usr/bin/python3, with PreToolUse Agent events from a temporary git project:
2. `Lookup: find the limit` on sonnet through Explore with `agents.lookup-model: sonnet`: deny naming the key and cheap.
3. The same event with no project key: allowed.
4. `Orchestrator a` on sonnet with `agents.orchestrator-model: sonnet`: deny naming the key and main;
   `Review: a` on fable with `agents.review-model: fable`: allowed.
5. A broken solo-sdd/config line and `Orchestrator a` on sonnet: allowed, a line in the temporary HOME's errors.log.
Run from the repository root: python3 tests/stands/settings-agent-models.py. The temporary folder is removed; the last
line is the summary."""
import json, os, pathlib, shutil, subprocess, sys, tempfile

GLOBAL = pathlib.Path(__file__).resolve().parents[2] / "global"


def guard(hook, env, cwd, desc, model, stype=None, agent_id=None):
    """The permission decision and its reason for one Agent launch: ("allow", "") when the hook prints nothing."""
    ti = {"description": desc, "prompt": "x", "model": model}
    if stype:
        ti["subagent_type"] = stype
    inp = {"session_id": "S1", "cwd": cwd, "hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": ti}
    if agent_id:
        inp["agent_id"] = agent_id
    p = subprocess.run(["/usr/bin/python3", hook, "guard"], input=json.dumps(inp), capture_output=True, text=True,
                       env=env, timeout=60)
    if p.returncode or not p.stdout.strip():
        return ("allow" if p.returncode == 0 else "exit %d" % p.returncode), p.stderr.strip()
    out = json.loads(p.stdout)["hookSpecificOutput"]
    return out["permissionDecision"], out["permissionDecisionReason"]


with tempfile.TemporaryDirectory() as t:
    t = os.path.realpath(t)
    home, proj = os.path.join(t, "home"), os.path.join(t, "proj")
    hooks = os.path.join(home, ".claude", "hooks")
    os.makedirs(hooks)
    for name in ("work_hooks.py", "model-policy.json"):
        shutil.copy(GLOBAL / name, os.path.join(hooks, name))
    hook = os.path.join(hooks, "work_hooks.py")
    env = {k: v for k, v in os.environ.items() if k not in ("SOLO_SDD_EXPENSIVE_OK", "CLAUDE_PROJECT_DIR")}
    env["HOME"] = home
    os.makedirs(os.path.join(proj, "solo-sdd"))
    subprocess.run(["git", "init", "-q"], cwd=proj, check=True, stdin=subprocess.DEVNULL, timeout=60)
    config = pathlib.Path(proj, "solo-sdd", "config")
    log = pathlib.Path(home, ".claude", "hook-state", "errors.log")
    checks = []

    config.write_text("agents.lookup-model: sonnet\n")
    d, r = guard(hook, env, proj, "Lookup: find the limit", "sonnet", "Explore", "a1")
    checks.append(("2 lookup on sonnet set by the project: deny", d == "deny" and "agents.lookup-model" in r
                   and "list cheap" in r, r))

    config.unlink()
    d, r = guard(hook, env, proj, "Lookup: find the limit", "sonnet", "Explore", "a1")
    checks.append(("3 the same with no project key: allowed", d == "allow", r))

    config.write_text("agents.orchestrator-model: sonnet\nagents.review-model: fable\n")
    d, r = guard(hook, env, proj, "Orchestrator a", "sonnet")
    checks.append(("4 orchestrator on sonnet set by the project: deny", d == "deny"
                   and "agents.orchestrator-model" in r and "list main" in r, r))
    d, r = guard(hook, env, proj, "Review: a", "fable", agent_id="a1")
    checks.append(("4 reviewer on fable set by the project: allowed", d == "allow", r))

    config.write_text("agents.orchestrator-model sonnet\n")
    d, r = guard(hook, env, proj, "Orchestrator a", "sonnet")
    logged = log.read_text() if log.exists() else ""
    checks.append(("5 broken config: allowed by the role rules, errors.log names the line",
                   d == "allow" and "solo-sdd/config:1" in logged, r or logged.strip()))

    for step, good, why in checks:
        print("%s %s%s" % ("ok    " if good else "FAILED", step, "" if good else ": " + why))
    passed = sum(g for _, g, _ in checks)
    print("settings-agent-models: %d of %d checks passed" % (passed, len(checks)))
sys.exit(0 if passed == len(checks) else 1)
