"""solo-sdd init: prepare a project git repository for spec-driven work and write its settings.

Detection and proposals live in setup_detect.py; the only external programs are git and gh, read-only.
"""
import hashlib, os, shutil, sys

from solo_sdd import integrations, providers, resources, rules_block, settings, setup_detect

# path in the project -> template under templates/, None for a folder
TREE = (("solo-sdd/project.md", "solo-sdd/project.md"), ("solo-sdd/analyze.md", "solo-sdd/analyze.md"),
        ("solo-sdd/specs", None), ("solo-sdd/changes", None), ("docs/waiting.md", "docs/waiting.md"))
QUESTIONS = ("mode", "agents", "delivery.mode")
NO_CI = "delivery.mode: pr needs a CI workflow in .github/workflows: sdd-pr.py merge refuses a PR without checks"
HEADER = "# solo-sdd settings; change with solo-sdd config set <key> <value> or solo-sdd init --reconfigure\n"
RULES = "AGENTS.md"
RECORD = "solo-sdd/rules-block"  # sha256 of the block body init wrote last: tells an older block from an edited one
GLOBAL = "~/AGENTS.md, ~/.codex/AGENTS.md, ~/.claude/CLAUDE.md"


def value(key, raw):
    """The normalized value of key; ValueError naming the allowed keys or values."""
    bad = settings.unknown_key(key)
    if bad:
        raise ValueError(bad)
    if key == "agents":
        return ", ".join(providers.parse(raw))
    return settings.check_value(key, raw)


def parse(argv):
    """(folder, given, yes, reconfigure) of the arguments after `init`; None for an unknown argument;
    ValueError for a wrong value or a key given twice with different values."""
    folder, given, yes, reconfigure, i = None, {}, False, False, 0

    def put(key, raw):
        v = value(key, raw)
        if given.get(key, v) != v:
            raise ValueError("%s given twice: %s and %s" % (key, given[key], v))
        given[key] = v
    while i < len(argv):
        a = argv[i]
        if a in ("--yes", "--reconfigure"):
            yes, reconfigure = yes or a == "--yes", reconfigure or a == "--reconfigure"
        elif a in ("--solo", "--team"):
            put("mode", a[2:])
        elif a in ("--agents", "--delivery", "--set"):
            if i + 1 == len(argv):
                return None
            i += 1
            if a == "--set":
                key, eq, raw = argv[i].partition("=")
                if not eq:
                    raise ValueError("--set takes key=value, not %r" % argv[i])
                put(key.strip(), raw)
            else:
                put("agents" if a == "--agents" else "delivery.mode", argv[i])
        elif a.startswith("-") or folder is not None:
            return None
        else:
            folder = a
        i += 1
    return folder or ".", given, yes, reconfigure


def ask(key, current, why=None, read=None):
    """The answer to one question; Enter or end of input keeps current, a wrong value asks again."""
    allowed = settings.REGISTRY[key][1]
    choices = ", ".join(allowed) if allowed else "a whole number from 1"
    if why:
        print("%s: proposed %s (%s)" % (key, current, why))
    while True:
        try:
            got = (read or input)("%s (%s) [%s]: " % (key, choices, current)).strip()
        except EOFError:
            print()
            return current
        if not got:
            return current
        try:
            return value(key, got)
        except ValueError as e:
            print(e)


def first_config(root, given, interactive, read):
    """The text of a new solo-sdd/config: the proposals with their reasons, flags and answers over them."""
    found = setup_detect.detect(root)
    proposed = setup_detect.propose(found)
    lines = [HEADER]
    for key in QUESTIONS:
        guess, why = proposed[key]
        got = given.get(key) or (ask(key, guess, why, read) if interactive else guess)
        if key == "delivery.mode" and not found["ci"] and (found["remote"] or got == "pr"):
            print(NO_CI)
        reason = why if got == guess else "chosen; proposed %s: %s" % (guess, why)
        lines.append("# %s: %s\n%s: %s\n" % (key, reason, key, got))
    for key in settings.REGISTRY:
        if key in given and key not in QUESTIONS:
            lines.append("# %s: chosen\n%s: %s\n" % (key, key, given[key]))
    return "".join(lines)


