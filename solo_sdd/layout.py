#!/usr/bin/env python3
"""Lays out skills, global rules, scripts and templates from this repository to the places
where Claude Code and Codex read them (map: targets.json).

    python3 sync.py status          what diverged and what will be done
    python3 sync.py push            lay out; edits made in place are not overwritten
    python3 sync.py push --global-rules  also lay out the global rules block (kept on by the state from then on)
    python3 sync.py push --force    lay out over edits made in place too (with a backup)
    python3 sync.py push --replace-foreign  also replace files solo-sdd did not lay out (with a backup)
    python3 sync.py pull <name>     take an edit made in place back into the repository

State of each copy:
    ok           matches the repository
    missing      no copy; push creates it
    outdated     the copy is the one laid out last time and the repository is newer; push updates it
    first        a copy exists but sync has not laid it out yet; push keeps a whole file (foreign) unless
                 --replace-foreign (then with a backup), and adds the block to a rules file
    drift        the copy was edited in place after the last layout; push skips it, pull or --force needed
    unreachable  no read or write access (the folder is closed to this process) or the file is not UTF-8

Hashes of what was laid out live in ~/.local/share/solo-sdd/state.json by paths from ~ (so the state is one
for this computer and for a session where the home folder is mounted at another path);
the _source key there is the path of this repository for status and sync pull; _global_rules is the choice of
the global rules block (a state without it: on when it records a copy of the block from an earlier version);
_integration_skills maps each copy of an owner integration skill to its integration, so push removes it when that
integration or skill is gone;
backups are next to it in backup/, the newest KEEP_BACKUPS run folders are kept.
A state.json that cannot be read or parsed stops every command (BrokenState) before any file changes.
"""
import copy, errno, hashlib, json, os, re, shutil, sys, tempfile, time

from solo_sdd import __version__, integration_run, integrations, providers, resources, rules_block

REPO = resources.ROOT
PULL_HINT = "python3 sync.py pull"
HOME = os.path.expanduser("~")
DATA = os.path.join(HOME, ".local", "share", "solo-sdd")
STATE = os.path.join(DATA, "state.json")
# Copies an earlier version laid out and this one no longer has a source for.
RETIRED = ("~/.local/bin/openspec-after-update.py", "~/.local/bin/test_openspec_after_update.py",
           "~/.local/share/solo-sdd/templates/openspec/config.yaml", "~/.local/share/solo-sdd/templates/openspec/analyze.md")
OLD_JOB = "~/Library/LaunchAgents/local.openspec-after-update.plist"
KEEP_BACKUPS = 20
RUN_NAME = re.compile(r"([0-9]{8}-[0-9]{6})(-[0-9]+-[0-9]+)?")  # <time>-<pid>-<n>; <time> alone from an earlier version
FOREIGN_HINT = "install --replace-foreign replaces it"
SKILL_MAX_BYTES = 1 << 20
SKILLS = "_integration_skills"  # state: copy key -> integration name


class BrokenState(Exception):
    """state.json exists and cannot be read, does not parse or is not a JSON object."""


class BadTargets(Exception):
    """targets.json names what the layout cannot place (a skill absent from `skills`)."""


def expand(path):
    return os.path.join(HOME, path[2:]) if path.startswith("~/") else path


