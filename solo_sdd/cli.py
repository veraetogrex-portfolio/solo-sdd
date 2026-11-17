"""solo-sdd entry point: command parsing."""
import difflib, os, shlex, subprocess, sys, tempfile

from solo_sdd import __version__, doctor, hooks, import_openspec, integration_run, integrations, keywords, layout, process_cli, process_format, providers, settings, settings_ui
from solo_sdd import init as project_init

layout.PULL_HINT = "solo-sdd sync pull"

COMMANDS = """solo-sdd commands:
  --version                          version
  status                             state of every copy
  install [--agents a,b] [--hooks] [--global-rules] [--replace-foreign]
                                     lay out skills, scripts and templates for the agents (default: the last choice, else
                                     the detected ones; other always); --hooks connects the hooks in
                                     ~/.claude/settings.json and, for codex, ~/.codex/hooks.json;
                                     --global-rules also writes the rules block into ~/AGENTS.md, ~/.codex/AGENTS.md and
                                     ~/.claude/CLAUDE.md (a home that has the block from an earlier version keeps it);
                                     a file solo-sdd did not lay out is kept, --replace-foreign replaces it with a backup
  uninstall [--purge | --global-rules | --hooks]
                                     remove copies and hooks; --purge also removes solo-sdd data and a solo schema left by an
                                     old version; --global-rules removes only the global rules block; --hooks only the hooks
  init [folder] [--yes] [--solo|--team] [--agents a,b] [--delivery local|pr] [--set key=value]... [--reconfigure]
                                     prepare a project git repository: solo-sdd/ (project.md, analyze.md, specs/, changes/,
                                     config from the detected authors, CODEOWNERS, branch protection, remote and agents;
                                     asks on a terminal), docs/waiting.md, the rules block in AGENTS.md and CLAUDE.md
                                     (rules.scope: global writes none); --reconfigure asks again for every setting
  doctor                             check the environment: python, copies, hooks, agents and their gaps, gh, AGENTS.md keywords
  update [--replace-foreign]         repeat the layout, suggest a package upgrade
  sync pull <name> [--from <place>]  take an edit made in place back into the repository
  migrate-agents [folder] [--write]  rename pre-English AGENTS.md headings and items to English; without --write only the diff
  validate [<id>] [--all] [--json]   check the solo-sdd/ process tree (one change or all), no external program
  list [--specs] [--json]            open changes with task progress and CLAIM/WAITING, or main specs with requirement counts
  new <id>                           create solo-sdd/changes/<id>/ from the templates
  archive <id> [--yes] [--force]     apply the change's deltas to the main specs and move it to changes/archive/
  config list|get <key>|set <key> <value>|unset <key>
                                     project settings in solo-sdd/config: every key with its value and source, one value, change one line
  config describe [<key>]|list --json
                                     what each key changes, its type, allowed values, defaults and value in effect; the
                                     list rows with these fields as JSON
  settings [folder]                  full-screen terminal screen of the project settings: every key by group with its
                                     value, source and description; edit by type, reset, save only the edited lines
  integrations list|enable <name>|disable <name>
                                     integrations of solo-sdd/integrations/, ~/.local/share/solo-sdd/integrations/ and
                                     the bundled ones with their source and state; enable or disable one by the integrations
                                     line of solo-sdd/config (integrations.off for a bundled one, enabled unless it names it)
                                     and rewrite the AGENTS.md block with the rules.md of the enabled ones
  check --point checks|ship [--changed] [--change <id>]
                                     run the enabled integrations of the point (--changed: those whose applies matches a
                                     changed file), one PASS|FAIL|SKIP line each; the result is recorded by the working
                                     tree under ~/.local/share/solo-sdd/checks/ and reused on the same tree; --change
                                     puts one Integrations line of the point into the change's verification.md Result
  check --point review|audit [--changed] [--tag <tag>]
                                     run nothing: one MATERIAL <name>: <path> line per enabled integration of the point;
                                     --tag: per enabled one with the tag, the bundled ones included, also outside a project
  import openspec [folder] [--write] plan of converting openspec/ into solo-sdd/; --write creates solo-sdd/, openspec/ stays
  ignore [--write]                   the git.ignore lines no rule of the repository's .gitignore files outside the solo-sdd
                                     block hides (every ! line too) and the tracked files they hide; --write puts them
                                     between # solo-sdd:begin and # solo-sdd:end of .gitignore, other bytes kept"""


IGNORE_BEGIN, IGNORE_END = "# solo-sdd:begin", "# solo-sdd:end"
# git variables that would point a git call at another repository than its -C folder
GIT_PLACE = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY")