def reconfigured(text, given, interactive, read, agents=None):
    """The text with only the lines of keys whose answer differs from the value in effect changed;
    agents: the AGENTS.md items of settings.agents_delivery."""
    current = settings.effective(settings.parse_settings(text), agents=agents)
    for key in list(QUESTIONS) + [k for k in settings.REGISTRY if k not in QUESTIONS]:
        got = given.get(key) or (ask(key, current[key][0], read=read) if interactive else None)
        if got is not None and value(key, got) != value(key, current[key][0]):  # agents: same names, other spelling
            text = settings.set_text(text, key, got)
            current = settings.effective(settings.parse_settings(text), agents=agents)
    return text


def _digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def rules_body(base, sections):
    """The block body: the base rules, then one `## Integration: <name>` section per (name, text) of sections."""
    return base + "".join("\n## Integration: %s\n\n%s" % (name, rules_block.norm(text)) for name, text in sections)


def project_rules(folder, scope, sections=(), create=True):
    """The solo-sdd rules block in the project AGENTS.md (bytes outside it kept) and CLAUDE.md with @AGENTS.md;
    sections: the (name, text) of the integration rules (integrations.rules_sections) the block ends with. An edited
    block or broken markers are drift and stay as they are; a block with CRLF line endings (a Windows checkout) is
    compared as LF and rewritten with CRLF. Without create (integrations enable and disable) only an existing block
    is rewritten and no file is created. Returns 1 when a file cannot be read or written."""
    path, record = os.path.join(folder, RULES), os.path.join(folder, RECORD)
    names = ", ".join(name for name, _ in sections)
    if scope == "global":
        try:
            has = rules_block.parse(_read(path)) is not None
        except (OSError, UnicodeDecodeError):
            has = False
        if create:
            print("rules.scope: global, %s gets no block%s; the rules come from the global block (%s): "
                  "solo-sdd install --global-rules" % (RULES, " (an existing one is kept)" if has else "", GLOBAL))
        if names:
            print("rules.scope: global, the rules of %s are not written to %s" % (names, RULES))
        if create or not has:
            return 0
        sections, names = (), ""  # enable and disable drop only the sections of an existing block: none kept stale
    strip = scope == "global"
    source = os.path.join(resources.ROOT, "global", "AGENTS.md")
    try:
        name = source
        body = rules_body(rules_block.norm(_read(source).replace("\r\n", "\n")), sections)  # CRLF clone: same rules
        name = path
        text = _read(path) if os.path.lexists(path) else None
        name = record
        recorded = _read(record).strip() if os.path.lexists(record) else None
    except (OSError, UnicodeDecodeError) as e:
        print("cannot read %s: %s" % (os.path.relpath(name, folder) if name != source else name,
                                      getattr(e, "strerror", None) or "not UTF-8"))
        return 1
    parts = None if text is None else rules_block.parse(text)
    if parts not in (None, rules_block.BROKEN):
        crlf = "\r\n" in parts[1]
        parts = parts[:1] + (parts[1].replace("\r\n", "\n"),) + parts[2:]
        if strip:  # under global the block keeps its base rules, of whichever version wrote them
            cut = parts[1].find("\n## Integration: ")
            if cut < 0:
                return 0
            body = parts[1][:cut]
    new = note = None
    if parts is None and not create and (recorded is None or text is None):
        if names:
            print("the rules of %s are not written: %s has no solo-sdd block; solo-sdd init writes it" % (names, RULES))
        return 0
    if parts is rules_block.BROKEN:
        note = "broken solo-sdd markers"
    elif parts is None and recorded is not None and text is not None:
        note = "the solo-sdd markers were erased"
    elif parts is None:
        new, done = (rules_block.block(body) if text is None else rules_block.append(text, body)[0]), "created"
    elif parts[1] == body:
        done = "ok"
    elif recorded == _digest(parts[1]):
        fresh = rules_block.block(body)
        new, done = parts[0] + (fresh.replace("\n", "\r\n") if crlf else fresh) + parts[2], "updated"
    else:
        note = "the solo-sdd block was edited in place"
    if note:
        print("drift   %s — %s, kept as is; the rules of this version: %s" % (
            RULES, note, os.path.join(resources.ROOT, "global", "AGENTS.md")))
    claude = os.path.join(folder, providers.PROVIDERS["claude"]["project_rules"])
    writes = ([path] if new is not None else []) + ([record] if not note and recorded != _digest(body) else []) + (
        [claude] if create and not os.path.lexists(claude) else [])
    for target in writes:  # a write that would fail is refused before the first one
        if not os.access(target if os.path.lexists(target) else os.path.dirname(target), os.W_OK):
            print("cannot write %s: not writable" % os.path.relpath(target, folder))
            return 1
    try:
        if new is not None:
            _write(path, new)
            print("%s the solo-sdd rules block in %s" % (done, RULES))
        if not note and recorded != _digest(body):
            _write(record, _digest(body) + "\n")
        if claude in writes:
            _write(claude, "@%s\n" % RULES)
            print("created CLAUDE.md")
    except OSError as e:
        print("cannot write %s: %s" % (e.filename and os.path.relpath(e.filename, folder), e.strerror))
        return 1
    return 0