def short(path):
    return "~" + path[len(HOME):] if path.startswith(HOME + os.sep) else path


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _replace(path, text, newline):
    """Writes a new file next to path and moves it into place: a stopped run leaves the old or the new file whole.
    A link is written through to its file; the mode of an existing file is kept; a write-protected file is refused
    as an in-place write would refuse it."""
    path = os.path.realpath(path)
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    try:
        mode = os.stat(path).st_mode & 0o7777
        if not os.access(path, os.W_OK):
            raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), path)
    except FileNotFoundError:
        mask = os.umask(0)
        os.umask(mask)
        mode = 0o666 & ~mask
    fd, tmp = tempfile.mkstemp(dir=folder, prefix="." + os.path.basename(path) + ".", suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def write(path, text):
    _replace(path, text, None)


def read_raw(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write_raw(path, text):
    _replace(path, text, "")


def load_state():
    """The state; a missing file is a fresh deployment, a broken one raises BrokenState."""
    try:
        state = json.loads(read(STATE))
    except FileNotFoundError:
        return {}
    except OSError as e:
        raise BrokenState(f"{short(STATE)}: {e.strerror or e}")
    except ValueError as e:  # UnicodeDecodeError included
        raise BrokenState(f"{short(STATE)}: {e}")
    if not isinstance(state, dict):
        raise BrokenState(f"{short(STATE)}: not a JSON object")
    return state


def save_state(state):
    write(STATE, json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def chosen(state):
    """Agents of this deployment: the stored choice; a state from before the choice: all; no state: the detected."""
    if state.get("_agents"):
        return [n for n in providers.ALL if n in state["_agents"]]
    if any(not k.startswith("_") for k in state):
        return list(providers.LEGACY)
    return providers.detected(HOME)


def load_targets():
    """targets.json; an entry laid out into skill folders that names a skill absent from `skills` raises BadTargets."""
    targets = json.loads(read(os.path.join(REPO, "targets.json")))
    for rel, copies in targets["files"].items():
        skills = copies.get("skills", {}) if isinstance(copies, dict) else {}
        if not isinstance(skills, dict) or not all(isinstance(v, str) for v in skills.values()):
            raise BadTargets(f"targets.json: {rel}: skills must map each skill to the path inside its folder")
        unknown = [s for s in skills if s not in targets["skills"]]
        if unknown:
            raise BadTargets(f"targets.json: {rel} names the skill {', '.join(unknown)}, which is not in skills")
    return targets


def opt_in_keys():
    """State keys of the copies laid out only on request (the global rules block)."""
    targets = load_targets()
    return {p for c in targets["files"].values() if isinstance(c, dict) and c.get("opt_in") for p in c["copies"]}


def global_rules(state):
    """The choice of the global rules block: the stored one, else on when an earlier version recorded a copy of it."""
    if "_global_rules" in state:
        return bool(state["_global_rules"])
    return any(k in state for k in opt_in_keys())


def pairs(agents=None, rules=None):
    """(name, file in the repository, absolute path of the copy, block) for every copy from targets.json
    that belongs to the chosen agents (None: the choice in the state) or to no agent; an opt-in copy
    only when rules (None: the choice in the state). A file entry with `skills` goes into the folder of each
    named skill for every agent that skill's SKILL.md goes to. A list: targets.json is checked before any copy."""
    if agents is None or rules is None:
        state = load_state()
        agents = chosen(state) if agents is None else agents
        rules = global_rules(state) if rules is None else rules
    targets = load_targets()
    needs = targets.get("needs", {})
    roots = {name: [expand(providers.PROVIDERS[a]["skills"]) for a in where
                    if a in agents and providers.probed(a) and all(providers.has(a, c) for c in needs.get(name, ()))]
             for name, where in targets["skills"].items()}
    out = []
    for name in targets["skills"]:
        source = os.path.join(REPO, "skills", name, "SKILL.md")
        out += [(name, source, os.path.join(root, name, "SKILL.md"), False) for root in roots[name]]
    for rel, copies in targets["files"].items():
        if rel.endswith("/**"):  # a whole repository folder: one per file, without hidden ones
            base = rel[:-3]
            for dirpath, dirs, files in os.walk(os.path.join(REPO, base)):
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "__pycache__")
                for f in sorted(files):
                    if not f.startswith("."):
                        sub = os.path.relpath(os.path.join(dirpath, f), os.path.join(REPO, base))
                        out.append((f"{base}/{sub}", os.path.join(REPO, base, sub), os.path.join(expand(copies[0]), sub), False))
            continue
        if isinstance(copies, dict) and "skills" in copies:
            out += [(rel, os.path.join(REPO, rel), os.path.join(root, skill, inner), False)
                    for skill, inner in copies["skills"].items() for root in roots[skill]]
            continue
        block = isinstance(copies, dict) and copies.get("mode") == "block"
        if isinstance(copies, dict) and copies.get("opt_in") and not rules:
            continue
        for place in copies["copies"] if isinstance(copies, dict) else copies:
            if providers.owner(place) in (None, *agents):
                out.append((rel, os.path.join(REPO, rel), expand(place), block))
    return out


def _unreadable(path, folder=False):
    """The reason a path that exists cannot be read for lack of permission (a folder that cannot be listed or entered,
    a closed file), else None: a missing path, a link loop or a link to a file is not a closed source."""
    try:
        if folder:
            os.listdir(path)
            os.stat(os.path.join(path, "."))  # a listable folder without x cannot be entered
        else:
            os.close(os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)))
    except OSError as e:
        if e.errno in (errno.EACCES, errno.EPERM):
            return e.strerror
    return None