def ignore_block(text):
    """(start, end) offsets of the solo-sdd block of a .gitignore text (end after its end line), None without one;
    ValueError naming .gitignore:<line> for a begin without its end, an end without its begin or a second block."""
    found, start, offset = None, None, 0
    for n, line in enumerate(text.split("\n"), 1):
        mark = line.rstrip("\r")
        if mark == IGNORE_BEGIN and (start is not None or found):
            raise ValueError(".gitignore:%d: a second %s; nothing written" % (n, IGNORE_BEGIN))
        if mark == IGNORE_BEGIN:
            start = (n, offset)
        elif mark == IGNORE_END and start is None:
            raise ValueError(".gitignore:%d: %s without %s; nothing written" % (n, IGNORE_END, IGNORE_BEGIN))
        elif mark == IGNORE_END:
            found, start = (start[1], min(offset + len(line) + 1, len(text))), None
        offset += len(line) + 1
    if start is not None:
        raise ValueError(".gitignore:%d: %s without %s; nothing written" % (start[0], IGNORE_BEGIN, IGNORE_END))
    return found


def ignore_text(text, lines):
    """The .gitignore text with the solo-sdd block holding lines (no lines: no block), every other byte kept; a new
    block goes at the end after one added line break, with the file's CRLF line endings; an existing block keeps the
    line ending of its begin line (the break added before it can make a CRLF of a lone CR)."""
    span = ignore_block(text)
    eol = "\r\n" if ("\r\n" in text if span is None else text.startswith(IGNORE_BEGIN + "\r\n", span[0])) else "\n"
    block = "".join(ln + eol for ln in [IGNORE_BEGIN] + lines + [IGNORE_END]) if lines else ""
    if span:
        return text[:span[0]] + block + text[span[1]:]
    return text + (eol if text and block and not text.endswith("\n") else "") + block


