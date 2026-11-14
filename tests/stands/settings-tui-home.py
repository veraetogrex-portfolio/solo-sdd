#!/usr/bin/env python3
"""Stand of change settings-tui-home: `solo-sdd uninstall --hooks` and the Machine section of `solo-sdd settings`.

Every row has its own temporary HOME holding `solo-sdd install --agents claude,codex` of this tree and a PATH of fake
`claude` and `codex` (so both are detected whatever the machine has) plus /usr/bin and /bin; never the owner's home.
Step 1 runs the command; step 2 drives `python3 -m solo_sdd settings` on a pseudo-terminal (the vt100 emulator and
session of tests/stands/settings-tui.py) at 120x40 and 40x12, each with and without NO_COLOR.
Prints one PASS or FAIL line per row and `SUMMARY: all rows passed`, exit 1 on a failure.
"""
import importlib.util, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("settings_tui_stand", os.path.join(HERE, "settings-tui.py"))
tui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tui)

need, flat = tui.need, tui.flat
results = []
ITEMS = ["claude", "codex", "cursor", "other", "hooks", "rules"]  # the Machine section's rows, in order


def env_of(home, bin_dir, extra=None):
    """The variables of a row: its home and PATH; the depth a Claude Code session sets is left out, so doctor sees the
    temporary home's own settings."""
    return dict(extra or {}, HOME=home, PATH=bin_dir + ":/usr/bin:/bin", CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=None)


def sdd(cwd, home, bin_dir, *args):
    env = dict(os.environ, PYTHONPATH=ROOT, **env_of(home, bin_dir))
    env = {k: val for k, val in env.items() if val is not None}
    p = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=cwd, env=env, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=300)
    return p.returncode, p.stdout + p.stderr


def tree(home):
    found = {}
    for d, _, names in os.walk(home):
        for n in names:
            path = os.path.join(d, n)
            if os.path.isfile(path) and not os.path.islink(path):
                with open(path, "rb") as f:
                    found[os.path.relpath(path, home)] = f.read()
    return found


def row(label, fn):
    try:
        fn()
        good, detail = True, ""
    except Exception as e:  # a stand row reports, the next row runs
        good, detail = False, "%s: %s" % (type(e).__name__, e)
    results.append(good)
    print(("PASS " if good else "FAIL ") + label + ("" if good else ": " + detail[-900:]))


class Home:
    """A temporary home with the fake agents and the layout of this tree for claude and codex."""

    def __init__(self, base):
        self.dir = tempfile.mkdtemp(dir=base)
        self.home = os.path.join(self.dir, "home")
        self.bin = os.path.join(self.dir, "bin")
        os.makedirs(self.home)
        os.makedirs(self.bin)
        for name in ("claude", "codex"):
            path = os.path.join(self.bin, name)
            with open(path, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(path, 0o755)
        code, out = self.sdd(self.dir, "install", "--agents", "claude,codex")
        assert code == 0, out
        self.project = os.path.join(self.dir, "project")
        subprocess.run(["git", "init", "-q", "-b", "main", self.project], check=True)
        subprocess.run(["git", "-C", self.project, "config", "maintenance.auto", "false"], check=True)
        assert self.sdd(self.project, "init", "--yes")[0] == 0

    def sdd(self, cwd, *args):
        return sdd(cwd, self.home, self.bin, *args)

    def state(self):
        with open(os.path.join(self.home, ".local", "share", "solo-sdd", "state.json")) as f:
            return json.load(f)


def step_one(base):
    h = Home(base)
    settings = os.path.join(h.home, ".claude", "settings.json")
    mine = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}}
    with open(settings, "w") as f:
        json.dump(mine, f)
    status = h.sdd(h.dir, "status")[1]
    assert h.sdd(h.dir, "install", "--hooks")[0] == 0
    need("work_hooks.py" in open(settings).read(), "install --hooks connected")
    code, out = h.sdd(h.dir, "uninstall", "--hooks")
    need(code == 0, "uninstall --hooks: " + out)
    now = json.load(open(settings))
    need(now == mine, "only the person's hook is left: %s" % now)
    need("_hooks" not in h.state(), "_hooks cleared")
    need(h.sdd(h.dir, "status")[1] == status, "status shows the same copies")
    before = tree(h.home)
    code, out = h.sdd(h.dir, "uninstall", "--hooks")
    need(code == 0 and "not connected" in out and tree(h.home) == before, "a second call writes nothing: " + out)