def integration_pairs(agents):
    """([(integration:<name>, its SKILL.md, absolute path of the copy, False)], [refusal line], held) for each
    skills/<skill>/SKILL.md of every owner integration (read in HOME only) into the skill root of every chosen agent.
    Refused and named: a broken integration that has a skills folder, a skill name the map or an integration earlier
    in name order takes, a folder name outside the integration name rule, a linked skills folder, skill folder or
    SKILL.md, and a SKILL.md integration_text refuses (missing, not a regular file, over SKILL_MAX_BYTES, not UTF-8).
    held: what could not be read, so its recorded copies stay: "*" (the owner source), integration names, copy keys."""
    every = [expand(p["skills"]) for p in providers.PROVIDERS.values() if p["skills"]]
    owners = dict.fromkeys(load_targets()["skills"], "solo-sdd")
    for _, _, target, _ in pairs(providers.ALL, True):  # a skill folder the map fills is taken too
        for root in every:
            if target.startswith(root + os.sep):
                owners.setdefault(os.path.relpath(target, root).split(os.sep)[0], "solo-sdd")
    roots = [expand(providers.PROVIDERS[a]["skills"]) for a in agents if providers.probed(a)]
    recorded = load_state().get(SKILLS, {})
    out, refused, held = [], [], set()

    def hold(name, keys=None):
        """Keeps the recorded copies of name (or only keys) and reserves their skill names for it."""
        held.update(keys or [name])
        for key, owner in recorded.items():
            if owner == name and (keys is None or key in keys):
                owners.setdefault(key.rstrip("/").split("/")[-2], name.replace(":", " ", 1))

    base = os.path.join(HOME, integrations.INTEGRATION_SOURCES[1][1][2:])
    closed = _unreadable(base, True)
    if closed:
        held.add("*")
        refused.append(f"skipped    {'integration:-':38} {short(base)}: {closed}")
    for e in integrations.find_integrations(HOME, HOME, integrations.INTEGRATION_SOURCES[1:]):
        name = "integration:" + (e["name"] or "-")
        folder = os.path.join(e["dir"], "skills")
        where = e["file"].rsplit("/", 1)[0] + "/skills"
        if e["error"]:
            if not e["name"]:  # the owner source is not a folder: gone, unless the probe above found it closed
                if not closed:
                    refused.append(f"skipped    {name:38} {e['error']}")
                continue
            if _unreadable(e["dir"], True) or _unreadable(os.path.join(e["dir"], integrations.INTEGRATION_FILE)):
                hold(name)
            if name in held or os.path.lexists(folder):
                refused.append(f"skipped    {name:38} {e['error']}")
            continue
        if not os.path.lexists(folder):
            continue
        if os.path.islink(folder) or not os.path.isdir(folder):
            refused.append(f"skipped    {name:38} {where}: a link or not a folder")
            continue
        shut = _unreadable(folder, True)
        if shut:
            hold(name)
            refused.append(f"skipped    {name:38} {where}: {shut}")
            continue
        try:
            names = sorted(os.listdir(folder))
        except OSError as x:
            refused.append(f"skipped    {name:38} {where}: {x.strerror or x}")
            continue
        for raw in names:
            path, at = os.path.join(folder, raw), f"{where}/{integrations.integration_shown(raw)}"
            if not os.path.isdir(path) and not os.path.islink(path):
                continue  # a plain file is not a skill
            if not integrations.integration_name(raw):
                reason = "not a skill name (lowercase letters, digits and -)"
            elif os.path.islink(path):
                reason = "a link, not the folder itself"
            elif raw in owners:
                reason = f"the name {raw} is taken by {owners[raw]}"
            else:
                try:
                    integrations.integration_text(os.path.join(path, "SKILL.md"), at + "/SKILL.md", SKILL_MAX_BYTES)
                except integrations.IntegrationError as x:
                    skill = os.path.join(path, "SKILL.md")
                    if not os.path.islink(skill) and _unreadable(skill):
                        hold(name, {short(os.path.join(root, raw, "SKILL.md")) for root in every})
                    refused.append(f"skipped    {name:38} {x}")
                    continue
                owners[raw] = "integration " + e["name"]
                out += [(name, os.path.join(path, "SKILL.md"), os.path.join(root, raw, "SKILL.md"), False) for root in roots]
                continue
            refused.append(f"skipped    {name:38} {at}: {reason}")
    return out, refused, held


