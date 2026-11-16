#!/usr/bin/env python3
"""Stand of change cli-menu: bare `solo-sdd` opens the home menu on a terminal.

The first row runs `solo-sdd < /dev/null`. Every other row drives bare `python3 -m solo_sdd` of this tree on a
pseudo-terminal (the vt100 emulator and session of tests/stands/settings-tui.py) in temporary folders, with a
temporary HOME and PATH /usr/bin:/bin, at 120x40 and 40x12, each with and without NO_COLOR.
Prints one PASS or FAIL line per row and `SUMMARY: all rows passed`, exit 1 on a failure.
"""
import importlib.util, os, shutil, subprocess, sys, tempfile, termios, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("settings_tui_stand", os.path.join(HERE, "settings-tui.py"))
tui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tui)

need, flat = tui.need, tui.flat
ENTRIES = ["Project settings", "Integrations and checklists", "Machine", "Changes", "Doctor", "Commands", "Quit"]
results = []


def row(label, fn):
    try:
        fn()
        good, detail = True, ""
    except Exception as e:  # a stand row reports, the next row runs
        good, detail = False, "%s: %s" % (type(e).__name__, e)
    results.append(good)
    print(("PASS " if good else "FAIL ") + label + ("" if good else ": " + detail[-900:]))


def files(d):
    out = {}
    for base, dirs, names in os.walk(d):
        dirs[:] = [n for n in dirs if not (base == d and n == ".git")]
        for n in names:
            with open(os.path.join(base, n), "rb") as f:
                out[os.path.relpath(os.path.join(base, n), d)] = f.read()
    return out


def until(s, cond, limit=10.0):
    end = time.time() + limit
    while not cond(flat(s.term.text())):
        if time.time() > end:
            return False
        s.read(quiet=0.3, limit=1)
    return True


class Place:
    """A temporary HOME and the folders of the rows."""

    def __init__(self, base):
        self.dir = tempfile.mkdtemp(dir=base)
        self.home = os.path.join(self.dir, "home")
        os.makedirs(self.home)
        self.env = {"HOME": self.home, "PATH": "/usr/bin:/bin"}

    def sdd(self, cwd, *args):
        env = dict(os.environ, PYTHONPATH=ROOT, **self.env)
        p = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=cwd, env=env, capture_output=True,
                           text=True, stdin=subprocess.DEVNULL, timeout=120)
        return p.returncode, p.stdout + p.stderr

    def folder(self, name, git=True):
        d = os.path.join(self.dir, name)
        os.makedirs(d)
        if git:
            subprocess.run(["git", "init", "-q", "-b", "main", d], check=True)
            subprocess.run(["git", "-C", d, "config", "maintenance.auto", "false"], check=True)
        return d

    def project(self):
        d = self.folder("project")
        need(self.sdd(d, "init", "--yes")[0] == 0, "init --yes")
        for cid in ("alpha", "beta"):
            need(self.sdd(d, "new", cid)[0] == 0, "new " + cid)
            with open(os.path.join(d, "solo-sdd", "changes", cid, "tasks.md"), "w") as f:
                f.write("## 1. Work\n\n- [x] 1.1 one\n- [ ] 1.2 two\n")
        open(os.path.join(d, "solo-sdd", "changes", "alpha", "CLAIM"), "w").close()
        return d


def bare(base):
    p = Place(base)
    code, out = p.sdd(p.dir)
    need(code == 2 and "solo-sdd commands" in out, "the command list and code 2: %s %s" % (code, out[:200]))


