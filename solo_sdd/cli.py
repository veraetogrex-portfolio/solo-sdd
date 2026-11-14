"""solo-sdd entry point: command parsing."""
import difflib, os, sys

from solo_sdd import __version__, doctor, hooks, import_openspec, integration_run, integrations, keywords, layout, process_cli, process_format, providers, settings, settings_ui
from solo_sdd import init as project_init

layout.PULL_HINT = "solo-sdd sync pull"

COMMANDS = """solo-sdd commands:
  --version                          version
  status                             state of every copy
  install [--agents a,b] [--hooks] [--global-rules] [--replace-foreign]
                                     lay out skills, scripts and templates for the agents (default: the last choice, else
                                     the detected ones; other always); --hooks connects the hooks in settings.json;
                                     --global-rules also writes the rules block into ~/AGENTS.md, ~/.codex/AGENTS.md and
                                     ~/.claude/CLAUDE.md (a home that has the block from an earlier version keeps it);
                                     a file solo-sdd did not lay out is kept, --replace-foreign replaces it with a backup
  uninstall [--purge | --global-rules]
                                     remove copies and hooks; --purge also removes solo-sdd data and a solo schema left by an
                                     old version; --global-rules removes only the global rules block
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
  import openspec [folder] [--write] plan of converting openspec/ into solo-sdd/; --write creates solo-sdd/, openspec/ stays"""


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


def install(with_hooks=False, agents=None, rules=False, replace_foreign=False):
    if agents is not None:
        try:
            agents = providers.parse(agents)
        except ValueError as e:
            print(e)
            return 1
    state = layout.load_state()
    if "claude" not in (agents or layout.chosen(state)) and (with_hooks or state.get("_hooks")):
        print("hooks need claude among the agents: solo-sdd install --agents claude,... --hooks"
              + ("; the connected hooks go with solo-sdd uninstall" if state.get("_hooks") else ""))
        return 1
    problems = layout.push(agents=agents, rules=rules, replace_foreign=replace_foreign)
    for name in agents or layout.chosen(layout.load_state()):
        if not providers.probed(name):
            print("%s: %s" % (name, providers.unprobed()))
    connected = hooks.setup() if with_hooks else 0
    return 1 if problems or connected else 0


def uninstall(purge=False):
    layout.load_targets()  # a bad map stops before the hooks are restored, not halfway
    steps = layout.load_state().get("_hooks")
    code = hooks.restore(steps) if steps else 0
    if code == 0:
        state = layout.load_state()
        if state.pop("_hooks", None) is not None:
            layout.save_state(state)
    return 1 if layout.uninstall(purge) or code else 0


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
