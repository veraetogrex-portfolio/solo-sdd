"""`solo-sdd settings`: a full-screen terminal screen over the project's solo-sdd/config.

Screen is the state, the key handling and the drawing into plain lines; tests drive it by key names. The curses loop
in run_curses only maps keys and paints the lines.
"""
import contextlib
import io
import os
import sys
import textwrap
import unicodedata

from solo_sdd import init, integrations, process_format as pf, settings, setup_detect

MIN_W, MIN_H = 40, 12
KEYS = [k for g in settings.GROUPS for k in settings.REGISTRY if settings.ABOUT[k][0] == g]
FOOTER = {
    "list": "Up/Down move  Enter edit  r reset  i integrations  c checklists  s save  q quit",
    "integrations": "Up/Down move  Space switch on or off  Esc back",
    "checklists": "Up/Down move  a add  Enter edit  d remove  Esc back",
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
    def __init__(self, root, text, agents=None, ci=None, error=None, home=None):
        self.root, self.text, self.agents, self.ci = root, text, agents or {}, ci
        self.error, self.home = error, home if home is not None else os.path.expanduser("~")
        self.edits = {}  # key -> new value, None: back to the value below the file
        self.toggles = {}  # integration name -> True to enable, False to disable, saved through integrations.toggle
        self.pos, self.mode, self.message = 0, "broken" if error else "list", ""
        self.options, self.cursor, self.ticked, self.buffer = [], 0, set(), ""
        self.back, self.target, self.step, self.before = "list", None, None, {}
        self.ipos = self.cpos = 0
        self.base = {} if error else self.values()
        self.read_integrations()

    @classmethod
    def load(cls, root, home=None):
        agents, ci = settings.agents_delivery(root), setup_detect.ci(root)
        try:
            text = settings.read_settings_text(root)
            settings.parse_settings(text)
        except (OSError, UnicodeDecodeError, ValueError) as e:
            return cls(root, None, agents, ci, error=str(e), home=home)
        return cls(root, text, agents, ci, home=home)

    def read_integrations(self):
        """The integrations `solo-sdd integrations list` finds, and the names enabled by the file as it is on disk."""
        if self.error:
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

    def handle(self, key):
        """One key by name (up, down, enter, esc, space, backspace, resize, or the typed character); "exit" ends."""
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
        elif key == "esc":
            self.mode = "list"

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
        if width < MIN_W or height < MIN_H:
            return ["Terminal too small: needs %dx%d, now %dx%d" % (MIN_W, MIN_H, width, height)], set()
        head = ["solo-sdd settings  " + shown(self.root), ""]
        footer = textwrap.wrap(FOOTER[self.mode], width - 1)
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
            ch = win.get_wch()
            name = curses.keyname(ch).decode() if isinstance(ch, int) else ch
            if screen.handle(CURSES_KEYS.get(name, name if isinstance(ch, str) else "")) == "exit":
                return
    curses.wrapper(loop)


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
    if tree is None:
        print("no solo-sdd/ tree here: prepare the project with solo-sdd init")
        return 1
    try:
        run_curses(Screen.load(str(tree.parent)))
    except KeyboardInterrupt:
        return 130
    return 0
