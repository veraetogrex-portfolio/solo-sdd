#!/usr/bin/python3
"""Live scenario of change subagent-check-roles, steps 2-5, on the real guard hook.

The hook (global/work_hooks.py) and its model-policy.json are laid out into a temporary HOME as ~/.claude/hooks/ and run
as Claude Code runs them, on /usr/bin/python3, with PreToolUse events from a temporary git project:
2. From a subagent: `Analyze: a` without model and `Check: a` on opus allowed, `Judge: a` on haiku denied naming main,
   `Attack: a 4 4a` on haiku through general-purpose allowed, `Attack: a` without model or on opus denied naming a cheap
   model set explicitly, `Implement: a` denied naming the six allowed tags.
3. `agents.attack-model: sonnet` and `Attack: a` on sonnet: deny naming the key and cheap;
   `agents.review-model: fable` and `Judge: a` on fable: allowed.
4. A transcript with an edit of src/app.py, then Analyze:, Attack:, Judge: and Check: agents: `solo-sdd archive a --yes`
   denied naming src/app.py; with a `Review: a` agent appended: allowed.
Run from the repository root: python3 tests/stands/subagent-check-roles.py. The temporary folder is removed; the last
line is the summary."""
import json, os, pathlib, shutil, subprocess, sys, tempfile

GLOBAL = pathlib.Path(__file__).resolve().parents[2] / "global"
SIX = ("Review:", "Lookup:", "Analyze:", "Attack:", "Judge:", "Check:")


def run(hook, env, inp):
    """The permission decision and its reason for one PreToolUse event: ("allow", "") when the hook prints nothing."""
    inp = dict({"session_id": "S1", "hook_event_name": "PreToolUse"}, **inp)
    p = subprocess.run(["/usr/bin/python3", hook, "guard"], input=json.dumps(inp), capture_output=True, text=True,
                       env=env, timeout=60)
    if p.returncode or not p.stdout.strip():
        return ("allow" if p.returncode == 0 else "exit %d" % p.returncode), p.stderr.strip()
    out = json.loads(p.stdout)["hookSpecificOutput"]
    return out["permissionDecision"], out["permissionDecisionReason"]


def agent(hook, env, cwd, desc, model=None, stype=None, agent_id="a1"):
    ti = {"description": desc, "prompt": "x"}
    if model:
        ti["model"] = model
    if stype:
        ti["subagent_type"] = stype
    inp = {"cwd": cwd, "tool_name": "Agent", "tool_input": ti}
    if agent_id:
        inp["agent_id"] = agent_id
    return run(hook, env, inp)


def tool(name, **ti):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": ti}]}}


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
    os.makedirs(os.path.join(proj, "solo-sdd", "changes", "a"))
    os.makedirs(os.path.join(proj, "src"))
    pathlib.Path(proj, "src", "app.py").write_text("x = 1\n")
    pathlib.Path(proj, "solo-sdd", "changes", "a", "tasks.md").write_text("- [x] one\n")
    subprocess.run(["git", "init", "-q"], cwd=proj, check=True, stdin=subprocess.DEVNULL, timeout=60)
    config = pathlib.Path(proj, "solo-sdd", "config")
    checks = []

    step2 = [("Analyze: a without model", agent(hook, env, proj, "Analyze: a"), lambda d, r: d == "allow"),
             ("Check: a on opus", agent(hook, env, proj, "Check: a", "opus"), lambda d, r: d == "allow"),
             ("Judge: a on haiku", agent(hook, env, proj, "Judge: a", "haiku"),
              lambda d, r: d == "deny" and "opus, fable" in r),
             ("Attack: a 4 4a on haiku", agent(hook, env, proj, "Attack: a 4 4a", "haiku", "general-purpose"),
              lambda d, r: d == "allow"),
             ("Attack: a without model", agent(hook, env, proj, "Attack: a"),
              lambda d, r: d == "deny" and "cheap model set explicitly" in r),
             ("Attack: a on opus", agent(hook, env, proj, "Attack: a", "opus"),
              lambda d, r: d == "deny" and "cheap model set explicitly" in r),
             ("Implement: a", agent(hook, env, proj, "Implement: a", "sonnet"),
              lambda d, r: d == "deny" and all(tag in r for tag in SIX))]
    bad = ["%s -> %s %s" % (name, d, r) for name, (d, r), good in step2 if not good(d, r)]
    checks.append(("2 the four roles from a subagent", not bad, "; ".join(bad)))

    config.write_text("agents.attack-model: sonnet\n")
    d, r = agent(hook, env, proj, "Attack: a", "sonnet")
    checks.append(("3 attacker on sonnet set by the project: deny", d == "deny" and "agents.attack-model" in r
                   and "list cheap" in r, r))
    config.write_text("agents.review-model: fable\n")
    d, r = agent(hook, env, proj, "Judge: a", "fable")
    checks.append(("3 judge on fable set by the project: allowed", d == "allow", r))
    config.unlink()

    lines = [tool("Edit", file_path=os.path.join(proj, "src", "app.py"))]
    lines += [tool("Agent", description=desc, prompt="x") for desc in ("Analyze: a", "Attack: a 1", "Judge: a", "Check: a")]
    archive = {"cwd": proj, "tool_name": "Bash", "tool_input": {"command": "solo-sdd archive a --yes"}}
    transcript = pathlib.Path(t, "session.jsonl")
    transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))
    d1, r1 = run(hook, env, dict(archive, transcript_path=str(transcript)))
    transcript.write_text("".join(json.dumps(line) + "\n" for line in lines + [tool("Agent", description="Review: a", prompt="x")]))
    d2, r2 = run(hook, env, dict(archive, transcript_path=str(transcript)))
    checks.append(("4 archive after only outside checks: deny naming src/app.py, after a Review: agent: allowed",
                   d1 == "deny" and "src/app.py" in r1 and d2 == "allow", "%s %s / %s %s" % (d1, r1, d2, r2)))

    for step, good, why in checks:
        print("%s %s%s" % ("ok    " if good else "FAILED", step, "" if good else ": " + why))
    passed = sum(g for _, g, _ in checks)
    print("subagent-check-roles: %d of %d checks passed" % (passed, len(checks)))
sys.exit(0 if passed == len(checks) else 1)
