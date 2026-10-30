#!/usr/bin/env python3
"""Очередь диспетчера: какие открытые change запускать сейчас.

Запуск: sdd_dispatch_plan.py <MAIN> [--running id1,id2,...] [--ignore-dep id:имя]... [--shared путь]...

Готов: нет CLAIM и WAITING, нет ветки change/<id>, все Depends On в архиве, папка change закоммичена
(иначе причина «не закоммичен»: worktree от коммита её не увидит).
Причины по порядку: ветка («не смёрджен»), CLAIM, WAITING, «не закоммичен», зависимости.
Зависимости: имя, которого нет ни среди открытых change, ни в архиве, — «неизвестная зависимость: <имя>»
(«(это спека, не change)», если есть openspec/specs/<имя>), затем через «; » — «зависит от <открытые>».
Значение none, нет, -, — (без учёта регистра, с .,:; после него) первым в пункте Depends On — зависимостей нет.
--ignore-dep id:имя не считает имя зависимостью этого change; --shared путь добавляет общий путь (как «Общие:»).
CLAIM брошен: session=<id>, а файлы сессии в ~/.claude/hook-state не менялись 60 минут или их нет;
метка без id — файлу 12 часов или больше. Скрипт метку не снимает: это решает владелец.
Артефакты вне git: если игнорируется openspec/, AGENTS.md или CLAUDE.md, печатается строка «Артефакты вне git: <пути>».
Жёсткий конфликт двух change: общее требование (capability, имя) или общий файл из Impact.
Общие пути конфликта не дают: COMMON и пункт «Общие:» раздела AGENTS.md «Рабочая копия»;
путь с / на конце делает общими все файлы под ним. Пары, запущенные при общем пути, — строки «вместе:».
Лимит: пункт «Оркестраторов: <число>» раздела AGENTS.md «Рабочая копия», иначе 2.
Порядок: по числу открытых change, зависящих от данного (прямо или цепочкой), затем по id.
"""
import os
import re
import subprocess
import sys
import time

COMMON = {"AGENTS.md", "CLAUDE.md", "docs/waiting.md", "CHANGELOG.md"}
LIMIT = 2
NO_DEPS = {"none", "нет", "-", "—"}
STATE = os.path.join(os.path.expanduser("~"), ".claude", "hook-state")
SESSION_SILENCE = 3600
LABEL_AGE = 12 * 3600


def text(p):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def sections(src, title):
    """Строки раздела «## title» до следующего «## »."""
    out, inside = [], False
    for ln in src.splitlines():
        if ln.startswith("## "):
            inside = ln.strip() == "## " + title
        elif inside:
            out.append(ln)
    return out


def is_none(v):
    """Значение «зависимостей нет»: none, нет, -, — (с .,:;) или пусто."""
    return v.rstrip(".,:;").lower() in NO_DEPS or v in ("", ".")


def parse_deps(lines):
    """Имена из «Depends On»: значения в обратных кавычках, иначе первое слово пункта; пояснения в скобках не мешают."""
    deps = []
    for ln in lines:
        s = ln.strip().lstrip("-* ")
        vals = s.split("`")[1::2] or [v.split()[0] for v in s.split(",") if v.split()]
        head = s.split("`")[0].replace(",", " ").split()
        if head and is_none(head[0]):
            continue
        for i, v in enumerate(vals):
            v = v.strip()
            if is_none(v):
                if i == 0:
                    break
            elif re.fullmatch(r"[\w.-]+", v):
                deps.append(v)
    return deps


def is_file(v, main):
    if " " in v or "*" in v or v.endswith("/") or not ("/" in v or re.search(r"\.[A-Za-z0-9]+$", v)):
        return False
    return not os.path.isdir(os.path.join(main, v))


def is_common(v, common):
    """Путь назван в common или лежит под каталогом оттуда (значение с / на конце)."""
    return v in common or any(p.endswith("/") and v.startswith(p) for p in common)


def spec_names(main):
    """Имена подпапок openspec/specs; нет папки — пусто."""
    d = os.path.join(main, "openspec", "specs")
    try:
        return {n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n))}
    except OSError:
        return set()


def apply_ignores(changes, pairs):
    """Копия changes без пар (id, имя) в deps; чужие change и несуществующие id не затрагиваются."""
    pairs = set(pairs)
    return {cid: dict(c, deps=[d for d in c["deps"] if (cid, d) not in pairs])
            for cid, c in changes.items()}


