#!/usr/bin/env python3
"""Stand of change update-check: the version check and the update from the home menu, end to end.

Everything lives in one temporary folder T, removed at the end:
  - HOME is T/home; a named pipe under a file:// address stands in for PyPI (the address through SOLO_SDD_REGISTRY),
   logging every read as a request;
  - HOME/.local/share/uv/tools/solo-sdd is a virtual environment holding solo-sdd 0.2.0 laid out from this tree as
    the wheel lays it out (solo_sdd/ with its data/ folder), so the install method is uv;
  - a fake `uv` first on PATH logs its arguments and replaces that package with a 0.3.0 build of the same tree.
The menu runs from that environment on a pseudo-terminal (the vt100 emulator of tests/stands/settings-tui.py): every
row at 120x40, the menu rows also at 40x12 and both with NO_COLOR=1.
Prints one PASS or FAIL line per row and `SUMMARY: all rows passed`, exit 1 on a failure.
"""
import errno, fcntl, importlib.util, json, os, re, shutil, subprocess, sys, tempfile, termios, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("settings_tui_stand", os.path.join(HERE, "settings-tui.py"))
tui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tui)
sys.path.insert(0, ROOT)
from solo_sdd import rules_block  # noqa: E402

need, flat = tui.need, tui.flat
DATA = ["skills", "global", "templates", "integrations", "targets.json", "ALGORITHM.md", "sync.py"]
results = []


def row(label, fn):
    try:
        fn()
        good, detail = True, ""
    except Exception as e:  # a stand row reports, the next row runs
        good, detail = False, "%s: %s" % (type(e).__name__, e)
    results.append(good)
    print(("PASS " if good else "FAIL ") + label + ("" if good else ": " + detail[-1200:]), flush=True)


class Registry:
    """The local registry: a named pipe at the PyPI path under a file:// address. Each read the program opens is one
    logged request answered with `body` after `delay` seconds; `stopped` answers nothing (an empty body).
    A pipe, not an HTTP server: a sandboxed session may refuse loopback connections."""

    def __init__(self, base):
        root = os.path.join(base, "registry")
        self.pipe = os.path.join(root, "pypi", "solo-sdd", "json")
        os.makedirs(os.path.dirname(self.pipe))
        os.mkfifo(self.pipe)
        self.address = "file://" + root
        self.body, self.delay, self.stopped, self.log, self.running = b"", 0, False, [], True
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def writer(self):
        """A write end when a reader has the pipe open, else None (ENXIO: no reader)."""
        try:
            return os.open(self.pipe, os.O_WRONLY | os.O_NONBLOCK)
        except OSError as e:
            if e.errno != errno.ENXIO:
                raise
            return None

    def serve(self):
        while self.running:
            fd = self.writer()
            if fd is None:
                time.sleep(0.05)
                continue
            self.log.append("/pypi/solo-sdd/json")  # one reader: one request
            fcntl.fcntl(fd, fcntl.F_SETFL, fcntl.fcntl(fd, fcntl.F_GETFL) & ~os.O_NONBLOCK)
            time.sleep(self.delay)
            with os.fdopen(fd, "wb") as f:
                try:
                    f.write(b"" if self.stopped else self.body)
                except BrokenPipeError:  # the reader stopped at its size limit
                    pass
            while self.running:  # the same reader is not a second request: wait until it has closed the pipe
                fd = self.writer()
                if fd is None:
                    break
                os.close(fd)
                time.sleep(0.05)

    def answer(self, version=None, body=None):
        self.body = body if body is not None else json.dumps({"info": {"version": version}}).encode()

    def close(self):
        self.running = False


def build(dest, version):
    """The package as the wheel lays it out (pyproject force-include), with the given version."""
    pkg = os.path.join(dest, "solo_sdd")
    shutil.copytree(os.path.join(ROOT, "solo_sdd"), pkg, ignore=shutil.ignore_patterns("__pycache__"))
    for name in DATA:
        src = os.path.join(ROOT, name)
        (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(pkg, "data", name))
    with open(os.path.join(pkg, "__init__.py"), "w") as f:
        f.write('__version__ = "%s"\n' % version)