def run_size(base, rows, cols, extra, tag):
    def session(p, cwd):
        return tui.Session(cwd, rows, cols, dict(p.env, **extra), args=())

    def walk(s, upto):
        """The screens seen while Down reaches entry upto; a low screen windows the entries."""
        seen = s.term.text()
        for _ in range(upto):
            seen += "\n" + s.send("down")
        return seen

    def back_on_menu(s, p):
        need(until(s, lambda t: "Enter open" in t and "open changes" in t), "back on the menu", s.term.text())

    def header():
        p = Place(base)
        d = p.project()
        mode = p.sdd(d, "config", "get", "mode")[1].split()[0]
        s = session(p, d)
        try:
            t = flat(s.term.text())
            version = p.sdd(d, "--version")[1].strip()
            folder = d if len(d) < cols else "..." + d[len(d) - (cols - 4):]  # a narrow screen keeps the path's end
            for part in (folder, "solo-sdd " + version, "2 open changes, mode %s" % mode):
                need(part in t, "the header names " + part, s.term.text())
            seen = walk(s, len(ENTRIES) - 1)
            for e in ENTRIES:
                need("> " + e in seen, "the entry " + e, seen)
        finally:
            s.close()

    def entry(name, check):
        def fn():
            p = Place(base)
            d = p.project()
            s = session(p, d)
            try:
                walk(s, ENTRIES.index(name))
                s.send("enter")
                check(s, p, d)
            finally:
                s.close()
        return fn

    def settings_screen(s, p, d):
        need(until(s, lambda t: "solo-sdd settings" in t and "Enter edit" in t), "the settings screen", s.term.text())
        s.send("q")
        back_on_menu(s, p)

    def lists_screen(s, p, d):
        need(until(s, lambda t: "Integrations:" in t and "Space switch" in t), "the Integrations section",
             s.term.text())
        s.send("c")
        need(until(s, lambda t: "Checklists:" in t), "c opens the Checklists section", s.term.text())
        s.send("q")
        back_on_menu(s, p)

    def machine_screen(s, p, d):
        need(until(s, lambda t: "Machine" in t and "a apply" in t), "the Machine section", s.term.text())
        s.send("q")
        back_on_menu(s, p)

    def changes_view(s, p, d):
        before = files(d)
        need(until(s, lambda t: "alpha 1/2 CLAIM" in t and "beta 1/2" in t), "the two rows", s.term.text())
        for key in ("enter", "space", "d", "a", "e", "s", "y", "backspace"):
            s.send(key)
        need("alpha 1/2 CLAIM" in flat(s.term.text()), "still the changes", s.term.text())
        need(files(d) == before, "no key edits them")
        s.send("q")
        back_on_menu(s, p)

    def doctor_view(s, p, d):
        need(until(s, lambda t: "Doctor:" in t and "python" in t), "the doctor lines", s.term.text())
        s.send("q")
        back_on_menu(s, p)

    def commands_view(s, p, d):
        need(until(s, lambda t: "solo-sdd commands" in t), "the command list", s.term.text())
        s.send("q")
        back_on_menu(s, p)

    def echoes(s):
        fd = os.open(s.name, os.O_RDWR | os.O_NOCTTY)
        try:
            lflag = termios.tcgetattr(fd)[3]
        finally:
            os.close(fd)
        need(lflag & termios.ECHO and lflag & termios.ICANON, "the terminal echoes again")

    def quit_entry(s, p, d):
        need(s.wait() == 0, "Quit exits with code 0")
        echoes(s)

    def quit_key():
        p = Place(base)
        d = p.project()
        s = session(p, d)
        try:
            s.send("q")
            need(s.wait() == 0, "q exits with code 0")
            echoes(s)
        finally:
            s.close()

    def prepare():
        p = Place(base)
        d, copy = p.folder("fresh"), p.folder("copy")
        need(p.sdd(copy, "init", "--yes")[0] == 0, "init --yes in the copy")
        s = session(p, d)
        try:
            need("> Prepare this folder" in s.term.text(), "the entry", s.term.text())
            s.send("enter")
            for question in ("mode (", "agents (", "delivery.mode ("):
                need(until(s, lambda t: question in t), "the question " + question, s.term.text())
                s.send("enter")
            need(until(s, lambda t: "Enter returns to the menu" in t), "init done", s.term.text())
            s.send("enter")
            need(until(s, lambda t: "> Project settings" in t and "0 open changes" in t), "the project entries",
                 s.term.text())
            with open(os.path.join(d, "solo-sdd", "config"), "rb") as a, \
                    open(os.path.join(copy, "solo-sdd", "config"), "rb") as b:
                need(a.read() == b.read(), "solo-sdd/config as init --yes writes it")
        finally:
            s.close()

    def not_git():
        p = Place(base)
        d = p.folder("plain", git=False)
        s = session(p, d)
        try:
            s.send("enter")
            need(until(s, lambda t: "not a git repository: git init" in t), "the refusal", s.term.text())
            need(os.listdir(d) == [], "nothing written: %s" % os.listdir(d))
            need("> Prepare this folder" in s.term.text() and s.proc.poll() is None, "the menu stays", s.term.text())
        finally:
            s.close()

    def openspec_only():
        p = Place(base)
        d = p.folder("legacy")
        os.makedirs(os.path.join(d, "openspec", "specs"))
        with open(os.path.join(d, "openspec", "project.md"), "w") as f:
            f.write("# legacy\n")
        before = files(d)
        s = session(p, d)
        try:
            need(until(s, lambda t: "solo-sdd import openspec" in t), "the import hint", s.term.text())
            need("Prepare this folder" not in s.term.text(), "no Prepare entry", s.term.text())
            s.send("q")
            need(s.wait() == 0 and files(d) == before, "the folder keeps its files and bytes")
        finally:
            s.close()

    for label, fn in (("home menu in a project", header),
                      ("Project settings", entry("Project settings", settings_screen)),
                      ("Integrations and checklists", entry("Integrations and checklists", lists_screen)),
                      ("Machine", entry("Machine", machine_screen)),
                      ("Changes", entry("Changes", changes_view)),
                      ("Doctor", entry("Doctor", doctor_view)),
                      ("Commands", entry("Commands", commands_view)),
                      ("Quit", entry("Quit", quit_entry)), ("q on the menu", quit_key),
                      ("Prepare this folder", prepare), ("not a git repository", not_git),
                      ("only openspec/", openspec_only)):
        row("%dx%d %s: %s" % (cols, rows, tag, label), fn)


def main():
    base = tempfile.mkdtemp(prefix="cli-menu-")
    try:
        row("solo-sdd < /dev/null", lambda: bare(base))
        for rows, cols in ((40, 120), (12, 40)):
            for extra, tag in (({}, "colour"), ({"NO_COLOR": "1"}, "NO_COLOR")):
                run_size(base, rows, cols, extra, tag)
    finally:
        shutil.rmtree(base, True)
    print("SUMMARY: all rows passed" if all(results) else "SUMMARY: %d of %d rows failed" % (
        results.count(False), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
