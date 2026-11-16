"""`solo-sdd settings`: a full-screen terminal screen over the project's solo-sdd/config.

Screen is the state, the key handling and the drawing into plain lines; tests drive it by key names. The curses loop
in run_curses only maps keys and paints the lines.
"""
import collections
import contextlib
import io
import os
import sys
import textwrap
import threading
import unicodedata

from solo_sdd import __version__, init, integrations, process_format as pf, settings, setup_detect, update_check

MIN_W, MIN_H = 40, 12
STATE = "~/.local/share/solo-sdd"  # every install and uninstall writes its state and backups here
KEYS = [k for g in settings.GROUPS for k in settings.REGISTRY if settings.ABOUT[k][0] == g]
FOOTER = {
    "list": "Up/Down move  Enter edit  r reset  i integrations  c checklists  m machine  s save  q quit",
    "machine": "Up/Down move  Space switch  a apply  r refresh  Esc back  q quit",
    "apply": "Up/Down scroll  y run these  n back",
    "refused": "Esc back",
    "whole": "Up/Down scroll  Esc back",
    "applied": "Up/Down scroll  Esc back  q quit",
    "integrations": "Up/Down move  Space switch on or off  c checklists  Esc back",
    "checklists": "Up/Down move  a add  Enter edit  d remove  i integrations  Esc back",
    "pick": "Up/Down choose  Enter set  Esc back",
    "check": "Up/Down move  Space tick  Enter set  Esc back",
    "entry": "Type a value  Enter set (empty: reset)  Esc back",
    "confirm": "Up/Down scroll  y write  n back",
    "quit": "s save and quit  d discard and quit  b back",
    "broken": "q quit",
}
NO_TERMINAL = "solo-sdd settings needs a full-screen terminal; without one use solo-sdd config list|describe|set"


def fit(text, width):
    """Text cut to at most width terminal columns: a wide (East Asian) character takes two."""
    out, used = [], 0
    for c in text:
        w = 2 if unicodedata.east_asian_width(c) in "WF" else 0 if unicodedata.combining(c) else 1
        if used + w > width:
            break
        out.append(c)
        used += w
    return "".join(out)


def shown(text):
    """Text with every character a terminal would act on written as an escape: ESC is `\\x1b`."""
    return "".join(c if c.isprintable() else "\\x%02x" % ord(c) if ord(c) < 256 else "\\u%04x" % ord(c)
                   for c in text)


