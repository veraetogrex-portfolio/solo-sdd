#!/usr/bin/env python3
"""Стенд Live Scenario change worktree-native: хук `guard` и команда `.gitignore` из project-init.
Запуск из корня репозитория: `python3 tests/stands/worktree-native.py [путь к work_hooks.py]`
(по умолчанию хук из этого репозитория). Код 0 — всё как ожидалось."""
import json, os, re, subprocess, sys, tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")
HOOK = os.path.expanduser(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "global/work_hooks.py")
results = []

def check(good, text):
    results.append(good)
    print("%s  %s" % ("ok  " if good else "FAIL", text))

with tempfile.TemporaryDirectory(prefix="wt-native-stand-") as tmp:
    home, repo = os.path.join(tmp, "home"), os.path.realpath(os.path.join(tmp, "repo"))
    os.makedirs(home); os.makedirs(repo)
    subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
    agent = {"description": "Implement x", "prompt": "x", "model": "haiku", "isolation": "worktree"}
    cases = [("Bash", {"command": "claude --worktree feature-auth"}, False),
             ("Bash", {"command": "claude -w"}, False),
             ("EnterWorktree", {"name": "feat"}, False),
             ("EnterWorktree", {"path": repo + "/.claude/worktrees/a"}, False),
             ("Agent", agent, False),
             ("Bash", {"command": "codex exec --worktree 'implement x'"}, True),
             ("Bash", {"command": "git worktree add ../copy"}, True)]
    for tool, tin, want_deny in cases:
        inp = {"session_id": "stand", "cwd": repo, "tool_name": tool, "tool_input": tin}
        r = subprocess.run([sys.executable, HOOK, "guard"], input=json.dumps(inp), capture_output=True, text=True,
                           env=dict(os.environ, HOME=home))
        out = json.loads(r.stdout)["hookSpecificOutput"] if r.stdout.strip() else {}
        denied = out.get("permissionDecision") == "deny"
        label = "%s %s -> %s" % (tool, json.dumps(tin, ensure_ascii=False), "deny" if denied else "пропущено")
        check(denied == want_deny, label + ("  [%s]" % out.get("permissionDecisionReason", "")[:120] if denied != want_deny else ""))
    elog = os.path.join(home, ".claude/hook-state/errors.log")
    if os.path.exists(elog):  # хук fail-open: внутренняя ошибка выглядела бы как «пропущено»
        check(False, "хук упал:\n" + open(elog).read())

    skill = open(os.path.join(ROOT, "skills/project-init/SKILL.md")).read()
    cmds = [c for c in re.findall(r"`([^`]+)`", skill) if ".claude/worktrees/" in c and "check-ignore" in c]
    check(len(cmds) == 1, "в project-init ровно одна команда .gitignore (найдено %d)" % len(cmds))
    if len(cmds) == 1:
        def run(name, content):
            d = os.path.join(tmp, name); os.makedirs(d)
            subprocess.run(["git", "-C", d, "init", "-q"], check=True)
            if content is not None:
                open(os.path.join(d, ".gitignore"), "wb").write(content)
            return d
        def go(d):
            subprocess.run(["bash", "-c", cmds[0]], cwd=d, capture_output=True)
            return open(os.path.join(d, ".gitignore"), "rb").read()
        ign = lambda d: subprocess.run(["git", "-C", d, "check-ignore", "-q", ".claude/worktrees/a"]).returncode
        d = run("a", b".env")
        lines = go(d).decode().splitlines()
        check(lines == [".env", ".claude/worktrees/"] and ign(d) == 0, "без перевода строки в конце: %s, check-ignore %d" % (lines, ign(d)))
        check(go(d).decode().splitlines().count(".claude/worktrees/") == 1, "повторный запуск: строка один раз")
        d = run("c", b".claude/\n")
        check(go(d) == b".claude/\n", "правило .claude/ уже есть: файл не изменён")
        d = run("d", None)
        check(go(d) == b".claude/worktrees/\n" and ign(d) == 0, "нет .gitignore: файл создан")
    ok = all(results)
    print("итог: %s" % ("%d из %d как ожидалось" % (len(results), len(results)) if ok else "есть расхождения"))
sys.exit(0 if ok else 1)
