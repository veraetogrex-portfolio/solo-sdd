"""Connecting work_hooks.py and process-guard.py hooks in ~/.claude/settings.json and removing them back by the recorded steps."""
import copy, json, os, sys, time

from solo_sdd import layout

D = "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"
G = 'f="$HOME/.claude/hooks/work_hooks.py"; [ -f "$f" ] || exit 0; exec /usr/bin/python3 "$f" '
P = "The owner's merge rule (solo-sdd)"
OLD_P = "The owner's global rules (~/.claude/CLAUDE.md, section 13)"  # the prefix of earlier versions: replaced on a run
RULE = (P + ": Claude merges its own verified pull requests in the owner's repositories with sdd-pr.py merge or sdd-pr.py land, "
        "updates a change branch from the main branch with git merge origin/<main branch> in its worktree, and in a repository "
        "without a solo-sdd/ tree merges with gh pr merge from the /ship skill. Such a merge or update is approved work, not a merge "
        "without review, except in a project whose solo-sdd/config sets delivery.merge-by: human, where a person merges, and except "
        "when the merge or push triggers a production deploy, which still needs the owner's consent. This rule does not approve a raw "
        "gh api -X PUT .../merge call, nor gh pr merge in a repository with a solo-sdd/ tree: they skip the sdd-pr.py gates.")
STATUS = {"type": "command", "command": G + "status", "refreshInterval": 5}
GUARD = {"matcher": "Bash|Monitor", "hooks": [{"type": "command", "command": 'exec /usr/bin/python3 "$HOME/.claude/hooks/process-guard.py"',
                                               "timeout": 5, "onFailure": "block"}]}
DENY = ["Bash(%s *)" % n for n in ("pkill", "killall", "kill", "osascript", "launchctl", "shutdown")] + ["Read(**/.env)"]  # holds when the guard hook fails open


def sandbox_read(settings):
    """(state, detail) of the sandbox read deny for .env: off | active | gap. Claude Code merges Read(...) deny rules into
    the sandbox's read deny and ignores glob Read rules there on Linux; sandbox.filesystem.denyRead takes only absolute and ~
    paths, so it cannot name .env in every project (read from the Claude Code 2.1.312 binary, not run)."""
    sb = settings.get("sandbox")
    if not (isinstance(sb, dict) and sb.get("enabled") is True):
        return "off", "off, it needs the sandbox (sandbox.enabled in ~/.claude/settings.json)"
    rule = DENY[-1]
    if rule not in ((settings.get("permissions") or {}).get("deny") or []):
        return "gap", "not active, %s missing from permissions.deny; run solo-sdd install --hooks" % rule
    if sys.platform.startswith("linux"):
        return "gap", "not active, Claude Code ignores glob Read rules in the sandbox on linux"
    if sys.platform != "darwin":
        return "gap", "unknown, not checked on %s" % sys.platform
    return "active", "expected active, %s in permissions.deny applies to sandboxed commands (read from Claude Code, not run)" % rule


def _cmd(sub, **k):
    return dict({"type": "command", "command": G + sub}, **k)


def _need():
    b = _cmd("beat", **{"async": True, "timeout": 5})
    need = {}
    add = lambda e, g: need.setdefault(e, []).append(g)
    add("SessionStart", {"hooks": [_cmd("context", timeout=15)]})
    add("PreToolUse", {"matcher": "Bash|Read|Grep|Write|Edit|MultiEdit|NotebookEdit|Agent|EnterWorktree|SubagentHandback", "hooks": [_cmd("guard", timeout=10)]})
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


def guard_connected(settings):
    """A PreToolUse entry runs process-guard.py, connected by install or by hand."""
    h = settings.get("hooks") if isinstance(settings.get("hooks"), dict) else {}
    return any("process-guard.py" in json.dumps(g) for g in h.get("PreToolUse") or [])


def _prefixed(x):
    return isinstance(x, str) and x.startswith((P, OLD_P))


