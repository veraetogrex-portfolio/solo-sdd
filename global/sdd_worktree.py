#!/usr/bin/env python3
"""Рабочая копия change: игнорируемые git артефакты между основной папкой и worktree.

Запуск: sdd_worktree.py <setup|refresh|transport|undo|remove|discard> <MAIN> <WORKTREE>

Набор артефактов: всё под openspec/, файлы AGENTS.md и CLAUDE.md в корне и пути из
раздела AGENTS.md «Рабочая копия» (необязателен), которые git в MAIN игнорирует.
Формат раздела (до следующего заголовка «## »), значения в обратных кавычках:

    ## Рабочая копия

    - Пути: `docs/architecture.md`, `docs/waiting.md`
    - Подготовка: `npm ci --prefer-offline`

Пути относительные к корню, файлы или папки. Подготовка выполняется через sh -c в WORKTREE.

Кроме того, setup берёт в набор отдельно игнорируемые документы MAIN (не целой игнорируемой
папкой): .md, .txt, .rst, .adoc до 1 МиБ, без ссылок, node_modules, .venv и .env*. Их список
лежит в снимке (<WORKTREE>.base/.sdd-ignored); дальше они обрабатываются как весь набор.

setup      копирует нужное в WORKTREE, снимок кладёт в <WORKTREE>.base/, ставит ссылки
           на node_modules и .venv, дописывает их в info/exclude, запускает подготовку.
refresh    переносит в WORKTREE правки MAIN после setup (трёхстороннее слияние: база = снимок);
           при конфликте файл в WORKTREE получает маркеры, код 3; снимок обновляется до MAIN.
transport  переносит правки артефактов в MAIN (трёхстороннее слияние: база = снимок);
           при конфликте MAIN не меняется (код 3). Прежнее состояние лежит в <WORKTREE>.undo/.
           Отдельно игнорируемые файлы вне набора, разные в MAIN и WORKTREE, называет строкой
           «не перенесены: ...», код выхода от этого не меняется.
undo       возвращает MAIN к состоянию до последнего переноса.
remove     убирает ссылки, снимок, .undo, запись .start и сам worktree.
discard    убирает worktree без своих коммитов (HEAD равен записи <WORKTREE>.start, сделанной setup,
           коммит есть не только в удаляемой ветке) вместе с его веткой; иначе код 1, ничего не меняется.
"""
import filecmp
import os
import shutil
import subprocess
import sys

ROOTS = ["openspec", "AGENTS.md", "CLAUDE.md"]
LINKED = ["node_modules", ".venv"]
MARK = ".sdd-worktree"
LISTED = ".sdd-ignored"  # в снимке: отдельно игнорируемые документы набора, разделитель \0
DOCS = (".md", ".txt", ".rst", ".adoc")
DOC_LIMIT = 1024 * 1024


def git(repo, *args, data=None):
    return subprocess.run(["git", "-C", repo] + list(args), input=data, capture_output=True)


def read(p):
    with open(p, "rb") as f:
        return f.read()


def write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


def section(main):
    """Пути и команда подготовки из раздела «Рабочая копия»."""
    paths, cmd, inside = [], None, False
    try:
        lines = read(os.path.join(main, "AGENTS.md")).decode("utf-8").splitlines()
    except OSError:
        return paths, cmd
    for ln in lines:
        if ln.startswith("## "):
            inside = ln.strip() == "## Рабочая копия"
            continue
        if not inside:
            continue
        s = ln.strip().lstrip("-* ").strip()
        parts = s.split("`")
        vals = parts[1::2]
        if s.startswith("Пути:"):
            paths += [v.strip("/") for v in vals if v and not os.path.isabs(v) and ".." not in v.split("/")]
        elif s.startswith("Подготовка:") and vals:
            cmd = vals[0]
    return paths, cmd


def listed(wt):
    try:
        return read(os.path.join(wt + ".base", LISTED)).decode("utf-8").split("\0")
    except OSError:
        return []


