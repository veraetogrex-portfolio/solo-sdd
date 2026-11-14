#!/usr/bin/env python3
"""Stand of change settings-tui-lists: the Integrations and Checklists sections of `solo-sdd settings`.

Each row starts `python3 -m solo_sdd settings` of this tree on a pseudo-terminal (the vt100 emulator and the session
of tests/stands/settings-tui.py) in a temporary git repository after `init --yes`, with a temporary HOME, a project
integration `demo-check` that has rules and a broken one `bad-check`. The rows run at 120x40 and 40x12, each with and
without NO_COLOR. Prints one PASS or FAIL line per row and `SUMMARY: all rows passed`, exit 1 on a failure.
"""
import importlib.util, os, shutil, stat, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("settings_tui_stand", os.path.join(HERE, "settings-tui.py"))
tui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tui)
sys.path.insert(0, ROOT)
from solo_sdd import settings  # noqa: E402

results = []
need, flat, row_of = tui.need, tui.flat, None


def sdd(cwd, home, *args):
    p = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=cwd, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=ROOT, HOME=home), stdin=subprocess.DEVNULL, timeout=120)
    return p.returncode, p.stdout + p.stderr


def integration(base, name, broken=False):
    d = os.path.join(base, name)
    os.makedirs(d)
    with open(os.path.join(d, "integration"), "w", encoding="utf-8") as f:
        f.write("name: %s\nabout: the %s stand check\n%smaterial: m.md\n" % (name, name, "" if broken else "points: review\n"))
    with open(os.path.join(d, "m.md"), "w", encoding="utf-8") as f:
        f.write("# material\n")
    with open(os.path.join(d, "rules.md"), "w", encoding="utf-8") as f:
        f.write("- Rule of %s.\n" % name)


def project(base, home):
    d = tempfile.mkdtemp(dir=base)
    subprocess.run(["git", "init", "-q", "-b", "main", d], check=True)
    subprocess.run(["git", "-C", d, "config", "maintenance.auto", "false"], check=True)
    assert sdd(d, home, "init", "--yes")[0] == 0
    for name, broken in (("demo-check", False), ("bad-check", True)):
        integration(os.path.join(d, "solo-sdd", "integrations"), name, broken)
    return d


def read(d, name):
    with open(os.path.join(d, name), "rb") as f:
        return f.read()


def row(label, fn):
    try:
        fn()
        good, detail = True, ""
    except Exception as e:  # a stand row reports, the next row runs
        good, detail = False, "%s: %s" % (type(e).__name__, e)
    results.append(good)
    print(("PASS " if good else "FAIL ") + label + ("" if good else ": " + detail[-900:]))


def until(s, cond, limit=3.0):
    """True once cond holds for the screen; curses may still be drawing when a read goes quiet."""
    end = tui.time.time() + limit
    while not cond(s.term.text()):
        if tui.time.time() > end:
            return False
        s.read(quiet=0.2, limit=0.5)
    return True


ORDER = ["antislop", "bad-check", "demo-check", "security-audit"]  # by name, as integrations list sorts them