def laid(agents=None, rules=None):
    """The pairs of the map and of the owner integration skills for agents (None: the choice in the state)."""
    if agents is None:
        agents = chosen(load_state())
    return pairs(agents, rules) + integration_pairs(agents)[0]


def record(state, name, key):
    """Records which integration laid out the copy at key; a map copy is not recorded."""
    if name.startswith("integration:"):
        state.setdefault(SKILLS, {})[key] = name


def orphans(state, items, held=()):
    """Removal items for the recorded integration skill copies items do not lay out and held does not keep."""
    keep = {short(t) for _, _, t, _ in items}
    return [(name, None, expand(key), False) for key, name in sorted(state.get(SKILLS, {}).items())
            if key not in keep and key not in held and name not in held and "*" not in held]


def classify(source_text, target, state, block=False):
    """State of one copy: see the module description. block means the copy is kept as a block between markers."""
    try:
        if not os.path.exists(target):
            # A closed folder looks empty: check the nearest existing folder above.
            parent = os.path.dirname(target)
            while not os.path.exists(parent):
                parent = os.path.dirname(parent)
            if not os.access(parent, os.R_OK | os.X_OK):
                return "unreachable", None
            return "missing", None
        text = read_raw(target) if block else read(target)
    except (OSError, UnicodeDecodeError):
        return "unreachable", None
    if block:
        recorded = state.get(short(target))
        parts = rules_block.parse(text)
        if parts is rules_block.BROKEN:
            return "drift", None
        if parts is not None:
            body = parts[1]
            if body == rules_block.norm(source_text):
                return "ok", body
            if recorded is None:
                return "first", body
            return ("outdated" if recorded == digest(body) else "drift"), body
        if recorded is None:
            return "first", None
        if recorded != digest(text) and short(target) in state.get("_blocks", {}):
            return "drift", None  # the block was there, the markers are erased: treat as broken so personal text does not go into the repository
        return ("outdated" if recorded == digest(text) else "drift"), text
    if text == source_text:
        return "ok", text
    recorded = state.get(short(target))
    if recorded is None:
        return "first", text
    return ("outdated" if recorded == digest(text) else "drift"), text


def backup_root():
    return os.path.join(DATA, "backup")


def run_folder():
    """A new backup folder: own for every run, even in the same second and with the same pid."""
    root = backup_root()
    os.makedirs(root, exist_ok=True)
    prefix = f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    n = 1
    while True:
        folder = os.path.join(root, f"{prefix}-{n}")
        try:
            os.mkdir(folder)
            return folder
        except FileExistsError:
            n += 1


