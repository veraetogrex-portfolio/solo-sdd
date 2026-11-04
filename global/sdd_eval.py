#!/usr/bin/env python3
"""Повтор change на копиях проекта: сравнение конфигураций диспетчера на одном наборе.

Запуск:
  sdd-eval.py setup <набор.json> --config <конфигурация.json> --out <папка>
  sdd-eval.py run <папка> --label <метка>
  sdd-eval.py metrics <папка> --label <метка>
  sdd-eval.py compare <папка> --a <метка>... --b <метка>...

compare прогоняет тесты оракула на результате каждого прогона и печатает отчёт (код 0; 2 — меньше двух
прогонов у конфигурации или нет журнала; 3 — у копии нет команды тестов).

setup проверяет набор (код 2, ничего не создаётся), делает по копии проекта на базе каждого change
(первый родитель коммита-оракула), переносит правила, спеки и архив change, выполняет prepare и печатает
«<id> <HEAD> <хеш openspec>». Код 3 — сбой подготовки хотя бы одной копии. Поле набора answers (вопрос -> ответ)
пишется в .sdd-eval копии, run отдаёт его диспетчеру.
"""
import argparse
import fnmatch
import glob
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

DEFAULT_TESTS = ["*.test.*", "tests/"]
EMPTIED = ("Result", "Not Verified", "Decisions Without Owner")
DATED = r"\d{4}-\d{2}-\d{2}-"