def run(folder=".", given=None, yes=False, reconfigure=False, read=None, home=None):
    given = given or {}
    folder = os.path.abspath(folder)
    if not os.path.exists(os.path.join(folder, ".git")):
        print("not a git repository: git init")
        return 1
    if os.path.isdir(os.path.join(folder, "openspec")) and not os.path.lexists(os.path.join(folder, "solo-sdd")):
        print("openspec/ found, nothing created: convert it with solo-sdd import openspec, then run solo-sdd init again")
        return 0
    config = os.path.join(folder, settings.SETTINGS_FILE)
    old = new = None
    if os.path.lexists(config) and not reconfigure:
        if given:
            print("%s kept, the flags are not applied: solo-sdd init --reconfigure" % settings.SETTINGS_FILE)
    else:
        interactive = not yes and sys.stdin is not None and sys.stdin.isatty()  # stdin closed: sys.stdin is None
        try:
            old = settings.read_settings_text(folder) if os.path.lexists(config) else None
            new = first_config(folder, given, interactive, read) if old is None else reconfigured(
                old, given, interactive, read, settings.agents_delivery(folder))
        except (OSError, ValueError) as e:
            print(e)
            return 1
    try:  # the rules are refused before the first write; a broken config is named where the scope is read below
        listed = integrations.listed_names(settings.parse_settings(
            new if new is not None else settings.read_settings_text(folder)).get(integrations.LISTED, ""))
    except (OSError, ValueError):
        listed = []
    try:
        sections = integrations.rules_sections(integrations.find_integrations(
            folder, home if home is not None else os.path.expanduser("~")), listed)
    except integrations.IntegrationError as e:
        print("%s; nothing written" % e)
        return 1
    rel = None
    try:
        for rel, template in TREE:
            target = os.path.join(folder, rel)
            if os.path.lexists(target):
                continue
            if template is None:
                os.makedirs(target)
            else:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copyfile(os.path.join(resources.ROOT, "templates", template), target)
            print(f"created {rel}{'/' if template is None else ''}")
        rel = settings.SETTINGS_FILE
        if new is not None and new != old:
            with open(config, "w", encoding="utf-8", newline="") as f:
                f.write(new)
            print(("created %s" if old is None else "changed %s") % rel)
    except OSError as e:
        print(f"cannot create {rel}: {e.strerror}")
        return 1
    try:
        scope = settings.read_settings(folder)["rules.scope"][0]
    except (OSError, ValueError) as e:
        print("%s; the rules block is not written" % e)
        return 1
    code = project_rules(folder, scope, sections)
    print("next: /project-init")
    return code


def main(argv):
    """`init [folder] [flags]`: the exit code, or None on bad arguments."""
    try:
        args = parse(argv)
    except ValueError as e:
        print(e)
        return 1
    if args is None:
        return None
    return run(*args)