class Screen:
    def __init__(self, root, text, agents=None, ci=None, error=None, home=None, folder=None):
        self.root, self.text, self.agents, self.ci = root, text, agents or {}, ci
        self.error, self.home = error, home if home is not None else os.path.expanduser("~")
        self.edits = {}  # key -> new value, None: back to the value below the file
        self.toggles = {}  # integration name -> True to enable, False to disable, saved through integrations.toggle
        self.pos, self.mode, self.message = 0, "broken" if error else "list", ""
        self.options, self.cursor, self.ticked, self.buffer = [], 0, set(), ""
        self.back, self.target, self.step, self.before = "list", None, None, {}
        self.ipos = self.cpos = 0
        self.base = {} if error or text is None else self.values()
        self.machine, self.want, self.mpos, self.results, self.warned = None, None, 0, [], False
        self.folder, self.plan, self.refusal, self.scroll = folder or root, [], None, 0
        self.read_integrations()

    @classmethod
    def load(cls, root, home=None):
        agents, ci = settings.agents_delivery(root), setup_detect.ci(root)
        try:
            text = settings.read_settings_text(root)
            settings.parse_settings(text)
        except (OSError, UnicodeDecodeError, ValueError) as e:
            return cls(root, None, agents, ci, error=str(e), home=home)
        return cls(root, text, agents, ci, home=home, folder=root)

    def read_integrations(self):
        """The integrations `solo-sdd integrations list` finds, and the names enabled by the file as it is on disk."""
        if self.error or self.text is None:
            self.entries, self.enabled = [], set()
            return
        found = settings.parse_settings(self.text)
        self.entries = integrations.find_integrations(self.root, self.home, integrations.all_sources())
        self.enabled = set(integrations.enabled_names(self.entries, found))
        used = {e["name"] for e in self.entries if e["name"] and not e["shadowed"]}
        self.entries += [{"name": n, "source": "settings", "shadowed": False, "fields": None,  # disable drops such a name
                          "error": "listed in %s of %s, %s" % (integrations.LISTED, settings.SETTINGS_FILE,
                                                               integrations.NOWHERE)}
                         for n in integrations.listed_names(found.get(integrations.LISTED, "")) if n not in used]

    @property
    def unsaved(self):
        return bool(self.edits or self.toggles)

    def edited_text(self):
        text = self.text
        for key, value in self.edits.items():
            text = settings.set_text(text, key, value)
        return text

    def values(self):
        return settings.effective(settings.parse_settings(self.edited_text()), agents=self.agents)

    def keep(self, value, key=None):
        """Record an edit of a key (the selected one by default); one that leaves the file as it is drops the edit."""
        key = key or self.key
        if settings.set_text(self.text, key, value) == self.text:
            self.edits.pop(key, None)
        else:
            self.edits[key] = value

    @property
    def key(self):
        return KEYS[self.pos]

    # keys

    def fit_cursor(self):
        """The Machine cursor kept on a row that exists: a reread may leave fewer rows than before (fewer doctor lines,
        a state that cannot be read), and the whole-text view closes when its row is gone. Every key and every draw
        passes here, so no reader of the cursor sees a row that is not there."""
        if self.machine is None:
            return
        rows = len(self.machine_items()) + len(self.machine_info())
        self.mpos = max(0, min(self.mpos, rows - 1))
        if self.mode == "whole" and self.mpos < len(self.machine_items()):
            self.mode = "machine"

    def handle(self, key):
        """One key by name (up, down, enter, esc, space, backspace, resize, or the typed character); "exit" ends."""
        self.fit_cursor()
        if key == "resize":
            return None
        if self.mode == "broken":
            return "exit" if key == "q" else None
        return getattr(self, "on_" + self.mode)(key)

    def on_list(self, key):
        self.message = ""
        if key == "up":
            self.pos = (self.pos - 1) % len(KEYS)
        elif key == "down":
            self.pos = (self.pos + 1) % len(KEYS)
        elif key == "enter":
            self.open_editor()
        elif key == "r":
            if self.key in (integrations.LISTED, integrations.OFF):
                self.message = "%s changes only through the Integrations section: press i" % self.key
            else:
                self.keep(None)
        elif key == "i":
            self.mode = "integrations"
        elif key == "c":
            self.mode = "checklists"
        elif key == "m":
            self.open_machine()
        elif key == "s":
            if self.unsaved:
                self.mode, self.cursor = "confirm", 0
            else:
                self.message = "nothing to save"
        elif key == "q":
            if not self.unsaved:
                return "exit"
            self.mode = "quit"
        return None

    def open_editor(self):
        if self.key in (integrations.LISTED, integrations.OFF):  # never as text: the rules block changes with them
            self.mode = "integrations"
            return
        kind, allowed = settings.REGISTRY[self.key][:2]
        value = self.values()[self.key][0]
        if allowed and kind == "choice":
            self.mode, self.options = "pick", list(allowed)
            self.cursor = self.options.index(value) if value in self.options else 0
        elif allowed:
            self.mode, self.options, self.cursor = "check", list(allowed), 0
            self.ticked = {v.strip() for v in value.split(",") if v.strip()}
        else:
            self.entry(self.key, value, "list")

    def entry(self, target, value, back, step=None):
        self.mode, self.buffer, self.target, self.back, self.step = "entry", value, target, back, step

    def on_pick(self, key):
        if key == "up":
            self.cursor = (self.cursor - 1) % len(self.options)
        elif key == "down":
            self.cursor = (self.cursor + 1) % len(self.options)
        elif key == "enter":
            self.set(self.options[self.cursor])
        elif key == "esc":
            self.mode = "list"

    def on_check(self, key):
        if key == "up":
            self.cursor = (self.cursor - 1) % len(self.options)
        elif key == "down":
            self.cursor = (self.cursor + 1) % len(self.options)
        elif key == "space":
            self.ticked ^= {self.options[self.cursor]}
        elif key == "enter":
            self.set(", ".join(o for o in self.options if o in self.ticked))
        elif key == "esc":
            self.mode = "list"

    def on_entry(self, key):
        if key == "enter":
            self.finish_entry()
        elif key == "esc":
            if self.step:  # a checklist add or edit is dropped whole, not left with one of its keys
                self.edits = dict(self.before)
            self.mode, self.step = self.back, None
        elif key == "backspace":
            self.buffer = self.buffer[:-1]
        elif key == "space":
            self.buffer += " "
        elif len(key) == 1 and key.isprintable():
            self.buffer += key

    def finish_entry(self):
        """Enter in a text entry: a plain key takes the value (empty: reset); a checklist goes name, paths, file."""
        raw, step = self.buffer.strip(), self.step
        if step == "name":
            if not settings.good_name(raw):
                self.mode, self.step = self.back, None
                self.message = "a checklist name takes lowercase letters, digits and -, not starting with -: %r" % raw
                return
            if any(name == raw for name, _, _ in self.checklists()):
                self.mode, self.step = self.back, None
                self.message = "checklist %s exists: select it and press Enter to edit it" % raw
                return
            return self.entry("checklist.%s.paths" % raw, "", self.back, "paths")
        if not raw:
            if step:  # a checklist keeps both keys
                self.edits = dict(self.before)
                self.mode, self.step = self.back, None
                self.message = "%s takes a value; nothing changed" % self.target
                return
            self.keep(None, self.target)
            self.mode = self.back
            return
        if not self.set(raw, self.target):
            if step:
                self.edits = dict(self.before)
                self.message += "; nothing changed"
            self.step = None
            return
        if step != "paths":
            self.step = None
            return
        key = "checklist.%s.file" % self.target.split(".")[1]
        self.entry(key, self.values().get(key, ("",))[0], self.back, "file")

    def set(self, raw, key=None):
        """An entered value through the same check as `config set`; a refused one keeps the old value. True if kept."""
        key = key or self.key
        self.mode = self.back if self.mode == "entry" else "list"
        try:
            value = settings.check_value(key, raw)
        except settings.SettingsError as e:
            self.message = str(e)
            return False
        try:
            settings.parse_settings(settings.set_text(self.edited_text(), key, value))
        except settings.SettingsError as e:  # a value the file could not hold, e.g. a line separator
            self.message = str(e)
            return False
        self.keep(value, key)
        if key == "delivery.mode" and value == "pr" and not self.ci:
            self.message = init.NO_CI
        return True

    # integrations

    def integration_rows(self):
        return [e for e in self.entries if e["name"] or e["error"]]

    def state(self, name):
        return self.toggles.get(name, name in self.enabled)

    def on_integrations(self, key):
        rows = self.integration_rows()
        self.message = ""
        if key in ("up", "down") and rows:
            self.ipos = (self.ipos + (1 if key == "down" else -1)) % len(rows)
        elif key == "space" and rows:
            e = rows[self.ipos]
            if e["shadowed"] or not e["name"] or e["error"] and e["name"] not in self.enabled:
                self.message = "%s cannot be switched: %s" % (e["name"] or e["source"], self.reason(e))
            elif self.state(e["name"]) == (e["name"] in self.enabled):
                self.toggles[e["name"]] = e["name"] not in self.enabled
            else:
                del self.toggles[e["name"]]
        elif key == "c":
            self.mode = "checklists"
        elif key == "esc":
            self.mode = "list"

    def reason(self, e):
        if e["shadowed"]:
            used = next(u for u in self.entries if u["name"] == e["name"] and not u["shadowed"])
            return "shadowed by the %s copy" % used["source"]
        return shown(e["error"] or "")

    # checklists

    def checklists(self):
        """[(name, paths or None, file or None)] of the checklist keys in effect, by name."""
        values = self.values()
        names = sorted({k.split(".")[1] for k in values if k.startswith("checklist.") and k.count(".") == 2})
        get = lambda k: values[k][0] if k in values and values[k][0] else None  # noqa: E731
        return [(n, get("checklist.%s.paths" % n), get("checklist.%s.file" % n)) for n in names]

    def on_checklists(self, key):
        rows = self.checklists()
        self.message = ""
        if key in ("up", "down") and rows:
            self.cpos = (self.cpos + (1 if key == "down" else -1)) % len(rows)
        elif key == "a":
            self.before = dict(self.edits)
            self.entry(None, "", "checklists", "name")
        elif key == "enter" and rows:
            name, paths, _ = rows[self.cpos % len(rows)]
            self.before = dict(self.edits)
            self.entry("checklist.%s.paths" % name, paths or "", "checklists", "paths")
        elif key == "d" and rows:
            name = rows[self.cpos % len(rows)][0]
            for part in ("paths", "file"):
                self.keep(None, "checklist.%s.%s" % (name, part))
            self.cpos = 0
        elif key == "i":
            self.mode = "integrations"
        elif key == "esc":
            self.mode = "list"

    # machine: the agents, the hooks and the global rules of this home, changed by install and uninstall

    def open_machine(self):
        self.mode = "machine"
        if self.machine is None:
            self.read_machine()

    def read_machine(self):
        """The choices in effect and what the layout and doctor report, printing nothing; doctor runs here only."""
        from solo_sdd import doctor, layout, providers
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                state = layout.load_state()
                counts = collections.Counter(kind for kind, _, _ in layout.status(quiet=True))
                checks = [r for r in doctor.rows() if r[0] in ("warn", "fail")]
                chosen, rules = list(layout.chosen(state)), bool(layout.global_rules(state))
        except (layout.BrokenState, layout.BadTargets, OSError, ValueError) as e:
            self.machine, self.want = {"error": shown(str(e))}, None
            return
        self.machine = {"agents": chosen, "hooks": bool(state.get("_hooks") or state.get("_codex_hooks")),
                        "claude_hooks": bool(state.get("_hooks")), "rules": rules, "counts": counts,
                        "source": state.get("_source"), "version": state.get("_version"), "doctor": checks,
                        "detected": providers.detected(self.home), "error": None,
                        "updates": not update_check.load().get("off")}
        self.want = {"agents": set(chosen), "hooks": self.machine["hooks"], "rules": rules}

    def machine_items(self):
        from solo_sdd import providers
        return [("agent", n) for n in providers.ALL] + [("hooks", None), ("rules", None), ("updates", None)]

    def machine_pending(self):
        m, w = self.machine, self.want
        return bool(w) and (w["agents"] != set(m["agents"]) or w["hooks"] != m["hooks"] or w["rules"] != m["rules"])

    def machine_info(self):
        m = self.machine
        if not m or m.get("error"):
            return []
        counts = ", ".join("%d %s" % (n, k) for k, n in sorted(m["counts"].items())) or "no copies"
        info = ["layout: %s; from %s %s" % (counts, shown(m["source"] or "none"), shown(m["version"] or ""))]
        return info + (["%s %s: %s" % (lvl, name, shown(detail)) for lvl, name, detail in m["doctor"]]
                       or ["doctor: no warnings"])

    def on_machine(self, key):
        self.message, warned, self.warned = "", self.warned, False
        items = self.machine_items()
        if key in ("up", "down"):  # past the switches Down goes on through the layout and doctor lines
            self.mpos = (self.mpos + (1 if key == "down" else -1)) % (len(items) + len(self.machine_info()))
        elif key == "r":
            self.read_machine()
            self.message = "refreshed"
        elif key == "enter" and self.mpos >= len(items) and self.machine_info():
            self.mode, self.scroll = "whole", 0
        elif key == "space" and self.want and self.mpos < len(items):
            kind, name = items[self.mpos]
            if kind == "agent" and name == "other":
                self.message = "other is always chosen: it holds ~/.agents/skills and ~/AGENTS.md"
            elif kind == "agent":
                self.want["agents"] ^= {name}
            elif kind == "updates":  # no install or uninstall behind it: saved at once
                self.machine["updates"] = not self.machine["updates"]
                update_check.switch(self.machine["updates"])
                self.message = "update check %s" % ("on" if self.machine["updates"] else "off")
            else:
                self.want[kind] = not self.want[kind]
        elif key == "a" and self.want:
            if not self.machine_pending():
                self.message = "nothing to apply"
                return None
            from solo_sdd import layout
            try:
                self.plan = self.machine_plan()
            except (layout.BrokenState, layout.BadTargets, OSError, ValueError) as e:
                self.message = "cannot plan the commands: %s" % shown(str(e))
                return None
            self.refusal = None
            from solo_sdd import cli
            # install's own check, before any step: hooks kept on stay connected while install runs
            why = cli.hooks_refusal(self.want["agents"], self.want["hooks"],
                                    {"_hooks": self.machine["claude_hooks"]} if self.want["hooks"] else {})
            if why:
                self.refusal = why + "; tick an agent or turn the hooks off: nothing ran and no file changed"
            self.mode, self.scroll = "apply", 0
        elif key == "esc" and self.text is not None:
            self.mode = "list"
        elif key == "q":
            if self.machine_pending() and not warned:
                self.message, self.warned = "machine edits not applied: a applies them, q again leaves without them", True
                return None
            return "exit" if not self.unsaved else self.on_list("q")
        return None

    def machine_plan(self):
        """[(command, folders, call)] in the order they run: the hooks and the rules off first, then install."""
        from solo_sdd import cli, layout, providers
        m, w = self.machine, self.want
        rule_files = sorted(layout.opt_in_keys())
        plan = []
        if m["hooks"] and not w["hooks"]:
            plan.append(("solo-sdd uninstall --hooks", ["~/.claude/settings.json", "~/.codex/hooks.json", STATE], cli.uninstall_hooks))
        if m["rules"] and not w["rules"]:
            plan.append(("solo-sdd uninstall --global-rules", rule_files + [STATE], layout.uninstall_rules))
        # hooks on: newly, or for a chosen claude whose hooks are not connected while the codex hooks are
        hooks_on = w["hooks"] and (not m["hooks"] or "claude" in w["agents"] and not m.get("claude_hooks"))
        rules_on = w["rules"] and not m["rules"]
        if w["agents"] != set(m["agents"]) or hooks_on or rules_on:
            names = [n for n in providers.ALL if n in w["agents"]]
            command = "solo-sdd install --agents %s%s%s" % (",".join(names), " --hooks" if hooks_on else "",
                                                           " --global-rules" if rules_on else "")
            folders = [f for n in sorted(w["agents"] ^ set(m["agents"])) for f in providers.PROVIDERS[n]["owns"]]
            folders += (["~/.claude/settings.json", "~/.codex/hooks.json"] if hooks_on else []) + (rule_files if rules_on else []) + [STATE]
            plan.append((command, folders, lambda: cli.install(hooks_on, ",".join(names), rules_on)))
        return plan

    def on_apply(self, key):
        from solo_sdd import layout
        if key in ("up", "down"):
            self.scroll = max(0, self.scroll + (1 if key == "down" else -1))
        elif key == "y" and not self.refusal:
            self.results = []
            for command, _, call in self.plan:
                out = io.StringIO()
                try:
                    with contextlib.redirect_stdout(out):
                        code = call()
                except (layout.BrokenState, layout.BadTargets, OSError, ValueError) as e:  # what cli.main catches
                    code = 1
                    out.write("fail %s\n" % e)
                self.results.append((command, code, out.getvalue()))
                if code:
                    break
            self.read_machine()
            self.mode, self.scroll = "applied", 0
        elif key in ("n", "esc"):
            self.mode = "machine"

    def on_whole(self, key):
        if key in ("up", "down"):
            self.scroll = max(0, self.scroll + (1 if key == "down" else -1))
        elif key == "esc":
            self.mode = "machine"

    def on_applied(self, key):
        if key in ("up", "down"):
            self.scroll = max(0, self.scroll + (1 if key == "down" else -1))
        elif key == "esc":
            self.mode = "machine"
        elif key == "q":
            return self.on_machine("q")
        return None

    def draw_machine(self):
        m = self.machine
        if m.get("error"):
            return ["Machine: the solo-sdd state cannot be read", "", m["error"]], set()
        compact = self.room < 10  # a low screen drops the blank lines, so a selected row still reads whole
        gap = [] if compact else [""]
        head = [] if self.text is not None else self.wrap("No project here: solo-sdd init prepares one") + gap
        lines = []
        items = self.machine_items()
        for i, (kind, name) in enumerate(items):
            if kind == "agent":
                on, was = name in self.want["agents"], name in m["agents"]
                text = "[%s] agent %s%s" % ("x" if on else " ", name, "  detected" if name in m["detected"] else "")
            elif kind == "updates":
                on = was = m["updates"]
                text = "[%s] update check: ask for a newer solo-sdd at most once a day%s" % (
                    "x" if on else " ", " (off while %s is set)" % update_check.OFF if os.environ.get(update_check.OFF, "")
                    not in ("", "0") else "")
            else:
                on, was = self.want[kind], m[kind]
                text = "[%s] %s" % ("x" if on else " ", "hooks in ~/.claude/settings.json" if kind == "hooks"
                                    else "global rules block in ~/AGENTS.md and the agents' rules files")
            lines.append(("> " if i == self.mpos else "  ") + text + (" *not applied" if on != was else ""))
        info = self.machine_info()
        rows = lines + [("> " if len(items) + j == self.mpos else "  ") + ln for j, ln in enumerate(info)]
        body = head + ["Machine: changes every project's agents" if compact else
                       "Machine: these change every project's agents, through install and uninstall"] + gap
        whole = (info[self.mpos - len(items)] if self.mpos >= len(items) else
                 "Space switches it at once: the home menu and doctor stop or start asking the registry"
                 if items[self.mpos][0] == "updates" else
                 "Space switches it; a applies the switches through install and uninstall")
        fits, wrapped = max(1, self.room - len(body) - len(gap) - 1), self.wrap(whole)
        if len(wrapped) > fits:  # Enter shows the rest
            wrapped = wrapped[:fits - 1] + [fit(wrapped[fits - 1], self.width - 22) + " ... Enter shows all"]
        detail = gap + wrapped
        room = max(1, self.room - len(body) - len(detail))
        top = min(max(0, self.mpos - room // 2), max(0, len(rows) - room))
        return body + rows[top:top + room] + detail, {len(body) + self.mpos - top}

    def scrolled(self, lines):
        """lines windowed from the scroll offset; the offset stops at the last full window."""
        room = max(1, self.room - 1)
        self.scroll = min(self.scroll, max(0, len(lines) - room))
        more = "%d-%d of %d lines, Up/Down scrolls" % (self.scroll + 1, min(len(lines), self.scroll + room), len(lines))
        return ([more] if len(lines) > room else [""]) + lines[self.scroll:self.scroll + room], set()

    def on_confirm(self, key):
        if key in ("up", "down"):
            last = len(self.edits) + len(self.toggles) - 1
            self.cursor = max(0, min(last, self.cursor + (1 if key == "down" else -1)))
        elif key == "y":
            self.save()
        elif key in ("n", "esc"):
            self.mode = "list"

    def on_quit(self, key):
        if key == "d":
            return "exit"
        if key == "s":
            return "exit" if self.save() else None
        if key in ("b", "esc"):
            self.mode = "list"
        return None

    def save(self):
        """Write only the edited lines, as `config set` and `unset` do; never over a file changed since it was read."""
        self.mode = "list"
        path = os.path.join(self.root, settings.SETTINGS_FILE)
        try:
            disk = settings.read_settings_text(self.root)
        except (OSError, UnicodeDecodeError) as e:
            self.message = "cannot read %s: %s; nothing written" % (settings.SETTINGS_FILE, e)
            return False
        if disk != self.text:
            self.message = "%s changed on disk since the screen read it; nothing written" % settings.SETTINGS_FILE
            return False
        done = []
        for name, on in list(self.toggles.items()):  # the command's own path: the rules block changes with the line
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = integrations.toggle(self.root, "enable" if on else "disable", name, self.home)
            if code:
                self.reload()
                said = " ".join(out.getvalue().split())
                self.message = "integration %s not switched: %s%s" % (
                    name, said, "; saved before it: " + ", ".join(done) if done else "")
                return False
            del self.toggles[name]
            done.append(name)
        self.reload()
        if self.edits:
            new = self.edited_text()
            try:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(new)
            except OSError as e:
                self.message = "cannot write %s: %s; %s" % (settings.SETTINGS_FILE, e.strerror, (
                    "saved before it: " + ", ".join(done)) if done else "nothing written")
                return False
            done += list(self.edits)
            self.text, self.edits = new, {}
            self.read_integrations()
        self.base = self.values()
        self.message = "saved: " + ", ".join(done)
        return True

    def reload(self):
        """The file as an integration switch left it; the edits not saved yet stay on top of it."""
        self.text = settings.read_settings_text(self.root)
        self.base = settings.effective(settings.parse_settings(self.text), agents=self.agents)
        self.read_integrations()

    # drawing

    def draw(self, width, height):
        """(lines, indexes of highlighted lines) for a terminal of width x height."""
        self.fit_cursor()
        if width < MIN_W or height < MIN_H:
            return ["Terminal too small: needs %dx%d, now %dx%d" % (MIN_W, MIN_H, width, height)], set()
        head = ["solo-sdd settings  " + shown(self.folder or ""), ""]
        footer = textwrap.wrap(FOOTER["refused" if self.mode == "apply" and self.refusal else self.mode], width - 1)
        cap = max(1, min(3, height - len(head) - len(footer) - 6))  # the list keeps a row above its blank and detail
        message = textwrap.wrap(shown(self.message), width - 1) or [""]
        if len(message) > cap:
            message = message[:cap - 1] + [fit(message[cap - 1], width - 5) + " ..."]
        self.room = height - len(head) - len(message) - len(footer)  # the lines between the head and the message
        self.width = width
        if self.mode == "broken":
            body, marked = [shown(self.error), "", "The file is shown read-only: fix it and open the screen again."], set()
        elif self.mode == "list":
            body, marked = self.draw_list(self.room - 5)  # a blank line and 4 of detail below the list
            body += [""] + self.detail()
        else:
            body, marked = self.draw_mode()
        body = body[:self.room]
        lines = head + body + [""] * (self.room - len(body)) + message + footer
        return [fit(ln, width - 1) for ln in lines], {i + len(head) for i in marked}

    def row(self, key, values):
        value, source = values[key]
        text = "%-30s %s  [%s]" % (key, shown(value) or "(none)", source)
        if key in self.edits:
            text += " *unsaved"
        item = self.agents.get(key)
        if item is not None and source == "file" and value != item:
            text += "  overrides AGENTS.md: " + item
        return text

    def draw_list(self, room):
        values, rows, sel = self.values(), [], 0
        for group in settings.GROUPS:
            keys = [k for k in KEYS if settings.ABOUT[k][0] == group]
            if keys:
                rows.append(group)
            for k in keys:
                if k == self.key:
                    sel = len(rows)
                rows.append(("> " if k == self.key else "  ") + self.row(k, values))
        top = min(max(0, sel - room // 2), max(0, len(rows) - room))
        return rows[top:top + room], {sel - top}

    def detail(self):
        values = self.values()
        row = settings.describe(self.key, values)
        lines = [row["about"], "type " + row["type"],
                 "default %s, team default %s" % (row["default"] or "(none)", row["team_default"] or "(same)")]
        item = self.agents.get(self.key)
        if item is not None and values[self.key][1] == "file" and values[self.key][0] != item:
            lines.append("the file value overrides the Delivery item of AGENTS.md: " + item)
        return lines

    def section(self, title, rows, sel, detail):
        """A title, the rows windowed to keep the selected one, a blank line and the selected row's detail wrapped."""
        room = max(1, self.room - 3 - len(detail))
        top = min(max(0, sel - room // 2), max(0, len(rows) - room))
        return [title, ""] + rows[top:top + room] + [""] + detail, {sel - top + 2} if rows else set()

    def wrap(self, text):
        return textwrap.wrap(text, max(10, self.width - 1), subsequent_indent="  ", break_on_hyphens=False) or [""]

    def wrapped(self, text):
        lines = textwrap.wrap(text, max(10, self.width - 1))
        return lines if len(lines) <= 2 else [lines[0], fit(lines[1], self.width - 5) + " ..."]

    def draw_mode(self):
        if self.mode in ("pick", "check"):
            lines = [self.key + ": " + ("pick a value" if self.mode == "pick" else "tick the values"), ""]
            for i, o in enumerate(self.options):
                box = "" if self.mode == "pick" else "[x] " if o in self.ticked else "[ ] "
                lines.append(("> " if i == self.cursor else "  ") + box + o)
            return lines, {self.cursor + 2}
        if self.mode == "entry":
            if self.step == "name":
                title = "New checklist: its name (lowercase letters, digits and -)"
            else:
                title = self.target + ": " + settings.describe(self.target, self.values())["type"]
            return [title, "", "> " + shown(self.buffer) + "_"], set()
        if self.mode == "machine":
            return self.draw_machine()
        if self.mode == "whole":
            info = self.machine_info()
            return self.scrolled(self.wrap(info[self.mpos - len(self.machine_items())]))
        if self.mode == "apply":
            if self.refusal:
                return self.scrolled(self.wrap(self.refusal))
            lines = ["Run these commands?"]
            for command, folders, _ in self.plan:
                lines += self.wrap(command) + self.wrap("  changes " + ", ".join(folders))
            return self.scrolled(lines)
        if self.mode == "applied":
            lines = []
            for command, code, out in self.results:
                lines += self.wrap("exit %d: %s" % (code, command))
                lines += [w for ln in out.splitlines() for w in self.wrap("  " + shown(ln))]
            return self.scrolled(lines + ["the state is read again: Esc shows it"])
        if self.mode == "integrations":
            rows, lines = self.integration_rows(), []
            for i, e in enumerate(rows):
                if e["shadowed"] or not e["name"] or e["error"] and e["name"] not in self.enabled:
                    text = "[!] %s  %s  %s" % (e["name"] or "-", e["source"], self.reason(e))
                elif e["error"]:
                    on = self.state(e["name"])
                    text = "[%s] %s  %s  %s, broken: %s%s" % ("x" if on else " ", e["name"], e["source"],
                                                         "enabled" if on else "disabled", self.reason(e),
                                                         " *unsaved" if e["name"] in self.toggles else "")
                else:
                    on = self.state(e["name"])
                    text = "[%s] %s  %s  %s  %s: %s%s" % ("x" if on else " ", e["name"], e["source"],
                                                       "enabled" if on else "disabled", ", ".join(e["fields"]["points"]),
                                                       shown(e["fields"]["about"]),
                                                       " *unsaved" if e["name"] in self.toggles else "")
                lines.append(("> " if i == self.ipos else "  ") + text)
            if not rows:
                lines.append("no integration found")
            e = rows[self.ipos] if rows else None
            why = "" if e is None else self.reason(e) if e["shadowed"] or e["error"] else shown(e["fields"]["about"])
            where, sep, what = why.partition(": ")
            why = "%s (%s)" % (what, where) if sep and e["error"] else why  # the reason before its file
            detail = self.wrapped(("unsaved; " if e and e["name"] in self.toggles else "") + why)
            return self.section("Integrations: Space switches one; AGENTS.md changes with it on save", lines,
                                self.ipos, detail)
        if self.mode == "checklists":
            rows, lines, sel, detail = self.checklists(), [], self.cpos % max(1, len(self.checklists())), []
            for i, (name, paths, path) in enumerate(rows):
                notes = [m for m, bad in (("incomplete: no paths", paths is None), ("incomplete: no file", path is None),
                                          ("file missing", path is not None and not os.path.isfile(
                                              os.path.join(self.root, path)))) if bad]
                edited = any(k.startswith("checklist.%s." % name) for k in self.edits)
                lines.append("%s%s  paths: %s  file: %s%s%s" % (
                    "> " if i == sel else "  ", name, shown(paths or "-"), shown(path or "-"),
                    "".join("  [%s]" % n for n in notes), " *unsaved" if edited else ""))
                if i == sel:
                    detail = self.wrapped(("unsaved; " if edited else "") + ("; ".join(notes) or "paths and file set"))
            if not rows:
                lines.append("no checklist; a adds one")
            return self.section("Checklists: the files a person checks by a list before merging", lines, sel, detail)
        if self.mode == "confirm":
            values, room = self.values(), max(1, self.room - 2)
            rows = ["%s: %s -> %s" % (k, shown(self.base.get(k, ("",))[0]) or "(none)",
                                      shown(values.get(k, ("",))[0]) or "(none)") for k in self.edits]
            rows += ["integration %s: %s -> %s" % (n, "enabled" if n in self.enabled else "disabled",
                                                   "enabled" if on else "disabled") for n, on in self.toggles.items()]
            top = min(self.cursor, max(0, len(rows) - room))
            head = ("Write this key to %s?" % settings.SETTINGS_FILE if len(rows) == 1 else
                    "Write these %d keys to %s?" % (len(rows), settings.SETTINGS_FILE))
            if self.toggles:
                head = head[:-1] + " and the AGENTS.md rules block?"
            head = textwrap.wrap(head, max(10, self.width - 1))
            room = max(1, room - len(head) + 1)
            top = min(self.cursor, max(0, len(rows) - room))
            if len(rows) > room:
                return head + ["%d-%d shown, Up/Down scrolls" % (top + 1, min(len(rows), top + room))] + \
                    rows[top:top + room], set()
            return head + [""] + rows[top:top + room], set()
        return ["Unsaved edits: %s" % ", ".join(list(self.edits) + ["integration " + n for n in self.toggles])], set()


PROJECT = ["Project settings", "Integrations and checklists", "Machine", "Changes", "Doctor", "Commands", "Quit"]
PREPARE = "Prepare this folder"
SKIP = "Skip this version"
MENU_FOOTER = "Up/Down move  Enter open  q quit"
VIEW_FOOTER = "Up/Down scroll  q back"
UPDATE_FOOTER = "Up/Down scroll  y update  n back"


class Home:
    """The menu bare `solo-sdd` opens on a terminal: a header of the folder and the entries that open the settings
    screens (a Screen it hands the keys to until it exits) or a read-only text (changes, doctor, the command list)."""

    def __init__(self, folder, home=None):
        self.folder, self.home = os.path.abspath(folder), home
        self.pos, self.sub, self.start, self.view, self.scroll, self.message = 0, None, None, None, 0, ""
        self.found, self.checker, self.answer, self.applied = None, None, None, True
        self.refresh()

    @property
    def entries(self):
        """The folder's entries; with a newer version noticed, Update to it and Skip this version before Quit."""
        extra = ["Update to " + self.found, SKIP] if self.found else []
        return self.base[:-1] + extra + self.base[-1:]

    def start_check(self):
        """The version check off the drawing thread: the menu draws at once, the notice comes when it answers."""
        def work():
            try:
                self.answer = update_check.notice(update_check.check(True))
            except Exception:  # noqa: BLE001 the check is optional: any failure is no notice
                self.answer = None
        self.applied = False
        self.checker = threading.Thread(target=work, daemon=True)
        self.checker.start()

    def waiting(self):
        """True until the check's answer is drawn: the curses loop then wakes without a key."""
        return self.checker is not None and not self.applied

    def poll(self):
        """Takes the check's answer on the drawing thread, the cursor kept on the entry it was on."""
        if self.applied or self.checker is None or self.checker.is_alive():
            return
        name = self.entries[self.pos]
        self.found, self.applied = self.answer, True
        self.pos = self.entries.index(name) if name in self.entries else min(self.pos, len(self.entries) - 1)

    def refresh(self):
        """The header and the entries of the folder as it is now: after a screen or `init` it may have changed."""
        self.tree = pf.find_tree(self.folder)
        self.root = str(self.tree.parent) if self.tree else self.folder
        if self.tree:
            try:
                mode = settings.read_settings(self.root)["mode"][0]
            except (OSError, UnicodeDecodeError, ValueError) as e:
                mode = "unreadable: " + str(e)
            n = len(pf.open_changes(self.tree))
            # the count first: a long unreadable-mode reason is what a cut to two lines drops
            self.status, self.base = "%d open change%s, mode %s" % (n, "" if n == 1 else "s", mode), PROJECT
        elif os.path.isdir(os.path.join(self.folder, "openspec")) and not os.path.lexists(
                os.path.join(self.folder, "solo-sdd")):  # init's own test: it creates nothing here
            self.status = "openspec/ found: solo-sdd import openspec converts it"
            self.base = PROJECT[2:3] + PROJECT[4:]
        else:
            self.status, self.base = "no solo-sdd/ here", [PREPARE] + PROJECT[2:3] + PROJECT[4:]
        self.pos = min(self.pos, len(self.entries) - 1)

    def handle(self, key):
        """One key by name; "exit" ends, "init" asks the caller to run the `init` questions off the full screen."""
        if key == "resize":
            return None
        if self.sub:
            return self.on_sub(key)
        self.poll()
        if self.view and self.view[0].startswith("Update to "):
            if key == "y":
                self.view = None
                return "update"
            if key in ("n", "q", "esc"):
                self.view = None
                return None
        if self.view:
            if key in ("up", "down"):
                self.scroll = max(0, self.scroll + (1 if key == "down" else -1))
            elif key in ("q", "esc"):
                self.view = None
            return None
        self.message = ""
        if key in ("up", "down"):
            self.pos = (self.pos + (1 if key == "down" else -1)) % len(self.entries)
        elif key == "q":
            return "exit"
        elif key == "enter":
            return self.open(self.entries[self.pos])
        return None

    def open(self, entry):
        if entry == "Quit":
            return "exit"
        if entry == PREPARE:
            if os.path.exists(os.path.join(self.folder, ".git")):
                return "init"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                init.run(self.folder)  # refuses outside a git repository before any write
            self.message = " ".join(out.getvalue().split())
            return None
        if entry.startswith("Update to "):
            _, hint, _ = update_check.method()
            version = entry[len("Update to "):]
            self.view, self.scroll = (entry, [
                "Runs: " + hint,
                "Release notes: " + update_check.RELEASES + version,
                "Nothing runs until y.",
                "Then: solo-sdd install of the upgraded program; in a project whose rules block is from the older "
                "rules, solo-sdd init after a second question; then solo-sdd asks to be restarted."]), 0
            return None
        if entry == SKIP:
            update_check.skip(self.found)
            self.message = "%s skipped: the notice comes back with a newer version" % self.found
            name = self.entries[self.pos]
            self.found = None
            self.pos = self.entries.index(name) if name in self.entries else self.entries.index("Quit")
            return None
        if entry in ("Changes", "Doctor", "Commands"):
            self.view, self.scroll = (entry, self.text_of(entry)), 0
            return None
        sub = Screen.load(self.root, home=self.home) if self.tree else Screen(None, None, home=self.home,
                                                                                folder=self.folder)
        if entry == "Machine":
            sub.open_machine()
        elif entry == "Integrations and checklists" and sub.mode == "list":
            sub.mode = "integrations"
        # Esc here returns to the menu: where the entry opened, its sibling section, and the list a quit question's
        # b leads to, where Esc does nothing in the screen itself
        self.sub, self.start = sub, {sub.mode, "list"} | ({"checklists"} if sub.mode == "integrations" else set())
        return None

    def text_of(self, entry):
        from solo_sdd import cli, doctor, layout, process_cli
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                if entry == "Changes":
                    process_cli.list_cmd(self.tree, False, False)
                elif entry == "Doctor":
                    doctor.run()
                else:
                    print(cli.COMMANDS)
        except (layout.BrokenState, layout.BadTargets, OSError, ValueError) as e:  # what cli.main catches
            out.write("fail %s\n" % e)
        return out.getvalue().splitlines()

    def on_sub(self, key):
        """Keys go to the screen; q or Esc where it opened returns to the menu, unsaved edits asked about first."""
        sub = self.sub
        if key == "esc" and sub.mode in self.start:
            key = "q"
        got = sub.on_list("q") if key == "q" and sub.mode in ("integrations", "checklists") else sub.handle(key)
        if got == "exit":
            self.sub = None
            self.refresh()
        return None

    def draw(self, width, height):
        if self.sub:
            return self.sub.draw(width, height)
        if width < MIN_W or height < MIN_H:
            return ["Terminal too small: needs %dx%d, now %dx%d" % (MIN_W, MIN_H, width, height)], set()
        wrap = lambda text: textwrap.wrap(text, width - 1) or [""]  # noqa: E731
        folder = shown(self.folder)
        if fit(folder, width - 1) != folder:  # one line whatever the path, by columns: its end names the folder
            folder = "..." + fit(folder[::-1], width - 4)[::-1]
        self.poll()
        notice = "  %s available" % self.found if self.found else ""
        head = ["solo-sdd " + __version__ + notice] + wrap(shown(self.status))[:2] + [folder, ""]
        message = wrap(shown(self.message))[:2] if self.message else []
        updating = self.view and self.view[0].startswith("Update to ")
        footer = wrap(UPDATE_FOOTER if updating else VIEW_FOOTER if self.view else MENU_FOOTER)
        room = max(2, height - len(head) - len(message) - len(footer))
        if self.view:
            title, text = self.view
            lines = [w for ln in text for w in wrap(shown(ln))]
            self.scroll = min(self.scroll, max(0, len(lines) - room + 1))
            shown_to = min(len(lines), self.scroll + room - 1)
            body = ["%s: %d-%d of %d lines" % (title + (", read-only" if title == "Changes" else ""),
                                               self.scroll + 1 if lines else 0, shown_to, len(lines))]
            body, marked = body + lines[self.scroll:shown_to], set()
        else:
            top = max(0, self.pos - room + 1)
            body = [("> " if i == self.pos else "  ") + e for i, e in enumerate(self.entries)][top:top + room]
            marked = {len(head) + self.pos - top}
        lines = head + body + [""] * (room - len(body)) + message + footer
        return [fit(ln, width - 1) for ln in lines[:height]], marked


def home(folder="."):
    """Bare `solo-sdd` on a terminal: the menu; Prepare this folder runs the `init` questions off the full screen."""
    menu = Home(folder)
    menu.start_check()
    try:
        while True:
            got = run_curses(menu)
            if got == "init":
                init.run(menu.folder)
            elif got == "update":
                if update_check.update(menu.found, menu.root if menu.tree else None):
                    return 0  # the program in memory is the old one: it asked to be restarted
            else:
                break
            try:
                input("Enter returns to the menu ")
            except EOFError:
                pass
            menu.refresh()
    except KeyboardInterrupt:
        return 130
    return 0


CURSES_KEYS = {"KEY_UP": "up", "KEY_DOWN": "down", "KEY_ENTER": "enter", "\n": "enter", "\r": "enter", "\x1b": "esc",
               " ": "space", "KEY_BACKSPACE": "backspace", "\x7f": "backspace", "\b": "backspace",
               "KEY_RESIZE": "resize"}


def run_curses(screen):
    import curses
    import locale

    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:  # an unknown LANG: curses still draws ASCII
        pass
    os.environ.setdefault("ESCDELAY", "25")

    def loop(win):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        win.keypad(True)
        while True:
            h, w = win.getmaxyx()
            lines, marked = screen.draw(w, h)
            win.erase()
            for i, ln in enumerate(lines[:h]):
                try:
                    win.addstr(i, 0, ln, curses.A_REVERSE if i in marked else curses.A_NORMAL)
                except curses.error:  # the last cell of the screen
                    pass
            win.refresh()
            waiting = getattr(screen, "waiting", None)
            win.timeout(200 if waiting and waiting() else -1)  # a pending check redraws without a key
            try:
                ch = win.get_wch()
            except curses.error:  # no key within the timeout
                continue
            name = curses.keyname(ch).decode() if isinstance(ch, int) else ch
            got = screen.handle(CURSES_KEYS.get(name, name if isinstance(ch, str) else ""))
            if got:  # "exit", or what the caller runs off the full screen
                return got
    return curses.wrapper(loop)


def can_draw():
    """A terminal on stdin and stdout whose TERM curses knows and can move the cursor in."""
    if not (sys.stdin and sys.stdout and sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    import curses
    try:
        curses.setupterm()
        return curses.tigetstr("cup") is not None
    except curses.error:
        return False


def main(args):
    """`settings [folder]`: the exit code, or None on bad arguments."""
    if len(args) > 1:
        return None
    if not can_draw():
        print(NO_TERMINAL)
        return 1
    tree = pf.find_tree(args[0] if args else ".")
    try:
        if tree is None:  # no project: only the machine settings
            screen = Screen(None, None, folder=os.path.abspath(args[0] if args else "."))
            screen.open_machine()
        else:
            screen = Screen.load(str(tree.parent))
        run_curses(screen)
    except KeyboardInterrupt:
        return 130
    return 0
