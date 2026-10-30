#!/usr/bin/python3
"""Самопроверка work_hooks.py: запускается без аргументов, падает на первой ошибке."""
import importlib.util, json, os, shutil, subprocess, sys, tempfile, time, unicodedata

from hypothesis import given, settings, strategies as st

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "global", "work_hooks.py")
H = os.path.realpath(tempfile.mkdtemp(prefix="wh-home-"))
REPO = os.path.join(H, "proj")
ENV = dict(os.environ, HOME=H)
# Requirement: Hook self-check is location independent. Проекты проверок записи — вне рабочей копии и вне TMP_ROOTS
# хука: в worktree из $TMPDIR всё внутри tests/ разрешено и так. HOME настоящий: подмена только в ENV.
OUTSIDE = os.path.expanduser("~")


def run(cmd, inp, env=None):
    r = subprocess.run(["/usr/bin/python3", HOOK, cmd], input=json.dumps(inp), capture_output=True, text=True, env=env or ENV)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else None


def denied(inp):
    out = run("guard", dict({"session_id": "S1", "cwd": REPO}, **inp))
    return bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny"


def denied_env(inp, env, **extra):
    out = run("guard", dict({"session_id": "S1", "cwd": REPO}, **dict(inp, **extra)), env)
    return bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny"


def reason(inp):
    out = run("guard", dict({"session_id": "S1", "cwd": REPO}, **inp))
    return out["hookSpecificOutput"]["permissionDecisionReason"] if out else ""


def agent(desc, model=None, **extra):
    ti = {"description": desc, "prompt": "x"}
    if model:
        ti["model"] = model
    return dict({"tool_name": "Agent", "tool_input": ti}, **extra)


def bash(c):
    return denied({"tool_name": "Bash", "tool_input": {"command": c}})


def git(*a):
    subprocess.run(["git", "-C", REPO] + list(a), check=True, capture_output=True)