def ignore_hidden(top, text, items):
    """{item: '<file>:<line>: <pattern>'} of the items a rule of the repository's .gitignore files outside the block
    hides; a fresh repository holds copies of the .gitignore files on each item's way, so .git/info/exclude and the
    global excludes file, which do not travel with the repository, never count."""
    span = ignore_block(text)
    outside = text[:span[0]] + text[span[1]:] if span else text
    env = {k: v for k, v in os.environ.items() if k not in GIT_PLACE}
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "init", "-q", "--template=", tmp], env=env, check=True, capture_output=True,
                       stdin=subprocess.DEVNULL)
        for item in items:
            folders = item.rstrip("/").split("/")[:-1]
            for k in range(len(folders) + 1):
                rel = os.path.join(*(folders[:k] + [".gitignore"]))
                src, dst = os.path.join(top, rel), os.path.join(tmp, rel)
                if os.path.isfile(src) and not os.path.lexists(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    if k == 0:
                        with open(dst, "w", encoding="utf-8", newline="") as f:
                            f.write(outside)
                    else:
                        with open(src, "rb") as f, open(dst, "wb") as g:
                            g.write(f.read())
        r = subprocess.run(["git", "-C", tmp, "-c", "core.excludesFile=" + os.devnull, "check-ignore", "-v", "-n", "-z",
                            "--no-index", "--stdin"], input="".join(i + "\0" for i in items), env=env,
                           capture_output=True, text=True)
    if r.returncode > 1:
        raise ValueError("git check-ignore: " + r.stderr.strip())
    f = r.stdout.split("\0")
    return {f[i + 3]: "%s:%s: %s" % tuple(f[i:i + 3]) for i in range(0, len(f) - 3, 4)
            if f[i] and not f[i + 2].startswith("!")}


def ignore(folder=".", write=False):
    """`solo-sdd ignore [--write]`: the git.ignore lines no rule outside the solo-sdd block of .gitignore hides, put
    into that block with --write; a refusal changes no file. The exit code."""
    r = subprocess.run(["git", "-C", folder, "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, env=dict(os.environ, LC_ALL="C"))
    if r.returncode:
        print("not a git repository: %s; nothing written" % (r.stderr.strip() or folder))
        return 1
    top = r.stdout.rstrip("\n")
    path = os.path.join(top, ".gitignore")
    try:
        value = settings.read_settings(top)[settings.IGNORE_KEY][0]
        why = settings.tree_refusal(top, value)
        if why:
            raise ValueError("%s: %s" % (settings.SETTINGS_FILE, why))
        items = [i for i in value.split(", ") if i]
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    except FileNotFoundError:
        text = ""
    except (OSError, ValueError) as e:
        print("%s; nothing written" % e)
        return 1
    try:
        hidden = ignore_hidden(top, text, [i for i in items if not i.startswith("!")])
        lines = [i for i in items if i not in hidden]
        new = ignore_text(text, lines)
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        print(e)
        return 1
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".exclude") as f:
        f.write("".join(i + "\n" for i in items))
        f.flush()
        r = subprocess.run(["git", "-C", top, "ls-files", "-z", "-c", "-i", "--exclude-from=" + f.name],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode:  # a failed listing is no answer: the tracked paths it would name stay unknown
        print("cannot list the tracked files: %s; nothing written" % r.stderr.strip())
        return 1
    for item in items:
        print("%s: already hidden by %s, not in the block" % (item, hidden[item]) if item in hidden else item)
    for tracked in sorted(p for p in r.stdout.split("\0") if p):
        print("git tracks %s, the block does not remove it: git rm --cached -r -- %s" % (tracked, shlex.quote(tracked)))
    if new == text:
        print("no change")
    elif not write:
        print("not written: solo-sdd ignore --write writes it")
    else:
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new)
        except OSError as e:
            print("cannot write .gitignore: %s" % e.strerror)
            return 1
        print("wrote the solo-sdd block of .gitignore" if lines else "removed the solo-sdd block of .gitignore")
    return 0


def upgrade_hint(prefix, root):
    if "/uv/tools/" in prefix:
        return "uv tool upgrade solo-sdd"
    if "/pipx/venvs/" in prefix:
        return "pipx upgrade solo-sdd"
    if "node_modules" in root:
        return "npm update -g solo-sdd"
    if os.path.exists(os.path.join(root, ".git")):
        return f"git pull in {root}"
    return "python3 -m pip install --upgrade solo-sdd"


def hooks_refusal(chosen, with_hooks, state):
    """Why install refuses the hooks for the chosen agents, else None: hooks need claude or a codex whose `hooks`
    capability the probe confirmed, and connected Claude hooks need claude kept."""
    on = with_hooks or state.get("_hooks") or state.get("_codex_hooks")
    if on and "claude" not in chosen and not ("codex" in chosen and providers.has("codex", "hooks")):
        return ("hooks need claude or a confirmed codex among the agents: solo-sdd install --agents claude,... --hooks"
                + ("; the connected hooks go with solo-sdd uninstall" if state.get("_hooks") or state.get("_codex_hooks") else ""))
    if state.get("_hooks") and "claude" not in chosen:
        return "hooks need claude among the agents while its hooks are connected: solo-sdd uninstall --hooks removes them"
    return None


def install(with_hooks=False, agents=None, rules=False, replace_foreign=False):
    if agents is not None:
        try:
            agents = providers.parse(agents)
        except ValueError as e:
            print(e)
            return 1
    state = layout.load_state()
    chosen = agents or layout.chosen(state)
    refusal = hooks_refusal(chosen, with_hooks, state)
    if refusal:
        print(refusal)
        return 1
    codex_on = "codex" in chosen and providers.has("codex", "hooks") and bool(
        with_hooks or state.get("_hooks") or state.get("_codex_hooks"))
    if codex_on or state.get("_codex_hooks"):
        try:
            hooks.codex_check()  # a broken file stops before any copy is written
        except (ValueError, OSError) as e:
            print("fail %s" % e)
            return 1
    problems = layout.push(agents=agents, rules=rules, replace_foreign=replace_foreign)
    for name in chosen:
        if not providers.probed(name):
            print("%s: %s" % (name, providers.unprobed()))
    connected = hooks.setup() if with_hooks and "claude" in chosen else 0
    if codex_on or state.get("_codex_hooks"):
        connected = codex_hooks(codex_on) or connected
    return 1 if problems or connected else 0


def codex_hooks(on):
    """Writes or removes the solo-sdd entries of ~/.codex/hooks.json and records it in the state; 1 on an unusable file."""
    try:
        line = hooks.codex_write(on)
    except (ValueError, OSError) as e:
        print("fail %s" % e)
        return 1
    if line:
        print(line)
    state = layout.load_state()
    if on != bool(state.get("_codex_hooks")):
        if on:
            state["_codex_hooks"] = True
        else:
            state.pop("_codex_hooks")
        layout.save_state(state)
    return 0


def uninstall(purge=False):
    layout.load_targets()  # a bad map stops before the hooks are restored, not halfway
    steps = layout.load_state().get("_hooks")
    code = hooks.restore(steps) if steps else 0
    if code == 0:
        state = layout.load_state()
        if state.pop("_hooks", None) is not None:
            layout.save_state(state)
    if layout.load_state().get("_codex_hooks"):
        code = codex_hooks(False) or code
    return 1 if layout.uninstall(purge) or code else 0


def uninstall_hooks():
    """Disconnects only what install --hooks recorded; the copies, the rules block and a person's entries stay."""
    state = layout.load_state()
    steps = state.get("_hooks")
    if not steps and not state.get("_codex_hooks"):
        print("hooks are not connected; nothing changed")
        return 0
    if state.get("_codex_hooks") and codex_hooks(False):
        return 1
    if not steps:
        return 0
    if hooks.restore(steps):
        return 1
    state = layout.load_state()
    state.pop("_hooks", None)
    layout.save_state(state)
    print("ok: hooks disconnected, the copies stay; restart Claude Code")
    return 0


def update(replace_foreign=False):
    problems = layout.push(replace_foreign=replace_foreign)
    print(upgrade_hint(sys.prefix, layout.REPO))
    return 1 if problems else 0


def status():
    state = layout.load_state()
    print(f"source: {state.get('_source', layout.REPO)} {state.get('_version', __version__)}")
    layout.status()
    return 0


def migrate_agents(folder=".", write=False):
    """Diff of AGENTS.md with the pre-English headings and items renamed; --write applies it."""
    path = os.path.join(folder, "AGENTS.md")
    try:
        with open(path, encoding="utf-8", newline="") as f:
            old = f.read()
    except OSError as e:
        print(f"no AGENTS.md: {path}: {e.strerror}")
        return 1
    new, found = keywords.migrate_agents(old)
    if new == old:
        print(f"{path}: nothing to change")
        return 0
    sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "a/AGENTS.md", "b/AGENTS.md"))
    if write:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new)
        print(f"{path}: rewritten ({', '.join(found)})")
    else:
        print(f"{path}: not changed; apply with: solo-sdd migrate-agents {folder} --write")
    return 0


