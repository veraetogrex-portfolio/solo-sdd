#!/usr/bin/env python3
"""Stand of change settings-tui: `solo-sdd settings` driven through a pseudo-terminal.

Each row starts `python3 -m solo_sdd settings` of this tree in a temporary git repository prepared by `init --yes`,
on a pseudo-terminal of the row's size, sends keys and reads the screen through a small vt100 emulator (TERM=vt100,
so the escape sequences curses sends stay few) and the config file. The rows run at 120x40 and 40x12, each with and
without NO_COLOR; one more row edits and saves under TERM=xterm-256color and checks only the file.
Prints one PASS or FAIL line per row and `SUMMARY: all rows passed`, exit 1 on a failure.
"""
import fcntl, os, select, shutil, struct, subprocess, sys, tempfile, termios, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from solo_sdd import settings, settings_ui  # noqa: E402

KEYS = {"up": "\x1bOA", "down": "\x1bOB", "enter": "\r", "esc": "\x1b", "space": " ", "backspace": "\x7f",
        "ctrl-c": "\x03"}
results = []


class Term:
    """The vt100 subset curses uses here: cursor moves, erase, scroll region, index; attributes are ignored."""

    def __init__(self, rows, cols):
        self.buf = ""
        self.resize(rows, cols)

    def resize(self, rows, cols):
        self.rows, self.cols = rows, cols
        self.grid = [[" "] * cols for _ in range(rows)]
        self.y = self.x = 0
        self.top, self.bot, self.saved = 0, rows - 1, (0, 0)

    def text(self):
        return "\n".join("".join(r).rstrip() for r in self.grid)

    def clamp(self):
        self.y = max(0, min(self.rows - 1, self.y))
        self.x = max(0, min(self.cols - 1, self.x))

    def scroll(self, n, top=None):
        top = self.top if top is None else top
        for _ in range(n):
            del self.grid[top]
            self.grid.insert(self.bot, [" "] * self.cols)

    def scroll_down(self, n, top=None):
        top = self.top if top is None else top
        for _ in range(n):
            del self.grid[self.bot]
            self.grid.insert(top, [" "] * self.cols)

    def index(self):
        if self.y == self.bot:
            self.scroll(1)
        elif self.y < self.rows - 1:
            self.y += 1

    def put(self, c):
        if self.x >= self.cols:  # xenl: the wrap happens on the next character
            self.x = 0
            self.index()
        self.grid[self.y][self.x] = c
        self.x += 1

    def csi(self, params, final):
        if params.startswith("?"):
            return
        args = [int(p) if p.isdigit() else 0 for p in params.split(";")] if params else []
        a = args[0] if args else 0
        n = max(1, a)
        row = self.grid[self.y]
        if final in "Hf":
            self.y, self.x = (a or 1) - 1, ((args[1] if len(args) > 1 else 0) or 1) - 1
            self.clamp()
        elif final in "ABCDGd":
            self.y, self.x = {"A": (self.y - n, self.x), "B": (self.y + n, self.x), "C": (self.y, self.x + n),
                              "D": (self.y, min(self.x, self.cols - 1) - n), "G": (self.y, n - 1),
                              "d": (n - 1, self.x)}[final]
            self.clamp()
        elif final == "K":
            x = min(self.x, self.cols)
            span = range(x, self.cols) if a == 0 else range(0, x + 1) if a == 1 else range(self.cols)
            for i in span:
                if i < self.cols:
                    row[i] = " "
        elif final == "J":
            if a == 2:
                self.grid = [[" "] * self.cols for _ in range(self.rows)]
            else:
                self.csi("1" if a == 1 else "", "K")
                for r in (range(self.y + 1, self.rows) if a == 0 else range(0, self.y)):
                    self.grid[r] = [" "] * self.cols
        elif final == "r":
            self.top, self.bot = (a or 1) - 1, ((args[1] if len(args) > 1 else 0) or self.rows) - 1
            self.y = self.x = 0
        elif final in "LM" and self.top <= self.y <= self.bot:
            (self.scroll_down if final == "L" else self.scroll)(n, self.y)
        elif final in "ST":
            (self.scroll if final == "S" else self.scroll_down)(n)
        elif final == "@":
            row[self.x:self.x] = [" "] * n
            del row[self.cols:]
        elif final == "P":
            del row[self.x:self.x + n]
            row.extend([" "] * (self.cols - len(row)))
        elif final == "X":
            for i in range(self.x, min(self.cols, self.x + n)):
                row[i] = " "
        elif final == "b" and self.x > 0:
            for _ in range(n):
                self.put(row[self.x - 1])

    def feed(self, data):
        s, i = self.buf + data, 0
        while i < len(s):
            c = s[i]
            if c == "\x1b":
                if i + 1 >= len(s):
                    break
                d = s[i + 1]
                if d == "[":
                    j = i + 2
                    while j < len(s) and not "\x40" <= s[j] <= "\x7e":
                        j += 1
                    if j >= len(s):
                        break
                    self.csi(s[i + 2:j], s[j])
                    i = j + 1
                    continue
                if d in "()":
                    if i + 2 >= len(s):
                        break
                    i += 3
                    continue
                if d == "M":
                    if self.y == self.top:
                        self.scroll_down(1)
                    elif self.y > 0:
                        self.y -= 1
                elif d in "DE":
                    self.index()
                    if d == "E":
                        self.x = 0
                elif d == "7":
                    self.saved = (self.y, self.x)
                elif d == "8":
                    self.y, self.x = self.saved
                i += 2
                continue
            if c == "\r":
                self.x = 0
            elif c == "\n":
                self.index()
            elif c == "\b":
                self.x = max(0, min(self.x, self.cols) - 1)
            elif c >= " ":
                self.put(c)
            i += 1
        self.buf = s[i:]