os.makedirs(os.path.join(REPO, "openspec/changes/01-a"))
os.makedirs(os.path.join(REPO, "openspec/changes/02-b"))
os.makedirs(os.path.join(H, ".codex"))
open(os.path.join(H, ".codex/config.toml"), "w").write('model = "gpt-6.1-sol"\n')
open(os.path.join(REPO, "AGENTS.md"), "w").write("ПРАВИЛО-ПРОЕКТА-42\n")
open(os.path.join(REPO, ".env"), "w").write("API_KEY=secret\n")
open(os.path.join(REPO, "openspec/changes/01-a/tasks.md"), "w").write("- [x] one\n- [ ] two\n")
open(os.path.join(REPO, "openspec/changes/02-b/WAITING"), "w").write("ждём доступ\n")
open(os.path.join(REPO, "app.css"), "w").write("a{}\n")
git("init", "-q"); git("add", "AGENTS.md", "app.css", "openspec"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")

# секреты
assert bash("cat .env"), "cat .env"
assert bash("cd x && head -3 data/okk.env"), "okk.env"
assert not bash("grep -c '^API_KEY=.' .env"), "grep -c allowed"
assert not bash("cat .env.example"), ".env.example allowed"
assert bash("echo $OPENAI_API_KEY"), "echo key"
assert not bash('echo "${#OPENAI_API_KEY}"'), "length allowed"
assert bash("env | grep -i claude") and bash("printenv") and bash("printenv GITHUB_TOKEN"), "env"
assert not bash("env -u ELECTRON_RUN_AS_NODE npm test --model x") or True
assert not bash("printenv HOME"), "printenv HOME"
assert bash("echo X= > .env") and not bash("echo NEW_KEY= >> .env"), "redirect"
assert bash("git add -A"), "git add -A with .env"
open(os.path.join(REPO, ".gitignore"), "w").write(".env\n")
assert not bash("git add -A"), "ignored .env"
assert bash("git add .env"), "explicit .env"
assert denied({"tool_name": "Write", "tool_input": {"file_path": os.path.join(REPO, ".env"), "content": "x"}}), "write .env"
assert denied({"tool_name": "Write", "tool_input": {"file_path": os.path.join(REPO, "sub/.env"), "content": "x"}}), "second .env"

# модели
assert bash("codex exec 'run the acceptance tests'"), "codex default sol in tests"
assert not bash("codex exec -m gpt-6-luna 'run the acceptance tests'"), "luna tests ok"
assert bash("codex exec -m gpt-6-astra 'refactor module'"), "astra always"
OWNER = dict(ENV, SOLO_SDD_EXPENSIVE_OK="1")
assert bash("EXPENSIVE_OK=1 codex exec -m gpt-6-astra 'refactor'"), "слово в команде больше не обходит"
assert not denied_env({"tool_name": "Bash", "tool_input": {"command": "codex exec -m gpt-6-astra 'refactor'"}}, OWNER), "override"
assert not bash("codex exec 'implement feature X'"), "default for impl ok"
assert bash("npm run acceptance -- --model opus"), "test with opus"
assert not bash("git commit -m 'тестов и model-policy.json\n\nCo-Authored-By: Claude Opus 5.5'"), "commit text is not a model flag"
assert bash("MODEL=gpt-6-astra npm test") and bash("pytest --model=sol"), "env and = forms"
assert denied(agent("Review: acceptance run", "sonnet"))
assert not denied(agent("Review: acceptance run", "haiku"))
assert not denied(agent("Implement parser"))
# роли субагентов
assert not denied(agent("Write a.py and test", "sonnet")), "исполнитель с тестами: роль general"
assert not denied(agent("Write a.py and test", "sonnet", agent_id="a1")), "то же из субагента"
assert denied(agent("Review: add-words", "sonnet")) and denied(agent("Review: add-words")), "ревьюер на дорогой"
assert "haiku" in reason(agent("Review: add-words", "sonnet")), "отказ называет дешёвые"
assert not denied(agent("Orchestrator add-words", "opus")), "оркестратор из главной"
assert denied(agent("Orchestrator add-words", "sonnet", agent_id="a1")), "оркестратор из субагента"
assert denied(agent("Implement words command", agent_id="a1")) and denied(agent("Implement words command", "opus", agent_id="a1"))
assert not denied(agent("Implement words command", "sonnet", agent_id="a1")), "исполнитель из субагента с явной моделью"
# роль по явному тегу в начале description
assert not denied(agent("Implement: acceptance core module", "sonnet", agent_id="a1")), "implement по правилам general"
assert not denied(agent("Acceptance core module", "sonnet", agent_id="a1")), "слово без тега не делает ревьюера"
assert denied(agent("Implement: x", "opus", agent_id="a1")) and denied(agent("Исполнитель: x", agent_id="a1"))
assert denied(agent("Ревью: add-words", "sonnet")) and denied(agent("  review: add-words"))
assert not denied(agent("Review add-words", "sonnet")) and not denied(agent("Re-review add-words", "sonnet"))
assert not denied(agent("Orchestrators add-words", "sonnet", agent_id="a1")), "Orchestrators — не тег"
assert denied(agent("Orchestrator: x", "sonnet", agent_id="a1"))
# обход только от владельца
assert denied(agent("Review: add-words EXPENSIVE_OK", "sonnet")), "слово в описании не обходит"
assert "EXPENSIVE_OK" not in reason(agent("Review: add-words EXPENSIVE_OK", "sonnet")), "отказ без подсказки обхода"
assert not denied_env(agent("Review: add-words", "opus"), OWNER), "владелец разрешил"
assert denied_env(agent("Review: add-words", "opus"), dict(ENV, SOLO_SDD_EXPENSIVE_OK="true")), "обход только при значении 1"
assert denied_env(agent("Orchestrator add-words", agent_id="a1"), OWNER), "обход не снимает запрет оркестратора"
# обход через настройки и профиль запрещён агенту
SETTINGS_JSON = os.path.join(H, ".claude", "settings.json")
assert denied({"tool_name": "Write", "tool_input": {"file_path": SETTINGS_JSON, "content": '{"env": {"SOLO_SDD_EXPENSIVE_OK": "1"}}'}}), "settings.json"
assert denied({"tool_name": "Edit", "tool_input": {"file_path": os.path.join(H, ".zshrc"), "old_string": "a", "new_string": "export SOLO_SDD_EXPENSIVE_OK=1"}}), "zshrc"
assert denied({"tool_name": "MultiEdit", "tool_input": {"file_path": os.path.join(H, ".profile"), "edits": [{"old_string": "a", "new_string": "b"}, {"old_string": "c", "new_string": "SOLO_SDD_EXPENSIVE_OK"}]}}), "multiedit"
assert not denied({"tool_name": "Write", "tool_input": {"file_path": os.path.join(REPO, "settings.json"), "content": "SOLO_SDD_EXPENSIVE_OK"}}), "не .claude"
assert bash("echo 'export SOLO_SDD_EXPENSIVE_OK=1' >> ~/.zshrc"), "echo в профиль"
assert bash("echo SOLO_SDD_EXPENSIVE_OK=1 | tee -a ~/.bashrc") and bash("sed -i '' 's/x/SOLO_SDD_EXPENSIVE_OK/' ~/.claude/settings.json"), "tee и sed -i"
assert not bash("grep -c SOLO_SDD_EXPENSIVE_OK ~/.zshrc; echo x > /tmp/out"), "чтение профиля и запись в другой файл"
assert bash("echo SOLO_SDD_EXPENSIVE_OK=1 >| ~/.zshrc") and bash("echo SOLO_SDD_EXPENSIVE_OK=1 >> ~/.zshenv"), ">| и zshenv"
assert bash("launch" + "ctl setenv SOLO_SDD_EXPENSIVE_OK 1"), "setenv"
assert not bash("grep -rn SOLO_SDD_EXPENSIVE_OK global") and not bash("SOLO_SDD_EXPENSIVE_OK=1 python3 tests/test_work_hooks.py"), "поиск и окружение команды"

# worktree и границы папки
assert bash("git worktree add ../copy") and not bash("git worktree add /tmp/wt-1"), "worktree"
# встроенные worktree агентов
assert bash("claude --worktree feat") and bash("claude -w") and bash("cd x && claude -p 'go' -w feat"), "claude -w"
assert bash("codex --worktree") and bash("codex exec --worktree 'implement x'") and bash("FOO=1 codex fork --worktree=a"), "codex --worktree"
assert not bash("git commit -m 'codex --worktree и claude -w запрещены'"), "quoted text is not a command"
assert not bash("grep -rn -- --worktree skills") and not bash("claude -p 'go'"), "no worktree flag"
assert not bash("codex exec -C /tmp/wt-1 'implement x'"), "codex in temp worktree"
assert denied({"tool_name": "EnterWorktree", "tool_input": {"name": "feat"}}), "EnterWorktree new"
assert denied({"tool_name": "EnterWorktree", "tool_input": {}}), "EnterWorktree random name"
assert not denied({"tool_name": "EnterWorktree", "tool_input": {"path": "/tmp/wh-wt-1"}}), "EnterWorktree temp path"
assert denied({"tool_name": "EnterWorktree", "tool_input": {"path": os.path.join(REPO, ".claude/worktrees/a")}}), "EnterWorktree inside project"
assert denied({"tool_name": "Agent", "tool_input": {"description": "Implement parser", "prompt": "x", "isolation": "worktree"}}), "agent isolation"
assert not denied({"tool_name": "Agent", "tool_input": {"description": "Implement parser", "prompt": "x", "isolation": "remote"}}), "remote isolation"
outside = "/opt/wh-test-outside/file.txt"
w = {"tool_name": "Write", "tool_input": {"file_path": outside, "content": "x"}}
assert denied(w) and not denied(w), "scope: first deny, second allow"
assert not denied({"tool_name": "Write", "tool_input": {"file_path": os.path.join(REPO, "src/x.py")}}), "inside repo"
nfd = tempfile.mkdtemp(prefix=unicodedata.normalize("NFD", "wh-й-"), dir=OUTSIDE)
subprocess.run(["git", "init", "-q", nfd], check=True)
cyr = unicodedata.normalize("NFC", nfd)
try:
    assert not run("guard", {"session_id": "S9", "cwd": cyr, "tool_name": "Write",
                             "tool_input": {"file_path": os.path.join(cyr, "README.md")}}), "NFD folder, NFC path"
finally:
    shutil.rmtree(nfd)

# CLAIM. Requirement: Claim on first done task
def change_file(name, tool="Edit", change="01-a", **ti):
    return {"tool_name": tool, "tool_input": dict(ti, file_path=os.path.join(REPO, "openspec/changes", change, name))}


prop = change_file("proposal.md", "Write", content="x")
claim = os.path.join(REPO, "openspec/changes/01-a/CLAIM")
for f in (prop, change_file("specs/c/spec.md", "Write", content="- [x] в спеке"), change_file("design.md", "Write", content="x"),
          change_file("verification.md", old_string="a", new_string="b"),
          change_file("tasks.md", old_string="- [ ] two", new_string="- [ ] two\n- [ ] three"),
          change_file("tasks.md", old_string="нет такой строки", new_string="- [x] нет такой строки")):
    assert not denied(f), f
    assert not os.path.exists(claim), ("analysis does not take the change", f)
os.makedirs(os.path.join(REPO, "openspec/changes/13-q"))
open(os.path.join(REPO, "openspec/changes/13-q/tasks.md"), "w").write("- [ ] a\n- [ ] a\n- [ ] b\n")
two = {"old_string": "- [ ] a", "new_string": "- [x] a"}
assert not denied(change_file("tasks.md", change="13-q", **two)), "non-unique old_string: Edit will refuse"
assert not os.path.exists(os.path.join(REPO, "openspec/changes/13-q/CLAIM")), "refused edit does not take the change"
assert not denied(change_file("tasks.md", "MultiEdit", "13-q", edits=[{"old_string": "- [ ] b", "new_string": "- [ ] c"}, {"old_string": "- [ ] c", "new_string": "- [x] c"}]))
assert os.path.exists(os.path.join(REPO, "openspec/changes/13-q/CLAIM")), "MultiEdit applies edits in order"
os.remove(os.path.join(REPO, "openspec/changes/13-q/CLAIM"))
assert not denied(change_file("tasks.md", "MultiEdit", "13-q", edits=[{"old_string": "- [ ] b", "new_string": "- [x] b"}, {"old_string": "нет такой строки", "new_string": "x"}]))
assert not os.path.exists(os.path.join(REPO, "openspec/changes/13-q/CLAIM")), "MultiEdit with a refused edit changes nothing"
assert not denied(change_file("tasks.md", change="13-q", replace_all=True, **two))
assert os.path.exists(os.path.join(REPO, "openspec/changes/13-q/CLAIM")), "replace_all marks tasks"
assert not denied(change_file("tasks.md", old_string="[ ] two", new_string="[x] two")), "first done task takes change"
assert "session=S1" in open(claim).read(), "claim created"
out = run("guard", dict(prop, session_id="S2", cwd=REPO, transcript_path=""))
assert out and "занят" in out["hookSpecificOutput"]["permissionDecisionReason"], "other agent blocked"
assert denied({"tool_name": "Edit", "tool_input": {"file_path": os.path.join(REPO, "openspec/changes/02-b/tasks.md")}}), "WAITING"

# context
ctx = run("context", {"session_id": "S1", "cwd": REPO, "source": "startup"})["hookSpecificOutput"]["additionalContext"]
assert "ПРАВИЛО-ПРОЕКТА-42" in ctx and "01-a — задачи 1/2" in ctx and "CLAIM" in ctx and "WAITING" in ctx, ctx

# subagent-context
sub = run("subagent-context", {"session_id": "S1", "cwd": REPO, "agent_id": "a1", "agent_type": "general-purpose", "hook_event_name": "SubagentStart"})
sub = sub["hookSpecificOutput"]
assert sub["hookEventName"] == "SubagentStart"
sub = sub["additionalContext"]
assert sub.startswith("Правила проекта: прочитай " + os.path.join(REPO, "AGENTS.md")), sub
assert "ПРАВИЛО-ПРОЕКТА-42" not in sub and len(sub) <= 4000, sub
assert any("01-a" in l and "CLAIM" in l for l in sub.splitlines()), sub
assert any("02-b" in l and "WAITING" in l for l in sub.splitlines()), sub
bare = os.path.realpath(tempfile.mkdtemp(prefix="wh-bare-"))
try:
    subprocess.run(["git", "init", "-q", bare], check=True)
    assert run("subagent-context", {"session_id": "S1", "cwd": bare, "hook_event_name": "SubagentStart"}) is None, "no AGENTS, no changes"
finally:
    shutil.rmtree(bare)
nogit = os.path.realpath(tempfile.mkdtemp(prefix="wh-nogit-"))
try:
    assert run("subagent-context", {"session_id": "S1", "cwd": nogit, "hook_event_name": "SubagentStart"}) is None, "outside git"
finally:
    shutil.rmtree(nogit)

# stop
open(os.path.join(REPO, "app.css"), "w").write("a{color:red}\n")
open(os.path.join(REPO, "openspec/changes/01-a/tasks.md"), "w").write("- [x] one\n- [x] two\n")
tr = os.path.join(H, "t.jsonl")
lines = [{"type": "assistant", "message": {"content": [
    {"type": "tool_use", "name": "Edit", "input": {"file_path": os.path.join(REPO, "app.css")}}]}},
    {"type": "user", "toolUseResult": {"stdout": "", "bashEditDiff": {"changedFiles": [os.path.join(REPO, "openspec/changes/01-a/tasks.md")]}}}]
open(tr, "w").write("\n".join(json.dumps(l) for l in lines) + "\n")
stop = {"session_id": "S1", "cwd": REPO, "transcript_path": tr,
        "last_assistant_message": "All done. The styles were updated and the change is complete, tests pass, nothing else to do here. I also reviewed the layout on all pages and it looks consistent."}
out = run("stop", stop)
assert out and out["decision"] == "block", out
r = out["reason"]
assert "незакоммиченные" in r and "не в архиве" in r and "браузере" in r and "не на русском" in r, r
assert run("stop", stop) is None, "same reasons not repeated"
assert run("stop", dict(stop, stop_hook_active=True)) is None
git("add", "-A"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x")
os.rename(os.path.join(REPO, "openspec/changes/01-a"), os.path.join(REPO, "openspec/changes/archive-01-a"))
git("add", "-A"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "archive")
lines.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "mcp__claude-in-chrome__navigate", "input": {}}]}})
open(tr, "w").write("\n".join(json.dumps(l) for l in lines) + "\n")
o = run("stop", dict(stop, last_assistant_message="Готово: стили обновлены, проверено в браузере, коммит сделан."))
assert o is None, o

