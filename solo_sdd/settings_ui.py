"""`solo-sdd settings`: a full-screen terminal screen over the project's solo-sdd/config.

Screen is the state, the key handling and the drawing into plain lines; tests drive it by key names. The curses loop
in run_curses only maps keys and paints the lines.
"""
import os
import sys
import textwrap
import unicodedata

from solo_sdd import init, process_format as pf, settings, setup_detect

MIN_W, MIN_H = 40, 12
KEYS = [k for g in settings.GROUPS for k in settings.REGISTRY if settings.ABOUT[k][0] == g]
FOOTER = {
    "list": "Up/Down move  Enter edit  r reset  s save  q quit",
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
    def __init__(self, root, text, agents=None, ci=None, error=None):
        self.root, self.text, self.agents, self.ci = root, text, agents or {}, ci
        self.error = error
        self.edits = {}  # key -> new value, None: back to the value below the file
        self.pos, self.mode, self.message = 0, "broken" if error else "list", ""
        self.options, self.cursor, self.ticked, self.buffer = [], 0, set(), ""
        self.base = {} if error else self.values()

    @classmethod
    def load(cls, root):
        agents, ci = settings.agents_delivery(root), setup_detect.ci(root)
        try:
            text = settings.read_settings_text(root)
            settings.parse_settings(text)
        except (OSError, UnicodeDecodeError, ValueError) as e:
            return cls(root, None, agents, ci, error=str(e))
        return cls(root, text, agents, ci)

    def edited_text(self):
        text = self.text
        for key, value in self.edits.items():
            text = settings.set_text(text, key, value)
        return text

    def values(self):
        return settings.effective(settings.parse_settings(self.edited_text()), agents=self.agents)

    def keep(self, value):
        """Record an edit of the selected key; one that leaves the file as it is drops the key's edit."""
        if settings.set_text(self.text, self.key, value) == self.text:
            self.edits.pop(self.key, None)
        else:
            self.edits[self.key] = value

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
            self.keep(None)
        elif key == "s":
            if self.edits:
                self.mode, self.cursor = "confirm", 0
            else:
                self.message = "nothing to save"
        elif key == "q":
            if not self.edits:
                return "exit"
            self.mode = "quit"
        return None

    def open_editor(self):
        kind, allowed = settings.REGISTRY[self.key][:2]
        value = self.values()[self.key][0]
        if allowed and kind == "choice":
            self.mode, self.options = "pick", list(allowed)
            self.cursor = self.options.index(value) if value in self.options else 0
        elif allowed:
            self.mode, self.options, self.cursor = "check", list(allowed), 0
            self.ticked = {v.strip() for v in value.split(",") if v.strip()}
        else:
            self.mode, self.buffer = "entry", value

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
            if self.buffer.strip():
                self.set(self.buffer)
            else:
                self.keep(None)
                self.mode = "list"
        elif key == "esc":
            self.mode = "list"
        elif key == "backspace":
            self.buffer = self.buffer[:-1]
        elif key == "space":
            self.buffer += " "
        elif len(key) == 1 and key.isprintable():
            self.buffer += key

    def set(self, raw):
        """An entered value through the same check as `config set`; a refused one keeps the old value."""
        self.mode = "list"
        try:
            value = settings.check_value(self.key, raw)
        except settings.SettingsError as e:
            self.message = str(e)
            return
        try:
            settings.parse_settings(settings.set_text(self.edited_text(), self.key, value))
        except settings.SettingsError as e:  # a value the file could not hold, e.g. a line separator
            self.message = str(e)
            return
        self.keep(value)
        if self.key == "delivery.mode" and value == "pr" and not self.ci:
            self.message = init.NO_CI

    def on_confirm(self, key):
        if key in ("up", "down"):
            self.cursor = max(0, min(len(self.edits) - 1, self.cursor + (1 if key == "down" else -1)))
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
        new = self.edited_text()
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new)
        except OSError as e:
            self.message = "cannot write %s: %s; nothing written" % (settings.SETTINGS_FILE, e.strerror)
            return False
        names = ", ".join(self.edits)
        self.text, self.edits = new, {}
        self.base = self.values()
        self.message = "saved: " + names
        return True

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

    def draw_mode(self):
        if self.mode in ("pick", "check"):
            lines = [self.key + ": " + ("pick a value" if self.mode == "pick" else "tick the values"), ""]
            for i, o in enumerate(self.options):
                box = "" if self.mode == "pick" else "[x] " if o in self.ticked else "[ ] "
                lines.append(("> " if i == self.cursor else "  ") + box + o)
            return lines, {self.cursor + 2}
        if self.mode == "entry":
            return [self.key + ": " + settings.describe(self.key, self.values())["type"], "",
                    "> " + shown(self.buffer) + "_"], set()
        if self.mode == "confirm":
            values, room = self.values(), max(1, self.room - 2)
            rows = ["%s: %s -> %s" % (k, shown(self.base[k][0]) or "(none)", shown(values[k][0]) or "(none)")
                    for k in self.edits]
            top = min(self.cursor, max(0, len(rows) - room))
            head = "Write these %d keys to %s?" % (len(rows), settings.SETTINGS_FILE)
            if len(rows) > room:
                return [head, "%d-%d shown, Up/Down scrolls" % (top + 1, min(len(rows), top + room))] + \
                    rows[top:top + room], set()
            return [head, ""] + rows[top:top + room], set()
        return ["Unsaved edits: %s" % ", ".join(self.edits)], set()


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
