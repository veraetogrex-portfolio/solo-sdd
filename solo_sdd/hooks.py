"""Подключение хуков work_hooks.py в ~/.claude/settings.json и обратное снятие по записанным шагам."""
import copy, json, os, time

from solo_sdd import layout

D = "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"
G = 'f="$HOME/.claude/hooks/work_hooks.py"; [ -f "$f" ] || exit 0; exec /usr/bin/python3 "$f" '
P = "The owner's global rules (~/.claude/CLAUDE.md, section 13)"
RULE = (P + " require Claude to merge its own verified pull requests in the owner's repositories with sdd-pr.py merge or sdd-pr.py land "
        "(gh pr merge in the /ship skill), and to update a change branch from the main branch with git merge origin/<main branch> in its worktree. "
        "Such a merge or update is approved work, not a merge without review, unless the merge or push triggers a production deploy, "
        "which still needs the owner's consent. This rule does not approve a raw gh api -X PUT .../merge call: it skips the hash and behind checks.")
STATUS = {"type": "command", "command": G + "status", "refreshInterval": 5}


def _cmd(sub, **k):
    return dict({"type": "command", "command": G + sub}, **k)


def _need():
    b = _cmd("beat", **{"async": True, "timeout": 5})
    need = {}
    add = lambda e, g: need.setdefault(e, []).append(g)
    add("SessionStart", {"hooks": [_cmd("context", timeout=15)]})
    add("PreToolUse", {"matcher": "Bash|Write|Edit|MultiEdit|NotebookEdit|Agent|EnterWorktree|SubagentHandback", "hooks": [_cmd("guard", timeout=10)]})
    add("SubagentStart", {"hooks": [_cmd("subagent-context", timeout=10)]})
    add("PreToolUse", {"matcher": "*", "hooks": [b]})
    add("PostToolUse", {"matcher": "*", "hooks": [b]})
    for e in ("PostToolUse", "PostToolUseFailure"):
        add(e, {"matcher": "Bash", "hooks": [_cmd("claims", timeout=10)]})
    add("Stop", {"hooks": [_cmd("stop", timeout=30), b]})
    for e in ("UserPromptSubmit", "SubagentStart", "SubagentStop"):
        add(e, {"hooks": [b]})
    add("SessionEnd", {"hooks": [_cmd("end", timeout=10)]})
    return need


def path():
    return os.path.expanduser("~/.claude/settings.json")


def _ours(g):
    return "work_hooks.py" in json.dumps(g)


def _prefixed(x):
    return isinstance(x, str) and x.startswith(P)


