#!/usr/bin/env python3
"""Живой сценарий dispatch-eval-replay без подписки: настоящий global/sdd_eval.py на игрушечном проекте
из 8 change; вместо claude подмена первой в PATH, она вливает коммит-оракул и архивирует change.

Использование: python3 tests/stands/eval-replay.py
Код 0 — все проверки сошлись. Временную папку и HOME стенд создаёт и удаляет сам."""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL, PLAN = ROOT / "global/sdd_eval.py", ROOT / "global/sdd_dispatch_plan.py"
IDS = ["20%d-feat" % i for i in range(8)]
DEPS = {"201-feat": "- `100-dep`\n", "202-feat": "- `999-ghost`\n", "203-feat": "нет\n"}
ASKED, BROKEN = "203-feat", "204-feat"
RUNNER = 'rc=0\nfor f in "$@"; do sh "$f" || { echo "FAIL $f"; rc=1; }; done\nexit $rc\n'
AGENTS = "# P\n\n## Команды\n\n| Что | Команда |\n|---|---|\n| Тесты | `sh run-tests.sh` |\n\n## Поставка\n\n- Режим: pr\n"
FAKE = """#!%s
import json, os, subprocess, sys
meta = json.load(open(".sdd-eval"))
open(os.environ["STAND_ARGV"], "a").write(json.dumps(sys.argv[1:]) + "\\n")
subprocess.run(["git", "merge", "-q", "--ff-only", meta["oracle"]], check=True)
os.makedirs("openspec/changes/archive", exist_ok=True)
os.rename("openspec/changes/" + meta["id"], "openspec/changes/archive/2026-01-01-" + meta["id"])
if meta["id"] == "%s" and os.environ["STAND_ASK"] == "1":
    d = os.path.expanduser("~/.claude/projects/p")
    os.makedirs(d, exist_ok=True)
    sid = sys.argv[sys.argv.index("--session-id") + 1]
    msg = {"type": "assistant", "message": {"content": [{"type": "text", "text": "Нужно от вас: выбрать режим"}]}}
    open(os.path.join(d, sid + ".jsonl"), "w").write(json.dumps(msg) + "\\n")
""" % (sys.executable, ASKED)

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("ok: " if ok else "FAIL: ") + name + ("" if ok else " — " + detail[-400:]))


