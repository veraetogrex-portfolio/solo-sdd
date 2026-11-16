"""The version check of the home menu and `doctor`, and the update steps the menu runs on confirmation.

Only `check(network=True)` asks a registry, and only through `fetch`; every other command reads the cache at most.
No text of a registry answer but a version of the form N.N.N in ASCII digits is kept, shown or put into a command.
"""
import http.client, json, os, re, socket, subprocess, sys, threading, time, urllib.error, urllib.request

from solo_sdd import __version__, layout

DAY = 24 * 3600
TIMEOUT = 2
LIMIT = 1 << 20  # bytes of an answer; a longer one is no answer
OFF = "SOLO_SDD_NO_UPDATE_CHECK"
ADDRESS = "SOLO_SDD_REGISTRY"  # tests only: one address standing in for both registries
REGISTRIES = {"pypi": ("https://pypi.org", "/pypi/solo-sdd/json"), "npm": ("https://registry.npmjs.org", "/solo-sdd/latest")}
RELEASES = "https://github.com/veraetogrex-portfolio/solo-sdd/releases/tag/v"  # the Repository URL of pyproject.toml
VERSION = re.compile(r"[0-9]{1,9}\.[0-9]{1,9}\.[0-9]{1,9}")
REASONS = ("timed out", "no connection", "the registry refused the request", "the answer is not a version")
PACKAGE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the folder holding this solo_sdd package
# like the npm wrapper: the package folder before the current one, so a solo-sdd clone in cwd does not shadow it
BOOT = "import runpy, sys; sys.path.insert(0, sys.argv.pop(1)); runpy.run_module('solo_sdd', run_name='__main__', alter_sys=True)"


def path():
    return os.path.join(layout.DATA, layout.UPDATE_CHECK)


def method():
    """(registry, the upgrade command shown, its argv) of the install method; registry None for a clone."""
    from solo_sdd import cli
    hint = cli.upgrade_hint(sys.prefix, layout.REPO)
    if hint.startswith("git pull"):
        return None, hint, None
    argv = hint.split()
    if argv[0] == "python3":
        argv[0] = sys.executable  # the interpreter this solo-sdd runs on
    return ("npm" if argv[0] == "npm" else "pypi"), hint, argv


def key(version):
    return tuple(int(x) for x in version.split("."))


def installed():
    m = re.match(r"([0-9]+)\.([0-9]+)\.([0-9]+)", __version__)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def load():
    """The cache with only fields of the expected type; a missing or broken file is an empty cache."""
    try:
        with open(path(), "rb") as f:
            data = json.loads(f.read(65536).decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, RecursionError):
        return {}
    if not isinstance(data, dict):
        return {}
    out = {}
    if type(data.get("checked")) in (int, float):
        out["checked"] = data["checked"]
    for name in ("latest", "skip"):
        if isinstance(data.get(name), str) and VERSION.fullmatch(data[name]):
            out[name] = data[name]
    if data.get("error") in REASONS:
        out["error"] = data["error"]
    if data.get("off") is True:
        out["off"] = True
    return out


def save(cache):
    """Writes the cache whole or not at all; a write that fails leaves the check to the next launch."""
    target = path()
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        tmp = "%s.%d.%d.tmp" % (target, os.getpid(), threading.get_ident())  # the menu's check thread saves too
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        os.replace(tmp, target)
    except OSError:
        pass


def env_off():
    return os.environ.get(OFF, "") not in ("", "0")


def off_reason(cache=None):
    if env_off():
        return "%s=%s" % (OFF, "1" if os.environ[OFF] == "1" else "set")
    if (load() if cache is None else cache).get("off"):
        return "switched off in the Machine section"
    return None


def fetch(url):
    """The only network call: the answer's bytes, at most LIMIT + 1 of them; `ask` bounds its whole time."""
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
        body = b""
        while len(body) <= LIMIT:
            chunk = r.read1(65536)
            if not chunk:
                break
            body += chunk
    return body


def bounded(url):
    """fetch within TIMEOUT seconds in all, the name lookup included: a later answer is dropped with its thread."""
    got = {}

    def work():
        try:
            got["body"] = fetch(url)
        except BaseException as e:  # noqa: BLE001 handed to the caller's thread
            got["error"] = e
    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    worker.join(TIMEOUT)
    if worker.is_alive():
        raise TimeoutError
    if "error" in got:
        raise got["error"]
    return got["body"]


def parse(body, registry):
    """The version of an answer, or None: over LIMIT, not UTF-8 JSON, another shape or not N.N.N in ASCII digits."""
    if len(body) > LIMIT:
        return None
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None
    if registry == "pypi":
        data = data.get("info") if isinstance(data, dict) else None
    version = data.get("version") if isinstance(data, dict) else None
    return version if isinstance(version, str) and VERSION.fullmatch(version) else None