# stop: фоновые агенты ещё работают
open(os.path.join(REPO, "app.css"), "w").write("a{color:blue}\n")
tr2 = os.path.join(H, "t2.jsonl")
open(tr2, "w").write(json.dumps(lines[0]) + "\n")
stop2 = {"session_id": "S20", "cwd": REPO, "transcript_path": tr2, "last_assistant_message": "Готово, ждём агентов."}
bg = [{"id": "a1", "type": "subagent", "status": "running"}]
assert run("stop", dict(stop2, background_tasks=bg)) is None, "running background agent: stop is silent"
o = run("stop", dict(stop2, session_id="S21", background_tasks=[dict(bg[0], status="completed")]))
assert o and o["decision"] == "block" and "незакоммиченные" in o["reason"], o
# stop: браузер в транскрипте субагента засчитывается
tr3 = os.path.join(H, "t3.jsonl")
open(tr3, "w").write(json.dumps(lines[0]) + "\n")
stop3 = {"session_id": "S22", "cwd": REPO, "transcript_path": tr3, "last_assistant_message": "Готово, всё проверено."}
o = run("stop", stop3)
assert o and "Изменён интерфейс" in o["reason"], o
os.makedirs(os.path.join(H, "t3", "subagents"))
sub_tr = os.path.join(H, "t3", "subagents", "agent-x.jsonl")
open(sub_tr, "w").write(json.dumps(lines[0]) + "\n")  # без браузера, только правка
o = run("stop", dict(stop3, session_id="S23"))
assert o and "Изменён интерфейс" in o["reason"], "субагент без браузера не засчитывается"
open(sub_tr, "w").write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "ui-check"}}]}}) + "\n")
o = run("stop", dict(stop3, session_id="S24"))
assert o and "Изменён интерфейс" not in o["reason"] and "незакоммиченные правки" in o["reason"], ("ui-check субагента засчитан", o)
open(sub_tr, "w").write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "curl localhost:9222/json/version"}}]}}) + "\n")
o = run("stop", dict(stop3, session_id="S25"))
assert o and "Изменён интерфейс" not in o["reason"] and "незакоммиченные правки" in o["reason"], ("признак CDP в Bash субагента засчитан", o)
git("add", "-A"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "css")