def put(base, rel, text):
    p = Path(base, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def sh(args, cwd=None, env=None):
    return subprocess.run([str(a) for a in args], cwd=cwd, env=env, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)


def git(repo, *args):
    r = sh(["git", "-C", repo] + list(args))
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def build(tmp):
    proj = tmp / "proj"
    proj.mkdir()
    git(proj, "init", "-q", "-b", "main")
    put(proj, ".gitignore", "openspec/\nAGENTS.md\nCLAUDE.md\n")
    put(proj, "run-tests.sh", RUNNER)
    git(proj, "add", "-A")
    git(proj, "commit", "-qm", "base")
    changes = []
    for cid in IDS:
        n = cid[:3]
        put(proj, "code_%s.sh" % n, "f_%s() { :; }\n" % n)
        put(proj, "t%s.test.sh" % n, ". ./code_%s.sh\ntype f_%s >/dev/null 2>&1\n" % (n, n))
        git(proj, "add", "-A")
        git(proj, "commit", "-qm", cid)
        changes.append({"id": cid, "oracle": git(proj, "rev-parse", "HEAD")})
        d = "openspec/changes/archive/2025-12-01-" + cid
        put(proj, d + "/proposal.md", "## Why\nw\n\n## Depends On\n\n" + DEPS.get(cid, "none\n"))
        put(proj, d + "/tasks.md", "- [x] a\n- [ ] b\n")
        put(proj, d + "/verification.md", "## Live Scenario\n\nшаг\n\n## Result\n\nOK\n\n## Not Verified\n\nничего\n")
        put(proj, d + "/CLAIM", "c\n")
    put(proj, "AGENTS.md", AGENTS)
    put(proj, "openspec/config.yaml", "schema: solo\n")
    put(proj, "openspec/changes/archive/2025-11-01-100-dep/proposal.md", "## Why\nd\n")
    put(tmp, "set.json", json.dumps({"project": str(proj), "prepare": "true", "tests": ["*.test.sh"], "changes": changes,
                                     "answers": {"Режим поставки": "local"}}))
    put(tmp, "cfg.json", json.dumps({"name": "base", "working_copy": []}))


def main():
    tmp = Path(tempfile.mkdtemp()).resolve()
    try:
        return stand(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def stand(tmp):
    build(tmp)
    home, fake, E = tmp / "home", tmp / "bin", tmp / "E"
    home.mkdir()
    fake.mkdir()
    E.mkdir()
    (fake / "claude").write_text(FAKE)
    (fake / "claude").chmod(stat.S_IRWXU)
    env = dict(os.environ, HOME=str(home), PATH="%s:%s" % (fake, os.environ["PATH"]), STAND_ARGV=str(tmp / "argv"),
               GIT_AUTHOR_NAME="s", GIT_AUTHOR_EMAIL="s@s", GIT_COMMITTER_NAME="s", GIT_COMMITTER_EMAIL="s@s")

    def ev(*args, ask="0"):
        return sh([sys.executable, EVAL] + list(args), cwd=ROOT, env=dict(env, STAND_ASK=ask))

    a, b = ev("setup", tmp / "set.json", "--config", tmp / "cfg.json", "--out", E / "a"), \
        ev("setup", tmp / "set.json", "--config", tmp / "cfg.json", "--out", E / "b")
    check("setup дважды: 8 копий, HEAD и хеш openspec совпадают", a.returncode == 0 and a.stdout == b.stdout
          and len(os.listdir(E / "a")) == 8, a.stdout + a.stderr)
    check("зависимость не в архиве: строка и копия", "зависимость не в архиве: 202-feat 999-ghost" in a.stdout
          and (E / "a/202-feat").is_dir() and "не в архиве: 203-feat" not in a.stdout, a.stdout)
    c = E / "a/201-feat"
    ch = c / "openspec/changes/201-feat"
    tasks, ver, agents = (ch / "tasks.md").read_text(), (ch / "verification.md").read_text(), (c / "AGENTS.md").read_text()
    check("копия до кода: задачи сброшены, нет CLAIM, нет remote, режим local",
          "[x]" not in tasks and "OK" not in ver and not (ch / "CLAIM").exists() and not git(c, "remote")
          and "Режим: local" in agents and "Режим: pr" not in agents, tasks + ver + agents)
    plan = sh([sys.executable, PLAN, c], env=env)
    check("план копии с архивной зависимостью: запустить, без неизвестной зависимости",
          (c / "openspec/changes/archive/2025-11-01-100-dep").is_dir() and "запустить: 201-feat" in plan.stdout
          and "неизвестная зависимость" not in plan.stdout, plan.stdout + plan.stderr)

    ra, rb = ev("run", E / "a", "--label", "a1", ask="1"), ev("run", E / "b", "--label", "b1")
    argv = json.loads((tmp / "argv").read_text().splitlines()[0])
    check("run: промпт /spec-dispatch, ответы в --append-system-prompt, все смёрджены",
          argv[:2] == ["-p", "/spec-dispatch"] and "Режим поставки → local" in argv[argv.index("--append-system-prompt") + 1]
          and "завершено 8 из 8" in ra.stdout and "завершено 8 из 8" in rb.stdout, ra.stdout + ra.stderr + rb.stdout)
    check("run: отметка вопроса по строке «Нужно от вас»", "%s смёрджен вопрос: выбрать режим" % ASKED in ra.stdout, ra.stdout)
    for f, x, y in ((E / "a", "a1", "a2"), (E / "b", "b1", "b2")):
        shutil.copy(f / "runs" / (x + ".json"), f / "runs" / (y + ".json"))

    same = ev("compare", E, "--a", "a1", "a2", "--b", "a1", "a2")
    check("самосравнение: без перевернувшихся", same.returncode == 0 and "Перевернувшиеся: нет" in same.stdout, same.stdout + same.stderr)
    for cid in (ASKED, BROKEN):
        n = cid[:3]
        put(E / "a" / cid, "code_%s.sh" % n, "x=1\n")
        git(E / "a" / cid, "-c", "user.name=s", "-c", "user.email=s@s", "commit", "-qam", "удалён экспорт")
    r = ev("compare", E, "--a", "a1", "a2", "--b", "b1", "b2")
    flips = r.stdout.split("Перевернувшиеся:")[1].split("С вопросом:")[0]
    check("удалён экспорт: смёрджен, оракул красный с именем теста", r.returncode == 0 and
          "смёрджен, оракул красный: t204.test.sh" in r.stdout, r.stdout + r.stderr)
    check("перевернулся только change без вопроса", BROKEN in flips and ASKED not in flips, r.stdout)
    check("вопрос: раздел «С вопросом» и пометка в таблице, счёт по оракулу",
          "- %s: a1: вопрос: выбрать режим" % ASKED in r.stdout and "оракул красный: t203.test.sh (вопрос)" in r.stdout
          and "| a | 6, 6 из 8 |" in r.stdout and "| b | 8, 8 из 8 |" in r.stdout, r.stdout)

    proj = home / ".claude/projects/fx"
    shutil.copytree(ROOT / "tests/eval/fixtures", proj)
    m = ev("metrics", "--session", "fixture-session", "--prices", ROOT / "tests/eval/prices.json")
    check("metrics --session на фикстуре", m.returncode == 0 and "смёрджено: 1" in m.stdout and "время: 0.47 ч" in m.stdout, m.stdout + m.stderr)

    print("итог: %d из %d" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