def backup(target, folder):
    """Saves the file byte for byte; an occupied path raises FileExistsError instead of replacing."""
    dest = os.path.join(folder, short(target).lstrip("~/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(target, "rb") as source, open(dest, "xb") as copy:
        shutil.copyfileobj(source, copy)
    return dest


def prune_backups(current):
    """Keeps the current run folder and the KEEP_BACKUPS - 1 newest other run folders (by the time in the name,
    then by modification time); an entry with another name is neither counted nor deleted."""
    root = os.path.dirname(current)
    runs = []
    for name in os.listdir(root):
        path = os.path.join(root, name)
        found = RUN_NAME.fullmatch(name)
        if found and path != current and os.path.isdir(path) and not os.path.islink(path):
            runs.append((found.group(1), os.stat(path).st_mtime_ns, name, path))
    pruned = 0
    for *_, path in sorted(runs, reverse=True)[KEEP_BACKUPS - 1:]:
        try:
            shutil.rmtree(path)
            pruned += 1
        except OSError as e:
            print(f"no access  {short(path)}: {e.strerror}")
    if pruned:
        print(f"pruned backups: {pruned}")


def status(quiet=False):
    state = load_state()
    rows = []
    for name, source, target, block in laid(chosen(state), global_rules(state)):
        kind, _ = classify(read(source), target, state, block)
        rows.append((kind, name, target))
        if not quiet or kind != "ok":
            print(f"{kind:11} {name:38} {short(target)}")
    return rows


def retire(state, laid):
    """Removes a retired copy equal to its last layout and its state entry; an edited one is kept and named.
    A path the current targets still lay out (laid) is not retired. The launchd job of the old version is only
    named: system jobs are the user's to unload."""
    for key in RETIRED:
        target = expand(key)
        if key in laid:
            continue
        if not os.path.lexists(target):
            state.pop(key, None)
            continue
        try:
            same = state.get(key) == digest(read(target))
            if same:
                os.remove(target)
        except (OSError, UnicodeDecodeError) as e:
            print(f"kept       {key} — no longer laid out, not readable: {getattr(e, 'strerror', None) or 'not UTF-8'}")
            continue
        if same:
            state.pop(key, None)
            print(f"removed    {key} — no longer laid out")
            if os.path.dirname(target).startswith(DATA + os.sep):  # templates/openspec/: an emptied folder goes too
                try:
                    os.rmdir(os.path.dirname(target))
                except OSError:
                    pass
        elif key in state:
            print(f"kept       {key} — drift: differs from its last layout, no longer laid out; delete it yourself")
        else:
            print(f"kept       {key} — not laid out by solo-sdd, no longer used; delete it yourself")
    if os.path.lexists(expand(OLD_JOB)):
        print(f"old job    {OLD_JOB} — runs the removed openspec-after-update.py; unload and delete it yourself")


def push(force=False, quiet=False, agents=None, rules=False, replace_foreign=False):
    """Lays out the copies of agents (None: the choice in the state); copies of agents dropped from the choice go.
    rules turns the global rules block on; without it the block follows the choice in the state. A whole file
    solo-sdd did not lay out (first) is kept unless replace_foreign."""
    state = load_state()
    initial = copy.deepcopy(state)
    agents = agents or chosen(state)
    rules = rules or global_rules(state)
    current, refused, held = integration_pairs(agents)
    current = pairs(agents, rules) + current
    every = pairs(providers.ALL, True) + integration_pairs(providers.ALL)[0]
    keep = set(current)
    dropped = [p for p in every if p not in keep]
    gone, problems, kept, _ = remove_copies(dropped, state)
    for key in {short(t) for _, _, t, _ in dropped} - kept:
        state.pop(key, None)
        state.get("_blocks", {}).pop(key, None)
        state.get(SKILLS, {}).pop(key, None)
    if gone:
        print(f"removed    {gone} copies of agents no longer chosen")
    for line in refused:
        print(line)
    problems += len(refused)
    for key in {short(t) for n, _, t, _ in every if not n.startswith("integration:")} & set(state.get(SKILLS, {})):
        del state[SKILLS][key]  # the map lays the path out now: the copy is solo-sdd's
    lost = orphans(state, every, held)
    _, code, kept, _ = remove_copies(lost, state, gone=True)
    problems += code
    for key in {short(t) for _, _, t, _ in lost} - kept:
        state.pop(key, None)
        del state[SKILLS][key]
    folder = None
    for name, source, target, block in current:
        source_text = read(source)
        kind, text = classify(source_text, target, state, block)
        key = short(target)
        want = digest(rules_block.norm(source_text) if block else source_text)
        if kind == "ok":
            state[key] = want
            record(state, name, key)
            continue
        if block and kind == "drift" and text is None:
            print(f"skipped    {name:38} {key} — broken solo-sdd markers")
            problems += 1
            continue
        if kind == "drift" and not force:
            hint = ("move the edit into its integration folder" if name.startswith("integration:")
                    else f"{PULL_HINT} {name}")
            print(f"skipped    {name:38} {key} — edited in place: {hint}")
            problems += 1
            continue
        if kind == "unreachable":
            print(f"no access  {name:38} {key}")
            problems += 1
            continue
        if kind == "first" and not block and not replace_foreign:
            print(f"foreign {key}: kept ({FOREIGN_HINT})")
            problems += 1
            continue
        try:
            note = ""
            sep = None
            exists = kind != "missing" if block else text is not None
            if block:
                body = rules_block.norm(source_text)
                if kind == "missing":
                    new = rules_block.block(body)
                else:
                    raw = read_raw(target)
                    if rules_block.parse(raw) is not None:
                        new = rules_block.replace(raw, body)
                        sep = state.get("_blocks", {}).get(key)  # the separator stays from the first write of the block
                    elif state.get(key) == digest(raw):
                        new = rules_block.block(body)
                        exists = raw != body
                    else:
                        new, sep = rules_block.append(raw, body)
            else:
                new = source_text
            if exists:
                folder = folder or run_folder()
                note = f" (saved: {short(backup(target, folder))})"
            (write_raw if block else write)(target, new)
        except FileExistsError:
            print(f"no access  {name:38} {key}: backup already exists")
            problems += 1
            continue
        except OSError as e:
            print(f"no access  {name:38} {key}: {e.strerror}")
            problems += 1
            continue
        state[key] = want
        record(state, name, key)
        if block:
            state.setdefault("_blocks", {})[key] = sep
        print(f"{'created' if kind == 'missing' else 'updated':10} {name:38} {key}{note}")
    if not state.get(SKILLS, True):
        del state[SKILLS]
    retire(state, {short(target) for _, _, target, _ in pairs(agents, rules)})
    state["_agents"] = agents
    state["_global_rules"] = rules
    state["_source"] = REPO
    state["_version"] = __version__
    if state != initial or not os.path.exists(STATE):
        save_state(state)
    if folder:
        prune_backups(folder)
    if not quiet and problems == 0:
        print("all laid out")
    return problems


def remove_copies(items, state, gone=False):
    """Removes the copies of items that match their last deployment; (removed, code, kept keys, any recorded).
    gone: the source of the items is gone, so each removed path is named and a kept one is named as drift."""
    roots = {expand(p["skills"]) for p in providers.PROVIDERS.values() if p["skills"]}
    removed = code = 0
    recorded_any = False
    kept = set()  # kept copies: their entries stay so a repeated install sees drift, not first
    for name, source, target, block in items:
        key = short(target)
        recorded = state.get(key)
        if recorded is None:
            continue
        recorded_any = True
        if not os.path.exists(target):
            continue
        try:
            raw = read_raw(target)
            keep = None
            drop = False
            if not block:
                if digest(read(target)) == recorded:
                    drop = True
                else:
                    keep = "edited in place"
            else:
                parts = rules_block.parse(raw)
                if parts is rules_block.BROKEN:
                    keep = "broken solo-sdd markers"
                elif parts is None:
                    if digest(raw) == recorded:
                        drop = True
                    else:
                        keep = "edited in place"
                elif digest(parts[1]) == recorded:
                    sep = state.get("_blocks", {}).get(key)
                    rest = rules_block.remove(raw, sep)
                    if sep is None and rest == "":
                        drop = True
                    else:
                        write_raw(target, rest)
                        removed += 1
                else:
                    keep = "edited in place"
            if drop:
                os.remove(target)
                removed += 1
                if gone:
                    print(f"removed    {name:38} {key} — its integration skill is gone")
                parent = os.path.dirname(target)  # empty skill folders, including nested ones (ui-check/antislop/references)
                while parent not in roots and any(parent.startswith(r + os.sep) for r in roots):
                    try:
                        os.rmdir(parent)
                    except OSError:
                        break
                    parent = os.path.dirname(parent)
        except (OSError, UnicodeDecodeError) as e:
            print(f"no access  {name:38} {key}: {getattr(e, 'strerror', None) or 'not UTF-8'}")
            code = 1
            kept.add(key)
            continue
        if keep:
            kept.add(key)
            print(f"kept       {name:38} {key} — "
                  + (f"drift: {keep}, its integration skill is gone; delete it yourself" if gone else keep))
    return removed, code, kept, recorded_any


def uninstall(purge=False):
    """Removes copies that match the last deployment, of every agent; edited ones are kept. Hooks are removed by cli.uninstall."""
    state = load_state()
    items = laid(providers.ALL, True)
    removed, code, kept, recorded_any = remove_copies(items + orphans(state, items), state)
    blocks = state.get("_blocks", {})
    for key in [k for k in state if not k.startswith("_") and k not in kept]:
        del state[key]
        blocks.pop(key, None)
    for key in [k for k in blocks if k not in kept]:
        del blocks[key]
    skills = state.get(SKILLS, {})
    for key in [k for k in skills if k not in kept]:
        del skills[key]
    for key in ("_source", "_version", "_agents", "_global_rules") + (() if blocks else ("_blocks",)) + (() if skills else (SKILLS,)):
        state.pop(key, None)
    if kept & opt_in_keys():
        state["_global_rules"] = False  # a kept edited block is not an earlier deployment to lay out again
    save_state(state)
    if purge and "_hooks" in state:
        print("fail purge: hooks not removed, schema and data kept")
        code = 1
    elif purge:
        code = purge_data(items) or code
        folder = os.path.join(HOME, ".local", "share", "openspec", "schemas", "solo")
        try:
            shutil.rmtree(folder)
        except FileNotFoundError:
            pass
        except OSError as e:
            print(f"no access {folder}: {e.strerror}")
            code = 1
    print(f"copies removed: {removed}" if recorded_any or "_hooks" in state else "nothing to remove")
    return code


def purge_data(items):
    """Deletes in DATA only the top-level entries solo-sdd writes there: those holding a copy of items, the state, the
    backups and the checks cache. A link or any other entry is the owner's: kept and named. DATA goes once empty."""
    own = [t for _, _, t, _ in items] + [STATE, backup_root(), os.path.join(HOME, integration_run.CHECKS_DIR)]
    names = {os.path.relpath(p, DATA).split(os.sep)[0] for p in own if p.startswith(DATA + os.sep)}
    try:
        entries = sorted(os.listdir(DATA))
    except FileNotFoundError:
        return 0
    except OSError as e:
        print(f"no access  {short(DATA)}: {e.strerror}")
        return 1
    code, kept = 0, False
    for name in entries:
        path = os.path.join(DATA, name)
        if name not in names or os.path.islink(path):
            print(f"kept       {short(path)} — not written by solo-sdd; delete it yourself if it is not needed")
            kept = True
            continue
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError as e:
            print(f"no access  {short(path)}: {e.strerror}")
            code = 1
    if kept or code:
        return code  # not empty: every entry left was named above
    try:
        os.rmdir(DATA)
    except OSError as e:
        print(f"no access  {short(DATA)}: {e.strerror}")
        return 1
    return 0


def uninstall_rules():
    """Removes only the global rules block by the managed block rules (an edited one is kept) and turns the choice off."""
    state = load_state()
    items = [p for p in pairs(providers.ALL, True) if short(p[2]) in opt_in_keys()]
    removed, code, kept, _ = remove_copies(items, state)
    for key in {short(t) for _, _, t, _ in items} - kept:
        state.pop(key, None)
        state.get("_blocks", {}).pop(key, None)
    if not state.get("_blocks", True):
        del state["_blocks"]
    state["_global_rules"] = False
    save_state(state)
    print(f"global rules removed: {removed}")
    return code


def pull(name, origin=None):
    """Pulls into the repository a copy edited in place (drift or first). If several copies
    were edited differently, say where to take it from: --from ~/.codex/skills or --from ~/AGENTS.md."""
    state = load_state()
    found = {}
    source = None
    blocks = set()
    broken = False
    for item, src, target, block in pairs(providers.ALL, True):  # also a copy kept after its agent left the choice
        if item != name:
            continue
        source = src
        if origin is not None:
            place = HOME if origin.rstrip("/") == "~" else expand(origin.rstrip("/"))
            if target != place and not target.startswith(place + os.sep):
                continue
        kind, text = classify(read(src), target, state, block)
        # outdated: the copy was not touched and the repository is newer; pulling it would roll the repository back.
        if block and kind == "drift" and text is None:
            print(f"skipped    {item:38} {short(target)} — broken solo-sdd markers")
            broken = True
        if kind in ("drift", "first") and text is not None:
            found.setdefault(text, []).append(target)
            if block:
                blocks.add(src)
    if source is None:
        print(f"no such name: {name}")
        return 1
    if not found:
        if broken:
            return 1
        print(f"{name}: no copy differs from the repository")
        return 0
    if len(found) > 1:
        print(f"{name}: copies differ from each other, name the source with --from:")
        for text, targets in found.items():
            print("  " + ", ".join(short(t) for t in targets))
        return 1
    text, targets = next(iter(found.items()))
    if source in blocks:
        text = rules_block.norm(text)
        write_raw(source, text)
    else:
        write(source, text)
    for target in targets:
        state[short(target)] = digest(text)
    save_state(state)
    print(f"{name}: taken from {short(targets[0])} into {os.path.relpath(source, REPO)}; "
          f"check the diff, commit and run push to lay it out to the other places")
    return 0


def main(argv):
    try:
        return _main(argv)
    except BrokenState as e:
        print(f"fail state: {e}")
        return 1
    except BadTargets as e:
        print(f"fail {e}")
        return 1


def _main(argv):
    if not argv or argv[0] not in ("status", "push", "pull"):
        print(__doc__)
        return 2
    command, rest = argv[0], argv[1:]
    if command == "status":
        status(quiet="--quiet" in rest)
        return 0
    if command == "push":
        return 1 if push(force="--force" in rest, quiet="--quiet" in rest, rules="--global-rules" in rest,
                         replace_foreign="--replace-foreign" in rest) else 0
    names = [a for a in rest if not a.startswith("--")]
    origin = None
    if "--from" in rest:
        position = rest.index("--from") + 1
        if position >= len(rest):
            print("--from needs a folder or file: --from ~/.codex/skills")
            return 2
        origin = rest[position]
    if origin in names:
        names.remove(origin)
    if len(names) != 1:
        print("name one item: python3 sync.py pull <skill or path from targets.json>")
        return 2
    return pull(names[0], origin)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