def run_size(base, home, rows, cols, extra, tag):
    big = cols >= 80
    env = dict(extra, HOME=home)

    def session(d):
        return tui.Session(d, rows, cols, env)

    def pick(s, name):
        return s.send("i", *["down"] * ORDER.index(name))

    def section():
        d = project(base, home)
        s = session(d)
        try:
            t = s.send("i")
            seen = {n for n in ORDER if n in t}
            for name in ORDER[1:]:  # a small screen windows the rows: each one is reached by Down
                s.send("down")
                if until(s, lambda text: any(ln.startswith("> ") and name in ln for ln in text.splitlines())):
                    seen.add(name)
            need(seen == set(ORDER) and (not big or all(n in t for n in ORDER)), "every integration listed, seen %s" % sorted(seen), t)
            if big:
                lines = t.splitlines()
                need(any("antislop" in ln and "bundled" in ln and "enabled" in ln for ln in lines), "antislop", t)
                need(any("demo-check" in ln and "project" in ln and "disabled" in ln for ln in lines), "demo-check", t)
                need(any("bad-check" in ln and "[!]" in ln for ln in lines), "bad-check marked", t)
            s.send(*["down"] * ((ORDER.index("bad-check") - (len(ORDER) - 1)) % len(ORDER)))  # from the last row
            need(until(s, lambda text: "points is required" in flat(text)), "bad-check's reason in the detail",
                 s.term.text())
            t = s.term.text()
            need("Space switch" in flat(t), "the section footer", t)
        finally:
            s.close()

    def bundled_off():
        d = project(base, home)
        twin = d + "-twin"
        shutil.copytree(d, twin, symlinks=True)
        s = session(d)
        try:
            pick(s, "antislop")
            t = s.send("space", "esc", "s")
            need(("integration antislop: enabled -> disabled" if big else "integration antislop: enabled") in flat(t),
                 "the confirmation", t)
            s.send("y")
            need("integrations.off: antislop" in read(d, settings.SETTINGS_FILE).decode(), "the off line")
            listed = sdd(d, home, "integrations", "list")[1]
            need("antislop bundled disabled" in listed, "integrations list: " + listed)
            assert sdd(twin, home, "integrations", "disable", "antislop")[0] == 0
            for f in (settings.SETTINGS_FILE, "AGENTS.md"):
                need(read(d, f) == read(twin, f), "%s equals the command's copy" % f)
        finally:
            s.close()

    def project_on():
        d = project(base, home)
        s = session(d)
        try:
            pick(s, "demo-check")
            s.send("space", "esc", "s", "y")
            need("integrations: demo-check" in read(d, settings.SETTINGS_FILE).decode(), "the integrations line")
            need(b"- Rule of demo-check." in read(d, "AGENTS.md"), "the rules in the AGENTS.md block")
        finally:
            s.close()

    def broken():
        d = project(base, home)
        before = read(d, settings.SETTINGS_FILE)
        s = session(d)
        try:
            pick(s, "bad-check")
            t = s.send("space")
            need("cannot be switched" in flat(t), "the reason", t)
            t = s.send("esc", "s")
            need("nothing to save" in t, "nothing pending", t)
            need(read(d, settings.SETTINGS_FILE) == before, "the file unchanged")
        finally:
            s.close()

    def read_only_rules():
        d = project(base, home)
        path = os.path.join(d, "AGENTS.md")
        before = (read(d, settings.SETTINGS_FILE), read(d, "AGENTS.md"))
        os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        s = session(d)
        try:
            pick(s, "demo-check")
            t = s.send("space", "esc", "s", "y")
            need("not switched" in flat(t), "the reason shown", t)
            need((read(d, settings.SETTINGS_FILE), read(d, "AGENTS.md")) == before, "neither file changed")
        finally:
            s.close()
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    def checklists():
        d = project(base, home)
        s = session(d)
        try:
            t = s.send("c")
            need("a adds one" in flat(t) or "a add" in flat(t), "the empty section", t)
            s.send("a", "money-safety", "enter", "billing/**", "enter", "docs/checklists/money.md", "enter")
            t = s.term.text()
            need("money-safety" in t, "the new checklist", t)
            if big:
                need("[file missing]" in t and "*unsaved" in t, "marked file missing and unsaved", t)
            s.send("esc", "s", "y")
            found = settings.parse_settings(read(d, settings.SETTINGS_FILE).decode())
            need(found.get("checklist.money-safety.paths") == "billing/**"
                 and found.get("checklist.money-safety.file") == "docs/checklists/money.md", "both keys: %s" % found)
            t = s.send("c", "a", "Money", "space", "Safety", "enter")
            need("lowercase letters" in flat(t), "the wrong name refused", t)
            need(read(d, settings.SETTINGS_FILE).decode().count("checklist.") == 2, "nothing added")
            file_line = [ln for ln in read(d, settings.SETTINGS_FILE).decode().splitlines(True) if ".file:" in ln]
            s.send("enter", ", src/pay/*.py", "enter", "enter", "esc", "s", "y")
            text = read(d, settings.SETTINGS_FILE).decode()
            need("checklist.money-safety.paths: billing/**, src/pay/*.py" in text, "the paths edited: " + text)
            need([ln for ln in text.splitlines(True) if ".file:" in ln] == file_line, "the file line keeps its bytes")
            s.send("c", "d", "esc", "s", "y")
            need("checklist." not in read(d, settings.SETTINGS_FILE).decode(), "removed")
        finally:
            s.close()

    def incomplete():
        d = project(base, home)
        assert sdd(d, home, "config", "set", "checklist.docs.paths", "docs/**")[0] == 0
        s = session(d)
        try:
            t = s.send("c")
            need("docs" in t, "the checklist listed", t)
            need("incomplete: no file" in flat(t), "marked incomplete, the file named", t)
        finally:
            s.close()

    for label, fn in (("section listed", section), ("bundled one off equals the command", bundled_off),
                      ("project one on, its rules", project_on), ("broken one does not switch", broken),
                      ("read-only AGENTS.md changes nothing", read_only_rules),
                      ("checklists: add, wrong name, edit, remove", checklists), ("incomplete checklist", incomplete)):
        row("%dx%d %s: %s" % (cols, rows, tag, label), fn)


def main():
    base = tempfile.mkdtemp(prefix="settings-tui-lists-")
    home = os.path.join(base, "home")
    os.makedirs(home)
    try:
        for rows, cols in ((40, 120), (12, 40)):
            for extra, tag in (({}, "colour"), ({"NO_COLOR": "1"}, "NO_COLOR")):
                run_size(base, home, rows, cols, extra, tag)
    finally:
        shutil.rmtree(base, True)
    print("SUMMARY: all rows passed" if all(results) else "SUMMARY: %d of %d rows failed" % (
        results.count(False), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