class Session:
    def __init__(self, cwd, rows, cols, env=None, args=("settings",)):
        self.master, self.slave = os.openpty()
        self.name = os.ttyname(self.slave)
        self.size(rows, cols)
        self.term = Term(rows, cols)
        full = dict(os.environ, PYTHONPATH=ROOT, TERM="vt100", NCURSES_NO_PADDING="1")
        full.pop("NO_COLOR", None)
        full.update(env or {})
        self.proc = subprocess.Popen([sys.executable, "-m", "solo_sdd", *args], cwd=cwd, env=full, stdin=self.slave,
                                     stdout=self.slave, stderr=self.slave, start_new_session=True,
                                     preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0))
        self.read(first=True)

    def size(self, rows, cols):
        fcntl.ioctl(self.slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

    def read(self, first=False, quiet=0.25, limit=15):
        end, seen = time.time() + limit, not first
        while time.time() < end:
            ready = select.select([self.master], [], [], quiet if seen else 1)[0]
            if not ready:
                if seen or self.proc.poll() is not None:
                    return
                continue
            try:
                data = os.read(self.master, 65536)
            except OSError:
                return
            seen = True
            self.term.feed(data.decode("utf-8", "replace"))

    def send(self, *keys):
        for k in keys:
            os.write(self.master, KEYS.get(k, k).encode())
            if k == "esc":
                time.sleep(0.1)  # ESCDELAY
        self.read()
        return self.term.text()

    def resize(self, rows, cols):
        self.term.resize(rows, cols)
        self.size(rows, cols)
        self.read()

    def wait(self, timeout=10):
        try:
            return self.proc.wait(timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            return self.proc.wait()

    def close(self):
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        os.close(self.master)
        os.close(self.slave)


def sdd(cwd, *args):
    p = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=cwd, env=dict(os.environ, PYTHONPATH=ROOT),
                       capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
    return p.returncode, p.stdout + p.stderr


def project(base, extra=""):
    d = tempfile.mkdtemp(dir=base)
    subprocess.run(["git", "init", "-q", "-b", "main", d], check=True)
    subprocess.run(["git", "-C", d, "config", "maintenance.auto", "false"], check=True)
    assert sdd(d, "init", "--yes")[0] == 0
    for key, value in (("agents", "claude, codex, other"), ("process.review-rounds", "4")):
        assert sdd(d, "config", "set", key, value)[0] == 0
    if extra:
        with open(os.path.join(d, settings.SETTINGS_FILE), "a", encoding="utf-8", newline="") as f:
            f.write(extra)
    return d


def config(d):
    with open(os.path.join(d, settings.SETTINGS_FILE), encoding="utf-8", newline="") as f:
        return f.read()


def row(label, fn):
    try:
        detail = fn()
        good = detail is None
    except Exception as e:  # a stand row reports, the next row runs
        good, detail = False, "%s: %s" % (type(e).__name__, e)
    results.append(good)
    print(("PASS " if good else "FAIL ") + label + ("" if good else ": " + str(detail)[-900:]))


def to(s, key):
    return s.send(*["down"] * settings_ui.KEYS.index(key))


def flat(text):
    """The screen with its line breaks and runs of spaces collapsed: a wrapped footer or message reads whole."""
    return " ".join(text.split())


def need(cond, what, screen=""):
    if not cond:
        raise AssertionError(what + ("\n--- screen ---\n" + screen if screen else ""))


def run_size(base, rows, cols, env, tag):
    big = cols >= 80
    about = {k: settings.ABOUT[k][1] for k in settings_ui.KEYS}

    def opened():
        d = project(base)
        s = Session(d, rows, cols, env)
        try:
            t = s.term.text()
            need("solo-sdd settings" in t and settings_ui.KEYS[0] in t, "title and the first key", t)
            need(about[settings_ui.KEYS[0]][:cols - 2] in t, "the first key's description", t)
            if big:
                need(all(k in t for k in settings_ui.KEYS) and "delivery" in t, "every key and the groups", t)
            t = s.send("down")
            need(about[settings_ui.KEYS[1]][:cols - 2] in t, "Down: the next key's description", t)
            row = settings.describe(settings_ui.KEYS[1], {})
            need("default %s, team default %s" % (row["default"] or "(none)", row["team_default"] or "(same)") in t,
                 "Down: the default and team default", t)
            for word in ("move", "Enter edit", "r reset", "s save", "q quit"):
                need(word in flat(t), "the list footer names " + word, t)
            t = s.send("up")
            need(about[settings_ui.KEYS[0]][:cols - 2] in t, "Up: back to the first key", t)
        finally:
            s.close()

    def edits_and_save():
        d = project(base)
        before = config(d)
        s = Session(d, rows, cols, env)
        try:
            to(s, "delivery.mode")
            t = s.send("enter")
            need("Enter set" in flat(t) and "Esc back" in flat(t), "the pick footer", t)
            t = s.send("down", "enter")
            need("needs a CI workflow"[:cols - 2] in t or "delivery.mode: pr needs"[:cols - 2] in t, "the CI warning", t)
            if big:
                need(any("delivery.mode" in ln and " pr " in ln and "*unsaved" in ln for ln in t.splitlines()),
                     "pr marked unsaved", t)
            s.send(*["up"] * settings_ui.KEYS.index("delivery.mode"))
            to(s, "dispatch.limit")
            t = s.send("enter")
            need("Type a value" in flat(t), "the entry footer", t)
            t = s.send("backspace", "0", "enter")
            need("takes a whole number"[:cols - 20] in t, "the reason for 0", t)
            t = s.send("enter", "backspace", "3", "enter")
            if big:
                need(any("dispatch.limit" in ln and " 3 " in ln and "*unsaved" in ln for ln in t.splitlines()), "3", t)
            s.send(*["up"] * settings_ui.KEYS.index("dispatch.limit"))
            to(s, "agents")
            t = s.send("enter")
            need("Space tick" in flat(t), "the checkbox footer", t)
            t = s.send("down", "space", "enter")
            if big:
                need(any("claude, other" in ln and "*unsaved" in ln for ln in t.splitlines()), "agents", t)
            s.send(*["up"] * settings_ui.KEYS.index("agents"))
            to(s, "process.review-rounds")
            t = s.send("r")
            if big:
                need(any("process.review-rounds" in ln and " 3 " in ln and "[default]" in ln for ln in t.splitlines()),
                     "reset to the default", t)
            t = s.send("s")
            need("Write these 4 keys" in flat(t) and "dispatch.limit: 2 -> 3" in t and "y write" in flat(t),
                 "the confirmation list and its footer", t)
            t = s.send("y")
            need("saved:" in t, "saved", t)
            after = config(d)
            changed = {ln.partition(":")[0].strip() for ln in set(before.splitlines()) ^ set(after.splitlines())}
            need(changed == {"delivery.mode", "dispatch.limit", "agents", "process.review-rounds"},
                 "only the edited lines differ: %s" % sorted(changed))
            listed = sdd(d, "config", "list")[1].splitlines()
            need({"delivery.mode pr file", "dispatch.limit 3 file", "agents claude, other file",
                  "process.review-rounds 3 default"} <= set(listed), "config list: %s" % listed)
            need(s.send("q") is not None and s.wait() == 0, "q leaves with code 0 after save")
        finally:
            s.close()

    def quit_and_ctrl_c():
        d = project(base)
        before = config(d)
        s = Session(d, rows, cols, env)
        try:
            to(s, "dispatch.limit")
            t = s.send("enter", "backspace", "4", "enter", "q")
            need("Unsaved edits" in t and "d discard" in flat(t), "the quit question and its footer", t)
            t = s.send("b")
            need("Enter edit" in flat(t), "back to the list", t)
            s.send("ctrl-c")
            code = s.wait()
            need(code == 130, "Ctrl-C exit code %s" % code)
            fd = os.open(s.name, os.O_RDWR | os.O_NOCTTY)  # the session's descriptors are revoked when it ends
            try:
                lflag = termios.tcgetattr(fd)[3]
            finally:
                os.close(fd)
            need(lflag & termios.ECHO and lflag & termios.ICANON, "the terminal echoes again")
            need(config(d) == before, "Ctrl-C wrote nothing")
        finally:
            s.close()

    def changed_on_disk():
        d = project(base)
        s = Session(d, rows, cols, env)
        try:
            to(s, "dispatch.limit")
            s.send("enter", "backspace", "5", "enter")
            with open(os.path.join(d, settings.SETTINGS_FILE), "a", encoding="utf-8") as f:
                f.write("# another process\n")
            disk = config(d)
            t = s.send("s", "y")
            need("changed on disk"[:cols - 20] in t.replace("\n", " ") or "changed on" in t, "the message", t)
            need(config(d) == disk, "nothing written")
        finally:
            s.close()

    def broken():
        d = project(base)
        with open(os.path.join(d, settings.SETTINGS_FILE), "w", encoding="utf-8") as f:
            f.write("mode: solo\n\n# c\ndelivery.mode pr\n")
        s = Session(d, rows, cols, env)
        try:
            t = s.term.text()
            need("solo-sdd/config:4" in t, "file and line", t)
            s.send("enter", "down", "s")
            need(s.proc.poll() is None and config(d) == "mode: solo\n\n# c\ndelivery.mode pr\n", "nothing edited")
            s.send("q")
            need(s.wait() == 0, "q leaves")
        finally:
            s.close()

    def escaped():
        d = project(base, "delivery.base: main\x1bx\n")
        s = Session(d, rows, cols, env)
        try:
            to(s, "delivery.base")
            t = s.term.text()
            need(("main\\x1bx" if big else "main\\x") in t and "\x1b" not in t, "the ESC shown as \\x1b", t)
        finally:
            s.close()

    def overrides():
        d = project(base)
        assert sdd(d, "config", "set", "delivery.mode", "pr")[0] == 0
        with open(os.path.join(d, "AGENTS.md"), "a", encoding="utf-8") as f:
            f.write("\n## Delivery\n\n- Mode: local\n")
        s = Session(d, rows, cols, env)
        try:
            t = to(s, "delivery.mode")
            if big:
                need(any("delivery.mode" in ln and "overrides AGENTS.md: local" in ln for ln in t.splitlines()),
                     "the row mark", t)
            need("overrides the Delivery" in flat(t), "the detail line", t)
        finally:
            s.close()

    for label, fn in (("open, Down, Up", opened), ("AGENTS.md overridden", overrides), ("edit by type, reset, save", edits_and_save),
                      ("quit asks, Ctrl-C", quit_and_ctrl_c), ("changed on disk", changed_on_disk),
                      ("broken file read-only", broken), ("ESC in a value", escaped)):
        row("%dx%d %s: %s" % (cols, rows, tag, label), fn)


def main():
    base = tempfile.mkdtemp(prefix="settings-tui-")
    try:
        for rows, cols in ((40, 120), (12, 40)):
            for env, tag in (({}, "colour"), ({"NO_COLOR": "1"}, "NO_COLOR")):
                run_size(base, rows, cols, env, tag)

        def small_then_resize():
            s = Session(project(base), 40, 30)
            try:
                need("Terminal too small" in s.term.text(), "the request to enlarge", s.term.text())
                s.resize(24, 80)
                need("mode" in s.term.text() and "Terminal too small" not in s.term.text(), "the list after resize",
                     s.term.text())
            finally:
                s.close()
        row("30 columns, then 80", small_then_resize)

        def refusals():
            d = project(base)
            code, out = sdd(d, "settings")
            need((code, out) == (1, settings_ui.NO_TERMINAL + "\n"), "stdin closed: %s %r" % (code, out))
            s = Session(d, 24, 80, {"TERM": "dumb"})
            need(s.wait() == 1 and settings_ui.NO_TERMINAL in " ".join(s.term.text().split()), "TERM=dumb",
                 s.term.text())
            s.close()
            s = Session(d, 24, 80, {"TERM": "no-such-terminal"})
            need(s.wait() == 1 and settings_ui.NO_TERMINAL in flat(s.term.text()), "an unknown TERM", s.term.text())
            s.close()
            plain = tempfile.mkdtemp(dir=base)
            s = Session(plain, 24, 80)
            need(s.wait() == 1 and "solo-sdd init" in s.term.text(), "no tree", s.term.text())
            s.close()
        row("refusals: no terminal, TERM=dumb, an unknown TERM, no tree", refusals)

        def xterm():
            d = project(base)
            s = Session(d, 40, 120, {"TERM": "xterm-256color"})
            try:
                to(s, "dispatch.limit")
                s.send("enter", "backspace", "3", "enter", "s", "y", "q")
                need(s.wait() == 0 and "dispatch.limit: 3" in config(d), "saved under xterm-256color")
            finally:
                s.close()
        row("xterm-256color: edit and save", xterm)
    finally:
        shutil.rmtree(base, True)
    print("SUMMARY: all rows passed" if all(results) else "SUMMARY: %d of %d rows failed" % (
        results.count(False), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