def sh(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def git(project, *args):
    r = sh(["git", "-C", project] + list(args))
    if r.returncode:
        raise RuntimeError("git %s: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout


def main_branch(project):
    r = sh(["git", "-C", project, "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().split("/", 1)[-1]
    return sh(["git", "-C", project, "branch", "--show-current"]).stdout.strip()


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def is_test_file(path, patterns):
    for pat in patterns:
        if pat.endswith("/"):
            if ("/" + path).find("/" + pat) >= 0:
                return True
        elif fnmatch.fnmatch(os.path.basename(path), pat):
            return True
    return False


def oracle_files(project, oracle):
    return git(project, "diff-tree", "--no-commit-id", "--name-only", "-r", oracle + "^1", oracle).splitlines()


def oracle_tests(project, oracle, patterns):
    """Тестовые файлы оракула; удалённые в нём (нет «<oracle>:<путь>») не считаются."""
    return [f for f in oracle_files(project, oracle) if is_test_file(f, patterns)
            and sh(["git", "-C", project, "cat-file", "-e", "%s:%s" % (oracle, f)]).returncode == 0]


def copies(folder):
    return sorted(os.path.join(folder, d) for d in os.listdir(folder)
                  if os.path.isfile(os.path.join(folder, d, ".sdd-eval")))


def sections(src, title):
    """Строки раздела «## title» до следующего «## »."""
    out, inside = [], False
    for ln in src.splitlines():
        if ln.startswith("## "):
            inside = ln.strip() == "## " + title
        elif inside:
            out.append(ln)
    return out


def plan_deps():
    """parse_deps из sdd_dispatch_plan.py рядом со скриптом (после раскладки имя с дефисом)."""
    for n in ("sdd_dispatch_plan.py", "sdd-dispatch-plan.py"):
        p = os.path.join(HERE, n)
        if os.path.isfile(p):
            sp = importlib.util.spec_from_file_location("sdd_dispatch_plan", p)
            m = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(m)
            return m.parse_deps
    raise RuntimeError("нет sdd_dispatch_plan.py рядом с sdd_eval.py")


def reset_tasks(text):
    return re.sub(r"^(\s*- )\[[xX]\]", r"\1[ ]", text, flags=re.M)


def reset_verification(text):
    """Тело разделов Result, Not Verified, Decisions Without Owner становится пустым; остальное как было."""
    out, skip = [], False
    for ln in text.splitlines(keepends=True):
        if ln.startswith("## "):
            skip = ln.strip()[3:] in EMPTIED
            out += [ln.rstrip("\r\n") + "\n", "\n"] if skip else [ln]
        elif not skip:
            out.append(ln)
    return "".join(out)


def delta_requirements(text):
    """Имена требований дельты по видам: ADDED, MODIFIED, REMOVED, RENAMED (имена из FROM и TO)."""
    res = {k: [] for k in ("ADDED", "MODIFIED", "REMOVED", "RENAMED")}
    kind = None
    for ln in text.splitlines():
        m = re.match(r"## (ADDED|MODIFIED|REMOVED|RENAMED) Requirements", ln)
        if m:
            kind = m.group(1)
        elif ln.startswith("## "):
            kind = None
        elif kind:
            m = re.match(r"(?:### |- (?:FROM|TO):\s*`?### )Requirement:\s*(.+?)`?\s*$", ln)
            if m:
                res[kind].append(m.group(1))
    return res


def strip_added(spec_text, names):
    """Убирает блоки требований names: от «### Requirement: имя» до следующего «### Requirement:», «## » или конца."""
    out, skip = [], False
    for ln in spec_text.splitlines(keepends=True):
        if ln.startswith("### Requirement:"):
            skip = ln[len("### Requirement:"):].strip() in names
        elif ln.startswith("## "):
            skip = False
        if not skip:
            out.append(ln)
    return "".join(out)


def replace_section(text, title, body):
    lines = text.splitlines(keepends=True)
    for i, ln in enumerate(lines):
        if ln.strip() == "## " + title:
            j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
            return "".join(lines[:i] + [ln.rstrip("\r\n") + "\n", body] + lines[j:])
    sep = "" if not text else ("\n" if text.endswith("\n") else "\n\n")
    return text + sep + "## %s\n%s" % (title, body)


def patch_agents(text, lines):
    """«Поставка» -> «Режим: local»; «Рабочая копия» -> строки конфигурации, первой «Оркестраторов: 1»."""
    text = replace_section(text, "Поставка", "\n- Режим: local\n\n")
    own = ["Оркестраторов: 1"] + [s for s in lines if not s.startswith("Оркестраторов:")]
    return replace_section(text, "Рабочая копия", "\n" + "".join("- %s\n" % s for s in own) + "\n")


def tree_hash(directory):
    h = hashlib.sha256()
    files = sorted(os.path.relpath(os.path.join(d, f), directory)
                   for d, _, fs in os.walk(directory) for f in fs)
    for rel in files:
        with open(os.path.join(directory, rel), "rb") as f:
            h.update(rel.encode("utf-8") + b"\0" + f.read() + b"\0")
    return h.hexdigest()


def archived(project, cid):
    arch = os.path.join(project, "openspec", "changes", "archive")
    hit = sorted(d for d in (os.listdir(arch) if os.path.isdir(arch) else [])
                 if re.fullmatch(DATED + re.escape(cid), d))
    return os.path.join(arch, hit[0]) if hit else None


def validate(spec, cfg, out):
    """Все проблемы набора и конфигурации разом."""
    bad = []
    project = os.path.abspath(os.path.expanduser(spec.get("project") or ""))
    chs = spec.get("changes")
    if not isinstance(chs, list):
        return ["поле changes: нет списка"], project
    if len(chs) < 8:
        bad.append("changes: %d, нужно не меньше 8" % len(chs))
    if not cfg.get("name"):
        bad.append("конфигурация: нет поля name")
    ans = spec.get("answers", {})
    if not isinstance(ans, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in ans.items()):
        bad.append("answers: нужен объект «вопрос → ответ», строки")
    if not os.path.isdir(project):
        return bad + ["project: нет папки " + project], project
    if not os.path.isfile(os.path.join(project, "AGENTS.md")):
        bad.append("нет AGENTS.md в " + project)
    main = main_branch(project)
    pats = spec.get("tests", DEFAULT_TESTS)
    seen = set()
    for i, c in enumerate(chs):
        cid, oracle = c.get("id"), c.get("oracle")
        name = cid or "changes[%d]" % i
        for field, v in (("id", cid), ("oracle", oracle)):
            if not v:
                bad.append("%s: нет поля %s" % (name, field))
        if not cid or not oracle:
            continue
        if cid in seen:
            bad.append("%s: повтор в наборе" % cid)
            continue
        seen.add(cid)
        if not archived(project, cid):
            bad.append("%s: нет папки в openspec/changes/archive" % cid)
        if os.path.exists(os.path.join(out, cid)):
            bad.append("%s: папка копии уже есть: %s" % (cid, os.path.join(out, cid)))
        if sh(["git", "-C", project, "merge-base", "--is-ancestor", oracle, main]).returncode:
            bad.append("%s: оракул %s не найден в ветке %s" % (cid, oracle, main))
        elif sh(["git", "-C", project, "rev-parse", "--verify", "-q", oracle + "^1"]).returncode:
            bad.append("%s: у оракула нет первого родителя" % cid)
        elif not oracle_tests(project, oracle, pats):
            bad.append("оракул без тестов: " + cid)
    return bad, project


def carry(project, copy, rel):
    src = os.path.join(project, rel)
    if os.path.isfile(src):
        os.makedirs(os.path.dirname(os.path.join(copy, rel)), exist_ok=True)
        shutil.copy2(src, os.path.join(copy, rel))


def fix_file(path, fn):
    if os.path.isfile(path):
        write(path, fn(read(path)))


def build_copy(project, main, spec, cfg, out, c):
    """Копия одного change; возвращает (строки stdout, заметки о спеке)."""
    cid, oracle = c["id"], c["oracle"]
    copy = os.path.join(out, cid)
    base = git(project, "rev-parse", oracle + "^1").strip()
    git(out, "clone", "-q", "--no-checkout", "-b", main, project, copy)
    git(copy, "checkout", "-q", "-B", main, base)
    git(copy, "remote", "remove", "origin")
    for t in git(copy, "tag", "-l").split():
        git(copy, "tag", "-d", t)
    lines, notes = [], []
    carry(project, copy, "CLAUDE.md")
    write(os.path.join(copy, "AGENTS.md"), patch_agents(read(os.path.join(project, "AGENTS.md")),
                                                        cfg.get("working_copy", [])))
    osp = os.path.join(project, "openspec")
    for f in sorted(os.listdir(osp)) if os.path.isdir(osp) else []:
        carry(project, copy, os.path.join("openspec", f))
    if os.path.isdir(os.path.join(osp, "specs")):
        shutil.copytree(os.path.join(osp, "specs"), os.path.join(copy, "openspec", "specs"), dirs_exist_ok=True)
    for f in git(project, "ls-files", "-z", "-o", "-i", "--exclude-standard", "docs").split("\0"):
        if f and not os.path.islink(os.path.join(project, f)):
            carry(project, copy, f)
    arch = archived(project, cid)
    dst = os.path.join(copy, "openspec", "changes", cid)
    shutil.copytree(arch, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("CLAIM", "WAITING"))
    fix_file(os.path.join(dst, "tasks.md"), reset_tasks)
    fix_file(os.path.join(dst, "verification.md"), reset_verification)
    prop = os.path.join(arch, "proposal.md")
    for dep in plan_deps()(sections(read(prop), "Depends On")) if os.path.isfile(prop) else []:
        da = archived(project, dep)
        if da:
            shutil.copytree(da, os.path.join(copy, "openspec", "changes", "archive", os.path.basename(da)),
                            dirs_exist_ok=True)
        else:
            lines.append("зависимость не в архиве: %s %s" % (cid, dep))
    specs = os.path.join(arch, "specs")
    for cap in sorted(os.listdir(specs)) if os.path.isdir(specs) else []:
        sp = os.path.join(specs, cap, "spec.md")
        if not os.path.isfile(sp):
            continue
        delta = delta_requirements(read(sp))
        target = os.path.join(copy, "openspec", "specs", cap, "spec.md")
        if delta["ADDED"] and os.path.isfile(target):
            left = strip_added(read(target), set(delta["ADDED"]))
            if "### Requirement:" in left:
                write(target, left)
            else:
                shutil.rmtree(os.path.dirname(target))
        for kind in ("MODIFIED", "REMOVED", "RENAMED"):
            notes += ["спека после изменения: %s %s" % (cid, n) for n in delta[kind]]
    lines += notes
    meta = {"config": cfg["name"], "id": cid, "oracle": oracle, "base": base, "main": main, "project": project,
            "spec_notes": notes, "tests": spec.get("tests", DEFAULT_TESTS), "answers": spec.get("answers", {})}
    write(os.path.join(copy, ".sdd-eval"), json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    with open(os.path.join(copy, ".git", "info", "exclude"), "a", encoding="utf-8") as f:
        f.write(".sdd-eval\n")
    return lines, copy, base


def cmd_setup(a):
    a.out = os.path.abspath(a.out)
    spec, cfg = read_json(a.set), read_json(a.config)
    bad, project = validate(spec, cfg, a.out)
    if bad:
        print("\n".join(bad), file=sys.stderr)
        return 2
    main = main_branch(project)
    os.makedirs(a.out, exist_ok=True)
    failed = False
    for c in spec["changes"]:
        try:
            lines, copy, base = build_copy(project, main, spec, cfg, a.out, c)
            r = subprocess.run(["sh", "-c", spec.get("prepare", "true")], cwd=copy, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        except (RuntimeError, OSError) as e:
            print("%s: сбой подготовки: %s" % (c["id"], e), file=sys.stderr)
            failed = True
            continue
        for ln in lines:
            print(ln, flush=True)
        if r.returncode:
            print("%s: prepare код %d\n%s" % (c["id"], r.returncode, "\n".join(r.stdout.splitlines()[-10:])),
                  file=sys.stderr)
            failed = True
            continue
        print("%s %s %s" % (c["id"], git(copy, "rev-parse", "HEAD").strip(),
                            tree_hash(os.path.join(copy, "openspec"))), flush=True)
    return 3 if failed else 0


# ---- run ----

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_merged(copy, meta):
    r = sh(["git", "-C", copy, "rev-list", "--count", "%s..%s" % (meta["base"], meta["main"])])
    ahead = r.returncode == 0 and int(r.stdout.strip() or 0) > 0
    return ahead and archived(copy, meta["id"]) is not None


NO_ASK = ("Окна вопроса владельцу нет, ответа не будет: не спрашивай владельца (ни AskUserQuestion, ни «Нужно от вас» "
          "с вопросом), решай сам по ответам ниже.")


def answers_prompt(answers):
    return "\n".join([NO_ASK] + ["- %s → %s" % kv for kv in answers.items()])


def questions(sid):
    """Первые вопросы диспетчера и оркестраторов из журнала сессии: AskUserQuestion и «Нужно от вас» с вопросом."""
    path = find_session(sid)
    if not path:
        return None
    files = [path] + sorted(glob.glob(os.path.join(path[:-len(".jsonl")], "subagents", "agent-*.jsonl")))
    found = []
    for i, p in enumerate(files):
        try:
            objs = parsed(jlines(p))
        except OSError:
            continue
        for o in objs:
            for b in blocks(o):
                if b.get("type") == "tool_use" and b.get("name") == "AskUserQuestion":
                    qs = (b.get("input") or {}).get("questions")
                    found += [str(q["question"]) for q in qs if isinstance(q, dict) and q.get("question")] \
                        if isinstance(qs, list) else []
                elif i == 0 and o.get("type") == "assistant" and b.get("type") == "text":
                    for ln in str(b.get("text", "")).splitlines():
                        m = re.search(r"Нужно от вас(.*)", ln)
                        rest = m.group(1).lstrip(":—-* ").strip() if m else ""
                        if rest and not rest.lower().startswith(("ничего", "нет")):
                            found.append(rest)
    return "; ".join(found)[:300] or None


def run_copy(copy, folder, label, model):
    meta = read_json(os.path.join(copy, ".sdd-eval"))
    sid, start = str(uuid.uuid4()), now()
    log = os.path.join(folder, "runs", "%s.%s.log" % (label, meta["id"]))
    try:
        with open(log, "wb") as f:
            code = subprocess.run(["claude", "-p", "/spec-dispatch", "--model", model, "--session-id", sid,
                                   "--append-system-prompt", answers_prompt(meta.get("answers", {}))],
                                  cwd=copy, stdin=subprocess.DEVNULL, stdout=f,
                                  stderr=subprocess.STDOUT).returncode
    except OSError:
        code = 127
    done = code == 0 and is_merged(copy, meta)
    rec = {"session": sid, "start": start, "end": now(), "exit": code, "status": "смёрджен" if done else "не завершён"}
    q = questions(sid)
    if q:
        rec["question"] = "вопрос: " + q
    return meta, rec


def write_atomic(path, obj):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def cmd_run(a):
    folder = os.path.abspath(a.folder)
    journal = os.path.join(folder, "runs", a.label + ".json")
    if os.path.exists(journal):
        print("журнал уже есть: " + journal, file=sys.stderr)
        return 2
    cps = copies(folder) if os.path.isdir(folder) else []
    if not cps:
        print("в папке нет копий: " + folder, file=sys.stderr)
        return 2
    os.makedirs(os.path.join(folder, "runs"), exist_ok=True)
    data = {"label": a.label, "dispatcher_model": a.dispatcher_model, "config": None, "copies": {}}
    lock = threading.Lock()

    def one(copy):
        meta, rec = run_copy(copy, folder, a.label, a.dispatcher_model)
        with lock:
            data["config"] = meta["config"]
            data["copies"][meta["id"]] = rec
            write_atomic(journal, data)

    with ThreadPoolExecutor(max_workers=max(1, a.parallel)) as ex:
        list(ex.map(one, cps))
    for cid in sorted(data["copies"]):
        c = data["copies"][cid]
        print("%s %s%s" % (cid, c["status"], " " + c["question"] if c.get("question") else ""))
    ok = sum(c["status"] == "смёрджен" for c in data["copies"].values())
    print("завершено %d из %d" % (ok, len(cps)))
    return 0


# ---- metrics ----

COUNTERS = ("input", "cache_5m", "cache_1h", "cache_read", "output")
HERE = os.path.dirname(os.path.abspath(__file__))
REJECT = "Статус не принят хуком"
MERGE_CMD = re.compile(r"merge -q --no-ff --no-edit change/(\S+)")


def find_session(sid):
    hit = sorted(glob.glob(os.path.join(os.path.expanduser("~/.claude/projects"), "*", sid + ".jsonl")))
    return hit[0] if hit else None


def usage_by_message(lines):
    """id сообщения -> {model, input, cache_5m, cache_1h, cache_read, output}; максимум каждого счётчика."""
    out = {}
    for ln in lines:
        try:
            o = json.loads(ln)
            m = o["message"]
            mid, u = m["id"], m["usage"]
            if o.get("type") != "assistant" or m.get("model") == "<synthetic>" or not mid:
                continue
            cc = u.get("cache_creation")
            c5, c1 = ((cc.get("ephemeral_5m_input_tokens", 0), cc.get("ephemeral_1h_input_tokens", 0))
                      if isinstance(cc, dict) else (u.get("cache_creation_input_tokens", 0), 0))
            row = dict(zip(COUNTERS, (u.get("input_tokens") or 0, c5 or 0, c1 or 0,
                                      u.get("cache_read_input_tokens") or 0, u.get("output_tokens") or 0)))
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
        cur = out.setdefault(mid, dict(row, model=m.get("model")))
        for k in COUNTERS:
            cur[k] = max(cur[k], row[k])
    return out


def load_roles():
    for p in (os.path.join(HERE, "model-policy.json"), os.path.expanduser("~/.claude/hooks/model-policy.json")):
        if os.path.isfile(p):
            return read_json(p).get("roles", {})
    return {}


def role_of(description, roles):
    d = (description or "").lower()
    for role in ("review", "orchestrator", "implement"):
        if any(d.startswith(t.lower()) for t in roles.get(role, [])):
            return role
    return "general"


def jlines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def parsed(lines):
    out = []
    for ln in lines:
        try:
            o = json.loads(ln)
        except ValueError:
            continue
        if isinstance(o, dict):
            out.append(o)
    return out


def blocks(o):
    c = (o.get("message") or {}).get("content") if isinstance(o.get("message"), dict) else None
    return [b for b in c if isinstance(b, dict)] if isinstance(c, list) else []


def result_text(b):
    c = b.get("content")
    if isinstance(c, list):
        return "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
    return c if isinstance(c, str) else ""


def parse_ts(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return None


def merges(objs):
    """Merge-ключи главного файла -> timestamp результата (самый поздний на ключ)."""
    cmds, found = {}, {}
    for o in objs:
        for b in blocks(o):
            if b.get("type") == "tool_use" and b.get("name") == "Bash":
                cmds[b.get("id")] = (b.get("input") or {}).get("command", "")
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in cmds:
                t, cmd, key = result_text(b), cmds[b["tool_use_id"]], None
                if re.search(r'"merged"\s*:\s*true', t):
                    sha = re.search(r'"sha"\s*:\s*"([^"]+)"', t)
                    key = sha.group(1) if sha else b["tool_use_id"]
                elif re.search(r"PR #\d+\b[^\n]*merged \(", t):
                    key = "PR " + re.search(r"PR #(\d+)", t).group(1)
                elif MERGE_CMD.search(cmd) and "exit 0" in t:
                    key = MERGE_CMD.search(cmd).group(1)
                if key and o.get("timestamp"):
                    found[key] = max(found.get(key, ""), o["timestamp"])
    return found


def session_metrics(sid, prices):
    path = find_session(sid)
    if not path:
        return None
    roles = load_roles()
    subs = sorted(glob.glob(os.path.join(path[:-len(".jsonl")], "subagents", "agent-*.jsonl")))
    files = [(path, "dispatcher")]
    agents = {"orchestrator": 0, "implement": 0, "general": 0, "review": 0}
    for p in subs:
        try:
            desc = read_json(p[:-len(".jsonl")] + ".meta.json").get("description")
        except (OSError, ValueError):
            desc = None
        r = role_of(desc, roles)
        agents[r] += 1
        files.append((p, r))
    seen, owner, rejected = {}, {}, 0
    main_objs, cost_state = [], None
    for i, (p, r) in enumerate(files):
        lines = jlines(p)
        objs = parsed(lines)
        if i == 0:
            main_objs = objs
            cost_state = next((o for o in reversed(objs) if o.get("type") == "cost-state"), None)
        rejected += sum(REJECT in result_text(b) for o in objs for b in blocks(o) if b.get("type") == "tool_result")
        for mid, u in usage_by_message(lines).items():
            if mid in seen:
                for k in COUNTERS:
                    seen[mid][k] = max(seen[mid][k], u[k])
            else:
                seen[mid], owner[mid] = u, r
    zero = lambda: dict.fromkeys(COUNTERS, 0)
    by_role, models = {}, {}
    for mid, u in seen.items():
        for d in (by_role.setdefault("%s/%s" % (owner[mid], u["model"]), zero()),
                  models.setdefault(u["model"], zero())):
            for k in COUNTERS:
                d[k] += u[k]
    journal_out = {m: d["output"] for m, d in models.items()}
    cs_usage = (cost_state or {}).get("modelUsage") or {}
    for m, d in models.items():
        if m in cs_usage and "outputTokens" in cs_usage[m]:
            d["output"], d["output_source"] = cs_usage[m]["outputTokens"], "cost-state"
        else:
            d["output_source"] = "journal"
    for d in list(by_role.values()) + list(models.values()):
        d["input_total"] = d["input"] + d["cache_5m"] + d["cache_1h"] + d["cache_read"]
    unpriced = sorted(m for m in models if not isinstance(prices.get(m), dict))
    cost = None
    if not unpriced:
        cost = 0.0
        for u in seen.values():
            pr = prices[u["model"]]
            lg = pr.get("long")
            if lg and u["input"] + u["cache_5m"] + u["cache_1h"] + u["cache_read"] > lg["above"]:
                pr = lg
            cost += (u["input"] * pr["input"] + u["cache_5m"] * pr["cache_write_5m"] +
                     u["cache_1h"] * pr["cache_write_1h"] + u["cache_read"] * pr["cache_read"] +
                     u["output"] * pr["output"]) / 1e6
        for m, d in models.items():
            rest = max(0, d["output"] - journal_out[m])
            pr = prices[m].get("long") or prices[m]
            # ponytail: остаток выхода цены по верхнему тарифу, в cost-state нет разбиения по сообщениям
            cost += rest * pr["output"] / 1e6
    mg = merges(main_objs)
    first = next((o.get("timestamp") for o in main_objs for b in blocks(o)
                  if b.get("type") == "tool_use" and b.get("name") == "Agent"
                  and role_of((b.get("input") or {}).get("description"), roles) == "orchestrator"), None)
    last = max(mg.values()) if mg else None
    t0, t1 = parse_ts(first), parse_ts(last)
    return {"session": sid, "roles": by_role, "models": models, "cost_usd": cost, "unpriced": unpriced,
            "cost_state_usd": (cost_state or {}).get("totalCostUSD"), "agents": agents,
            "returns": sum(1 for o in main_objs for b in blocks(o)
                           if b.get("type") == "tool_use" and b.get("name") == "SendMessage"),
            "rejected": rejected, "merged": len(mg), "first_orchestrator": first, "last_merge": last,
            "hours": (t1 - t0) / 3600 if t0 is not None and t1 is not None else None}


def money(x):
    return "н/д" if x is None else "$%.2f" % x


def prices_path(arg):
    return arg or next((p for p in ("tests/eval/prices.json", os.path.join(os.path.dirname(HERE), "tests/eval/prices.json"))
                        if os.path.isfile(p)), "tests/eval/prices.json")


def label_metrics(folder, label, prices):
    """Метрики прогона по журналу <folder>/runs/<label>.json; пишет <label>.metrics.json.
    Возвращает (dict, missing): missing — журнала сессии хотя бы одной копии нет."""
    folder = os.path.abspath(folder)
    run = read_json(os.path.join(folder, "runs", label + ".json"))
    out, missing = {}, False
    for cid in sorted(run["copies"]):
        rec = run["copies"][cid]
        m = session_metrics(rec["session"], prices)
        if m is None:
            out[cid], missing = {"error": "журнал не найден", "status": rec["status"]}, True
            continue
        m["status"] = rec["status"]
        copy = os.path.join(folder, cid)
        t0, hours = parse_ts(m["first_orchestrator"]), None
        if rec["status"] == "смёрджен" and t0 is not None and os.path.isfile(os.path.join(copy, ".sdd-eval")):
            r = sh(["git", "-C", copy, "log", "-1", "--format=%ct", read_json(os.path.join(copy, ".sdd-eval"))["main"]])
            if r.returncode == 0 and r.stdout.strip():
                hours = (int(r.stdout) - t0) / 3600
        m["hours"] = hours
        out[cid] = m
    ok = [m for m in out.values() if "error" not in m]
    total = {"cost_usd": None if not ok or any(m["cost_usd"] is None for m in ok) else sum(m["cost_usd"] for m in ok),
             "models": {}, "agents": {}, "returns": sum(m["returns"] for m in ok),
             "rejected": sum(m["rejected"] for m in ok)}
    for m in ok:
        for name, d in m["models"].items():
            t = total["models"].setdefault(name, {"input_total": 0, "output": 0})
            t["input_total"] += d["input_total"]
            t["output"] += d["output"]
        for k, v in m["agents"].items():
            total["agents"][k] = total["agents"].get(k, 0) + v
    data = {"label": label, "copies": out, "total": total}
    write_atomic(os.path.join(folder, "runs", label + ".metrics.json"), data)
    return data, missing


def cmd_metrics(a):
    pp = prices_path(a.prices)
    if not os.path.isfile(pp):
        print("файл цен не найден: " + pp, file=sys.stderr)
        return 2
    prices = read_json(pp)
    if a.session:
        m = session_metrics(a.session, prices)
        if m is None:
            print("журнал не найден: " + a.session, file=sys.stderr)
            return 3
        div = max(m["merged"], 1)
        print("смёрджено: %d" % m["merged"])
        print("время: %s ч" % ("н/д" if m["hours"] is None else "%.2f" % m["hours"]))
        for k in sorted(m["roles"]):
            print("%s: %.2fM на change" % (k, m["roles"][k]["input_total"] / 1e6 / div))
        print("агенты: " + ", ".join("%s %d" % kv for kv in m["agents"].items()))
        print("возвраты: %d, отклонённых статусов: %d" % (m["returns"], m["rejected"]))
        print("стоимость: %s (cost-state %s)" % (money(m["cost_usd"]), money(m["cost_state_usd"])))
        return 0
    if not a.folder or not a.label:
        print("нужен --session или <папка> --label", file=sys.stderr)
        return 2
    folder = os.path.abspath(a.folder)
    jp = os.path.join(folder, "runs", a.label + ".json")
    if not os.path.isfile(jp):
        print("нет журнала прогона: " + jp, file=sys.stderr)
        return 2
    data, missing = label_metrics(folder, a.label, prices)
    for cid, m in data["copies"].items():
        if "error" in m:
            print("%s журнал не найден" % cid)
        else:
            print("%s %s %s %s" % (cid, m["status"], "н/д" if m["hours"] is None else "%.2f" % m["hours"],
                                   money(m["cost_usd"])))
    return 3 if missing else 0


# ---- compare ----

def test_command(copy):
    """Команда тестов из таблицы «Команды» AGENTS.md копии: первое значение в кавычках строки «Тесты»."""
    try:
        text = read(os.path.join(copy, "AGENTS.md"))
    except OSError:
        return None
    for ln in sections(text, "Команды"):
        cells = ln.split("|")
        if len(cells) > 2 and cells[1].strip() == "Тесты" and "`" in cells[2]:
            return cells[2].split("`")[1] or None
    return None


def parse_failed(output):
    """Имена упавших тестов: строки «FAIL  <что-то>» без ANSI, уникальные, не больше 20."""
    names = []
    for ln in re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", output).splitlines():
        m = re.match(r"\s*FAIL\s+(.+)", ln)
        if m and m.group(1).strip() not in names:
            names.append(m.group(1).strip())
    return names[:20]


def worktree_script():
    for n in ("sdd_worktree.py", "sdd-worktree.py"):
        if os.path.isfile(os.path.join(HERE, n)):
            return os.path.join(HERE, n)
    raise RuntimeError("нет sdd_worktree.py рядом с sdd_eval.py")


def oracle_run(copy, meta, timeout):
    """Тесты оракула на результате копии: {"green", "failed", "output_tail"}."""
    project, oracle = meta["project"], meta["oracle"]
    files = oracle_tests(project, oracle, meta["tests"])
    if not files:
        return {"green": False, "failed": ["нет файлов оракула"], "output_tail": ""}
    cmd = test_command(copy)
    tmp = tempfile.mkdtemp()
    wt = os.path.join(tmp, "wt")
    script = worktree_script()
    try:
        git(copy, "worktree", "add", "-q", "--detach", wt, meta["main"])
        r = sh([sys.executable, script, "setup", copy, wt])
        if r.returncode:
            raise RuntimeError("setup: " + (r.stderr.strip().splitlines() or r.stdout.strip().splitlines() or ["?"])[-1])
        # ссылки на игнорируемые результаты prepare копии; remove и rmtree ссылки не разворачивают
        for ent in git(copy, "ls-files", "-z", "-o", "-i", "--exclude-standard", "--directory").split("\0"):
            rel = ent.rstrip("/")
            if rel and rel != ".sdd-eval" and not os.path.lexists(os.path.join(wt, rel)):
                os.makedirs(os.path.dirname(os.path.join(wt, rel)), exist_ok=True)
                os.symlink(os.path.join(copy, rel), os.path.join(wt, rel))
        for f in files:
            data = subprocess.run(["git", "-C", project, "show", "%s:%s" % (oracle, f)], capture_output=True,
                                  stdin=subprocess.DEVNULL, check=True).stdout
            dst = os.path.join(wt, f)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as fh:
                fh.write(data)
        try:
            r = subprocess.run(["sh", "-c", cmd + " " + " ".join(shlex.quote(f) for f in files)], cwd=wt,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"green": False, "failed": ["таймаут %s с" % timeout], "output_tail": ""}
        out = r.stdout.decode("utf-8", "replace")
        tail = "\n".join(out.splitlines()[-20:])
        if r.returncode == 0:
            return {"green": True, "failed": [], "output_tail": tail}
        return {"green": False, "failed": parse_failed(out) or files, "output_tail": tail}
    finally:
        if sh([sys.executable, script, "remove", copy, wt]).returncode:
            sh(["git", "-C", copy, "worktree", "remove", "--force", wt])
        shutil.rmtree(tmp, ignore_errors=True)


def find_journal(folder, label):
    hits = [os.path.join(folder, "runs", label + ".json")] + sorted(glob.glob(os.path.join(folder, "*", "runs", label + ".json")))
    return next((h for h in hits if os.path.isfile(h)), None)


def hours_s(h):
    return "н/д" if h is None else "%.2f" % h


def cmd_compare(a):
    for name, labels in (("a", a.a), ("b", a.b)):
        if len(set(labels)) < 2:
            print("нужно ≥ 2 прогонов: " + name, file=sys.stderr)
            return 2
    folder = os.path.abspath(a.folder)
    uniq = list(dict.fromkeys(a.a + a.b))
    jpath = {}
    for lb in uniq:
        jpath[lb] = find_journal(folder, lb)
        if not jpath[lb]:
            print("нет журнала прогона: " + lb, file=sys.stderr)
            return 2
    runs = {lb: read_json(jpath[lb]) for lb in uniq}
    home = {lb: os.path.dirname(os.path.dirname(jpath[lb])) for lb in uniq}
    bad = False
    for lb in uniq:
        for cid, rec in sorted(runs[lb]["copies"].items()):
            copy = os.path.join(home[lb], cid)
            if rec["status"] != "смёрджен":
                continue
            cmd = test_command(copy)
            if not cmd:
                print("нет команды тестов: %s (%s)" % (cid, copy), file=sys.stderr)
                bad = True
            elif re.search(r"&&|\|\||[;|\n]", cmd):
                print("команда тестов — цепочка: %s (%s)" % (cid, copy), file=sys.stderr)
                bad = True
    if bad:
        return 3
    pp = prices_path(a.prices)
    prices = read_json(pp) if os.path.isfile(pp) else None
    res, mets, notes = {}, {}, set()
    for lb in uniq:
        mp = os.path.join(home[lb], "runs", lb + ".metrics.json")
        if os.path.isfile(mp):
            mets[lb] = read_json(mp)
        elif prices is not None:
            mets[lb] = label_metrics(home[lb], lb, prices)[0]
        else:
            mets[lb] = {"copies": {}}
        for cid, rec in sorted(runs[lb]["copies"].items()):
            copy = os.path.join(home[lb], cid)
            mp = os.path.join(copy, ".sdd-eval")
            meta = read_json(mp) if os.path.isfile(mp) else {}
            notes.update(meta.get("spec_notes", []))
            if rec["status"] != "смёрджен":
                res[lb, cid] = {"done": False, "text": "не смёрджен", "failed": None}
                continue
            try:
                o = oracle_run(copy, meta, a.timeout)
            except (RuntimeError, subprocess.CalledProcessError) as e:
                print("сбой оракула: %s: %s" % (cid, e), file=sys.stderr)
                return 3
            res[lb, cid] = {"done": o["green"], "failed": o["failed"],
                            "text": "выполнен" if o["green"] else "смёрджен, оракул красный: " + ", ".join(o["failed"])}

    def met(lb, cid):
        m = mets[lb].get("copies", {}).get(cid, {})
        return (None, None) if "error" in m else (m.get("hours"), m.get("cost_usd"))

    ids = sorted({cid for lb in uniq for cid in runs[lb]["copies"]})
    out = ["# Сравнение: a = %s; b = %s" % (", ".join(a.a), ", ".join(a.b)), "",
           "| Change | " + " | ".join(uniq) + " |", "|---|" + "---|" * len(uniq)]
    for cid in ids:
        cells = []
        for lb in uniq:
            r = res.get((lb, cid))
            if not r:
                cells.append("нет в прогоне")
            elif r["text"] == "не смёрджен":
                cells.append("не смёрджен" + (" (вопрос)" if runs[lb]["copies"][cid].get("question") else ""))
            else:
                h, c = met(lb, cid)
                q = " (вопрос)" if runs[lb]["copies"][cid].get("question") else ""
                cells.append("%s%s %s ч %s" % (r["text"], q, hours_s(h), money(c)))
        out.append("| %s | %s |" % (cid, " | ".join(cells)))
    out += ["", "| Конфигурация | Выполнено по прогонам | Время, ч | Стоимость |", "|---|---|---|---|"]
    for name, labels in (("a", a.a), ("b", a.b)):
        labels = list(dict.fromkeys(labels))
        counts = [sum(res.get((lb, c), {}).get("done", False) for c in runs[lb]["copies"]) for lb in labels]
        total = max(len(runs[lb]["copies"]) for lb in labels)
        mm = [met(lb, c) for lb in labels for c in runs[lb]["copies"]]
        hs, cs = [m[0] for m in mm if m[0] is not None], [m[1] for m in mm if m[1] is not None]
        out.append("| %s | %s из %d | %s | %s |" % (name, ", ".join(map(str, counts)), total,
                                                    hours_s(sum(hs) if hs else None), money(sum(cs) if cs else None)))
    asked = {cid: ["%s: %s" % (lb, runs[lb]["copies"][cid]["question"]) for lb in uniq
                   if runs[lb]["copies"].get(cid, {}).get("question")] for cid in ids}
    asked = {cid: v for cid, v in asked.items() if v}
    flips = []
    for (xn, xs), (yn, ys) in ((("a", a.a), ("b", a.b)), (("b", a.b), ("a", a.a))):
        for cid in ids:
            if cid not in asked and all(res.get((lb, cid), {}).get("done") for lb in xs):
                why = []
                for lb in dict.fromkeys(ys):
                    r = res.get((lb, cid))
                    if not r or not r["done"]:
                        why.append("%s: %s" % (lb, "нет в прогоне" if not r else
                                               ", ".join(r["failed"]) if r["failed"] else r["text"]))
                if why:
                    flips.append("- %s: выполнен во всех прогонах %s, не выполнен в %s" % (cid, xn, "; ".join(why)))
    out += [""] + (["Перевернувшиеся:"] + flips if flips else ["Перевернувшиеся: нет"])
    if asked:
        out += ["", "С вопросом:"] + ["- %s: %s" % (cid, "; ".join(v)) for cid, v in sorted(asked.items())]
    if notes:
        out += ["", "Спека после изменения:"] + ["- " + n for n in sorted(notes)]
    print("\n".join(out))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Повтор change на копиях проекта")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup")
    s.add_argument("set")
    s.add_argument("--config", required=True)
    s.add_argument("--out", required=True)
    r = sub.add_parser("run")
    r.add_argument("folder")
    r.add_argument("--label", required=True)
    r.add_argument("--dispatcher-model", default="sonnet")
    r.add_argument("--parallel", type=int, default=1)
    m = sub.add_parser("metrics")
    m.add_argument("folder", nargs="?")
    m.add_argument("--label")
    m.add_argument("--session")
    m.add_argument("--prices")
    c = sub.add_parser("compare")
    c.add_argument("folder")
    c.add_argument("--a", nargs="+", required=True)
    c.add_argument("--b", nargs="+", required=True)
    c.add_argument("--timeout", type=int, default=1800)
    c.add_argument("--prices")
    a = ap.parse_args(argv)
    return {"setup": cmd_setup, "run": cmd_run, "metrics": cmd_metrics, "compare": cmd_compare}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