def load(p):
    """(settings, file bytes); no file means (None, None); unusable content raises ValueError with the reason."""
    try:
        with open(p, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return None, None
    except OSError as e:
        raise ValueError(f"no access: {e.strerror}")
    try:
        s = json.loads(raw.decode("utf-8"))
    except ValueError as e:
        raise ValueError(f"file is not valid JSON: {e}")
    if not isinstance(s, dict):
        raise ValueError("top level is not an object")
    for k in ("hooks", "env", "autoMode", "permissions"):
        if k in s and not isinstance(s[k], dict):
            raise ValueError(f"{k} is not an object")
    if "deny" in s.get("permissions", {}) and not isinstance(s["permissions"]["deny"], list):
        raise ValueError("permissions.deny is not a list")
    for e, v in s.get("hooks", {}).items():
        if not isinstance(v, list):
            raise ValueError(f"hooks.{e} is not a list")
    if "allow" in s.get("autoMode", {}) and not isinstance(s["autoMode"]["allow"], list):
        raise ValueError("autoMode.allow is not a list")
    return s, raw


def apply(settings):
    """(new settings, step|None); the originals are not changed."""
    s = copy.deepcopy(settings)
    need, step = _need(), {}
    h = s.setdefault("hooks", {})
    had_pre, events = "PreToolUse" in h, []
    for e in list(need) + [e for e in h if e not in need]:
        have = [(i, g) for i, g in enumerate(h.get(e, [])) if _ours(g)]
        want = need.get(e, [])
        if [g for _, g in have] == want:
            continue
        events.append({"event": e, "added": want, "removed": [[i, g] for i, g in have], "created": e not in h})
        h[e] = [g for g in h.get(e, []) if not _ours(g)] + want
    if not guard_connected(s):  # an entry connected by hand is neither duplicated nor recorded
        h.setdefault("PreToolUse", []).append(GUARD)
        events.append({"event": "PreToolUse", "added": [GUARD], "removed": [], "created": not had_pre and not any(
            ev["event"] == "PreToolUse" for ev in events)})
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
    deny = s.get("permissions", {}).get("deny", [])
    missing = [x for x in DENY if x not in deny]
    if missing:
        s.setdefault("permissions", {})["deny"] = deny + missing
        step["deny"] = missing
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
        p = settings.get("permissions")
        if isinstance(p, dict) and isinstance(p.get("deny"), list):
            for x in step.get("deny", []):  # one copy each: a copy the owner added later stays
                if x in p["deny"]:
                    p["deny"].remove(x)
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
    bp = before.get("permissions") if isinstance(before.get("permissions"), dict) else {}
    pm = settings.get("permissions")
    if isinstance(pm, dict) and pm.get("deny") == [] and "deny" not in bp:
        del pm["deny"]
    for k in ("hooks", "env", "autoMode", "permissions"):
        if settings.get(k) == {} and k not in before:
            del settings[k]
    return settings


def setup():
    """Connects the hooks and records the step in the state. 0 is success, 1 means the settings are unusable (file untouched)."""
    p = path()
    try:
        before, _ = load(p)
        state = layout.load_state()
        step = connect()
    except (ValueError, OSError) as e:
        print(f"fail settings: {e}")
        return 1
    if step is not None:
        state = layout.load_state()
        state.setdefault("_hooks", []).append(step)
        layout.save_state(state)
    value = load(p)[0]["env"][D]
    ours = any(x.get("env", {}).get(D) == value for x in state.get("_hooks", []))
    own = D in (before or {}).get("env", {}) and not ours
    print("ok: hooks connected, open /hooks or restart Claude Code")
    print(f"subagent depth {value}: " + ("set by the owner, not changed" if own else "written, applies to new sessions"))
    print("sandbox read deny: " + sandbox_read(load(p)[0])[1])
    return 0


def restore(steps):
    """Removes what was recorded from settings.json. 0 is success or nothing to remove, 1 means the settings are unusable (file untouched)."""
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
        _bak(p, raw)
        if data is None:
            os.remove(p)
        else:
            _put(p, data)
    except (ValueError, OSError) as e:
        print(f"fail settings: {e}")
        return 1
    return 0


def load_bytes(raw):
    """Parses the backup bytes; no backup or an unusable one gives empty settings."""
    if raw is None:
        return {}
    try:
        s = json.loads(raw.decode("utf-8"))
    except ValueError:
        return {}
    return s if isinstance(s, dict) else {}
