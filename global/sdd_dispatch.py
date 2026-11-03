#!/usr/bin/env python3
"""sdd-dispatch.py: механика диспетчера: accept (приёмка статуса), land-local (merge в режиме local)."""
import os
import re
import subprocess
import sys

USAGE = """использование:
  sdd-dispatch.py accept <файл статуса>
  sdd-dispatch.py land-local <MAIN> <WORKTREE> <id> [--check <команда>]...
  коды accept: 0 сходится, 1 расхождения, 2 блок не разобран
  коды land-local: 0 смёрджен, 1 сбой шага, 2 основная не чистая, 3 проверка красная с change, 4 основная красная, 6 конфликт merge или переноса"""
VALIDATE_CMD = "openspec validate --all --strict --no-interactive"
HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd, cwd=None, shell=False):
    """Вывод stdout+stderr вместе, код выхода снимается у самой команды."""
    p = subprocess.run(cmd, shell=shell, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def git(main, *args):
    return subprocess.run(["git", "-C", main] + list(args), stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")


def tail(text, n):
    return text.rstrip("\n").splitlines()[-n:]


def field(text, name):
    m = re.search(r"^[ \t]*%s:[ \t]*(.*?)[ \t]*$" % name, text, re.M)
    return m.group(1) if m else ""


def accept(path):
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        print("блок не разобран: файл не читается: %s" % e)
        return 2
    if not text.strip():
        print("блок не разобран: файл пуст")
        return 2
    if not re.search(r"^[ \t]*STATUS:", text, re.M):
        print("блок не разобран: нет строки STATUS:")
        return 2
    status = field(text, "STATUS")
    if status != "archived":
        print("статус не archived: %s, команды не выполнены" % status)
        return 2
    wt, validate, live = (field(text, f) for f in ("WORKTREE", "VALIDATE", "LIVE"))
    for name, val in (("WORKTREE", wt), ("VALIDATE", validate), ("LIVE", live)):
        if not val:
            print("блок не разобран: поле %s пусто" % name)
            return 2
    live_cmd, sep, expect = live.partition(" -> ")
    if not sep or not expect.strip():
        print("блок не разобран: в LIVE нет ' -> ' или текст после него пуст")
        return 2
    if not os.path.isdir(wt):
        print("блок не разобран: папки WORKTREE нет: %s" % wt)
        return 2
    bad = 0
    code, out = run(validate.partition(" -> ")[0], wt, True)
    if code:
        bad = 1
        print("VALIDATE: %s — указан exit 0, получено exit %d" % (validate.partition(" -> ")[0], code))
        for l in tail(out, 3):
            print("    " + l)
    expect = expect.strip()
    code, out = run(live_cmd, wt, True)
    if code or expect not in out:
        bad = 1
        got = ["exit %d" % code] if code else []
        if expect not in out:
            got.append("текста нет")
        print("LIVE: %s — указано «%s», получено %s" % (live_cmd, expect, ", ".join(got)))
        for l in tail(out, 3):
            print("    " + l)
    if not bad:
        print("статус сходится")
    return bad


def worktree_script():
    for n in ("sdd-worktree.py", "sdd_worktree.py"):
        p = os.path.join(HERE, n)
        if os.path.exists(p):
            return p
    return os.path.join(HERE, "sdd-worktree.py")


def wt_run(sub, main, wt):
    code, out = run([sys.executable, worktree_script(), sub, main, wt])
    if out.strip():
        print(out.rstrip("\n"))
    return code, out


def rollback(main, wt, prev):
    """reset --keep к коммиту до merge, затем undo переноса. Возвращает текст ошибки или ''."""
    r = git(main, "reset", "--keep", prev)
    if r.returncode:
        return "reset: " + r.stderr.strip()
    code, out = run([sys.executable, worktree_script(), "undo", main, wt])
    if code:
        return "undo: " + out.strip()
    return ""


def land_local(main, wt, cid, checks):
    main, wt = os.path.abspath(main), os.path.abspath(wt)
    branch = "change/" + cid
    dirty = [l[3:] for l in git(main, "status", "--porcelain", "--untracked-files=no").stdout.splitlines()]
    if dirty:
        print("не смёрджен: основная папка не чистая: " + ", ".join(dirty))
        return 2
    prev = git(main, "rev-parse", "HEAD").stdout.strip()
    r = git(main, "merge", "-q", "--no-ff", "--no-edit", branch)
    if r.returncode:
        files = git(main, "diff", "--name-only", "--diff-filter=U").stdout.split()
        if files or not git(main, "rev-parse", "-q", "--verify", "MERGE_HEAD").returncode:
            git(main, "merge", "--abort")
        if files:
            print("не смёрджен: конфликт merge: " + ", ".join(files))
            return 6
        print("не смёрджен: merge: " + (r.stderr.strip() or r.stdout.strip()))
        return 1
    code, out = wt_run("transport", main, wt)
    if code:
        if code == 3:
            r = git(main, "reset", "--keep", prev)  # при конфликте transport MAIN не менял
            err = "reset: " + r.stderr.strip() if r.returncode else ""
        else:
            err = rollback(main, wt, prev)
        if err:
            print("не смёрджен: " + err)
            return 1
        if code == 3:
            m = re.search(r"конфликт, MAIN не изменён: (.*)", out)
            print("не смёрджен: конфликт переноса: " + (m.group(1).strip() if m else ""))
            return 6
        print("не смёрджен: transport: " + out.strip())
        return 1
    for cmd in checks + [VALIDATE_CMD]:
        code, out = run(cmd, main, True)
        if not code:
            continue
        err = rollback(main, wt, prev)
        if err:
            print("не смёрджен: " + err)
            return 1
        code2, out2 = run(cmd, main, True)
        if code2:
            print("основная красная: " + cmd)
            lines = tail(out2, 20)
            rc = 4
        else:
            print("не смёрджен: проверка красная с change: " + cmd)
            lines = tail(out, 20)
            rc = 3
        for l in lines:
            print("    " + l)
        return rc
    h = git(main, "rev-parse", "HEAD").stdout.strip()
    code, out = wt_run("remove", main, wt)
    if code:
        print("смёрджен %s, не убрано: remove: %s" % (h, out.strip()))
        return 1
    r = git(main, "branch", "-d", branch)
    if r.returncode:
        print("смёрджен %s, не убрано: branch -d: %s" % (h, r.stderr.strip()))
        return 1
    print("смёрджен " + h)
    return 0


def main(argv):
    if len(argv) == 2 and argv[0] == "accept":
        return accept(argv[1])
    if len(argv) >= 4 and argv[0] == "land-local":
        rest, checks, i = argv[4:], [], 0
        while i < len(rest):
            if rest[i] != "--check" or i + 1 >= len(rest):
                break
            checks.append(rest[i + 1])
            i += 2
        else:
            return land_local(argv[1], argv[2], argv[3], checks)
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
