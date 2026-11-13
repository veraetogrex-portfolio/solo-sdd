#!/usr/bin/python3
"""Live scenario of change hook-tool-names: the browser signs of the deployed model-policy.json.

In a temporary HOME: `sync.py push` deploys the hooks; the deployed policy copy gets an extra browser prefix and loses
`--remote-debugging-port` from `browser.bash`; the deployed `work_hooks.py stop` runs on sessions with an interface edit;
then `browser` set to a number, a policy file that does not parse, and an edited `cheap` kept by `sync.py push` as drift.
Run from the repository root: python3 tests/stands/hook-tool-names.py. The temporary folder is removed; the last line is
the summary."""
import json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
UI = "The interface changed"
results = []


def step(name, good, detail):
    results.append(bool(good))
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def run(env, *args, inp=None, cwd=ROOT):
    p = subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True, timeout=300, input=inp,
                       stdin=None if inp is not None else subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


tmp = os.path.realpath(tempfile.mkdtemp(prefix="hook-tool-names-"))
try:
    home = os.path.join(tmp, "home")
    for d in (".claude", ".codex"):
        os.makedirs(os.path.join(home, d))
    env = dict(os.environ, HOME=home)
    env.pop("SOLO_SDD_EXPENSIVE_OK", None)
    hook = os.path.join(home, ".claude/hooks/work_hooks.py")
    pol = os.path.join(home, ".claude/hooks/model-policy.json")
    elog = os.path.join(home, ".claude/hook-state/errors.log")

    code, out = run(env, PY, "sync.py", "push")
    if code != 0 or not os.path.exists(hook) or not os.path.exists(pol):
        raise SystemExit("FAILED sync.py push: exit %d\n%s" % (code, out[-800:]))

    repo = os.path.join(home, "proj")
    os.makedirs(repo)
    css = os.path.join(repo, "app.css")
    open(css, "w").write("a{}\n")
    git = ["git", "-C", repo, "-c", "user.email=t@t", "-c", "user.name=t"]
    for a in (["init", "-q"], ["add", "app.css"], ["commit", "-qm", "init"]):
        subprocess.run(git + a, check=True, capture_output=True)
    open(css, "w").write("a{color:red}\n")
    n = [0]

    def stop(main_tools=(), sub_tools=()):
        """The deployed stop hook's reason for a session that edited app.css and called the given tools."""
        n[0] += 1
        tr = os.path.join(tmp, "s%d.jsonl" % n[0])

        def line(name, ti):
            return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": ti}]}}) + "\n"
        open(tr, "w").write(line("Edit", {"file_path": css}) + "".join(line(*t) for t in main_tools))
        if sub_tools:
            os.makedirs(os.path.join(tmp, "s%d" % n[0], "subagents"))
            open(os.path.join(tmp, "s%d" % n[0], "subagents", "agent-a.jsonl"), "w").write("".join(line(*t) for t in sub_tools))
        code, out = run(env, PY, hook, "stop", inp=json.dumps({"session_id": "stand%d" % n[0], "cwd": repo,
                        "transcript_path": tr, "last_assistant_message": "Done."}), cwd=repo)
        return json.loads(out).get("reason", "") if code == 0 and out.strip() else "exit %d %s" % (code, out[-300:])

    def seen(r):
        return "interface-check reason %s, uncommitted-edits reason %s" % (UI in r, "uncommitted" in r)

    def log():
        text = open(elog).read() if os.path.exists(elog) else ""
        if os.path.exists(elog):
            os.remove(elog)
        return text.strip()

    MY = ("mcp__mybrowser__open", {})
    CDP = ("Bash", {"command": "curl -s localhost:9222/json/list --remote-debugging-port"})
    HEADLESS = ("Bash", {"command": "chromium --headless --screenshot app.html"})

    # 1: no browser at all: the check is on
    r = stop()
    step("1 control: an interface edit without a browser", UI in r and "uncommitted" in r, seen(r))

    # 2: the deployed copy adds a prefix and drops a built-in Bash sign
    shipped = open(pol).read()
    doc = json.loads(shipped)
    doc["browser"]["tools"].append("mcp__mybrowser__")
    doc["browser"]["bash"].remove("--remote-debugging-port")
    edited = json.dumps(doc, indent=2)
    open(pol, "w").write(edited)
    r1, r2 = stop(sub_tools=[MY]), stop(main_tools=[CDP])
    step("2 another browser tool in a subagent", UI not in r1 and "uncommitted" in r1, seen(r1))
    step("3 a built-in sign removed from the copy still counts", UI not in r2 and "uncommitted" in r2 and not log(), seen(r2))

    # 3: browser holds a number: only the built-in signs
    open(pol, "w").write(json.dumps(dict(doc, browser=42)))
    r1, r2 = stop(main_tools=[HEADLESS]), stop(sub_tools=[MY])
    text = log()
    lines = text.splitlines()
    step("4 a broken key: built-in signs only, one log line per run", UI not in r1 and UI in r2 and len(lines) == 2
         and all(l.split()[2] == "browser" for l in lines), "headless counted %s, mybrowser counted %s, errors.log %r"
         % (UI not in r1, UI not in r2, lines))

    # 4: a policy file that does not parse
    open(pol, "w").write(edited[: len(edited) // 2])
    r = stop()
    text = log()
    step("5 a policy file that does not parse", UI in r and "model-policy.json" in text, "%s; errors.log %r" % (seen(r), text[:160]))

    # 5: an edited model list is kept by sync.py push as drift
    doc["cheap"].append("my-cheap-model")
    mine = json.dumps(doc, indent=2)
    open(pol, "w").write(mine)
    code, out = run(env, PY, "sync.py", "push")
    push_line = [l for l in out.splitlines() if "model-policy.json" in l]
    code2, st = run(env, PY, "sync.py", "status")
    st_line = [l for l in st.splitlines() if "model-policy.json" in l]
    kept = open(pol).read() == mine
    step("6 an edited copy is kept as drift", kept and st_line and st_line[0].split()[0] == "drift",
         "kept %s; push: %s; status: %s" % (kept, " ".join((push_line or ["-"])[0].split()), " ".join((st_line or ["-"])[0].split())))
finally:
    shutil.rmtree(tmp, True)

print("SUMMARY: all steps passed" if all(results) else "SUMMARY: %d of %d steps passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