def run_size(base, rows, cols, extra, tag):
    def session(h, cwd=None):
        return tui.Session(cwd or h.project, rows, cols, env_of(h.home, h.bin, extra))

    def at(s, item):
        return s.send(*["down"] * ITEMS.index(item))

    def opened():
        h = Home(base)
        s = session(h)
        try:
            s.send("m")
            need(tui_until(s, lambda x: "Machine" in x), "the Machine section", s.term.text())
            seen = s.term.text()
            for _ in ITEMS[1:]:  # a small screen windows the rows: each one is reached by Down
                seen += "\n" + s.send("down")
            for name in ("claude", "codex", "other"):
                need(("[x] agent %s" % name) in seen, name + " ticked", seen)
            need("[ ] hooks" in seen and "[ ] global rules" in seen, "hooks and rules off", seen)
            for _ in range(12):  # Down goes on through the layout and doctor lines
                seen += "\n" + s.send("down")
            need("warn depth" in flat(seen), "the depth warning of doctor", seen)
            need("layout: " in seen and " ok" in seen, "the copy counts", seen)
            for _ in range(30):  # Up until the layout row is the selected one
                if "> layout:" in s.term.text():
                    break
                s.send("up")
            need("> layout:" in s.term.text() and h.state()["_version"] in flat(s.term.text()), "the version, read whole",
                 s.term.text())
        finally:
            s.close()

    def outside():
        h = Home(base)
        plain = os.path.join(h.dir, "plain")
        os.makedirs(plain)
        s = session(h, plain)
        try:
            t = s.term.text()
            need("Machine" in t and "solo-sdd init" in flat(t), "only the Machine section, init named", t)
            s.send("esc")
            need("Machine" in s.term.text(), "Esc does not leave it")
            s.send("q")
            need(s.wait() == 0, "q leaves")
        finally:
            s.close()

    def narrow():
        h = Home(base)
        s = session(h)
        try:
            s.send("m")
            at(s, "codex")
            t = s.send("space", "a")
            need("solo-sdd install --agents claude,other" in flat(t) and "~/.codex/" in flat(t),
                 "the command and folder", t)
            s.send("y")
            need(tui_until(s, lambda x: "exit 0: solo-sdd install" in flat(x)), "the output shown", s.term.text())
            left = [p for p in tree(h.home) if p.startswith(".codex/skills/")]
            need(left == [], "no unchanged copy under ~/.codex/skills: %s" % left[:3])
        finally:
            s.close()

    def hooks_on_off():
        h = Home(base)
        s = session(h)
        try:
            s.send("m")
            at(s, "hooks")
            t = s.send("space", "a")
            need("solo-sdd install --agents claude,codex,other --hooks" in flat(t), "the hooks command", t)
            s.send("y")
            need(tui_until(s, lambda x: "exit 0" in x), "hooks on ran", s.term.text())
            need(h.state().get("_hooks"), "hooks on")
            s.send("esc")
            t = s.send("space", "a")
            need("solo-sdd uninstall --hooks" in flat(t), "the uninstall command", t)
            s.send("y")
            need(tui_until(s, lambda x: "exit 0: solo-sdd uninstall --hooks" in flat(x)), "hooks off ran", s.term.text())
            need(not h.state().get("_hooks"), "hooks off")
        finally:
            s.close()

    def rules_on():
        h = Home(base)
        s = session(h)
        try:
            s.send("m")
            at(s, "rules")
            s.send("space", "a", "y")
            need(tui_until(s, lambda x: "exit 0" in x), "install --global-rules ran", s.term.text())
            for rel in ("AGENTS.md", ".codex/AGENTS.md", ".claude/CLAUDE.md"):
                with open(os.path.join(h.home, rel), encoding="utf-8") as f:
                    need("solo-sdd:begin" in f.read(), "the block in ~/" + rel)
        finally:
            s.close()

    def hooks_need_claude():
        h = Home(base)
        assert h.sdd(h.dir, "install", "--hooks")[0] == 0
        before = tree(h.home)
        s = session(h)
        try:
            s.send("m")
            at(s, "claude")
            s.send("space", "a", "y")
            need(tui_until(s, lambda x: "need claude" in flat(x)), "the refusal naming claude", s.term.text())
            after = {p: b for p, b in tree(h.home).items() if "/hook-state/" not in "/" + p}
            need(after == {p: b for p, b in before.items() if "/hook-state/" not in "/" + p}, "no file changed")
        finally:
            s.close()

    def cancelled():
        h = Home(base)
        before = tree(h.home)
        s = session(h)
        try:
            s.send("m")
            at(s, "rules")
            t = s.send("space", "a", "n")
            need("Machine" in t, "back to the section", t)
            need(tree(h.home) == before, "no command ran")
        finally:
            s.close()

    for label, fn in (("Machine section", opened), ("outside a project", outside), ("untick codex, apply", narrow),
                      ("hooks on, then off", hooks_on_off), ("global rules on", rules_on),
                      ("hooks without claude refused", hooks_need_claude), ("apply cancelled", cancelled)):
        row("%dx%d %s: %s" % (cols, rows, tag, label), fn)


def tui_until(s, cond, limit=8.0):
    """True once cond holds for the screen; doctor and install take seconds."""
    end = tui.time.time() + limit
    while not cond(s.term.text()):
        if tui.time.time() > end:
            return False
        s.read(quiet=0.3, limit=1)
    return True


def main():
    base = tempfile.mkdtemp(prefix="settings-tui-home-")
    try:
        row("step 1: uninstall --hooks", lambda: step_one(base))
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