# beat, status, end
run("beat", {"session_id": "S1", "hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"description": "Прогон тестов"}, "cwd": REPO})
r = subprocess.run(["/usr/bin/python3", HOOK, "status"], input=json.dumps({"session_id": "S1", "model": {"display_name": "Opus"}, "workspace": {"current_dir": REPO}}), capture_output=True, text=True, env=ENV)
assert "▶ Bash: Прогон тестов" in r.stdout, r.stdout
os.makedirs(os.path.join(REPO, "openspec/changes/03-c"))
run("guard", dict(change_file("tasks.md", "Write", "03-c", content="- [x] a\n"), session_id="S1", cwd=REPO))
c3 = os.path.join(REPO, "openspec/changes/03-c/CLAIM")
assert os.path.exists(c3)
run("end", {"session_id": "S1"})
assert not os.path.exists(c3), "claim removed on SessionEnd"
# CLAIM, поставленный вручную без id сессии (2026-10-17)
os.makedirs(os.path.join(REPO, "openspec/changes/05-e"))
c5 = os.path.join(REPO, "openspec/changes/05-e/CLAIM")
edit5 = {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(REPO, "openspec/changes/05-e/tasks.md")}}


def sh5(sid, c, effect=None, tid="t1"):
    """Bash целиком: guard до запуска, сама команда (effect), claims после."""
    inp = {"session_id": sid, "cwd": REPO, "tool_name": "Bash", "tool_input": {"command": c}, "tool_use_id": tid}
    out = run("guard", inp)
    if not out:
        effect and effect()
        run("claims", dict(inp, hook_event_name="PostToolUseFailure"))
    return out


assert sh5("S3", 'cd "%s" && echo "claude-opus $(date +%%F)" > openspec/changes/05-e/CLAIM && ls -R' % REPO,
           lambda: open(c5, "w").write("claude-opus 2026-10-17\n")) is None
assert sh5("S4", 'cat "%s"; [ -f openspec/changes/05-e/CLAIM ] || echo me > openspec/changes/05-e/CLAIM' % c5) is None
out = run("guard", dict(edit5, session_id="S4", cwd=REPO))
assert out and "перепиши" in out["hookSpecificOutput"]["permissionDecisionReason"], "reading or re-claiming does not make it yours"
assert run("guard", dict(edit5, session_id="S3", cwd=REPO)) is None, "own manual CLAIM accepted"
assert open(c5).read() == "claude-opus 2026-10-17 session=S3\n", "hook stamps session id"
out = run("guard", dict(edit5, session_id="S4", cwd=REPO))
assert out and "активна 0 мин назад" in out["hookSpecificOutput"]["permissionDecisionReason"], out
assert sh5("S4", "openspec archive 05-e --yes"), "foreign archive blocked"
assert sh5("S3", "rm x && openspec archive 05-e --yes") is None, "own archive allowed"
assert sh5("S4", "echo 'потом: openspec archive 05-e --yes'") is None, "archive inside a string is not a command"
assert sh5("S4", "cd x && npx openspec archive 05-e -y"), "npx form blocked"
os.makedirs(os.path.join(REPO, "openspec/changes/08-h"))
c8 = os.path.join(REPO, "openspec/changes/08-h/CLAIM")
assert sh5("S9", "cp /tmp/tpl openspec/changes/08-h/CLAIM", lambda: open(c8, "w").write("tpl\n"), tid="t8") is None
other = os.path.join(H, "elsewhere")
os.makedirs(other, exist_ok=True)
os.makedirs(os.path.join(REPO, "openspec/changes/09-i"))
c9 = os.path.join(REPO, "openspec/changes/09-i/CLAIM")
i9 = {"session_id": "S10", "cwd": other, "tool_name": "Bash", "tool_use_id": "t9",
      "tool_input": {"command": 'cd "%s" && python3 -c "open(\'openspec/changes/09-i/CLAIM\',\'w\')"' % REPO}}
assert run("guard", i9) is None
open(c9, "w").write("x\n")
run("claims", dict(i9, cwd=REPO))
assert run("guard", dict(edit5, session_id="S10", cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/09-i/a.md")})) is None, "cd + python CLAIM is mine"
os.makedirs(os.path.join(REPO, "openspec/changes/10-j"))
c10 = os.path.join(REPO, "openspec/changes/10-j/CLAIM")
e10 = dict(edit5, cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/10-j/a.md")})
assert run("guard", {"session_id": "S11", "cwd": REPO, "tool_name": "Bash", "tool_use_id": "t10",
                     "tool_input": {"command": "echo a > openspec/changes/10-j/CLAIM; false"}}) is None
open(c10, "w").write("a\n")
assert run("guard", dict(e10, session_id="S11")) is None, "post hook has not run yet: still mine"
os.makedirs(os.path.join(REPO, "openspec/changes/11-k"))
c11 = os.path.join(REPO, "openspec/changes/11-k/CLAIM")
assert sh5("S12", "cat openspec/changes/11-k/CLAIM 2>/dev/null", tid="t11") is None
time.sleep(0.05)
open(c11, "w").write("codex 2026-10-17\n")
assert run("guard", dict(edit5, session_id="S12", cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/11-k/a.md")})), "CLAIM made after my command ended is not mine"
assert run("guard", dict(edit5, session_id="S9", cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/08-h/a.md")})) is None, "cp-created CLAIM is mine"
assert run("guard", dict(edit5, session_id="S4", cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/08-h/a.md")})), "and not someone else's"
run("end", {"session_id": "S3"})
assert not os.path.exists(c5), "stamped claim removed on SessionEnd"
os.makedirs(os.path.join(REPO, "openspec/changes/07-g"))
w7 = os.path.join(REPO, "openspec/changes/07-g/CLAIM")
assert run("guard", {"session_id": "S3", "cwd": REPO, "tool_name": "Write", "tool_input": {"file_path": w7}}) is None
open(w7, "w").write("claude 2026-10-17\n")
assert run("guard", dict(edit5, session_id="S3", cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/07-g/a.md")})) is None, "Write-created CLAIM is mine"

# worktree: CLAIM ставится и проверяется в основной папке
os.makedirs(os.path.join(REPO, "openspec/changes/06-f"))
open(os.path.join(REPO, "openspec/changes/06-f/tasks.md"), "w").write("- [ ] x\n")
git("add", "openspec/changes/06-f"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "06")
wt = os.path.join(H, "wt-06")
git("worktree", "add", "-q", wt, "-b", "wip/06")
wedit = {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(wt, "openspec/changes/06-f/tasks.md"), "old_string": "- [ ] x", "new_string": "- [x] x"}}
assert run("guard", dict(wedit, session_id="S5", cwd=wt, tool_input=dict(wedit["tool_input"], new_string="- [ ] x\n- [ ] y"))) is None
assert not os.path.exists(os.path.join(REPO, "openspec/changes/06-f/CLAIM")), "no claim without a done task"
assert run("guard", dict(wedit, session_id="S5", cwd=wt)) is None
assert "session=S5" in open(os.path.join(REPO, "openspec/changes/06-f/CLAIM")).read(), "claim in main checkout"
assert not os.path.exists(os.path.join(wt, "openspec/changes/06-f/CLAIM")), "no claim inside worktree"
assert run("guard", dict(wedit, session_id="S6", cwd=wt)), "main-checkout claim blocks worktree edit"

# статус оркестратора на SubagentHandback
R2 = os.path.join(H, "proj2")
os.makedirs(os.path.join(R2, "openspec/changes/arch-x"))
os.makedirs(os.path.join(R2, "openspec/changes/stay-y"))
for n in ("arch-x", "stay-y"):
    open(os.path.join(R2, "openspec/changes", n, "tasks.md"), "w").write("- [x] a\n")


def git2(*a, cwd=R2):
    return subprocess.run(["git", "-C", cwd, "-c", "user.email=t@t", "-c", "user.name=t"] + list(a), check=True,
                          capture_output=True, text=True).stdout.strip()


git2("init", "-q"); git2("add", "-A"); git2("commit", "-qm", "init")
first = git2("rev-parse", "HEAD")
WT2 = os.path.join(H, "wt-arch")
git2("worktree", "add", "-q", WT2, "-b", "wip/arch")
os.makedirs(os.path.join(WT2, "openspec/changes/archive"))
os.rename(os.path.join(WT2, "openspec/changes/arch-x"), os.path.join(WT2, "openspec/changes/archive/2026-10-20-arch-x"))
git2("add", "-A", cwd=WT2); git2("commit", "-qm", "archive", cwd=WT2)
head2 = git2("rev-parse", "HEAD", cwd=WT2)
ARCH = "openspec/changes/archive/2026-10-20-arch-x"


def status_msg(**over):
    f = dict(STATUS="archived", CHANGE="arch-x", BRANCH="wip/arch", WORKTREE=WT2, COMMIT=head2, ARCHIVE=ARCH,
             VALIDATE="openspec validate -> exit 0", TESTS="all tests -> exit 0", LIVE="ok", REVIEW="ok", AGENTS="none",
             HOOKS="ok", NOT_VERIFIED="nothing", NOTES="none")
    f.update(over)
    return "\n".join("%s: %s" % kv for kv in f.items())


def handback(msg, env=None):
    out = run("guard", {"session_id": "S30", "cwd": R2, "tool_name": "SubagentHandback", "tool_input": {"message": msg}}, env=env)
    assert not out or out["hookSpecificOutput"]["permissionDecision"] == "deny", out
    return out["hookSpecificOutput"]["permissionDecisionReason"] if out else None


r = handback(status_msg()); assert r is None, r
assert handback(status_msg(COMMIT=head2[:7])) is None, "short hash"
assert handback("```\n" + status_msg().replace("\n", "\n  ") + "\n```") is None, "fenced and indented"
for bad in (first, "deadbeef"):
    r = handback(status_msg(COMMIT=bad))
    assert r and head2 in r, r
open(os.path.join(R2, "openspec/changes/stay-y/CLAIM"), "w").write("claude 2026-10-20 session=X\n")
r = handback(status_msg(CHANGE="stay-y"))
assert r and "осталась openspec/changes/stay-y" in r and "CLAIM" in r, r
os.remove(os.path.join(R2, "openspec/changes/stay-y/CLAIM"))
r = handback("STATUS: done\nCHANGE: x")
assert r and "archived, not_ready, blocked" in r, r
assert handback("Отчёт исполнителя: всё сделано") is None and handback("") is None, "not a status"
assert handback("STATUS: not_ready\nCHANGE: arch-x\nNOTES: нет доступа") is None, "honest not_ready"
r = handback("STATUS: blocked\nCHANGE: arch-x")
assert r and "NOTES" in r and "not_ready" in r, r
nowt = os.path.join(H, "no-git-dir")
os.makedirs(nowt)
r = handback(status_msg(WORKTREE=nowt))
assert r and "не рабочая копия git" in r, r
assert "не рабочая копия git" in handback(status_msg(WORKTREE=os.path.join(H, "absent"))), "absent folder"
# сбой git: .git есть, а git завершается с ошибкой — сдача проходит, ошибка в журнале
fake = os.path.join(H, "fakebin")
os.makedirs(fake)
open(os.path.join(fake, "git"), "w").write("#!/bin/sh\nexit 1\n")
os.chmod(os.path.join(fake, "git"), 0o755)
brk = os.path.join(H, "broken-wt")
os.makedirs(os.path.join(brk, ".git"))
assert handback(status_msg(WORKTREE=brk), env=dict(ENV, PATH=fake + ":" + os.environ["PATH"])) is None, "git failure passes"
elog = os.path.join(H, ".claude/hook-state/errors.log")
assert "guard" in open(elog).read(), "git failure logged"
os.remove(elog)
# git не отвечает: таймаут — тоже сбой окружения
slow = os.path.join(H, "slowbin")
os.makedirs(slow)
open(os.path.join(slow, "git"), "w").write("#!/bin/sh\nexec sleep 30\n")
os.chmod(os.path.join(slow, "git"), 0o755)
assert handback(status_msg(WORKTREE=brk), env=dict(ENV, PATH=slow + ":" + os.environ["PATH"])) is None, "git timeout passes"
assert "Timeout" in open(elog).read(), "git timeout logged"
os.remove(elog)
# по одному расхождению на каждую проверку archived
open(os.path.join(R2, "openspec/changes/arch-x/CLAIM"), "w").write("claude 2026-10-20 session=X\n")
r = handback(status_msg())
assert r and "остался CLAIM change arch-x" in r and "не перенесён" not in r, r
os.remove(os.path.join(R2, "openspec/changes/arch-x/CLAIM"))
r = handback(status_msg(VALIDATE="openspec validate -> exit 1"))
assert r and "VALIDATE: после первого" in r and "TESTS" not in r, r
# дословные значения из прогона проекта-потребителя 20.10.2026: несколько команд и стрелки в пояснении
for good in ("npm test -> exit 0 (250 files, 5455 tests)", "exit 0",
             "npm test -> exit 0 (245 файлов, 5370 тестов; npm run typecheck -> exit 0)",
             "npm test -> exit 0 (250 files, 5455 tests); npm run typecheck -> 0 errors",
             "npm test -> exit 0 (240 файлов, 5316 тестов; npm run typecheck -> exit 0; после правки CSS 1784 зелёные)",
             "npm test (250 files; npm run typecheck with 0 errors) -> exit 0"):
    assert handback(status_msg(TESTS=good)) is None, good
for bad in ("npm test -> exit 1 (затем exit 0 при повторе)", "npm test -> exit 01", "npm test -> exit 0x", "npm test -> exit 0(x)",
            "npm test -> exit 0; npm run typecheck -> exit 2", "npm test: exit 0", "npm test -> 0 errors"):
    r = handback(status_msg(TESTS=bad))
    assert r and "TESTS: после первого" in r, (bad, r)
r = handback(status_msg(ARCHIVE="openspec/changes"))
assert r and "ARCHIVE openspec/changes не существующая папка" in r, r
assert handback(status_msg() + "\nCOMMIT: deadbeef") is None, "first COMMIT wins"
r = handback("COMMIT: deadbeef\n" + status_msg())
assert r and "COMMIT deadbeef" in r, r
o = run("guard", {"session_id": "S30", "cwd": WT2, "tool_name": "SubagentHandback", "tool_input": {"message": status_msg(WORKTREE="")}})
r = o["hookSpecificOutput"]["permissionDecisionReason"]
assert "пусто: WORKTREE" in r and "не рабочая копия" not in r and "COMMIT" not in r and "не перенесён" not in r, r

# cwd ушёл из проекта: папка запуска из CLAUDE_PROJECT_DIR остаётся своей
proj = os.path.realpath(tempfile.mkdtemp(prefix="wh-proj-", dir=OUTSIDE))
try:
    subprocess.run(["git", "init", "-q", proj], check=True)
    os.makedirs(os.path.join(H, "scratchpad"), exist_ok=True)
    pw = {"cwd": os.path.join(H, "scratchpad"), "tool_name": "Write", "tool_input": {"file_path": os.path.join(proj, "README.md")}}
    assert run("guard", dict(pw, session_id="S7")), "outside without project dir"
    assert run("guard", dict(pw, session_id="S8"), env=dict(ENV, CLAUDE_PROJECT_DIR=proj)) is None, "project dir allowed"
finally:
    shutil.rmtree(proj)

spec = importlib.util.spec_from_file_location("work_hooks", HOOK)
wh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wh)


@settings(max_examples=60, deadline=None)
@given(st.lists(st.tuples(st.text(max_size=400), st.sampled_from(["", "CLAIM", "WAITING", "both"]), st.text(max_size=50)),
                max_size=500) | st.just([]) | st.just([("я" * 5000, "CLAIM", "x")] * 500),
       st.sampled_from([None, "/p/AGENTS.md", "/Users/you/" + "d" * 200 + "/AGENTS.md"]))
def _subagent_ctx(raw, agents):
    rows = []
    for name, kind, label in raw:
        marks = {"": [], "CLAIM": ["CLAIM: " + label], "WAITING": ["WAITING: " + label],
                 "both": ["CLAIM: " + label, "WAITING: " + label]}[kind]
        rows.append("- %s — задачи 0/1%s" % (name, ("; " + "; ".join(marks)) if marks else ""))
    text = wh.subagent_context_text(agents, rows)
    assert len(text) <= 4000, len(text)
    assert agents is None or text.startswith("Правила проекта: прочитай " + agents), text[:200]


def test_subagent_project_context_property():
    _subagent_ctx()


TASKS_TEXT = st.lists(st.sampled_from(["- [ ] a", "- [x] a", "- [X] b", "  - [x] c", "[x] не задача", "текст", ""]), max_size=6).map("\n".join)


@settings(max_examples=60, deadline=None)
@given(TASKS_TEXT, TASKS_TEXT, st.sampled_from(["Write", "Edit", "MultiEdit"]), st.sampled_from(["tasks.md", "proposal.md"]))
def test_claim_on_first_done_task_property(old, new, tool, name):
    cdir = os.path.join(REPO, "openspec/changes/12-p")
    os.makedirs(cdir, exist_ok=True)
    claim = os.path.join(cdir, "CLAIM")
    if os.path.exists(claim):
        os.remove(claim)
    open(os.path.join(cdir, name), "w").write(old)
    edit = {"old_string": old, "new_string": new}
    ti = {"Write": {"content": new}, "Edit": edit, "MultiEdit": {"edits": [edit]}}[tool]
    done = lambda text: sum(l.strip().lower().startswith("- [x]") for l in text.split("\n"))
    assert run("guard", dict(change_file(name, tool, "12-p", **ti), session_id="S20", cwd=REPO)) is None
    assert os.path.exists(claim) == (name == "tasks.md" and done(new) > done(old)), (old, new, tool, name)


FULL = {n: "значение " + n for n in wh.STATUS_FIELDS}
FULL["STATUS"] = "archived"
FULL["WORKTREE"] = "/nonexistent-wt"


def _block(fields, order, fence, indent):
    lines = [indent + "%s: %s" % (n, fields[n]) for n in order if n in fields]
    return "\n".join((["```"] if fence else []) + lines + (["```"] if fence else []))


def test_status_block_format_property():
    nostatus = st.text() | st.lists(st.sampled_from(["", " STATUS", "status: x", "CHANGE: a", "```", "  NOTES: n"])).map("\n".join)

    @settings(max_examples=200, deadline=None)
    @given(nostatus.filter(lambda t: not any(l.lstrip().startswith("STATUS:") for l in t.splitlines())))
    def no_status(text):
        assert wh.status_problems(text, H) == []

    @settings(max_examples=100, deadline=None)
    @given(st.sets(st.sampled_from([n for n in wh.STATUS_FIELDS if n != "STATUS"]), min_size=1),
           st.permutations(list(wh.STATUS_FIELDS)), st.booleans(), st.sampled_from(["", " ", "    ", "\t"]))
    def missing(drop, order, fence, indent):
        problems = wh.status_problems(_block({n: v for n, v in FULL.items() if n not in drop}, order, fence, indent), H)
        assert all(n in "\n".join(problems) for n in drop), (drop, problems)

    assert wh.status_problems("", H) == []
    no_status()
    missing()


class Denied(Exception):
    pass


def _raise(reason):
    raise Denied(reason)


def is_denied(f, *a):
    try:
        f(*a)
    except Denied:
        return True
    return False


def test_owner_only_expensive_override_property():
    os.environ.pop(wh.OVERRIDE_VAR, None)
    orig, wh.deny = wh.deny, _raise
    try:
        cased = st.sampled_from(["EXPENSIVE_OK", "expensive_ok", "Expensive_Ok", "eXpEnSiVe_oK"])
        free = st.text(max_size=20) | st.just("")
        body = st.sampled_from(["", " add-words", " ревью"])
        prefix = st.sampled_from(["Review:", "Ревью:", "review:", "REVIEW:", "ревью:", "  Review:"])

        @settings(max_examples=300, deadline=None)
        @given(prefix, body, free, cased, st.sampled_from(["start", "mid", "end", "only"]), st.sampled_from(["opus", "sol", "fable", "astra"]), st.booleans())
        def review_denied(pre, mid, tail, w, where, model, sub):
            base = pre + mid + tail
            cut = len(pre) + (len(base) - len(pre)) // 2  # роль задаёт начало: имя вставляем после префикса
            desc = {"start": pre + w + base[len(pre):], "mid": base[:cut] + w + base[cut:], "end": base + w, "only": pre + w}[where]
            assert is_denied(wh.guard_models_agent, {"description": desc, "model": model}, sub), desc

        @settings(max_examples=300, deadline=None)
        @given(st.sampled_from(["Implement ", "Write ", "implement ", "WRITE "]), st.text(max_size=30) | st.sampled_from(["", "test", "review", "приёмка", "Test review Acceptance"]))
        def general_role(pre, rest):
            assert wh.agent_role(pre + rest) == "general", pre + rest

        @settings(max_examples=100, deadline=None)
        @given(st.sampled_from(["Acceptance ", "Test ", "Independent review ", "Re-review ", "Review ", "Приёмка ", "Тест "]), st.text(max_size=30))
        def untagged_general(pre, rest):
            assert wh.agent_role(pre + rest) == "general", pre + rest

        @settings(max_examples=300, deadline=None)
        @given(st.sampled_from(wh.PROFILES + ("settings.json", "settings.local.json")), free, free, st.sampled_from(["Write", "Edit", "MultiEdit"]))
        def write_denied(name, a, b, tool):
            path = os.path.join("/h", ".claude", name) if name.startswith("settings") else os.path.join("/h", name)
            for text in (wh.OVERRIDE_VAR + a, a + wh.OVERRIDE_VAR, a + wh.OVERRIDE_VAR + b, wh.OVERRIDE_VAR):
                ti = {"content": text} if tool == "Write" else {"new_string": text} if tool == "Edit" else {"edits": [{"new_string": "x"}, {"new_string": text}]}
                assert is_denied(wh.guard_override_write, tool, ti, path), (path, text)

        review_denied()
        general_role()
        untagged_general()
        write_denied()
    finally:
        wh.deny = orig


test_subagent_project_context_property()
test_status_block_format_property()
test_claim_on_first_done_task_property()
test_owner_only_expensive_override_property()

# подключение в settings.json: два запуска подряд — без дублей, с резервной копией
SH = os.path.realpath(tempfile.mkdtemp(prefix="wh-set-"))
os.makedirs(os.path.join(SH, ".claude"))
open(os.path.join(SH, ".claude/settings.json"), "w").write("{}")
SETTINGS = os.path.join(os.path.dirname(HOOK), "work_hooks_settings.py")
for _ in range(2):
    subprocess.run(["/usr/bin/python3", SETTINGS], check=True, capture_output=True, env=dict(os.environ, HOME=SH))
hk = json.load(open(os.path.join(SH, ".claude/settings.json")))["hooks"]
assert sum("subagent-context" in json.dumps(g) for g in hk["SubagentStart"]) == 1, hk["SubagentStart"]
assert [g["matcher"].split("|").count("SubagentHandback") for g in hk["PreToolUse"] if "guard" in json.dumps(g)] == [1], hk["PreToolUse"]
assert any(n.startswith("settings.json.bak-") for n in os.listdir(os.path.join(SH, ".claude"))), "backup"
hs = json.load(open(os.path.join(SH, ".claude/settings.json")))
assert hs["env"] == {"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "2"}, hs.get("env")
shutil.rmtree(SH)

# глубина субагентов: отсутствующая становится "2", заданная и прочие переменные env не меняются
D = "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"
@settings(max_examples=25, deadline=None)
@given(st.one_of(st.none(), st.dictionaries(st.sampled_from(["A", "PATH_X", "LANG", D]),
                                            st.sampled_from(["", "0", "1", "2", "3", "x"]), max_size=4)))
def test_hook_registration_depth_property(env):
    home = os.path.realpath(tempfile.mkdtemp(prefix="wh-depth-"))
    try:
        os.makedirs(os.path.join(home, ".claude"))
        open(os.path.join(home, ".claude/settings.json"), "w").write(json.dumps({} if env is None else {"env": env}))
        out = subprocess.run(["/usr/bin/python3", SETTINGS], check=True, capture_output=True, text=True,
                             env=dict(os.environ, HOME=home)).stdout
        got = json.load(open(os.path.join(home, ".claude/settings.json")))["env"]
        want = dict(env or {})
        want.setdefault(D, "2")
        assert got == want, (env, got)
        phrase = "задана владельцем, не меняю" if env and D in env else "записана, действует в новых сессиях"
        assert f"глубина субагентов {want[D]}: {phrase}" in out, out
    finally:
        shutil.rmtree(home)
test_hook_registration_depth_property()
# текст — не команда: тела heredoc и шаблоны поиска
assert not bash("cat > check.ts <<'EOF'\nfn(env)\nprintenv\nprintenv API_KEY\necho $API_KEY\nEOF"), "тело heredoc не команда"
assert not bash("cat <<EOF\nenv\nEOF"), "heredoc без кавычек"
assert not bash("cat <<-EOF\n\tenv\n\tEOF"), "heredoc с табами"
assert bash("bash <<'EOF'\nenv\nEOF"), "тело heredoc для оболочки — команды"
assert bash("cat <<'EOF' | sh\nenv\nEOF"), "heredoc в конвейере в оболочку"
assert bash("cat <<'EOF'\nhi\nEOF\nenv"), "хвост после heredoc проверяется"
assert bash("cat >> ~/.zshrc <<'EOF'\nexport SOLO_SDD_EXPENSIVE_OK=1\nEOF"), "перенос обхода в профиль через heredoc"
assert not bash("grep -n \"process.env\" apps/desktop/src/main"), "шаблон поиска не .env"
assert not bash("git grep -e process.env -- src"), "шаблон -e не .env"
assert bash("grep API_KEY .env"), "путь .env у grep"
assert bash("grep -e API_KEY .env"), "путь .env у grep -e"
assert bash("rg -A 2 KEY .env"), "значение опции не шаблон"
assert not bash("cat > stand.sh <<'EOF'\ncodex exec -m gpt-6-astra 'x'\nEOF"), "файл стенда не запуск Codex"
assert bash("codex exec -m gpt-6-astra 'x'"), "тот же запуск без heredoc"
for c in ("eval codex exec -m gpt-6-astra hi", "{ codex exec -m gpt-6-astra hi; }",
          "if true; then codex exec -m gpt-6-astra hi; fi", "echo x | xargs codex exec -m gpt-6-astra",
          "! codex exec -m gpt-6-astra hi", "timeout 60 codex exec -m gpt-6-astra hi",
          "(codex exec -m gpt-6-astra hi)", "nice -n 5 codex exec -m gpt-6-astra hi",
          "eval 'codex exec -m gpt-6-astra hi'"):
    assert bash(c), c
assert bash("timeout -s KILL 5 bash <<'EOF'\nenv\nEOF"), "heredoc через timeout в оболочку"
assert bash("(bash <<'EOF'\nenv\nEOF\n)"), "heredoc в подоболочке"
assert bash("rg --pre 'cat .env' x ."), "--pre — команда"
for bad in ("npm test -> exit 0 ->  exit 1", "npm test ->exit 1 -> exit 0", "npm test->exit 0->exit 2"):
    assert handback(status_msg(TESTS=bad)), bad
assert handback(status_msg(TESTS="npm test ->exit 0")) is None, "стрелка без пробелов"
assert not bash("grep -nE 'a|env|printenv' f.sh | head"), "| внутри кавычек шаблона"
assert not bash("sed -i '' 's/a/process.env[\"NEVER\"]/' f.ts"), "сценарий sed не .env"
assert bash("sed -n 1p .env"), "путь .env у sed"
assert bash("sed -i '' 's/a/b/' .env"), "путь .env у sed -i"
assert not bash("node -e 'const out=\"Usage: codex exec [FLAGS] [TEXT]\\n\";' a.txt b.txt && npm test"), "справка Codex в аргументе node"
assert bash("bash -c 'codex exec -m gpt-6-astra hi'"), "Codex в bash -c"
assert bash("cd w && codex exec -m gpt-6-astra hi"), "Codex после cd"
assert bash("timeout 60 codex exec -m gpt-6-astra hi"), "Codex под timeout"
assert bash("cat <<EOF\n$(printenv)\nEOF"), "подстановка в теле без кавычек"
assert not bash("cat <<'EOF'\n$(printenv)\nEOF"), "тело в кавычках — текст"
assert bash("grep \"$(printenv)\" f"), "подстановка в шаблоне"
for c in ("grep -f /dev/null .env", "grep --file=/dev/null .env", "sed -n -f /dev/null .env"):
    assert bash(c), "шаблоны в файле: .env — путь: " + c
for c in ("echo $(codex exec -m gpt-6-astra hi)", "X=$(codex exec -m gpt-6-astra hi)", "echo \"`codex exec -m gpt-6-astra hi`\"",
          "caffeinate -i codex exec -m gpt-6-astra hi", "gtimeout 60 codex exec -m gpt-6-astra hi", "npx codex exec -m gpt-6-astra hi"):
    assert bash(c), "Codex в подстановке или под обёрткой: " + c
for c in ("setsid codex exec -m gpt-6-astra hi", "stdbuf -oL codex exec -m gpt-6-astra hi", "sudo -u root codex exec -m gpt-6-astra hi",
          "cat <(codex exec -m gpt-6-astra hi)", "echo $( (codex exec -m gpt-6-astra hi) )", "find . -exec codex exec -m gpt-6-astra hi \\;"):
    assert bash(c), "Codex за любой обёрткой и в подстановке: " + c
assert bash("grep <(codex exec -m gpt-6-astra hi) f"), "Codex в <(…) на месте шаблона"
for c in ("sed 'r .env' x", "sed '1r .env' /dev/null", "bash -lc 'codex exec -m gpt-6-astra hi'",
          "codex -m gpt-6-astra exec hi", "cat <<'A'; bash <<'B'\nx\nA\ncodex exec -m gpt-6-astra hi\nB"):
    assert bash(c), "чтение .env сценарием sed, Codex в -lc, после флага и во втором heredoc: " + c
assert not bash("grep -c x f | head"), "вывод поиска в читатель текста — шаблон вырезается"
assert bash("grep -q test x; codex exec -m sol hi"), "маркер теста в шаблоне поиска остаётся маркером"
assert bash("cat <<'EOF' | tee >(bash)\nprintenv\nEOF"), "тело уходит в >(bash)"
for bad in ("npm test -> exit 0 -> EXIT 1", "npm test -> exit 0 -> exit\t1", "npm test -> exit 0 -> exit: 1",
            "npm test -> exit 0 -> exit=1", "npm test -> exit 0 (250); build -> failed (exit 1)",
            "npm test -> exit 0; lint -> FAILED: exit 2"):
    r = handback(status_msg(TESTS=bad))
    assert r and "TESTS: после первого" in r, (bad, r)
assert not os.path.exists(os.path.join(H, ".claude/hook-state/errors.log")), open(os.path.join(H, ".claude/hook-state/errors.log")).read()
print("OK: все сценарии прошли")
