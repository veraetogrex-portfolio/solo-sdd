#!/usr/bin/python3
"""Подключает ~/.claude/hooks/work_hooks.py в ~/.claude/settings.json. Повторный запуск не дублирует записи."""
import json, os, shutil, time
p = os.path.expanduser("~/.claude/settings.json")
shutil.copy2(p, p + ".bak-" + time.strftime("%Y%m%d-%H%M%S"))
s = json.load(open(p))
G = 'f="$HOME/.claude/hooks/work_hooks.py"; [ -f "$f" ] || exit 0; exec /usr/bin/python3 "$f" '
c = lambda sub, **k: dict({"type": "command", "command": G + sub}, **k)
b = c("beat", **{"async": True, "timeout": 5})
h = s.setdefault("hooks", {})
for e in list(h):
    h[e] = [g for g in h[e] if "work_hooks.py" not in json.dumps(g)]
add = lambda e, g: h.setdefault(e, []).append(g)
add("SessionStart", {"hooks": [c("context", timeout=15)]})
add("PreToolUse", {"matcher": "Bash|Write|Edit|MultiEdit|NotebookEdit|Agent|EnterWorktree|SubagentHandback", "hooks": [c("guard", timeout=10)]})
add("SubagentStart", {"hooks": [c("subagent-context", timeout=10)]})
add("PreToolUse", {"matcher": "*", "hooks": [b]})
add("PostToolUse", {"matcher": "*", "hooks": [b]})
for e in ("PostToolUse", "PostToolUseFailure"):
    add(e, {"matcher": "Bash", "hooks": [c("claims", timeout=10)]})
add("Stop", {"hooks": [c("stop", timeout=30), b]})
for e in ("UserPromptSubmit", "SubagentStart", "SubagentStop"):
    add(e, {"hooks": [b]})
add("SessionEnd", {"hooks": [c("end", timeout=10)]})
s.setdefault("statusLine", {"type": "command", "command": G + "status", "refreshInterval": 5})
r = ("The owner's global rules (~/.claude/CLAUDE.md, section 13) require Claude to merge its own verified pull requests "
     "in the owner's repositories with gh pr merge and then update the local main branch. Such a merge is approved work, "
     "not a merge without review, unless the merge or push triggers a production deploy, which still needs the owner's consent.")
a = s.setdefault("autoMode", {}).setdefault("allow", ["$defaults"])
if r not in a:
    a.append(r)
D = "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"
e = s.setdefault("env", {})
own = D in e
e.setdefault(D, "2")
text = json.dumps(s, ensure_ascii=False, indent=2) + "\n"
json.loads(text)
open(p, "w").write(text)
print("ok: хуки подключены, откройте /hooks или перезапустите Claude Code")
print(f"глубина субагентов {e[D]}: " + ("задана владельцем, не меняю" if own else "записана, действует в новых сессиях"))