class Place:
    def __init__(self, base, registry):
        self.dir = tempfile.mkdtemp(dir=base)
        self.home = os.path.join(self.dir, "home")
        for d in (".claude", ".codex"):
            os.makedirs(os.path.join(self.home, d))
        self.venv = os.path.join(self.home, ".local", "share", "uv", "tools", "solo-sdd")
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", self.venv], check=True, stdin=subprocess.DEVNULL)
        self.python = os.path.join(self.venv, "bin", "python")
        site = subprocess.run([self.python, "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
                              capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL).stdout.strip()
        build(site, "0.2.0")
        build(os.path.join(self.dir, "next"), "0.3.0")
        self.cache = os.path.join(self.home, ".local", "share", "solo-sdd", "update-check.json")
        self.uvlog = os.path.join(self.dir, "uv.log")
        bindir = os.path.join(self.dir, "bin")
        os.makedirs(bindir)
        with open(os.path.join(bindir, "uv"), "w") as f:
            f.write('#!/bin/sh\necho "$@" >> "%s"\nif [ -e "%s/uv-fail" ]; then echo "uv: upgrade refused by the stand"; exit 1; fi\n'
                    'rm -rf "%s/solo_sdd" && cp -R "%s/next/solo_sdd" "%s/" && echo "Updated solo-sdd v0.2.0 -> v0.3.0"\n'
                    % (self.uvlog, self.dir, site, self.dir, site))
        os.chmod(os.path.join(bindir, "uv"), 0o755)
        self.env = {"HOME": self.home, "PATH": bindir + ":/usr/bin:/bin", "SOLO_SDD_REGISTRY": registry.address,
                    "PYTHONPATH": None, "SOLO_SDD_NO_UPDATE_CHECK": None}
        self.project = os.path.join(self.dir, "project")
        subprocess.run(["git", "init", "-q", "-b", "main", self.project], check=True, stdin=subprocess.DEVNULL)
        need(self.sdd("install")[0] == 0, "install of 0.2.0")
        need(self.sdd("init", "--yes")[0] == 0, "init --yes")

    def sdd(self, *args, extra=None):
        env = dict(os.environ)
        for k, v in dict(self.env, **(extra or {})).items():
            env.pop(k, None) if v is None else env.__setitem__(k, v)
        p = subprocess.run([self.python, "-m", "solo_sdd", *args], cwd=self.project, env=env, capture_output=True,
                           text=True, stdin=subprocess.DEVNULL, timeout=120)
        return p.returncode, p.stdout + p.stderr

    def set_cache(self, **fields):
        os.makedirs(os.path.dirname(self.cache), exist_ok=True)
        with open(self.cache, "w") as f:
            json.dump(fields, f)

    def read_cache(self):
        with open(self.cache, "rb") as f:
            return f.read()

    def uv_calls(self):
        try:
            with open(self.uvlog) as f:
                return f.read().splitlines()
        except FileNotFoundError:
            return []

    def older_rules(self):
        """The project's block as an older solo-sdd left it: one line added, its digest recorded."""
        agents = os.path.join(self.project, "AGENTS.md")
        with open(agents, encoding="utf-8") as f:
            before, body, after = rules_block.parse(f.read())
        old = body.replace("\n", "\nan older rule line\n", 1)
        with open(agents, "w", encoding="utf-8", newline="") as f:
            f.write(before + rules_block.block(old) + after)
        import hashlib
        with open(os.path.join(self.project, "solo-sdd", "rules-block"), "w") as f:
            f.write(hashlib.sha256(old.encode()).hexdigest() + "\n")


class Rec(tui.Term):
    """The emulator that also keeps every byte read: the update steps print off the full screen."""

    def feed(self, data):
        self.raw = getattr(self, "raw", "") + data
        return super().feed(data)

    def plain(self):
        return flat(re.sub(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][A-Z0-9]|\x1b[=>]|\r", " ", getattr(self, "raw", "")))


class Menu(tui.Session):
    """Bare `solo-sdd` of the uv environment on a pseudo-terminal."""

    def __init__(self, place, rows, cols, extra=None):
        self.master, self.slave = os.openpty()
        self.size(rows, cols)
        self.term = Rec(rows, cols)
        env = dict(os.environ, TERM="vt100", NCURSES_NO_PADDING="1")
        env.pop("NO_COLOR", None)
        for k, v in dict(place.env, **(extra or {})).items():
            env.pop(k, None) if v is None else env.__setitem__(k, v)
        self.proc = subprocess.Popen([place.python, "-m", "solo_sdd"], cwd=place.project, env=env, stdin=self.slave,
                                     stdout=self.slave, stderr=self.slave, start_new_session=True,
                                     preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0))
        self.read(first=True)

    def until(self, cond, limit=10.0, raw=False):
        end = time.time() + limit
        while not cond(self.term.plain() if raw else flat(self.term.text())):
            if time.time() > end:
                return False
            self.read(quiet=0.3, limit=1)
        return True

    def to(self, entry):
        for _ in range(12):
            if "> " + entry in flat(self.term.text()):
                return
            self.send("down")
        need(False, "the entry " + entry, self.term.text())


def wait_checked(place, before, limit=6.0):
    end = time.time() + limit
    while time.time() < end:
        if os.path.exists(place.cache) and place.read_cache() != before:
            return True
        time.sleep(0.1)
    return False


def menu_rows(base, registry, rows, cols, extra, tag):
    place = Place(base, registry)

    def notice_after_draw():
        registry.answer("0.3.0")
        registry.delay, registry.log[:] = 1, []  # within the 2 second limit with room for a loaded machine
        s = Menu(place, rows, cols, extra)
        try:
            t = flat(s.term.text())
            need("Enter open" in t and "available" not in t, "the menu draws before the answer", s.term.text())
            need(s.until(lambda t: "0.3.0 available" in t, 8), "the header shows 0.3.0 available", s.term.text())
            need(registry.log == ["/pypi/solo-sdd/json"], "one request to PyPI: %s" % registry.log)
        finally:
            s.close()
            registry.delay = 0

    def update_then_cancel():
        s = Menu(place, rows, cols, extra)
        try:
            need(s.until(lambda t: "0.3.0 available" in t), "the notice", s.term.text())
            s.to("Update to 0.3.0")
            seen = flat(s.send("enter"))
            for _ in range(8):
                seen += " " + flat(s.send("down"))
            for part in ("Runs: uv tool upgrade solo-sdd", "Release notes: "
                         "https://github.com/veraetogrex-portfolio/solo-sdd/releases/tag/v0.3.0", "y update"):
                need("".join(part.split()) in "".join(seen.split()), "the update screen shows " + part, seen)
            need("Enter open" in flat(s.send("n")), "n returns to the menu", s.term.text())
            need(place.uv_calls() == [], "uv did not run: %s" % place.uv_calls())
        finally:
            s.close()

    def skip():
        s = Menu(place, rows, cols, extra)
        try:
            need(s.until(lambda t: "0.3.0 available" in t), "the notice", s.term.text())
            s.to("Skip this version")
            need("0.3.0 skipped" in flat(s.send("enter")), "the skip message", s.term.text())
            need("available" not in flat(s.term.text()), "the notice is gone", s.term.text())
        finally:
            s.close()
        registry.log[:] = []
        s = Menu(place, rows, cols, extra)
        try:
            time.sleep(1)
            s.read()
            need("available" not in flat(s.term.text()), "a reopened menu: no notice for 0.3.0", s.term.text())
        finally:
            s.close()
        cache = json.loads(place.read_cache())
        place.set_cache(**dict(cache, checked=0))
        registry.answer("0.3.1")
        s = Menu(place, rows, cols, extra)
        try:
            need(s.until(lambda t: "0.3.1 available" in t), "0.3.1 available", s.term.text())
        finally:
            s.close()
        place.set_cache(checked=time.time(), latest="0.3.0")
        registry.answer("0.3.0")

    tag = "%dx%d%s" % (cols, rows, ", NO_COLOR" if extra.get("NO_COLOR") else "")
    row("%s: home menu, server answers 0.3.0: drawn first, then 0.3.0 available" % tag, notice_after_draw)
    row("%s: Update to 0.3.0, Enter then cancel: command and link shown, uv not run" % tag, update_then_cancel)
    row("%s: Skip this version: no notice, then 0.3.1 available" % tag, skip)
    return place


def full_rows(base, registry, place):
    def doctor():
        code, out = place.sdd("doctor")
        line = [ln for ln in out.splitlines() if ln.startswith(("ok version:", "warn version:"))]
        need(len(line) == 1 and line[0].startswith("warn version: 0.3.0 available") and "uv tool upgrade solo-sdd" in line[0],
             "doctor: %s" % line)

    def cached():
        registry.stopped, registry.log[:] = True, []
        before = place.read_cache()
        s = Menu(place, 40, 120)
        try:
            need(s.until(lambda t: "0.3.0 available" in t), "the notice from the cache", s.term.text())
            time.sleep(1)
            need(registry.log == [] and place.read_cache() == before, "no request: %s" % registry.log)
        finally:
            s.close()
            registry.stopped = False

    def agent_commands():
        place.set_cache(checked=0, latest="0.3.0")
        before, registry.log[:] = place.read_cache(), []
        for args in (["list"], ["validate", "--all"], ["config", "get", "mode"]):
            place.sdd(*args)
        need(registry.log == [] and place.read_cache() == before, "no request: %s" % registry.log)

    def hostile():
        for body in (json.dumps({"info": {"version": "0.3.0\u001b[2J; rm -rf ~"}}).encode(), b"x" * (2 << 20),
                     b'{"info": 5}'):
            place.set_cache(checked=0)
            registry.answer(body=body)
            before, registry.log[:] = place.read_cache(), []
            s = Menu(place, 40, 120)
            try:
                need(wait_checked(place, before), "the menu asked", str(registry.log))
                time.sleep(0.5)
                s.read()
                t = flat(s.term.text())
                need("Enter open" in t and "solo-sdd 0.2.0" in t, "the screen is not cleared", s.term.text())
                need("available" not in t and "rm -rf" not in s.term.plain(), "no notice", s.term.text())
                cache = json.loads(place.read_cache())
                need(set(cache) == {"checked", "error"} and cache["error"] == "the answer is not a version",
                     "the cache holds nothing of the answer: %s" % cache)
            finally:
                s.close()
        registry.answer("0.3.0")
        place.set_cache(checked=time.time(), latest="0.3.0")

    def switched_off():
        place.set_cache(checked=0, latest="0.3.0")
        registry.log[:] = []
        s = Menu(place, 40, 120, {"SOLO_SDD_NO_UPDATE_CHECK": "1"})
        try:
            time.sleep(1.5)
            s.read()
            need("available" not in flat(s.term.text()), "no notice", s.term.text())
        finally:
            s.close()
        out = place.sdd("doctor", extra={"SOLO_SDD_NO_UPDATE_CHECK": "1"})[1]
        need("ok version: 0.2.0; the update check is off: SOLO_SDD_NO_UPDATE_CHECK=1" in out, out)
        need(registry.log == [], "no request: %s" % registry.log)

    def machine_switch():
        s = Menu(place, 40, 120)
        try:
            s.to("Machine")
            s.send("enter")
            need(s.until(lambda t: "update check" in t), "the switch row", s.term.text())
            for _ in range(12):
                if "> [x] update check" in flat(s.term.text()):
                    break
                s.send("down")
            need("[ ] update check" in flat(s.send("space")), "switched off", s.term.text())
        finally:
            s.close()
        place.set_cache(**dict(json.loads(place.read_cache()), checked=0))
        registry.log[:] = []
        s = Menu(place, 40, 120)
        try:
            time.sleep(1.5)
            s.read()
            need(registry.log == [], "no request: %s" % registry.log)
        finally:
            s.close()
        place.set_cache(checked=time.time(), latest="0.3.0")

    def upgrade_fails():
        open(os.path.join(place.dir, "uv-fail"), "w").close()
        s = Menu(place, 40, 120)
        try:
            need(s.until(lambda t: "0.3.0 available" in t), "the notice", s.term.text())
            s.to("Update to 0.3.0")
            s.send("enter", "y")
            need(s.until(lambda t: "Enter returns to the menu" in t, raw=True), "the steps end", s.term.plain())
            out = s.term.plain()
            need("uv: upgrade refused by the stand" in out and "fail: uv tool upgrade solo-sdd exited 1" in out, out)
            need("solo-sdd install did not run" in out, out)
        finally:
            s.close()
        os.remove(os.path.join(place.dir, "uv-fail"))
        status = place.sdd("status")[1]
        need(" 0.2.0" in status.splitlines()[0] and len(place.uv_calls()) == 1, "the layout stays 0.2.0: " + status[:200])
        os.remove(place.uvlog)

    def upgrade():
        place.older_rules()
        need(place.sdd("doctor")[1].count("warn project-rules: ") == 1, "the block is older before")
        s = Menu(place, 40, 120)
        try:
            need(s.until(lambda t: "0.3.0 available" in t), "the notice", s.term.text())
            s.to("Update to 0.3.0")
            s.send("enter", "y")
            need(s.until(lambda t: "Refresh it with solo-sdd init? [y/N]" in t, 60, raw=True), "the init question",
                 s.term.plain())
            s.send("y\r")
            need(s.until(lambda t: "restart solo-sdd" in t, 60, raw=True), "the restart request", s.term.plain())
            need(s.wait(30) == 0, "solo-sdd exits after asking to restart")
        finally:
            s.close()
        need(place.uv_calls() == ["tool upgrade solo-sdd"], "uv ran once: %s" % place.uv_calls())
        need(place.sdd("--version")[1].strip() == "0.3.0", "--version prints 0.3.0")
        need(" 0.3.0" in place.sdd("status")[1].splitlines()[0], "status shows the 0.3.0 layout")
        out = place.sdd("doctor")[1]
        need("ok project-rules: " in out, "doctor: ok project-rules", out)

    row("120x40: solo-sdd doctor: warn version with uv tool upgrade solo-sdd", doctor)
    row("120x40: home menu again within 24 hours, server stopped: notice from the cache, no request", cached)
    row("120x40: list, validate --all, config get mode with a stale cache: no request", agent_commands)
    row("120x40: hostile version, 2 MB body, {\"info\": 5}: no notice, nothing cached, screen kept", hostile)
    row("120x40: SOLO_SDD_NO_UPDATE_CHECK=1: no request, doctor names the check as off", switched_off)
    row("120x40: Machine update check switch off, reopen: no request", machine_switch)
    row("120x40: fake uv exiting 1: its output shown, layout stays 0.2.0", upgrade_fails)
    row("120x40: Update to 0.3.0 in a project with older rules: uv once, 0.3.0 laid out, init, restart", upgrade)


def main():
    base = tempfile.mkdtemp(prefix="update-check-")
    registry = Registry(base)
    try:
        place = menu_rows(base, registry, 40, 120, {}, "")
        full_rows(base, registry, place)
        for rows, cols, extra in ((40, 120, {"NO_COLOR": "1"}), (12, 40, {}), (12, 40, {"NO_COLOR": "1"})):
            menu_rows(base, registry, rows, cols, extra, "")
    finally:
        if not registry.thread.is_alive():  # a dead registry would let every "no request" row pass
            row("the local registry served every row", lambda: need(False, "its thread ended"))
        registry.close()
        shutil.rmtree(base, True)
    if all(results):
        print("SUMMARY: all rows passed")
        return 0
    print("SUMMARY: %d of %d rows failed" % (results.count(False), len(results)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