def agents_section(main):
    """Общие пути и лимит из раздела «Рабочая копия»."""
    common, limit = set(COMMON), LIMIT
    for ln in sections(text(os.path.join(main, "AGENTS.md")), "Рабочая копия"):
        s = ln.strip().lstrip("-* ").strip()
        if s.startswith("Общие:"):
            common |= {v.lstrip("/") for v in s.split("`")[1::2] if v}
        elif s.startswith("Оркестраторов:"):
            m = re.search(r"\d+", s)
            if m:
                limit = int(m.group())
    return common, limit


def has_branch(main, cid):
    r = subprocess.run(["git", "-C", main, "branch", "--list", "change/" + cid],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return bool(r.stdout.strip())


def uncommitted(main, cid):
    """В папке change есть неотслеживаемые или незакоммиченные файлы (игнорируемые status не показывает)."""
    r = subprocess.run(["git", "-C", main, "status", "--porcelain", "--untracked-files=all", "--",
                        "openspec/changes/" + cid],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return bool(r.stdout.strip())


def ignored_artifacts(main):
    """Игнорируемые git из openspec/, AGENTS.md, CLAUDE.md; вне репозитория или без совпадений — пусто."""
    r = subprocess.run(["git", "-C", main, "check-ignore", "--", "openspec/", "AGENTS.md", "CLAUDE.md"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.stdout.split() if r.returncode == 0 else []


def worktree_of(main, cid):
    """Путь worktree ветки change/<id> или пустая строка."""
    r = subprocess.run(["git", "-C", main, "worktree", "list", "--porcelain"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    path = ""
    for ln in r.stdout.splitlines():
        if ln.startswith("worktree "):
            path = ln[len("worktree "):]
        elif ln == "branch refs/heads/change/" + cid:
            return path
    return ""


def abandoned(claim):
    """Причина ожидания для брошенной метки или None. Не удалось прочитать — не брошена: важнее не спросить о живой."""
    now = time.time()
    try:
        born = os.path.getmtime(claim)
        with open(claim, encoding="utf-8", errors="replace") as f:
            m = re.search(r"session=([\w-]+)", f.read())
        if not m:
            return "CLAIM брошен: метка %d ч" % ((now - born) / 3600) if now - born >= LABEL_AGE else None
        marks = []
        for suffix in ("json", "claims"):
            try:
                marks.append(os.path.getmtime(os.path.join(STATE, "%s.%s" % (m.group(1), suffix))))
            except FileNotFoundError:
                pass
    except OSError:
        return None
    if marks and now - max(marks) < SESSION_SILENCE:
        return None
    return "CLAIM брошен: сессия %s молчит %d ч" % (m.group(1)[:8], (now - max(marks or [born])) / 3600)


def read_project(main, shared=()):
    """Диск -> (changes, archived, limit); changes: id -> {claim, waiting, branch, deps, reqs, files, shared}."""
    base = os.path.join(main, "openspec", "changes")
    if not os.path.isdir(base):
        raise OSError("нет папки " + base)
    common, limit = agents_section(main)
    common |= set(shared)
    archived = set()
    arch = os.path.join(base, "archive")
    if os.path.isdir(arch):
        archived = {re.sub(r"^\d{4}-\d{2}-\d{2}-", "", d) for d in os.listdir(arch)
                    if os.path.isdir(os.path.join(arch, d))}
    changes = {}
    for cid in sorted(os.listdir(base)):
        d = os.path.join(base, cid)
        prop = os.path.join(d, "proposal.md")
        if cid == "archive" or not os.path.isfile(prop):
            continue
        src = text(prop)
        reqs = set()
        sd = os.path.join(d, "specs")
        for cap in sorted(os.listdir(sd)) if os.path.isdir(sd) else []:
            for ln in text(os.path.join(sd, cap, "spec.md")).splitlines():
                m = re.search(r"###\s*Requirement:\s*(.+?)`?\s*$", ln)
                if m:
                    reqs.add((cap, m.group(1)))
        files, shared = set(), set()
        for ln in sections(src, "Impact"):
            for v in ln.split("`")[1::2]:
                if is_common(v, common):
                    shared.add(v)
                elif is_file(v, main):
                    files.add(v)
        changes[cid] = {
            "claim": os.path.exists(os.path.join(d, "CLAIM")),
            "abandoned": abandoned(os.path.join(d, "CLAIM")),
            "waiting": os.path.exists(os.path.join(d, "WAITING")),
            "branch": has_branch(main, cid),
            "worktree": worktree_of(main, cid),
            "uncommitted": uncommitted(main, cid),
            "deps": parse_deps(sections(src, "Depends On")),
            "reqs": reqs, "files": files, "shared": shared,
        }
    return changes, archived, limit


def dependents(changes):
    """id -> число открытых change, зависящих от него прямо или цепочкой (циклы безопасны)."""
    rev = {}
    for cid, c in changes.items():
        for d in c["deps"]:
            rev.setdefault(d, set()).add(cid)
    out = {}
    for cid in changes:
        seen, todo = set(), [cid]
        while todo:
            for n in rev.get(todo.pop(), ()):
                if n not in seen and n != cid:
                    seen.add(n)
                    todo.append(n)
        out[cid] = len(seen)
    return out


def conflict(a, b):
    """Причина жёсткого конфликта change a с b или None."""
    for cap, name in sorted(a["reqs"] & b["reqs"]):
        return "требование %s/%s" % (cap, name)
    for f in sorted(a["files"] & b["files"]):
        return "файл " + f
    return None


def plan(changes, archived, limit, running=(), specs=()):
    """Чистое планирование -> (выданные по порядку, [(id, причина)])."""
    run = [r for r in running if r in changes]
    cands = [c for c in changes if c not in running]
    waits, ready = [], []
    for cid in cands:
        c = changes[cid]
        miss = [d for d in c["deps"] if d not in archived]
        if c["branch"]:
            wt = c.get("worktree")
            waits.append((cid, "не смёрджен: ветка change/" + cid + (", worktree " + wt if wt else "")))
        elif c["claim"]:
            waits.append((cid, c.get("abandoned") or "CLAIM"))
        elif c["waiting"]:
            waits.append((cid, "WAITING"))
        elif c.get("uncommitted"):
            waits.append((cid, "не закоммичен"))
        elif miss:
            unknown = [d + (" (это спека, не change)" if d in specs else "") for d in miss if d not in changes]
            opened = [d for d in miss if d in changes]
            waits.append((cid, "; ".join(([("неизвестная зависимость: " + ", ".join(unknown))] if unknown else [])
                                         + (["зависит от " + ", ".join(opened)] if opened else []))))
        else:
            ready.append(cid)
    cnt = dependents(changes)
    ready.sort(key=lambda i: (-cnt[i], i))
    granted = []
    for cid in ready:
        why = None
        for o in run + granted:
            r = conflict(changes[cid], changes[o])
            if r:
                why = "конфликт с %s: %s" % (o, r)
                break
        if why is None and limit - len(run) - len(granted) <= 0:
            why = "лимит"
        if why:
            waits.append((cid, why))
        else:
            granted.append(cid)
    return granted, waits


def together(changes, granted, running):
    """Строки «вместе:»: пары выданного с выданным или работающим при общем пути."""
    out = []
    run = [r for r in running if r in changes]
    for i, a in enumerate(granted):
        for b in granted[i + 1:] + run:
            paths = sorted(changes[a]["shared"] & changes[b]["shared"])
            if paths:
                out.append("вместе: %s и %s — %s" % (a, b, ", ".join(paths)))
    return out


def render(granted, waits, limit, running, pairs=(), outside=()):
    out = ["лимит: %d, работают: %d" % (limit, len(running)),
           "запустить: " + (" ".join(granted) or "нет")] + list(pairs)
    if outside:
        out.append("Артефакты вне git: " + ", ".join(outside))
    if waits:
        out.append("ждут:")
        out += ["  %s — %s" % w for w in waits]
    return "\n".join(out)


def main(argv):
    args, running, ignores, shared = [], [], [], []
    it = iter(argv)
    for a in it:
        if a == "--running":
            running = [x for x in next(it, "").split(",") if x]
        elif a == "--ignore-dep":
            cid, _, name = next(it, "").partition(":")
            ignores.append((cid, name))
        elif a == "--shared":
            shared.append(next(it, "").lstrip("/"))
        else:
            args.append(a)
    if len(args) != 1 or not all(all(i) for i in ignores) or not all(shared):
        print("Запуск: sdd_dispatch_plan.py <MAIN> [--running id1,id2] [--ignore-dep id:имя]... [--shared путь]...",
              file=sys.stderr)
        return 2
    try:
        changes, archived, limit = read_project(os.path.abspath(args[0]), shared)
    except OSError as e:
        print("ошибка чтения: %s" % e, file=sys.stderr)
        return 1
    granted, waits = plan(apply_ignores(changes, ignores), archived, limit, running,
                          spec_names(os.path.abspath(args[0])))
    run = [r for r in running if r in changes]
    print(render(granted, waits, limit, run, together(changes, granted, run),
                 ignored_artifacts(os.path.abspath(args[0]))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
