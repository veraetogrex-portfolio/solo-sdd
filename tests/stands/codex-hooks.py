#!/usr/bin/python3
"""Live scenario of change codex-hooks-layout, steps 2 and 3: the Codex hooks solo-sdd lays out in a temporary home.

Each temporary HOME has a `~/.codex` folder and an empty PATH; `solo-sdd install --agents claude,codex --hooks` lays out
`~/.codex/hooks/` and writes `~/.codex/hooks.json`. The laid-out hook runs the way that file starts it, on a Codex
`Stop` input whose transcript is tests/fixtures/codex-rollout.jsonl (the shapes of a real Codex rollout) in a git
project with `reply.language: ru`. One `ok` or `FAIL` line per check; run from the repository root:
python3 tests/stands/codex-hooks.py. The temporary folder is removed; the last line is the summary."""
import json, os, pathlib, shutil, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
FIXTURE = ROOT / "tests" / "fixtures" / "codex-rollout.jsonl"
RU_QUESTION = "А что с тестами?"
EN_400 = ("The change rolls the hooks out to every agent folder on this computer and the tests pass on both runners. " * 4)[:400]
FOREIGN = {"matcher": "Bash", "hooks": [{"type": "command", "command": "other-tool check"}]}
results = []


def check(good, detail):
    results.append(bool(good))
    print("%s %s" % ("ok  " if good else "FAIL", detail))


def files(root):
    out = {}
    for d, _, names in os.walk(root):
        for n in names:
            out[os.path.join(d, n)] = pathlib.Path(d, n).read_bytes()
    return out


tmp = os.path.realpath(tempfile.mkdtemp(prefix="codex-hooks-"))
try:
    empty = os.path.join(tmp, "bin")
    os.makedirs(empty)

    def home(name, hooks_json=None):
        h = os.path.join(tmp, name)
        os.makedirs(os.path.join(h, ".codex"))
        if hooks_json is not None:
            pathlib.Path(h, ".codex", "hooks.json").write_text(hooks_json)
        return h

    def sdd(h, *args, inp=None, cwd=None):
        env = {k: v for k, v in os.environ.items() if k != "SOLO_SDD_REPLY_LANG"}
        env.update(HOME=h, PATH=empty + os.pathsep + "/usr/bin:/bin", PYTHONPATH=str(ROOT))
        p = subprocess.run(list(args) if inp is not None else [PY, "-m", "solo_sdd", *args], cwd=cwd or h, env=env,
                           capture_output=True, text=True, timeout=300, input=inp, stdin=None if inp is not None else subprocess.DEVNULL)
        return p.returncode, p.stdout + p.stderr

    install = lambda h, *more: sdd(h, "install", "--agents", "claude,codex", "--hooks", *more)
    entries = lambda h: json.loads(pathlib.Path(h, ".codex", "hooks.json").read_text())["hooks"]

    a = home("clean")
    code, out = install(a)
    laid = pathlib.Path(a, ".codex/hooks/work_hooks.py")
    same = laid.exists() and laid.read_bytes() == (ROOT / "global/work_hooks.py").read_bytes()
    h = entries(a) if code == 0 else {}
    counts = {e: len(h.get(e, [])) for e in ("PreToolUse", "SessionStart", "SessionEnd", "Stop")}
    check(code == 0 and same and set(counts.values()) == {1} and sorted(h) == sorted(counts),
          "install: ~/.codex/hooks/work_hooks.py equals global/work_hooks.py, hooks.json entries %s (exit %d)" % (counts, code))
    before = files(a)
    code, _ = install(a)
    check(code == 0 and files(a) == before, "a second install changes no file (exit %d)" % code)

    b = home("hand")
    os.makedirs(os.path.join(b, ".codex/hooks"))
    hand = pathlib.Path(b, ".codex/hooks/work_hooks.py")
    hand.write_text("# a hand copy of 2026-10-15\n")
    code, out = install(b)
    check(code == 1 and "foreign ~/.codex/hooks/work_hooks.py: kept" in out and hand.read_text() == "# a hand copy of 2026-10-15\n",
          "an older hand copy is named foreign and kept, exit %d" % code)
    code, out = install(b, "--replace-foreign")
    saved = [p.read_text() for p in pathlib.Path(b, ".local/share/solo-sdd/backup").rglob("work_hooks.py")]
    check(code == 0 and hand.read_bytes() == laid.read_bytes() and saved == ["# a hand copy of 2026-10-15\n"],
          "--replace-foreign replaces it and the backup holds the old text (exit %d, backups %d)" % (code, len(saved)))

    c = home("foreign", json.dumps({"hooks": {"PreToolUse": [FOREIGN]}}))
    code, _ = install(c)
    pre = entries(c).get("PreToolUse", [])
    check(code == 0 and pre[:1] == [FOREIGN] and len(pre) == 2, "a foreign PreToolUse entry stays, ours beside it (exit %d)" % code)

    d = home("broken", "{broken")
    before = files(os.path.join(d, ".codex"))
    code, out = install(d)
    check(code == 1 and "~/.codex/hooks.json" in out and files(os.path.join(d, ".codex")) == before,
          "a broken hooks.json: exit %d naming it, nothing under ~/.codex written" % code)

    code, _ = sdd(c, "install", "--agents", "claude", "--hooks")
    check(code == 0 and entries(c) == {"PreToolUse": [FOREIGN]} and not os.path.exists(os.path.join(c, ".codex/hooks/work_hooks.py")),
          "install --agents claude --hooks: the solo-sdd entries and copies leave, the foreign entry stays (exit %d)" % code)

    repo = os.path.join(tmp, "proj")
    os.makedirs(os.path.join(repo, "solo-sdd"))
    subprocess.run(["git", "init", "-q", repo], check=True, stdin=subprocess.DEVNULL)
    pathlib.Path(repo, "solo-sdd/config").write_text("reply.language: ru\n")
    stop = next(x["command"] for g in entries(a)["Stop"] for x in g["hooks"])

    def stopped(n, extra=()):
        tr = os.path.join(tmp, "rollout-%d.jsonl" % n)
        pathlib.Path(tr).write_text(FIXTURE.read_text() + "".join(json.dumps(e) + "\n" for e in extra))
        inp = {"session_id": "codex-stand-%d" % n, "turn_id": "t2", "cwd": repo, "transcript_path": tr, "hook_event_name": "Stop",
               "stop_hook_active": False, "model": "gpt", "permission_mode": "default", "last_assistant_message": EN_400}
        code, out = sdd(a, "/bin/sh", "-c", stop, inp=json.dumps(inp), cwd=repo)
        return code, json.loads(out) if out.strip() else None

    code, o = stopped(1)
    check(code == 0 and o is None, "the laid-out hook, Codex Stop after the Russian request to translate, English reply: no block")
    asked = {"type": "event_msg", "payload": {"type": "item_completed", "item": {"type": "UserMessage", "content": [{"type": "text", "text": RU_QUESTION}]}}}
    code, o = stopped(2, [asked])
    check(code == 0 and bool(o) and o.get("decision") == "block" and "Rewrite it in Russian" in o.get("reason", ""),
          "the same transcript with a Russian question after it: a block")

    code, out = sdd(a, "doctor")
    rows = [l for l in out.splitlines() if l.startswith(("ok agent codex", "ok codex hooks"))]
    check(len(rows) == 2, "doctor: %s" % " | ".join(rows or [out[-300:]]))
finally:
    shutil.rmtree(tmp, True)
print("codex-hooks: %d of %d checks passed" % (sum(results), len(results)))
raise SystemExit(0 if all(results) else 1)