def ask(registry):
    """(version, None) or (None, one of REASONS): no text of the answer or of its error goes further."""
    host, tail = REGISTRIES[registry]
    try:
        version = parse(bounded(os.environ.get(ADDRESS, host).rstrip("/") + tail), registry)
    except urllib.error.HTTPError:
        return None, REASONS[2]
    except urllib.error.URLError as e:
        return None, REASONS[0] if isinstance(e.reason, (TimeoutError, socket.timeout)) else REASONS[1]
    except (TimeoutError, socket.timeout):
        return None, REASONS[0]
    except (OSError, ValueError, http.client.HTTPException):
        return None, REASONS[1]
    return (version, None) if version else (None, REASONS[3])


def check(network, now=None):
    """The cache after a request when `network`, the check is on and the last attempt is 24 hours old or more; every
    attempt stores its time, a failure keeps the version answered before."""
    registry = method()[0]
    cache = load()
    if registry is None or off_reason(cache):
        return {}
    if not network:
        return cache
    now = time.time() if now is None else now
    if 0 <= now - cache.get("checked", -DAY) < DAY:
        return cache
    version, error = ask(registry)
    cache = load()  # a skip saved while the request ran is kept
    cache["checked"] = now
    cache.pop("error", None)
    if version:
        cache["latest"] = version
    else:
        cache["error"] = error
    save(cache)
    return cache


def newer(cache):
    """The cached latest version when it is newer than the one running, else None."""
    latest = cache.get("latest")
    return latest if latest and key(latest) > installed() else None


def notice(cache):
    """The version the menu names: newer than the one running and than a skipped one."""
    latest = newer(cache)
    if latest and "skip" in cache and key(latest) <= key(cache["skip"]):
        return None
    return latest


def skip(version):
    cache = load()
    cache["skip"] = version
    save(cache)


def switch(on):
    cache = load()
    cache.pop("off", None)
    if not on:
        cache["off"] = True
    save(cache)


def row(network):
    """doctor's (level, "version", detail); a request only when `network`."""
    registry, hint, _ = method()
    if registry is None:
        return "ok", "version", "%s, a clone: not checked; update: %s" % (__version__, hint)
    cache = load()
    why = off_reason(cache)
    if why:
        return "ok", "version", "%s; the update check is off: %s" % (__version__, why)
    cache = check(network)
    latest = newer(cache)
    if latest:
        return "warn", "version", "%s available, %s installed; upgrade: %s, then solo-sdd install" % (latest, __version__, hint)
    if "error" in cache or "latest" not in cache:
        return "ok", "version", "%s; the latest is unknown: %s" % (__version__, cache.get("error", "not checked yet"))
    return "ok", "version", "%s is the latest" % __version__


def run(argv, cwd=None, capture=False):
    """The only process call of the update: (exit code, output when captured); its output streams otherwise."""
    sys.stdout.flush()
    try:
        p = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=capture, text=True)
    except OSError as e:
        print("fail: cannot run %s: %s" % (argv[0], e.strerror))
        return 127, ""
    return p.returncode, (p.stdout + p.stderr) if capture else ""


def program(*args):
    """argv of the solo-sdd installed in this package folder, the upgraded one after an upgrade."""
    return [sys.executable, "-c", BOOT, PACKAGE, *args]


def confirm(question):
    try:
        return input(question + " [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def update(version, root=None):
    """The update steps off the full screen: the upgrade, `install` of the upgraded program, then in a project whose
    rules block doctor names as older `init` after a question. True when every step passed; a failed one stops."""
    _, hint, argv = method()
    print("solo-sdd %s -> %s: %s" % (__version__, version, hint))
    code = run(argv)[0]
    if code:
        print("fail: %s exited %d; solo-sdd install did not run" % (hint, code))
        return False
    print("solo-sdd install")
    code = run(program("install"))[0]
    if code:
        print("fail: solo-sdd install exited %d" % code)
        return False
    if root:
        out = run(program("doctor"), cwd=root, capture=True)[1]
        older = any(ln.startswith("warn project-rules: ") and "from an older solo-sdd" in ln for ln in out.splitlines())
        if older and confirm("The solo-sdd block in AGENTS.md is from the older rules. Refresh it with solo-sdd init?"):
            code = run(program("init", root), cwd=root)[0]
            if code:
                print("fail: solo-sdd init exited %d" % code)
                return False
    print("solo-sdd %s is installed; restart solo-sdd: this menu still runs %s" % (version, __version__))
    return True
