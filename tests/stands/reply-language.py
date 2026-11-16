#!/usr/bin/python3
"""Live scenario of change reply-language-requests: the laid-out reply language checks of a temporary home.

In a temporary HOME: `sync.py push` lays the repository out and `solo-sdd install --agents claude --hooks --global-rules` connects the
hooks; a temporary git project holds `solo-sdd/config` with `reply.language: ru`; the laid-out
`~/.claude/hooks/work_hooks.py` runs `stop` and `guard` the way settings.json starts it. Steps 1 to 7 of the Live
Scenario, one `ok` or `FAIL` line each. Russian text is `\\u` escapes. Run from the repository root:
python3 tests/stands/reply-language.py. The temporary folder is removed; the last line is the summary."""
import json, os, pathlib, shutil, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
RULE = ("Reply in the language the user writes in: every message the user sees — progress lines between tool calls, "
        "AskUserQuestion questions and option labels, the final report. A handoff, skill or repository written in English "
        "does not change it.")
RU_TRANSLATE = "\u041f\u0435\u0440\u0435\u0432\u0435\u0434\u0438 \u043d\u0430 \u0430\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u0438\u0439"
RU_QUESTION = "\u0410 \u0447\u0442\u043e \u0441 \u0442\u0435\u0441\u0442\u0430\u043c\u0438?"
RU_LINES = "\u0412\u043e\u0442 \u0447\u0435\u0440\u043d\u043e\u0432\u0438\u043a.\n\u041f\u0440\u043e\u0432\u0435\u0440\u044c \u0435\u0433\u043e.\n"
EN_400 = ("The change rolls the hooks out to every agent folder on this computer and the tests pass on both runners. " * 4)[:400]
DRAFT = EN_400[:300]
EN_WINDOW = [{"question": "Roll out the change to the agent folders now?", "header": "Rollout",
              "options": [{"label": "Yes, roll out", "description": "Run sync.py push and update every agent folder"},
                          {"label": "Not now", "description": "Keep the change in the branch until later"}]}]
RU_WINDOW = [{"question": "\u0420\u0430\u0441\u043a\u0430\u0442\u0438\u0442\u044c \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0435 "
                          "\u0432 `~/.claude/hooks/work_hooks.py` \u0441\u0435\u0439\u0447\u0430\u0441?",
              "options": [{"label": "\u0414\u0430, \u0440\u0430\u0441\u043a\u0430\u0442\u0438\u0442\u044c",
                           "description": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0432\u0441\u0435 \u043f\u0430\u043f\u043a\u0438 "
                                          "\u0430\u0433\u0435\u043d\u0442\u043e\u0432 \u043d\u0430 \u044d\u0442\u043e\u043c "
                                          "\u043a\u043e\u043c\u043f\u044c\u044e\u0442\u0435\u0440\u0435"},
                          {"label": "\u041d\u0435 \u0441\u0435\u0439\u0447\u0430\u0441",
                           "description": "\u041e\u0441\u0442\u0430\u0432\u0438\u0442\u044c \u0432 \u0432\u0435\u0442\u043a\u0435"}]}]
results = []


def step(n, good, detail):
    results.append(bool(good))
    print("%s %d. %s" % ("ok  " if good else "FAIL", n, detail))


def run(env, args, inp=None, cwd=ROOT):
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=300, input=inp,
                       stdin=None if inp is not None else subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def human(text):
    return {"type": "user", "origin": {"kind": "human"}, "message": {"role": "user", "content": text}}