def roots(main, wt):
    return ROOTS + section(main)[0] + listed(wt)


def regular(p):
    return os.path.isfile(p) and not os.path.islink(p)


def loose_ignored(main):
    """Файлы, которые git игнорирует по отдельности: записи с --directory без / на конце."""
    r = git(main, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory")
    if r.returncode:
        raise RuntimeError("git ls-files: " + r.stderr.decode("utf-8", "replace").strip())
    names = [x.decode("utf-8", "replace") for x in r.stdout.split(b"\0") if x and not x.endswith(b"/")]
    # git не сворачивает игнорируемую папку с отслеживаемым файлом: её файлы приходят поштучно;
    # --no-index, иначе check-ignore считает такую папку отслеживаемой
    hidden = set(ignored(main, sorted({os.path.dirname(f) for f in names} - {""}), "--no-index"))
    return sorted(f for f in names if regular(os.path.join(main, f)) and os.path.dirname(f) not in hidden
                  and not set(f.split("/")) & set(LINKED))


def is_document(main, f):
    return (f.lower().endswith(DOCS) and not os.path.basename(f).startswith(".env")
            and os.path.getsize(os.path.join(main, f)) <= DOC_LIMIT)


def not_carried(main, wt):
    """Отдельно игнорируемые файлы вне набора, которые есть с двух сторон и отличаются."""
    known = set(files_under(main, roots(main, wt)))
    out = []
    for f in loose_ignored(main):
        w = os.path.join(wt, f)
        if f not in known and regular(w) and not filecmp.cmp(os.path.join(main, f), w, shallow=False):
            out.append(f)
    return out


def files_under(base, rels):
    """Относительные пути файлов (не ссылок) под корнями артефактов."""
    out = []
    for r in rels:
        p = os.path.join(base, r)
        if os.path.islink(p):
            continue
        if os.path.isfile(p):
            out.append(r)
        elif os.path.isdir(p):
            for d, _, fs in os.walk(p):
                for f in fs:
                    fp = os.path.join(d, f)
                    if not os.path.islink(fp):
                        out.append(os.path.relpath(fp, base))
    return sorted(set(out))


def ignored(repo, rels, *opts):
    """Какие из путей игнорирует git (отслеживаемые не считаются, если не передан --no-index)."""
    if not rels:
        return []
    r = git(repo, "check-ignore", *opts, "-z", "--stdin", data="\0".join(rels).encode("utf-8"))
    if r.returncode not in (0, 1):
        raise RuntimeError("git check-ignore: " + r.stderr.decode("utf-8", "replace").strip())
    return [x.decode("utf-8") for x in r.stdout.split(b"\0") if x]


def prune_empty(path, stop):
    path = os.path.dirname(path)
    stop = os.path.abspath(stop)
    while os.path.abspath(path) != stop and path.startswith(stop):
        try:
            os.rmdir(path)
        except OSError:
            return
        path = os.path.dirname(path)


def find_links(main):
    """node_modules не глубже трёх уровней (не заходя в них и в .git) и .venv в корне."""
    found = []
    for d, dirs, _ in os.walk(main):
        rel = os.path.relpath(d, main)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if ".git" in dirs:
            dirs.remove(".git")
        if "node_modules" in dirs:
            dirs.remove("node_modules")
            found.append(os.path.normpath(os.path.join(rel, "node_modules")))
        if depth >= 2:
            dirs[:] = []
    if os.path.isdir(os.path.join(main, ".venv")):
        found.append(".venv")
    return found


def link_modules(src, dst, level=0):
    """Настоящая node_modules в WORKTREE: ссылки на записи MAIN, ссылки-пакеты копируются с той же целью."""
    os.makedirs(dst)
    for name in sorted(os.listdir(src)):
        s, d = os.path.join(src, name), os.path.join(dst, name)
        if os.path.islink(s):
            os.symlink(os.readlink(s), d)
        elif os.path.isdir(s) and level == 0 and (name.startswith("@") or name == ".bin"):
            link_modules(s, d, 1)
        elif os.path.isdir(s) and name.startswith("."):
            continue
        else:
            os.symlink(os.path.abspath(s), d)
    if level == 0:
        write(os.path.join(dst, MARK), b"")


def add_exclude(main):
    r = git(main, "rev-parse", "--git-common-dir")
    if r.returncode:
        raise RuntimeError("git rev-parse: " + r.stderr.decode("utf-8", "replace").strip())
    p = os.path.join(main, r.stdout.decode().strip(), "info", "exclude")
    have = read(p).decode("utf-8").splitlines() if os.path.exists(p) else []
    add = [x for x in LINKED if x not in have]
    if add:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            if have and not read(p).endswith(b"\n"):
                f.write("\n")
            f.write("\n".join(add) + "\n")


def setup(main, wt):
    head = git(wt, "rev-parse", "HEAD")  # запись начала до всего остального: нужна и при неудачной подготовке
    if head.returncode:
        raise RuntimeError("git rev-parse: " + head.stderr.decode("utf-8", "replace").strip())
    write(wt + ".start", head.stdout)
    base = wt + ".base"
    paths, cmd = section(main)
    known = files_under(main, ROOTS + paths)
    extra = [f for f in loose_ignored(main) if f not in known and is_document(main, f)]
    cand = [f for f in known + extra if not os.path.exists(os.path.join(wt, f))]
    copied = ignored(main, cand)
    os.makedirs(base, exist_ok=True)  # refresh требует снимок и тогда, когда копировать нечего
    for f in copied:
        data = read(os.path.join(main, f))
        write(os.path.join(wt, f), data)
        write(os.path.join(base, f), data)
    extra = [f for f in extra if os.path.isfile(os.path.join(base, f))]
    if extra:
        write(os.path.join(base, LISTED), "\0".join(extra).encode("utf-8"))
    links = 0
    for rel in find_links(main):
        dst = os.path.join(wt, rel)
        if os.path.lexists(dst) or not os.path.isdir(os.path.dirname(dst)):
            continue
        if os.path.basename(rel) == "node_modules":
            link_modules(os.path.join(main, rel), dst)
        else:
            os.symlink(os.path.abspath(os.path.join(main, rel)), dst)
        links += 1
    add_exclude(main)
    if cmd:
        r = subprocess.run(["sh", "-c", cmd], cwd=wt, stdin=subprocess.DEVNULL)
        if r.returncode:
            raise RuntimeError("команда подготовки завершилась с кодом %d: %s" % (r.returncode, cmd))
    print("скопировано файлов %d, папок ссылок %d, команда: %s" % (len(copied), links, cmd or "нет"))
    return 0


def merge3(mine, base, theirs):
    """Слияние git merge-file; None при конфликте."""
    r = subprocess.run(["git", "merge-file", "-p", mine, base, theirs], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def plan(main, wt):
    """Что сделать с MAIN: (создать/записать {rel: bytes}, удалить [rel], конфликты [rel])."""
    base = wt + ".base"
    rels = roots(main, wt)
    in_base = set(files_under(base, rels)) if os.path.isdir(base) else set()
    in_wt = set(ignored(wt, files_under(wt, rels))) | (in_base & set(files_under(wt, rels)))
    put, drop, bad = {}, [], []
    for f in sorted(in_base | in_wt):
        m, b, w = (os.path.join(x, f) for x in (main, base, wt))
        wd = read(w) if f in in_wt else None
        bd = read(b) if f in in_base else None
        md = read(m) if os.path.isfile(m) else None
        if wd is not None and bd is None:
            if md is None:
                put[f] = wd
            elif md != wd:
                bad.append(f)
        elif wd is not None:
            if wd == bd:
                continue
            res = merge3(m, b, w) if md is not None else None
            if res is None:
                bad.append(f)
            elif res != md:
                put[f] = res
        elif md is not None:
            if md == bd:
                drop.append(f)
            else:
                bad.append(f)
    return put, drop, bad


def merge_marked(mine, base, theirs):
    """Слияние с маркерами конфликта: (результат, чисто ли)."""
    r = subprocess.run(["git", "merge-file", "-p", "-L", "WORKTREE", "-L", "base", "-L", "MAIN", mine, base, theirs],
                       capture_output=True)
    if r.returncode < 0 or r.returncode > 127:
        raise RuntimeError("git merge-file: " + r.stderr.decode("utf-8", "replace").strip())
    return r.stdout, r.returncode == 0


def refresh(main, wt):
    base = wt + ".base"
    if not os.path.isdir(base):
        raise RuntimeError("нет снимка %s: сначала setup" % base)
    rels = roots(main, wt)
    in_base = set(files_under(base, rels))
    names = sorted(set(ignored(main, files_under(main, rels))) | in_base)
    copied = merged = deleted = 0
    bad, keep = [], set()  # keep: конфликт без маркеров, снимок прежний — transport не перенесёт файл молча
    for f in names:
        m, b, w = (os.path.join(x, f) for x in (main, base, wt))
        md = read(m) if os.path.isfile(m) else None
        bd = read(b) if f in in_base else None
        wd = read(w) if os.path.isfile(w) else None
        if md is not None and bd is None:
            if wd is None:
                write(w, md)
                copied += 1
            elif wd != md:
                bad.append(f)
                keep.add(f)
        elif md is not None:
            if md != bd:
                if wd is None:
                    bad.append(f)
                    keep.add(f)
                else:
                    res, clean = merge_marked(w, b, m)
                    write(w, res)
                    if clean:
                        merged += 1
                    else:
                        bad.append(f)
        elif wd is not None:
            if wd == bd:
                os.unlink(w)
                prune_empty(w, wt)
                deleted += 1
            else:
                bad.append(f)
                keep.add(f)
        if f in keep:
            continue
        if md is None:
            if os.path.isfile(b):
                os.unlink(b)
                prune_empty(b, base)
        elif md != bd:
            write(b, md)
    if bad:
        print("конфликт, решить в WORKTREE: " + ", ".join(bad))
        return 3
    print("обновлено: скопировано %d, слито %d, удалено %d" % (copied, merged, deleted))
    return 0


def transport(main, wt):
    skipped = not_carried(main, wt)
    if skipped:
        print("не перенесены: " + ", ".join(skipped))
    put, drop, bad = plan(main, wt)
    if bad:
        print("конфликт, MAIN не изменён: " + ", ".join(bad))
        return 3
    if not (put or drop):
        print("перенесено: ничего не изменилось")
        return 0
    undo = wt + ".undo"
    shutil.rmtree(undo, ignore_errors=True)
    os.makedirs(undo)
    created = []
    for f in list(put) + drop:
        m = os.path.join(main, f)
        if os.path.isfile(m):
            write(os.path.join(undo, "files", f), read(m))
        else:
            created.append(f)
    with open(os.path.join(undo, ".created"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(created) + ("\n" if created else ""))
    merged = sum(1 for f in put if os.path.isfile(os.path.join(main, f)))
    for f, data in put.items():
        write(os.path.join(main, f), data)
    for f in drop:
        os.unlink(os.path.join(main, f))
        prune_empty(os.path.join(main, f), main)
    print("перенесено: скопировано %d, слито %d, удалено %d" % (len(put) - merged, merged, len(drop)))
    return 0


def undo(main, wt):
    u = wt + ".undo"
    if not os.path.isdir(u):
        print("нечего отменять")
        return 0
    cr = os.path.join(u, ".created")
    for f in (read(cr).decode("utf-8").splitlines() if os.path.exists(cr) else []):
        p = os.path.join(main, f)
        if os.path.isfile(p):
            os.unlink(p)
            prune_empty(p, main)
    saved = os.path.join(u, "files")
    for f in files_under(saved, ["."]) if os.path.isdir(saved) else []:
        write(os.path.join(main, f), read(os.path.join(saved, f)))
    shutil.rmtree(u)
    print("отменено")
    return 0


def unlink_links(wt):
    for rel in find_links(wt):
        p = os.path.join(wt, rel)
        if os.path.islink(p):
            os.unlink(p)
        elif os.path.isfile(os.path.join(p, MARK)):
            shutil.rmtree(p)  # ссылки внутри не разворачиваются, цели в MAIN целы


def rmdir_temp_parent(wt):
    parent = os.path.dirname(wt)
    if os.path.basename(parent).startswith("sdd-"):  # папка mktemp диспетчера: убрать, если опустела
        try:
            os.rmdir(parent)
        except OSError:
            pass


def remove(main, wt):
    # незакоммиченная работа: отказ до уборки, иначе worktree остался бы без снимка и ссылок
    dirty = git(wt, "status", "--porcelain")
    if dirty.returncode or dirty.stdout.strip():
        raise RuntimeError("git worktree remove: в worktree незакоммиченные изменения, ничего не удалено")
    unlink_links(wt)
    for x in (wt + ".base", wt + ".undo"):
        shutil.rmtree(x, ignore_errors=True)
    # без --force: игнорируемые копии и исключённые ссылки не мешают, а незакоммиченную работу git не даст стереть
    r = git(main, "worktree", "remove", wt)
    if r.returncode:
        raise RuntimeError("git worktree remove: " + r.stderr.decode("utf-8", "replace").strip())
    if os.path.exists(wt + ".start"):
        os.unlink(wt + ".start")
    rmdir_temp_parent(wt)
    print("worktree удалён")
    return 0


def discard(main, wt):
    try:
        start = read(wt + ".start").decode("utf-8").strip()
    except OSError:
        raise RuntimeError("нет записи начала %s.start: ничего не удалено" % wt)
    r = git(wt, "rev-parse", "HEAD")
    if r.returncode:
        raise RuntimeError("git rev-parse: %s: ничего не удалено" % r.stderr.decode("utf-8", "replace").strip())
    head = r.stdout.decode().strip()
    if head != start:
        raise RuntimeError("в worktree есть свои коммиты (HEAD %s, начало %s): ничего не удалено" % (head, start))
    branch = git(wt, "branch", "--show-current").stdout.decode().strip()
    refs = git(main, "for-each-ref", "--contains", head, "--format=%(refname)",
               "refs/heads", "refs/remotes", "refs/tags").stdout.decode().split()
    if not [x for x in refs if x != "refs/heads/" + branch]:
        raise RuntimeError("коммит %s есть только в %s: ничего не удалено" % (head, "ветке " + branch if branch else "этом worktree"))
    unlink_links(wt)
    for x in (wt + ".base", wt + ".undo"):
        shutil.rmtree(x, ignore_errors=True)
    r = git(main, "worktree", "remove", "--force", wt)
    if r.returncode:
        raise RuntimeError("git worktree remove: " + r.stderr.decode("utf-8", "replace").strip())
    if branch:
        r = git(main, "branch", "-D", branch)
        if r.returncode:
            raise RuntimeError("git branch -D: " + r.stderr.decode("utf-8", "replace").strip())
    os.unlink(wt + ".start")
    rmdir_temp_parent(wt)
    print("worktree отброшен: " + (branch or "без ветки"))
    return 0


COMMANDS = {"setup": setup, "refresh": refresh, "transport": transport, "undo": undo, "remove": remove, "discard": discard}


def main_cli(argv):
    if len(argv) != 4 or argv[1] not in COMMANDS:
        print("использование: sdd_worktree.py <setup|refresh|transport|undo|remove|discard> <MAIN> <WORKTREE>", file=sys.stderr)
        return 2
    main, wt = os.path.abspath(argv[2]), os.path.abspath(argv[3])
    try:
        return COMMANDS[argv[1]](main, wt)
    except (RuntimeError, OSError) as e:
        print("ошибка: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main_cli(sys.argv))
