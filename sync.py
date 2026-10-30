#!/usr/bin/env python3
"""Раскладывает скиллы, глобальные правила и скрипт схемы solo из этого репозитория по местам,
где их читают Claude Code и Codex (карта — targets.json).

    python3 sync.py status          что разошлось и что будет сделано
    python3 sync.py push            разложить; правки, сделанные на месте, не затираются
    python3 sync.py push --force    разложить и поверх правок на месте (с резервной копией)
    python3 sync.py pull <имя>      забрать правку, сделанную на месте, в репозиторий

Состояние каждой копии:
    ok           совпадает с репозиторием
    missing      копии нет — push создаст
    outdated     копия та, что разложена в прошлый раз, а репозиторий новее — push обновит
    first        копия есть, но sync её ещё не раскладывал — push заменит, сохранив резервную копию
    drift        копию правили на месте после прошлой раскладки — push пропустит, нужен pull или --force
    unreachable  нет доступа на чтение или запись (папка закрыта для этого процесса) или файл не в UTF-8

Хеши разложенного хранятся в ~/.local/share/solo-sdd/state.json по путям от ~ (так состояние одно
и для этого компьютера, и для сессии, где домашняя папка подключена по другому пути);
резервные копии — рядом в backup/.
"""
import hashlib, json, os, shutil, sys, time

REPO = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
DATA = os.path.join(HOME, ".local", "share", "solo-sdd")
STATE = os.path.join(DATA, "state.json")


def expand(path):
    return os.path.join(HOME, path[2:]) if path.startswith("~/") else path


def short(path):
    return "~" + path[len(HOME):] if path.startswith(HOME + os.sep) else path


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_state():
    try:
        return json.loads(read(STATE))
    except (OSError, ValueError):
        return {}


def save_state(state):
    write(STATE, json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def pairs():
    """(имя, файл в репозитории, абсолютный путь копии) для каждой копии из targets.json."""
    targets = json.loads(read(os.path.join(REPO, "targets.json")))
    roots = {key: expand(value) for key, value in targets["roots"].items()}
    for name, where in targets["skills"].items():
        source = os.path.join(REPO, "skills", name, "SKILL.md")
        for root in where:
            yield name, source, os.path.join(roots[root], name, "SKILL.md")
    for rel, copies in targets["files"].items():
        for copy in copies:
            yield rel, os.path.join(REPO, rel), expand(copy)


def classify(source_text, target, state):
    """Состояние одной копии: см. описание модуля."""
    try:
        if not os.path.exists(target):
            # Закрытая папка выглядит как пустая: проверяем ближайшую существующую папку выше.
            parent = os.path.dirname(target)
            while not os.path.exists(parent):
                parent = os.path.dirname(parent)
            if not os.access(parent, os.R_OK | os.X_OK):
                return "unreachable", None
            return "missing", None
        text = read(target)
    except (OSError, UnicodeDecodeError):
        return "unreachable", None
    if text == source_text:
        return "ok", text
    recorded = state.get(short(target))
    if recorded is None:
        return "first", text
    return ("outdated" if recorded == digest(text) else "drift"), text


def run_folder():
    """Новая папка резервных копий: своя у каждого запуска, даже в ту же секунду и при том же pid."""
    root = os.path.join(DATA, "backup")
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
    """Сохраняет файл байт в байт; занятый путь — FileExistsError, а не замена."""
    dest = os.path.join(folder, short(target).lstrip("~/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(target, "rb") as source, open(dest, "xb") as copy:
        shutil.copyfileobj(source, copy)
    return dest


def status(quiet=False):
    state = load_state()
    rows = []
    for name, source, target in pairs():
        kind, _ = classify(read(source), target, state)
        rows.append((kind, name, target))
        if not quiet or kind != "ok":
            print(f"{kind:11} {name:38} {short(target)}")
    return rows


def push(force=False, quiet=False):
    state = load_state()
    folder = None
    problems = 0
    for name, source, target in pairs():
        source_text = read(source)
        kind, text = classify(source_text, target, state)
        if kind == "ok":
            state[short(target)] = digest(source_text)
            continue
        if kind == "drift" and not force:
            print(f"пропущено  {name:38} {short(target)} — правили на месте: python3 sync.py pull {name}")
            problems += 1
            continue
        if kind == "unreachable":
            print(f"нет доступа {name:37} {short(target)}")
            problems += 1
            continue
        try:
            note = ""
            if text is not None:
                folder = folder or run_folder()
                note = f" (было сохранено: {short(backup(target, folder))})"
            write(target, source_text)
        except FileExistsError:
            print(f"нет доступа {name:37} {short(target)}: резервная копия уже есть")
            problems += 1
            continue
        except OSError as e:
            print(f"нет доступа {name:37} {short(target)}: {e.strerror}")
            problems += 1
            continue
        state[short(target)] = digest(source_text)
        print(f"{'создано' if kind == 'missing' else 'обновлено':10} {name:38} {short(target)}{note}")
    save_state(state)
    if not quiet and problems == 0:
        print("всё разложено")
    return problems


def pull(name, origin=None):
    """Забирает в репозиторий копию, изменённую на месте (drift или first). Если правили несколько
    копий по-разному, нужно указать, откуда брать: --from ~/.codex/skills или --from ~/AGENTS.md."""
    state = load_state()
    found = {}
    source = None
    for item, src, target in pairs():
        if item != name:
            continue
        source = src
        if origin is not None:
            place = HOME if origin.rstrip("/") == "~" else expand(origin.rstrip("/"))
            if target != place and not target.startswith(place + os.sep):
                continue
        kind, text = classify(read(src), target, state)
        # outdated — копию не трогали, новее репозиторий: забирать её значит откатить репозиторий.
        if kind in ("drift", "first") and text is not None:
            found.setdefault(text, []).append(target)
    if source is None:
        print(f"нет такого: {name}")
        return 1
    if not found:
        print(f"{name}: копий, отличных от репозитория, нет")
        return 0
    if len(found) > 1:
        print(f"{name}: копии отличаются друг от друга, укажи источник через --from:")
        for text, targets in found.items():
            print("  " + ", ".join(short(t) for t in targets))
        return 1
    text, targets = next(iter(found.items()))
    write(source, text)
    for target in targets:
        state[short(target)] = digest(text)
    save_state(state)
    print(f"{name}: взято из {short(targets[0])} в {os.path.relpath(source, REPO)}; "
          f"проверь diff, закоммить и выполни push, чтобы разложить по остальным местам")
    return 0


def main(argv):
    if not argv or argv[0] not in ("status", "push", "pull"):
        print(__doc__)
        return 2
    command, rest = argv[0], argv[1:]
    if command == "status":
        status(quiet="--quiet" in rest)
        return 0
    if command == "push":
        return 1 if push(force="--force" in rest, quiet="--quiet" in rest) else 0
    names = [a for a in rest if not a.startswith("--")]
    origin = None
    if "--from" in rest:
        position = rest.index("--from") + 1
        if position >= len(rest):
            print("после --from укажи папку или файл: --from ~/.codex/skills")
            return 2
        origin = rest[position]
    if origin in names:
        names.remove(origin)
    if len(names) != 1:
        print("укажи одно имя: python3 sync.py pull <скилл или путь из targets.json>")
        return 2
    return pull(names[0], origin)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
