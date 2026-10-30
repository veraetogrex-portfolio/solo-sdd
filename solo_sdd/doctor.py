"""solo-sdd doctor: проверки окружения, по строке `ok|warn|fail <что>: <подробность>`."""
import os, re, shutil, subprocess, sys

from solo_sdd import hooks, layout

NEED_OPENSPEC = (1, 14, 0)
NPM = "npm i -g @fission-ai/openspec"


def _version(text):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    return tuple(int(x) for x in m.groups()) if m else None


def _call(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as e:
        return None, str(e)
    return (p.stdout + p.stderr, None) if p.returncode == 0 else (None, f"код {p.returncode}")


def _python():
    cur = sys.version_info[:3]
    yield ("ok" if cur >= (3, 9) else "fail", "python", ".".join(map(str, cur)) + ("" if cur >= (3, 9) else ", нужен 3.9+"))
    out, err = _call(["/usr/bin/python3", "--version"])
    v = _version(out)
    if v and v >= (3, 9):
        yield "ok", "python-hooks", "/usr/bin/python3 " + ".".join(map(str, v))
    else:
        yield "fail", "python-hooks", f"хукам нужен /usr/bin/python3 3.9+; {'версия ' + '.'.join(map(str, v)) if v else (err or 'не найден')}"


def _openspec():
    if shutil.which("openspec") is None:
        yield "fail", "openspec", f"не найден; поставьте: {NPM}"
        yield "fail", "schema", "не проверена, нет openspec"
        return
    out, err = _call(["openspec", "--version"])
    v = _version(out)
    if v is None:
        yield "fail", "openspec", f"версия не определена ({err or out.strip()})"
    elif v < NEED_OPENSPEC:
        yield "fail", "openspec", f"версия {'.'.join(map(str, v))}, нужна 1.14.0+; обновите: {NPM}"
    else:
        yield "ok", "openspec", ".".join(map(str, v))
    out, err = _call(["openspec", "schemas"])
    if out is not None and re.search(r"(?m)^\s*solo\b", out):
        yield "ok", "schema", "solo"
    else:
        yield "fail", "schema", "нет схемы solo; выполните solo-sdd install"


def _layout(state):
    kinds = {}
    for _, source, target, block in layout.pairs():
        kind = layout.classify(layout.read(source), target, state, block)[0]
        kinds[kind] = kinds.get(kind, 0) + 1
    bad = [k for k in ("missing", "drift", "unreachable") if kinds.get(k)]
    if bad:
        yield "fail", "layout", ", ".join(f"{k} {kinds.get(k, 0)}" for k in ("missing", "drift", "unreachable")) + "; см. solo-sdd status"
    elif kinds.get("first") or kinds.get("outdated"):
        yield "warn", "layout", f"first {kinds.get('first', 0)}, outdated {kinds.get('outdated', 0)}; solo-sdd install"
    else:
        yield "ok", "layout", f"копий {sum(kinds.values())}"


def _hooks(state):
    if not state.get("_hooks"):
        yield "ok", "hooks", "не подключены"
        return
    try:
        s, _ = hooks.load(hooks.path())
        placed = s is not None and hooks.apply(s)[1] is None
    except ValueError:
        placed = False
    if placed:
        yield "ok", "hooks", "на месте"
    else:
        yield "fail", "hooks", "записи не на месте; выполните solo-sdd install --hooks"


def _depth():
    value = os.environ.get(hooks.D)
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
        yield "warn", "depth", f"{'не задана' if n is None else n}, нужно 2+; выполните solo-sdd install --hooks"
    else:
        yield "ok", "depth", str(n)


def _source(state):
    src = state.get("_source")
    if not src:
        yield "warn", "source", "раскладки не было"
    elif os.path.realpath(src) != os.path.realpath(layout.REPO):
        yield "warn", "source", f"разложено из {src}, запущено из {layout.REPO}"
    else:
        yield "ok", "source", src


def _gh():
    if shutil.which("gh") is None:
        yield "warn", "gh", "нет; нужен для ship и spec-dispatch"
    else:
        yield "ok", "gh", "найден"


def run():
    state = layout.load_state()
    rows = [*_python(), *_openspec(), *_layout(state), *_hooks(state), *_depth(), *_source(state), *_gh()]
    for level, name, detail in rows:
        print(f"{level} {name}: {detail}")
    return 1 if any(r[0] == "fail" for r in rows) else 0