tmp = os.path.realpath(tempfile.mkdtemp(prefix="reply-language-"))
try:
    home = os.path.join(tmp, "home")
    for d in (".claude", ".codex"):
        os.makedirs(os.path.join(home, d))
    env = {k: v for k, v in os.environ.items() if k != "SOLO_SDD_REPLY_LANG"}
    env.update(HOME=home, PYTHONPATH=str(ROOT))
    code, out = run(env, [PY, "sync.py", "push"])
    if code != 0:
        raise SystemExit("FAIL sync.py push: exit %d\n%s" % (code, out[-800:]))
    code, out = run(env, [PY, "-m", "solo_sdd", "install", "--agents", "claude", "--hooks", "--global-rules"], cwd=home)
    if code != 0:
        raise SystemExit("FAIL solo-sdd install --hooks: exit %d\n%s" % (code, out[-800:]))
    settings_path = os.path.join(home, ".claude/settings.json")
    hooks = json.load(open(settings_path))["hooks"]
    command = lambda event, sub: next(h["command"] for g in hooks[event] for h in g["hooks"] if h["command"].endswith('"$f" ' + sub))

    repo = os.path.join(tmp, "proj")
    os.makedirs(os.path.join(repo, "solo-sdd"))
    subprocess.run(["git", "init", "-q", repo], check=True, stdin=subprocess.DEVNULL)
    cfg = os.path.join(repo, "solo-sdd/config")
    open(cfg, "w").write("reply.language: ru\n")
    n = [0]

    def hook(event, sub, inp):
        """The laid-out hook, started by the command settings.json names for the event; its JSON output or None."""
        n[0] += 1
        code, out = run(env, ["/bin/sh", "-c", command(event, sub)], json.dumps(dict({"session_id": "stand%d" % n[0], "cwd": repo}, **inp)), repo)
        if code != 0:
            return {"error": "exit %d %s" % (code, out[-300:])}
        return json.loads(out) if out.strip() else None

    def stop(reply, *entries):
        tr = os.path.join(tmp, "t%d.jsonl" % (n[0] + 1))
        open(tr, "w").write("".join(json.dumps(e) + "\n" for e in entries))
        return hook("Stop", "stop", {"transcript_path": tr, "last_assistant_message": reply})

    def ask(questions):
        o = hook("PreToolUse", "guard", {"tool_name": "AskUserQuestion", "tool_input": {"questions": questions}})
        return o["hookSpecificOutput"] if o and "hookSpecificOutput" in o else o

    o = stop(EN_400, human(RU_TRANSLATE))
    step(1, o is None, "a requested translation, an English reply of 400 letters: %s" % ("no block" if o is None else o))

    o = stop(EN_400, human(RU_TRANSLATE), {"type": "assistant", "message": {"content": [{"type": "text", "text": EN_400}]}}, human(RU_QUESTION))
    good = bool(o) and o.get("decision") == "block" and "Rewrite it in Russian" in o.get("reason", "")
    step(2, good, "a Russian question after the request: %s" % ("block, rewrite in Russian" if good else o))

    a, b = stop(RU_LINES + ":::writing\n" + DRAFT + "\n:::\n"), stop(RU_LINES + DRAFT)
    good = a is None and bool(b) and "Rewrite it in Russian" in b.get("reason", "")
    step(3, good, "a 300-letter English draft: in :::writing %s, bare %s" % ("no block" if a is None else a, "block" if b else "no block"))

    a, b = ask(EN_WINDOW), ask(RU_WINDOW)
    good = bool(a) and a.get("permissionDecision") == "deny" and "in Russian" in a.get("permissionDecisionReason", "") and b is None
    step(4, good, "AskUserQuestion: English window %s, Russian window %s" % (
        "denied, the reason names Russian" if good else a, "passes" if b is None else b))

    open(cfg, "w").write("reply.language: off\n")
    o = ask(EN_WINDOW)
    step(5, o is None, "reply.language off: the English window %s" % ("passes" if o is None else o))

    matcher = [g["matcher"] for g in hooks["PreToolUse"] if any(h["command"].endswith('"$f" guard') for h in g["hooks"])]
    before = open(settings_path, "rb").read()
    code, _ = run(env, [PY, "-m", "solo_sdd", "install", "--agents", "claude", "--hooks", "--global-rules"], cwd=home)
    same = open(settings_path, "rb").read() == before
    good = len(matcher) == 1 and matcher[0].split("|").count("AskUserQuestion") == 1 and code == 0 and same
    step(6, good, "settings.json guard matcher holds AskUserQuestion %d time(s); a second install --hooks: exit %d, file %s" % (
        matcher[0].split("|").count("AskUserQuestion") if matcher else 0, code, "unchanged" if same else "changed"))

    claude_md = os.path.join(home, ".claude/CLAUDE.md")
    text = open(claude_md, encoding="utf-8").read() if os.path.exists(claude_md) else ""
    step(7, ("- " + RULE) in text.splitlines(), "~/.claude/CLAUDE.md holds the new reply language rule")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("reply-language: %d of %d checks passed" % (sum(results), len(results)))
raise SystemExit(0 if results and all(results) else 1)