def load(p):
    """(настройки, байты файла); файла нет — (None, None); непригодное содержимое — ValueError с причиной."""
    try:
        with open(p, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return None, None
    try:
        s = json.loads(raw.decode("utf-8"))
    except ValueError as e:
        raise ValueError(f"файл не разбирается как JSON: {e}")
    if not isinstance(s, dict):
        raise ValueError("верхний уровень не объект")
    for k in ("hooks", "env", "autoMode"):
        if k in s and not isinstance(s[k], dict):
            raise ValueError(f"{k} не объект")
    for e, v in s.get("hooks", {}).items():
        if not isinstance(v, list):
            raise ValueError(f"hooks.{e} не список")
    if "allow" in s.get("autoMode", {}) and not isinstance(s["autoMode"]["allow"], list):
        raise ValueError("autoMode.allow не список")
    return s, raw


def apply(settings):
    """(новые настройки, шаг|None); исходные не меняются."""
    s = copy.deepcopy(settings)
    need, step = _need(), {}
    h = s.setdefault("hooks", {})
    events = []
    for e in list(need) + [e for e in h if e not in need]:
        have = [(i, g) for i, g in enumerate(h.get(e, [])) if _ours(g)]
        want = need.get(e, [])
        if [g for _, g in have] == want:
            continue
        events.append({"event": e, "added": want, "removed": [[i, g] for i, g in have], "created": e not in h})
        h[e] = [g for g in h.get(e, []) if not _ours(g)] + want
    if events:
        step["hooks"] = events
    if "statusLine" not in s:
        s["statusLine"] = step["statusLine"] = STATUS
    created = "allow" not in s.get("autoMode", {})
    a = s.setdefault("autoMode", {}).setdefault("allow", ["$defaults"])
    old = list(a)
    i = next((i for i, x in enumerate(a) if _prefixed(x)), len(a))
    a[:] = a[:i] + [RULE] + [x for x in a[i:] if not _prefixed(x)]
    if a != old or created:
        step["rule"] = RULE
        step["rule_replaced"] = [[j, x] for j, x in enumerate(old) if _prefixed(x)]
        if created:
            step["defaults"] = True
    e = s.setdefault("env", {})
    if D not in e:
        e[D] = step.setdefault("env", {})[D] = "2"
    return (s, step) if step else (settings, None)


def _bak(p, raw):
    stamp, n = time.strftime("%Y%m%d-%H%M%S"), 0
    while True:
        dest = f"{p}.bak-{stamp}" + (f"-{n}" if n else "")
        try:
            with open(dest, "xb") as f:
                f.write(raw)
            return dest
        except FileExistsError:
            n += 1


def _put(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


def _dump(s):
    return (json.dumps(s, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def connect():
    p = path()
    s, raw = load(p)
    new, step = apply({} if s is None else s)
    if step is None:
        return None
    data = _dump(new)
    step["backup"] = layout.short(_bak(p, raw)) if raw is not None else None
    _put(p, data)
    return step


def disconnect(settings, steps):
    for step in reversed(steps):
        if "env" in step and isinstance(settings.get("env"), dict):
            for k, v in step["env"].items():
                if settings["env"].get(k) == v:
                    del settings["env"][k]
        a = settings.get("autoMode", {}).get("allow") if isinstance(settings.get("autoMode"), dict) else None
        if "rule" in step and isinstance(a, list):
            if step["rule"] in a:
                a.remove(step["rule"])
            for i, x in step["rule_replaced"]:
                a.insert(min(i, len(a)), x)
            if step.get("defaults") and "$defaults" in a:
                a.remove("$defaults")
        if "statusLine" in step and settings.get("statusLine") == step["statusLine"]:
            del settings["statusLine"]
        h = settings.get("hooks")
        for ev in reversed(step.get("hooks", [])):
            if not isinstance(h, dict) or not isinstance(h.get(ev["event"], []), list):
                continue
            lst = h.setdefault(ev["event"], [])
            for g in ev["added"]:
                for j in range(len(lst) - 1, -1, -1):
                    if lst[j] == g:
                        del lst[j]
                        break
            for i, g in sorted(ev["removed"], key=lambda r: r[0]):
                lst.insert(min(i, len(lst)), g)
    return settings


def prune(settings, before):
    bh = before.get("hooks") if isinstance(before.get("hooks"), dict) else {}
    ba = before.get("autoMode") if isinstance(before.get("autoMode"), dict) else {}
    h = settings.get("hooks")
    if isinstance(h, dict):
        for e in [e for e, v in h.items() if v == [] and e not in bh]:
            del h[e]
    m = settings.get("autoMode")
    if isinstance(m, dict) and m.get("allow") == [] and "allow" not in ba:
        del m["allow"]
    for k in ("hooks", "env", "autoMode"):
        if settings.get(k) == {} and k not in before:
            del settings[k]
    return settings


def setup():
    """Подключает хуки и записывает шаг в состояние. 0 — успех, 1 — настройки непригодны (файл не тронут)."""
    p = path()
    try:
        before, _ = load(p)
        state = layout.load_state()
        step = connect()
    except ValueError as e:
        print(f"fail settings: {e}")
        return 1
    if step is not None:
        state = layout.load_state()
        state.setdefault("_hooks", []).append(step)
        layout.save_state(state)
    ours = any("env" in x for x in state.get("_hooks", []))
    own = D in (before or {}).get("env", {}) and not ours
    value = load(p)[0]["env"][D]
    print("ok: хуки подключены, откройте /hooks или перезапустите Claude Code")
    print(f"глубина субагентов {value}: " + ("задана владельцем, не меняю" if own else "записана, действует в новых сессиях"))
    return 0


def restore(steps):
    """Снимает записанное из settings.json. 0 — успех или нечего снимать, 1 — настройки непригодны (файл не тронут)."""
    p = path()
    try:
        s, raw = load(p)
        if s is None:
            return 0
        first = layout.expand(steps[0]["backup"]) if steps[0].get("backup") else None
        try:
            with open(first, "rb") as f:
                before_raw = f.read()
        except (OSError, TypeError):
            before_raw = None
        before = load_bytes(before_raw)
        result = prune(disconnect(copy.deepcopy(s), steps), before)
        data = None if first is None and result == {} else (before_raw if before_raw is not None and result == before else _dump(result))
    except ValueError as e:
        print(f"fail settings: {e}")
        return 1
    _bak(p, raw)
    if data is None:
        os.remove(p)
    else:
        _put(p, data)
    return 0


def load_bytes(raw):
    """Разбор байтов резервной копии; нет копии или она непригодна — пустые настройки."""
    if raw is None:
        return {}
    try:
        s = json.loads(raw.decode("utf-8"))
    except ValueError:
        return {}
    return s if isinstance(s, dict) else {}