def main(argv=None):
    try:
        return _main(argv)
    except layout.BrokenState as e:
        print(f"fail state: {e}")
        return 1
    except layout.BadTargets as e:
        print(f"fail {e}")
        return 1


def _main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if not argv and settings_ui.can_draw():
        return settings_ui.home()
    if argv == ["--version"]:
        print(__version__)
        return 0
    if argv in (["status"], ["update"], ["doctor"]):
        return {"status": status, "update": update, "doctor": doctor.run}[argv[0]]()
    if argv == ["update", "--replace-foreign"]:
        return update(replace_foreign=True)
    if argv and argv[0] == "init":
        code = project_init.main(argv[1:])
        if code is not None:
            return code
    if argv and argv[0] == "install":
        flags = [a for a in argv[1:] if a in ("--hooks", "--global-rules", "--replace-foreign")]
        rest = [a for a in argv[1:] if a not in flags]
        if len(set(flags)) == len(flags) and (rest == [] or (len(rest) == 2 and rest[0] == "--agents")):
            return install("--hooks" in flags, rest[1] if rest else None, "--global-rules" in flags,
                           "--replace-foreign" in flags)
    if argv and argv[0] == "uninstall" and argv[1:] in ([], ["--purge"]):
        return uninstall(bool(argv[1:]))
    if argv == ["uninstall", "--global-rules"]:
        return layout.uninstall_rules()
    if argv == ["uninstall", "--hooks"]:
        return uninstall_hooks()
    if argv and argv[0] == "migrate-agents":
        rest = [a for a in argv[1:] if a != "--write"]
        if len(rest) <= 1 and len(argv) - len(rest) <= 2:
            return migrate_agents(*rest, write="--write" in argv[1:])
    if argv and argv[0] == "settings":
        code = settings_ui.main(argv[1:])
        if code is not None:
            return code
    if argv and argv[0] == "validate":
        code = process_format.run(argv[1:])
        if code is not None:
            return code
    if argv and argv[0] in ("list", "new", "archive"):
        code = process_cli.run(argv)
        if code is not None:
            return code
    if argv and argv[0] == "config":
        code = settings.run(argv[1:])
        if code is not None:
            return code
    if argv and argv[0] == "integrations":
        code = integrations.run(argv[1:])
        if code is not None:
            return code
    if argv and argv[0] == "check":
        code = integration_run.run(argv[1:])
        if code is not None:
            return code
    if argv in (["ignore"], ["ignore", "--write"]):
        return ignore(".", len(argv) == 2)
    if argv and argv[0] == "import":
        code = import_openspec.main(argv[1:])
        if code is not None:
            return code
    if argv[:2] == ["sync", "pull"]:
        code = layout.main(argv[1:])
        if not os.path.exists(os.path.join(layout.REPO, ".git")):
            print("source is the installed package: the edit is lost on upgrade, move it to a clone")
        return code
    if argv[:1] in (["-h"], ["--help"], ["help"]) or argv[1:2] in (["-h"], ["--help"]):
        print(COMMANDS)
        return 0
    if argv:
        print("solo-sdd: wrong command or arguments: " + " ".join(argv), file=sys.stderr)
    print(COMMANDS)
    return 2
