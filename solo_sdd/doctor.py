"""solo-sdd doctor: environment checks, one line each: `ok|warn|fail <what>: <detail>`."""
import datetime, json, os, re, shutil, subprocess, sys

from solo_sdd import hooks, integration_run, integrations, keywords, layout, process_format, providers, settings


def _version(text):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    return tuple(int(x) for x in m.groups()) if m else None


def _call(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as e:
        return None, str(e)
    return (p.stdout + p.stderr, None) if p.returncode == 0 else (None, f"code {p.returncode}")


def _python():
    cur = sys.version_info[:3]
    yield ("ok" if cur >= (3, 9) else "fail", "python", ".".join(map(str, cur)) + ("" if cur >= (3, 9) else ", 3.9+ needed"))
    out, err = _call(["/usr/bin/python3", "--version"])
    v = _version(out)
    if v and v >= (3, 9):
        yield "ok", "python-hooks", "/usr/bin/python3 " + ".".join(map(str, v))
    else:
        yield "fail", "python-hooks", f"hooks need /usr/bin/python3 3.9+; {'version ' + '.'.join(map(str, v)) if v else (err or 'not found')}"


def _layout(state):
    kinds = {}
    foreign = 0
    for _, source, target, block in layout.laid():
        kind = layout.classify(layout.read(source), target, state, block)[0]
        kinds[kind] = kinds.get(kind, 0) + 1
        foreign += kind == "first" and not block
    bad = [k for k in ("missing", "drift", "unreachable") if kinds.get(k)]
    if bad:
        yield "fail", "layout", ", ".join(f"{k} {kinds.get(k, 0)}" for k in ("missing", "drift", "unreachable")) + "; see solo-sdd status"
    elif kinds.get("first") or kinds.get("outdated"):
        yield "warn", "layout", (f"first {kinds.get('first', 0)}, outdated {kinds.get('outdated', 0)}; solo-sdd install"
                                 + (f" (foreign files {foreign}: --replace-foreign)" if foreign else ""))
    else:
        yield "ok", "layout", f"copies {sum(kinds.values())}"


def _hooks(state):
    if not state.get("_hooks"):
        yield "ok", "hooks", "not connected"
        return
    try:
        s, _ = hooks.load(hooks.path())
        placed = s is not None and hooks.apply(s)[1] is None
    except ValueError:
        placed = False
    if placed:
        yield "ok", "hooks", "in place"
    else:
        yield "fail", "hooks", "entries not in place; run solo-sdd install --hooks"


def _policy(state):
    """The deployed model policy the guard hook reads; only with hooks connected."""
    if not state.get("_hooks"):
        return
    path = os.path.expanduser("~/.claude/hooks/model-policy.json")
    try:
        with open(path, encoding="utf-8") as f:
            if not isinstance(json.load(f), dict):
                raise ValueError("not a JSON object")
    except (OSError, ValueError) as e:
        yield "fail", "model policy", f"{path}: {e}; the guard hook skips its model checks"
        return
    yield "ok", "model policy", "parsed"


# errors:begin
def recent_errors(path, days=7):
    """(count, last line) of the hooks' errors.log lines dated within `days`; a line without a leading ISO time is not
    counted. The source is solo_sdd/doctor.py, the copy in work_hooks.py (deployed alone) is written by
    scripts/sync_blocks.py."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return 0, None
    since, found = datetime.datetime.now() - datetime.timedelta(days=days), []
    for line in lines:
        try:
            t = datetime.datetime.fromisoformat(line.split(" ", 1)[0])
        except ValueError:
            continue
        if t.tzinfo:
            t = t.astimezone().replace(tzinfo=None)
        if t >= since:
            found.append(line)
    return len(found), (found[-1] if found else None)
# errors:end


def _hook_errors(days=7):
    n, last = recent_errors(os.path.expanduser("~/.claude/hook-state/errors.log"), days)
    if n:
        yield "warn", "hook errors", f"{n} in the last {days} days, last: {last}"
    else:
        yield "ok", "hook errors", "none"


def _guard():
    try:
        s, _ = hooks.load(hooks.path())
    except ValueError:
        s = None
    if s is not None and hooks.guard_connected(s):
        yield "ok", "process guard", "connected"
    else:
        yield "warn", "process guard", "not connected"


def _sandbox():
    try:
        s, _ = hooks.load(hooks.path())
    except ValueError as e:
        yield "warn", "sandbox read", f"unknown, settings unreadable: {e}"
        return
    state, detail = hooks.sandbox_read(s or {})
    yield ("warn" if state == "gap" else "ok"), "sandbox read", detail


def _depth():
    value = os.environ.get(hooks.D) or None
    if value is None:
        try:
            s, _ = hooks.load(hooks.path())
        except ValueError:
            s = None
        value = ((s or {}).get("env") or {}).get(hooks.D)
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = None
    if n is None or n < 2:
        yield "warn", "depth", f"{'not set' if n is None else n}, 2+ needed; run solo-sdd install --hooks"
    else:
        yield "ok", "depth", str(n)


def _source(state):
    src = state.get("_source")
    if not src:
        yield "warn", "source", "no layout yet"
    elif os.path.realpath(src) != os.path.realpath(layout.REPO):
        yield "warn", "source", f"laid out from {src}, run from {layout.REPO}"
    else:
        yield "ok", "source", src


def _gh():
    if shutil.which("gh") is None:
        yield "warn", "gh", "missing; ship and spec-dispatch need it"
    else:
        yield "ok", "gh", "found"


def _agents(folder="."):
    path = os.path.join(folder, "AGENTS.md")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            found = keywords.migrate_agents(f.read())[1]
    except OSError:
        yield "ok", "agents", "no AGENTS.md here"
        return
    if found:
        yield "warn", "agents", keywords.migrate_hint(path, found)
    else:
        yield "ok", "agents", "English keywords"


CODEX_LIMIT = 32768  # Codex default project_doc_max_bytes


def _toml_keys(text):
    """The two top-level keys from config.toml where tomllib is missing (Python < 3.11)."""
    # ponytail: only these two keys are read; a key it cannot place raises, other TOML errors pass unnoticed
    top = re.split(r"(?m)^\s*\[", text, maxsplit=1)[0]
    out = {}
    m = re.search(r"(?m)^\s*project_doc_max_bytes\s*=\s*([\d_]+)\s*(?:#.*)?$", top)
    if m:
        out["project_doc_max_bytes"] = int(m.group(1).replace("_", ""))
    m = re.search(r"""(?m)^\s*project_doc_fallback_filenames\s*=\s*\[((?:"[^"\n]*"|'[^'\n]*'|#[^\n]*|[^\]"'#])*)\]""", top)
    if m:
        out["project_doc_fallback_filenames"] = [a or b for a, b, _ in re.findall(r"\"([^\"]*)\"|'([^']*)'|(#[^\n]*)", m.group(1)) if not _]
    for key in ("project_doc_max_bytes", "project_doc_fallback_filenames"):
        # a key it did not read, anywhere in the file (bad value, or after a line it took for a table) -> unreadable
        if key not in out and re.search(r"(?m)^\s*%s\s*=" % key, text):
            raise ValueError(f"cannot read {key}")
    return out


def _codex_config(home):
    """(limit, fallback names, note) from $CODEX_HOME/config.toml; defaults when missing or broken."""
    try:
        with open(os.path.join(home, "config.toml"), encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return CODEX_LIMIT, [], None
    except (OSError, ValueError):
        text = None
    data = None
    if text is not None:
        try:
            try:
                import tomllib
            except ImportError:
                data = _toml_keys(text)
            else:
                data = tomllib.loads(text)
        except ValueError:
            pass
    if data is not None:
        limit = data.get("project_doc_max_bytes", CODEX_LIMIT)
        names = data.get("project_doc_fallback_filenames", [])
        if type(limit) is int and limit >= 0 and isinstance(names, list) and all(isinstance(n, str) for n in names):
            # like Codex: a fallback entry that is not a plain file name is ignored
            return limit, [n for n in names if n not in ("", ".", "..") and "/" not in n and "\0" not in n], None
    return CODEX_LIMIT, [], "config.toml unreadable, defaults used"


def _first(folder, names, skip_blank):
    """(path, bytes) of the file Codex takes in a folder, or None. A file blank after trimming is not loaded:
    the global scope then tries the next name (skip_blank), a project folder takes the first existing file only."""
    for name in names:
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:  # Codex loads nothing from a project folder whose file it cannot read
            if skip_blank:
                continue
            return None
        if data.decode("utf-8", "replace").strip():
            return path, len(data)
        if not skip_blank:
            return None
    return None


def _size_row(files, limit, glob=None):
    """Level and detail: project files against the limit, largest first; the global file is outside the budget."""
    tail = f"; global {glob[0]} {glob[1]} outside the budget" if glob else ""
    if limit == 0:
        return "warn", "project_doc_max_bytes = 0: Codex loads no project instructions" + tail
    if not files and not glob:
        return "ok", "no Codex instructions found"
    total = sum(size for _, size in files)
    listed = ", ".join(f"{path} {size}" for path, size in sorted(files, key=lambda f: -f[1])) or "no project instructions"
    if total > limit:  # a file of exactly the remaining budget is loaded whole
        return "fail", f"{total} of {limit} bytes; Codex drops everything after {limit} bytes; {listed}{tail}"
    return ("warn" if total * 5 >= limit * 4 else "ok"), f"{total} of {limit} bytes; {listed}{tail}"


def _rules_size(folder="."):
    """Doctor rules size: the project instructions Codex would load in this folder against project_doc_max_bytes."""
    home = os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex")
    limit, fallback, note = _codex_config(home)
    here = os.path.realpath(folder)
    chain, cur = [here], here
    while not os.path.exists(os.path.join(cur, ".git")):
        parent = os.path.dirname(cur)
        if parent == cur:  # no git root: Codex checks only the current folder
            chain = [here]
            break
        cur = parent
        chain.insert(0, cur)
    files = [_first(d, ["AGENTS.override.md", "AGENTS.md", *fallback], False) for d in chain]
    glob = _first(home, ("AGENTS.override.md", "AGENTS.md"), True)
    level, detail = _size_row([f for f in files if f], limit, glob)
    yield level, "rules-size", detail + (f"; {note}" if note else "")


def _providers(state, folder="."):
    """One line per chosen agent with its capability gaps; a project naming agents the installation lacks."""
    agents = layout.chosen(state)
    for name in agents:
        level, detail = providers.row(name)
        yield level, "agent " + name, detail
    tree = process_format.find_tree(folder)
    try:
        found = settings.parse_settings(settings.read_settings_text(str(tree.parent))) if tree else {}
    except (OSError, ValueError):
        return  # a broken settings file is named by solo-sdd config
    missing = [n for n in found.get("agents", "").split(", ") if n and n not in agents]
    if missing:
        want = ",".join(n for n in providers.ALL if n in agents or n in missing)
        yield "warn", "project-agents", "solo-sdd/config names %s, not installed; solo-sdd install --agents %s" % (", ".join(missing), want)


def _integrations(folder=".", home=None):
    """Inside a project: a fail row per integration error, then a row per enabled readable integration with its
    source, points, tool and last run (a project one with its command); `none enabled` when nothing is."""
    tree = process_format.find_tree(folder)
    if tree is None:
        return
    root, home = str(tree.parent), home if home is not None else os.path.expanduser("~")
    try:
        found = settings.parse_settings(settings.read_settings_text(root))
    except (OSError, ValueError) as e:
        yield "fail", "integrations", str(e)
        return
    entries = integrations.find_integrations(root, home, integrations.all_sources())
    listed = integrations.enabled_names(entries, found)  # the bundled ones on by default included
    errors = integrations.integration_errors(entries, listed, settings.SETTINGS_FILE)
    if not listed:
        yield "ok", "integrations", "none enabled"
    for name, error in errors:
        yield "fail", "integration " + (name or "-"), error
    used, broken, last = {e["name"]: e for e in entries if e["name"] and not e["shadowed"]}, {n for n, _ in errors}, integration_run.last_runs(root, home)
    for name in listed:
        if name in broken:
            continue
        e, f = used[name], used[name]["fields"]
        missing = bool(f["requires"]) and shutil.which(f["requires"]) is None
        run = "%s %s" % last[name] if name in last else "none"
        tool = "requires %s %s" % (f["requires"], "missing" if missing else "found") if f["requires"] else "requires none"
        detail = "%s, points %s, %s, last run %s" % (e["source"], "/".join(f["points"]), tool, run)
        yield ("warn" if missing else "ok"), "integration " + name, detail + (", command " + f["command"] if e["source"] == "project" else "")


def run():
    state = layout.load_state()
    rows = [*_python(), *_layout(state), *_hooks(state), *_policy(state), *_hook_errors(), *_guard(), *_sandbox(), *_depth(), *_source(state), *_providers(state), *_gh(), *_agents(), *_integrations(),
            *_rules_size()]
    for level, name, detail in rows:
        print(f"{level} {name}: {detail}")
    return 1 if any(r[0] == "fail" for r in rows) else 0
