#!/usr/bin/python3
"""Хуки рабочего процесса Claude Code. Подкоманды: context, subagent-context, guard, claims, stop, beat, end, status.

Источник требований: анализ сессий 2026-09-16..2026-10-15 (повторы «прочитай агентс мд»,
«продолжи», «архивируй», «мёрджить кто будет», «статус?», секреты, дорогие модели).
Любая внутренняя ошибка пропускает действие (fail-open) и пишется в hook-state/errors.log.
"""
import datetime
import glob
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
import unicodedata

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.realpath(__file__))
STATE = os.path.join(HOME, ".claude", "hook-state")
TMP_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")
UI_EXT = (".html", ".htm", ".css", ".scss", ".sass", ".less", ".tsx", ".jsx", ".vue", ".svelte")
BROWSER_TOOLS = ("mcp__claude-in-chrome__", "mcp__agent-browser__", "mcp__peekaboo__")
BROWSER_SKILLS = ("ui-check", "agent-browser", "claude-in-chrome", "webapp-testing", "run", "web-perf")
BROWSER_BASH = re.compile(r"agent-browser|playwright|puppeteer|--headless|chrome-devtools|screencapture|--remote-debugging-port|json/version|webSocketDebuggerUrl")
ENV_FILE = r"(?:[^\s;&|'\"<>]*/)?(?:[\w-]*\.env|\.env\.(?!example\b|sample\b|template\b|dist\b)[\w-]+)(?![\w.-])"
SECRET_VAR = r"\w*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|WEBHOOK|CREDENTIAL)\w*"


# ---------- общее ----------

def sh(args, cwd=None, timeout=5):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def git_strict(args, cwd=None, timeout=5):
    """Как sh, но сбой git (код не 0, таймаут) — исключение: проверка статуса не должна гадать при сбое."""
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL, check=True).stdout


_roots = {}


def git_root(path):
    d = path if os.path.isdir(path) else os.path.dirname(path)
    while d and not os.path.isdir(d):
        d = os.path.dirname(d)
    if d not in _roots:
        out = sh(["git", "rev-parse", "--show-toplevel"], cwd=d or None).strip()
        _roots[d] = nfc(os.path.realpath(out)) if out else None
    return _roots[d]


def nfc(path):
    # git на macOS отдаёт пути в NFD (й = и + знак), Claude — в NFC; без этого папки с й «чужие»
    return unicodedata.normalize("NFC", path)


def under(path, root):
    path, root = nfc(os.path.realpath(path)), nfc(os.path.realpath(root))
    return path == root or path.startswith(root.rstrip("/") + "/")


def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))


def state_path(sid, suffix="json"):
    os.makedirs(STATE, exist_ok=True)
    return os.path.join(STATE, "%s.%s" % (re.sub(r"[^\w-]", "_", sid or "nosession"), suffix))


def load_state(sid):
    try:
        with open(state_path(sid)) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(sid, st):
    p = state_path(sid)
    tmp = p + ".%d.tmp" % os.getpid()
    with open(tmp, "w") as f:
        json.dump(st, f, ensure_ascii=False)
    os.replace(tmp, p)


def read_head(path, limit):
    try:
        with open(path, errors="replace") as f:
            text = f.read(limit + 1)
    except Exception:
        return None
    return text if len(text) <= limit else text[:limit] + "\n…[обрезано хуком]"


# ---------- context: SessionStart ----------

def done_tasks(text):
    return len(re.findall(r"^\s*- \[[xX]\]", text, re.M))


def openspec_changes(root):
    base = os.path.join(root, "openspec", "changes")
    if not os.path.isdir(base):
        return []
    rows = []
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if name == "archive" or not os.path.isdir(d):
            continue
        tasks = read_head(os.path.join(d, "tasks.md"), 200000) or ""
        done = done_tasks(tasks)
        todo = len(re.findall(r"^\s*- \[ \]", tasks, re.M))
        marks = []
        for flag in ("CLAIM", "WAITING"):
            body = read_head(os.path.join(d, flag), 200)
            if body is not None:
                marks.append("%s: %s" % (flag, body.strip().splitlines()[0] if body.strip() else "пусто"))
        rows.append("- %s — задачи %d/%d%s" % (name, done, done + todo, ("; " + "; ".join(marks)) if marks else ""))
    return rows


def cmd_context(inp):
    cwd = os.path.realpath(inp.get("cwd") or os.getcwd())
    root = git_root(cwd)
    top = root or cwd
    parts = []
    if cwd != os.path.realpath(HOME):
        d, seen = cwd, []
        while True:
            seen.append(d)
            if d == top or d == os.path.dirname(d) or os.path.realpath(d) == os.path.realpath(HOME):
                break
            d = os.path.dirname(d)
        for d in reversed(seen):
            if os.path.realpath(d) == os.path.realpath(HOME):
                continue
            agents = read_head(os.path.join(d, "AGENTS.md"), 12000)
            claude = read_head(os.path.join(d, "CLAUDE.md"), 12000)
            if agents and agents != claude:
                parts.append("### %s/AGENTS.md\n%s" % (d, agents))
        for rel, limit in (("openspec/config.yaml", 6000), ("docs/status.md", 6000)):
            body = read_head(os.path.join(top, rel), limit)
            if body:
                parts.append("### %s\n%s" % (rel, body))
    if root:
        branch = sh(["git", "branch", "--show-current"], cwd=root).strip() or "detached"
        status = sh(["git", "-c", "core.quotepath=off", "status", "--short"], cwd=root).splitlines()
        shown = "\n".join(status[:25]) + ("\n…ещё %d" % (len(status) - 25) if len(status) > 25 else "")
        parts.append("### git: ветка %s, незакоммиченных путей %d\n%s" % (branch, len(status), shown or "чисто"))
        changes = openspec_changes(root)
        if changes:
            parts.append("### Активные OpenSpec change (CLAIM — занят, WAITING — ждёт)\n" + "\n".join(changes))
    if not parts:
        return
    text = ("Автоконтекст проекта от хука SessionStart (%s, источник: файлы и git в момент старта). "
            "Правила ниже уже прочитаны, читать их повторно не нужно. Незакоммиченные чужие изменения не откатывай.\n\n"
            % inp.get("source", "startup")) + "\n\n".join(parts)
    emit({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text[:30000]}})


# ---------- subagent-context: SubagentStart ----------

SUBAGENT_LIMIT = 4000


def subagent_context_text(agents, rows):
    """Контекст субагента: путь к AGENTS.md первым, затем change; при нехватке места список обрезается.
    ponytail: путь длиннее ~3900 знаков лимит не удержит; на практике не бывает."""
    head = ["Правила проекта: прочитай %s перед работой (файл не вставлен, читай сам)." % agents] if agents else []
    if rows:
        head.append("Открытые change основной папки (CLAIM — занят, WAITING — ждёт):")
    out, reserve = "\n".join(head), 30
    for i, row in enumerate(rows):
        row = row[:300]
        if len(out) + len(row) + 1 > SUBAGENT_LIMIT - reserve:
            out += "\n…ещё %d" % (len(rows) - i)
            break
        out += "\n" + row
    return out


def cmd_subagent_context(inp):
    root = git_root(os.path.realpath(inp.get("cwd") or os.getcwd()))
    if not root:
        return
    main = main_checkout(root)
    agents = os.path.join(main, "AGENTS.md")
    text = subagent_context_text(agents if os.path.isfile(agents) else None, openspec_changes(main))
    if text:
        emit({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": text}})


# ---------- guard: PreToolUse ----------

def deny(reason):
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                 "permissionDecisionReason": reason}})
    sys.exit(0)


def project_roots(cwd):
    # cwd сессии уходит вслед за `cd` в Bash (в scratchpad и т. п.), CLAUDE_PROJECT_DIR — папка запуска
    roots = [git_root(cwd) or cwd]
    pd = os.environ.get("CLAUDE_PROJECT_DIR")
    if pd and os.path.isdir(pd):
        roots.append(git_root(pd) or nfc(os.path.realpath(pd)))
    return list(dict.fromkeys(roots))


def allowed_roots(cwd):
    roots = project_roots(cwd) + [os.path.join(HOME, ".claude"), os.path.join(HOME, ".codex"),
                                  os.path.join(HOME, "Desktop", "solo-sdd")] + list(TMP_ROOTS)
    for p in (os.path.join(HOME, ".claude", "settings.json"),
              os.path.join(cwd, ".claude", "settings.json"), os.path.join(cwd, ".claude", "settings.local.json")):
        try:
            with open(p) as f:
                roots += json.load(f).get("permissions", {}).get("additionalDirectories", [])
        except Exception:
            pass
    return [os.path.expanduser(r) for r in roots]


def guard_scope(sid, cwd, path):
    if under(cwd, HOME) and os.path.realpath(cwd) == os.path.realpath(HOME):
        return
    if any(under(path, r) for r in allowed_roots(cwd)):
        return
    st = load_state(sid)
    warned = st.setdefault("scope_warned", [])
    if path in warned:
        return
    warned.append(path)
    save_state(sid, st)
    deny("Запись вне папки проекта: %s. По правилам все файлы проекта лежат внутри папки проекта. "
         "Если пользователь прямо просил писать туда, повтори ту же запись — второй раз хук пропустит." % path)


def env_files_near(cwd):
    found = []
    for d in {cwd, git_root(cwd) or cwd}:
        try:
            found += [os.path.join(d, n) for n in os.listdir(d) if re.fullmatch(ENV_FILE, n)]
        except Exception:
            pass
    return found


def guard_env_write(tool, path, cwd):
    if not re.fullmatch(ENV_FILE, os.path.basename(path)):
        return
    if tool == "Write" and os.path.exists(path):
        deny("Перезапись существующего %s запрещена: там ключи пользователя. Не хватает поля — "
             "назови пользователю имя переменной, он добавит её сам (или допиши пустое поле через >>)." % path)
    others = [p for p in env_files_near(cwd) if os.path.realpath(p) != os.path.realpath(path)]
    if tool == "Write" and others:
        deny("У пользователя уже есть %s. Второй .env не создавай: используй существующий." % ", ".join(others))


CLAIM_LINE = 'echo "claude $(date +%F) session=$CLAUDE_CODE_SESSION_ID" > '


def claim_log(sid, line=None):
    """Абсолютные пути CLAIM, которые создала эта сессия (сама, через Write или Bash).
    Отдельный файл с дозаписью: async-хук beat перезаписывает json-состояние и потерял бы запись."""
    p = state_path(sid, "claims")
    if line:
        with open(p, "a") as f:
            f.write(line + "\n")
        return None
    try:
        with open(p) as f:
            return f.read().splitlines()
    except Exception:
        return []


def change_dirs(cwd, name):
    return [os.path.join(main_checkout(r), "openspec", "changes", name) for r in project_roots(cwd)]


def bash_log(inp, **rec):
    with open(state_path(inp.get("session_id", ""), "cmds"), "a") as f:
        f.write(json.dumps(dict(rec, id=inp.get("tool_use_id", "")), ensure_ascii=False) + "\n")


def note_claim_cmd(inp, cmd):
    # Bash создаёт CLAIM как угодно (>, cp, python). Запоминаем время команды, а не разбираем её текст.
    if "CLAIM" in cmd:
        bash_log(inp, t=time.time(), cmd=cmd[:4000])


def cmd_claims(inp):
    """PostToolUse и PostToolUseFailure для Bash: конец команды. Приходит с опозданием, уже после
    старта следующего вызова, поэтому решение принимает guard, а не этот хук."""
    if "CLAIM" in ((inp.get("tool_input") or {}).get("command") or ""):
        bash_log(inp, end=time.time())


def bash_created(sid, claim, name):
    """CLAIM изменён во время команды этой сессии, где названы CLAIM и сам change."""
    try:
        with open(state_path(sid, "cmds")) as f:
            recs = [json.loads(l) for l in f if l.strip()]
    except Exception:
        return False
    ends = {r["id"]: r["end"] for r in recs if "end" in r}
    mt, now = os.path.getmtime(claim), time.time()
    for r in recs:
        if "t" in r and name in r["cmd"]:
            end = ends.get(r["id"], min(now, r["t"] + 600))
            if r["t"] <= mt <= end:
                return True
    return False


def foreign_claim(sid, claim, name):
    """Текст отказа, если CLAIM чужой, иначе None. Свой CLAIM без id сессии хук дописывает сам."""
    body = (read_head(claim, 300) or "").strip()
    owner = re.search(r"session=([\w-]+)", body)
    mine = bool(sid) and (owner.group(1) == sid if owner else
                          claim in claim_log(sid) or bash_created(sid, claim, name))
    if mine:
        if not owner:
            with open(claim, "w") as f:
                f.write("%s session=%s\n" % (body or "claude " + datetime.date.today().isoformat(), sid))
        if claim not in claim_log(sid):
            claim_log(sid, claim)
        return None
    age = int((time.time() - os.path.getmtime(claim)) / 60)
    if owner:
        marks = [os.path.getmtime(p) for p in (state_path(owner.group(1)), state_path(owner.group(1), "claims"))
                 if os.path.exists(p)]
        seen = ("сессия-владелец последний раз активна %d мин назад" % ((time.time() - max(marks)) / 60)
                if marks else "следов активности сессии-владельца нет")
    else:
        seen = ("без id сессии. Если его ставил ты сам (например, до /clear), перепиши: %s%s"
                % (CLAIM_LINE, claim))
    return ("Change %s занят другим агентом: CLAIM «%s», поставлен %d мин назад, %s. Возьми другой change. "
            "Если CLAIM явно брошенный, скажи об этом пользователю, сам не снимай." % (name, body, age, seen))


def main_checkout(root, run=sh):
    common = run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=root).strip()
    return nfc(os.path.realpath(os.path.dirname(common))) if common.endswith("/.git") else root


def more_done(tool, ti, path):
    """Правка увеличивает число отмеченных задач: текст на диске против текста после правки."""
    old = read_head(path, 200000) or ""
    if tool == "Write":
        return done_tasks(ti.get("content") or "") > done_tasks(old)
    new = old
    for e in ti.get("edits") or [ti]:
        s = e.get("old_string") or ""
        if s not in new or new.count(s) > 1 and not e.get("replace_all"):
            return False  # инструмент откажет целиком, MultiEdit тоже: правки не будет
        new = new.replace(s, e.get("new_string") or "")
    return done_tasks(new) > done_tasks(old)


def guard_claim(sid, path, tool, ti):
    m = re.match(r"(.*/openspec/changes/)([^/]+)/(.+)$", nfc(os.path.realpath(path)))
    if m and m.group(3) == "CLAIM" and not os.path.exists(path):
        claim_log(sid, m.group(0))
    if not m or m.group(2) == "archive" or m.group(3) in ("CLAIM", "WAITING"):
        return
    name, cdir = m.group(2), m.group(1) + m.group(2)
    if not os.path.isdir(cdir):
        return
    root = git_root(cdir)
    if root and main_checkout(root) != root:
        # worktree: CLAIM живёт в основной папке, там его видят соседи; в worktree его закоммитят
        cdir = os.path.join(main_checkout(root), os.path.relpath(cdir, root))
        if not os.path.isdir(cdir):
            return
    claim, waiting = os.path.join(cdir, "CLAIM"), os.path.join(cdir, "WAITING")
    if os.path.exists(claim):
        reason = foreign_claim(sid, claim, name)
        if reason:
            deny(reason)
        return
    if os.path.exists(waiting):
        deny("Change %s ждёт внешнего условия (WAITING: %s). Возьми другой change."
             % (name, (read_head(waiting, 300) or "").strip()))
    if m.group(3) != "tasks.md" or not more_done(tool, ti, path):
        return
    try:
        fd = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return guard_claim(sid, path, tool, ti)
    with os.fdopen(fd, "w") as f:
        f.write("claude %s session=%s\n" % (datetime.date.today().isoformat(), sid))
    claim_log(sid, claim)


def guard_archive(sid, cmd, cwd):
    for name in re.findall(r"(?:^|[;&|(\n])\s*(?:\w+=\S*\s+)*(?:npx\s+(?:-y\s+)?)?openspec\s+archive\s+"
                           r"(?:-\S+\s+)*[\"']?([\w.-]+)", cmd):
        for d in change_dirs(cwd, name):
            claim = os.path.join(d, "CLAIM")
            reason = os.path.exists(claim) and foreign_claim(sid, claim, name)
            if reason:
                deny("Архивировать нельзя. " + reason)


def policy():
    with open(os.path.join(HERE, "model-policy.json")) as f:
        return json.load(f)


def model_hits(text, names):
    return [n for n in names if re.search(r"(?i)(?<![a-z])%s(?![a-z])" % re.escape(n), text)]


OVERRIDE_VAR = "SOLO_SDD_EXPENSIVE_OK"
OWNER_ONLY = "Дорогую модель разрешает только владелец."


def owner_override():
    return os.environ.get(OVERRIDE_VAR) == "1"


# ---------- текст — не команда: тела heredoc и шаблоны поиска вырезаются перед проверками ----------
# Копия этого блока живёт в process-guard.py (скрипт раскладывается отдельно): правь оба места.
# тело heredoc — текст, только если его читают эти программы; любой другой получатель (оболочка, обёртка) — команды
TEXT_SINKS = {"cat", "tee", "head", "tail", "wc", "sort", "uniq", "grep", "egrep", "rg", "jq", "cut", "tr", "nl",
              "column", "fold", "fmt", "paste", "rev", "tac", "comm", "diff", "less", "more", "base64", "od", "xxd",
              "shasum", "md5", "python", "python3", "node"}
WRAPPERS = {"sudo", "env", "command", "exec", "nohup", "time", "timeout", "gtimeout", "nice", "caffeinate", "npx"}
GREPS = {"grep", "egrep", "rg", "ag"}
VALUE_OPTS = {"-A", "-B", "-C", "-m", "-g", "-t", "-f", "--file", "--include", "--exclude", "--glob", "--type", "--pre"}
SED_VALUE_OPTS = {"-f", "--file", "-l", "--line-length"}
HEREDOC = re.compile(r"(?<![<\\])<<(?!<)(-?)\s*([\"']?)([A-Za-z_]\w*)\2")


def split_cmd(text):
    """Делит команду на части по ; && || | & и переводу строки вне кавычек: [часть, разделитель, часть, ...]."""
    out, cur, q, i, n = [], [], None, 0, len(text)
    while i < n:
        c = text[i]
        if c == "\\" and q != "'" and i + 1 < n:
            cur.append(text[i:i + 2])
            i += 2
            continue
        if q:
            q = None if c == q else q
        elif c in "'\"":
            q = c
        else:
            sep = None
            if text.startswith("&&", i) or text.startswith("||", i):
                sep = text[i:i + 2]
            elif c in ";|\n":
                sep = c
            elif c == "&" and not (i and text[i - 1] in "<>&") and text[i + 1:i + 2] not in (">", "&"):
                sep = c
            if sep:
                out += ["".join(cur), sep]
                cur, i = [], i + len(sep)
                continue
        cur.append(c)
        i += 1
    return out + ["".join(cur)]


def quote_end(text, q=None):
    """Открытая кавычка в конце текста (None, ' или \")."""
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\" and q != "'":
            i += 2
            continue
        if q:
            q = None if c == q else q
        elif c in "'\"":
            q = c
        i += 1
    return q


LEAD = {"then", "do", "else", "elif", "if", "while", "until"}
NUM_ARG = re.compile(r"[\d.]+[smhd]?")
VALUED = {"-s", "--signal", "-n", "--adjustment", "-k", "--kill-after"}


def cmd_start(words, extra=()):
    """Индекс слова-программы: пропускает ведущие ( { !, ключевые слова, присваивания, обёртки и их числа/опции."""
    i = 0
    while i < len(words):
        w = words[i]
        if w[:1] in ("(", "{", "!") and w:
            words[i] = w.lstrip("({!")
            if words[i]:
                continue
            i += 1
        elif w in LEAD or w in WRAPPERS or w in extra or re.fullmatch(r"\w+=\S*", w) or (i and w.startswith("-")):
            i += 1
            if w in ("timeout", "gtimeout", "nice"):
                while i < len(words) and (words[i] in VALUED or words[i].startswith("-") or NUM_ARG.fullmatch(words[i])):
                    i += 2 if words[i] in VALUED else 1
        else:
            break
    return i


def first_word(seg):
    w = re.split(r"[<>]", seg, 1)[0].split()  # `bash<<EOF`: программа до перенаправления
    i = cmd_start(w)
    return os.path.basename(w[i].strip("'\"")) if i < len(w) else ""


def runs_text(parts, k):
    """Текст части k уходит процессу: она или команда конвейера после неё — не читатель текста или с <(…), >(…)."""
    while True:
        if first_word(parts[k]) not in TEXT_SINKS or re.search(r"[<>]\(", parts[k]):
            return True
        if parts[k + 1:k + 2] != ["|"]:
            return False
        k += 2


def strip_heredocs(cmd):
    lines, out, i, q = cmd.split("\n"), [], 0, None
    while i < len(lines):
        line = lines[i]
        i += 1
        while not q and re.search(r"(?<!\\)(?:\\\\)*\\$", line) and i < len(lines):
            line, i = line[:-1] + lines[i], i + 1  # перенос `\` — та же команда, тело начинается после неё
        out.append(line)
        if q:  # продолжение строки в кавычках: heredoc здесь не бывает
            q = quote_end(line, q)
            continue
        found = [m for m in HEREDOC.finditer(line) if quote_end(line[:m.start()]) is None]
        q = quote_end(line)
        if not found:
            continue
        parts = split_cmd(line)
        starts = [sum(len(p) for p in parts[:k]) for k in range(len(parts))]
        for m in found:
            # тело читают получатель этого heredoc и команды конвейера после него
            shell = runs_text(parts, max(k for k in range(0, len(parts), 2) if starts[k] <= m.start()))
            body = []
            while i < len(lines) and (lines[i].lstrip("\t") if m.group(1) else lines[i]) != m.group(3):
                body.append(lines[i])
                i += 1
            # маркер без кавычек: оболочка выполняет подстановки в теле
            if shell or (not m.group(2) and re.search(r"\$\(|`", "\n".join(body))):
                out.extend(body)
            if i < len(lines):
                out.append(lines[i])
                i += 1
    return "\n".join(out)


def split_words(seg):
    try:
        return shlex.split(seg)
    except ValueError:
        return seg.split()


def substitution(x):
    return any(t in x for t in ("$(", "`", "<(", ">("))


def strip_patterns(cmd):
    parts = split_cmd(cmd)
    for k in range(0, len(parts), 2):
        w = split_words(parts[k])
        i = cmd_start(w)
        if i >= len(w):
            continue
        prog = os.path.basename(w[i])
        if prog == "git" and w[i + 1:i + 2] == ["grep"]:
            i, prog = i + 1, "grep"
        sed = prog == "sed"
        if not sed and prog not in GREPS or parts[k + 1:k + 2] == ["|"] and runs_text(parts, k + 2):
            continue  # вывод поиска уходит в оболочку: шаблон остаётся на проверку
        # сценарий sed с командами r/w читает и пишет файлы: его не вырезаем
        text = lambda x: not substitution(x) and not (sed and re.search(r"(?:^|[;\n{}\d$/])\s*[rRwW]\s+\S", x))
        e_opts = ("-e", "--expression") if sed else ("-e", "--regexp")
        value_opts = SED_VALUE_OPTS if sed else VALUE_OPTS
        rest, pat, has_e, j = w[i + 1:], None, False, 0
        while j < len(rest):
            a = rest[j]
            if a in e_opts:
                has_e = True
                if j + 1 < len(rest) and text(rest[j + 1]):
                    rest[j + 1] = "PATTERN"
                j += 2
                continue
            if a.startswith(e_opts[1] + "=") or a.startswith("--file="):
                has_e = True
                if a.startswith(e_opts[1] + "=") and text(a):
                    rest[j] = e_opts[1] + "=PATTERN"
            elif a in value_opts:
                has_e = has_e or a in ("-f", "--file")  # шаблоны в файле: все позиционные — пути
                j += 2
                continue
            elif sed and a == "-i" and rest[j + 1:j + 2] == [""]:
                j += 2  # macOS: пустой аргумент после -i — суффикс копии
                continue
            elif not a.startswith("-") and pat is None:
                pat = j
            j += 1
        if pat is not None and not has_e and text(rest[pat]):
            rest[pat] = "PATTERN"
        if rest != w[i + 1:]:  # пересборка только при замене: кавычки shlex ломают <(…) и $(…)
            parts[k] = " ".join(shlex.quote(x) for x in w[:i + 1] + rest)
    return "".join(parts)


def command_text(cmd):
    return strip_patterns(strip_heredocs(cmd))


def substituted(cmd):
    """Тексты внутри $(…), <(…), >(…) и `…`: их выполняет оболочка."""
    out, i = [], 0
    while i < len(cmd):
        if cmd[i] == "`" and "`" in cmd[i + 1:]:
            j = cmd.index("`", i + 1)
            out.append(cmd[i + 1:j])
            i = j + 1
            continue
        if cmd[i] in "$<>" and cmd[i + 1:i + 2] == "(":
            depth, j = 1, i + 2
            while j < len(cmd) and depth:
                depth += {"(": 1, ")": -1}.get(cmd[j], 0)
                j += 1
            out.append(cmd[i + 2:j - 1])
            i = j
            continue
        i += 1
    return out


def codex_launches(cmd, depth=0):
    """Запуски codex exec: отдельное слово codex (вне строки в кавычках) с exec после него, где бы оно ни стояло
    (за обёрткой, в find -exec, xargs); подстановки, eval и строка -c у оболочки разбираются рекурсивно."""
    found = []
    for part in split_cmd(cmd)[::2] + (substituted(cmd) if depth < 3 else []):
        w = split_words(part)
        for k, a in enumerate(w):
            prog = os.path.basename(a.lstrip("({!"))
            if prog == "codex" and (w[k + 1:k + 2] == ["e"] or "exec" in w[k + 1:k + 4]):  # codex -m x exec
                found.append(" ".join(w[k:]))
            elif depth < 3 and (prog == "eval" or prog in ("sh", "bash", "zsh", "dash", "ksh") and any(re.fullmatch(r"-\w*c\w*", x) for x in w[k + 1:k + 3])):
                found += codex_launches(" ".join(w[k + 1:]), depth + 1)
                break
    return found


def guard_models_bash(cmd, raw=None):
    """cmd — команда без текста (command_text), raw — целиком: маркер теста в шаблоне поиска тоже маркер."""
    if owner_override():
        return
    pol = policy()
    is_test = re.search(pol["test_markers"], raw or cmd)
    launches = codex_launches(cmd)
    if launches:
        models = re.findall(r"(?:\s-m|--model)[\s=]+[\"']?([\w.\-]+)|model\s*=\s*[\"']?([\w.\-]+)", " ".join(launches))
        models = [a or b for a, b in models]
        if not models:
            cfg = read_head(os.path.join(HOME, ".codex", "config.toml"), 20000) or ""
            mm = re.search(r'^model\s*=\s*"([^"]+)"', cfg, re.M)
            models = [mm.group(1) if mm else "default"]
        joined = " ".join(models)
        if model_hits(joined, pol["expensive_always"]):
            deny("Codex с моделью %s — самая дорогая. Бери дешёвую (%s). %s" % (joined, ", ".join(pol["cheap"]), OWNER_ONLY))
        if is_test and not model_hits(joined, pol["cheap"]):
            deny("Тест или приёмка на Codex %s. По правилам тесты идут на самых дешёвых моделях: %s. "
                 "Укажи -m явно. %s" % (joined, ", ".join(pol["cheap"]), OWNER_ONLY))
        return
    if is_test:
        flags = " ".join(re.findall(r"(?i)(?:--model|(?<![\w-])-m|\bmodel)[\s=:]+[\"']?([\w.\-]+)", cmd))
        hits = model_hits(flags, pol["expensive"])
        if hits:
            deny("Тест или приёмка с дорогой моделью (%s). Возьми дешёвую: %s. %s" % (", ".join(hits), ", ".join(pol["cheap"]), OWNER_ONLY))


def agent_role(desc):
    d = (desc or "").strip().casefold() + " "  # пробел в конце: «Orchestrator» без хвоста тоже тег
    for role, prefixes in policy()["roles"].items():
        if any(d.startswith(p.casefold()) for p in prefixes):
            return role
    return "general"


def guard_models_agent(ti, from_subagent=False):
    desc = ti.get("description") or ""
    role = agent_role(desc)
    if role == "orchestrator" and from_subagent:
        deny("Оркестраторов запускает только главная сессия, не субагент.")
    if owner_override():
        return
    pol = policy()
    model = ti.get("model")
    if role == "review" and not (model and model_hits(model, pol["cheap"])):
        deny("Субагент приёмки или ревью на модели %s. Укажи model явно, из дешёвых: %s. %s"
             % (model or "inherit", ", ".join(pol["cheap"]), OWNER_ONLY))
    if role in ("general", "implement") and from_subagent and not (model and not model_hits(model, pol["expensive"])):
        deny("Субагент запускает исполнителя на модели %s. Укажи недорогую модель явно (model: sonnet или haiku). %s"
             % (model or "inherit", OWNER_ONLY))


PROFILES = (".zshenv", ".zshrc", ".zprofile", ".bashrc", ".bash_profile", ".profile")


def is_env_config(path):
    base = os.path.basename(path)
    return base in PROFILES or (base in ("settings.json", "settings.local.json")
                                and os.path.basename(os.path.dirname(path)) == ".claude")


def guard_override_write(tool, ti, path):
    if not is_env_config(path):
        return
    texts = [ti.get("content"), ti.get("new_string")] + [e.get("new_string") for e in ti.get("edits") or [] if isinstance(e, dict)]
    if any(OVERRIDE_VAR in t for t in texts if isinstance(t, str)):
        deny("Запись %s в %s отклонена: обход правил моделей включает только владелец, вне сессии агента." % (OVERRIDE_VAR, path))


def guard_override_bash(cmd):
    if OVERRIDE_VAR not in cmd:
        return
    # цель записи: файл сразу после >, >>, tee или в sed -i; чтение того же файла в соседней команде не в счёт
    names = r"[\"']?[^\s;&|]*(?:%s|\.claude/settings(?:\.local)?\.json)" % "|".join(re.escape(n) for n in PROFILES)
    writes = re.search(r"(?:>[>|]?|\btee\b(?:\s+-\w+)*)\s*" + names, cmd) or \
        re.search(r"\bsed\s+[^;&|\n]*-\w*i[^;&|\n]*?\s" + names, cmd)
    if re.search(r"launchctl\s+setenv", cmd) or writes:
        deny("Команда переносит %s в окружение будущих сессий. Обход правил моделей включает только владелец." % OVERRIDE_VAR)


def guard_secrets_bash(cmd, cwd):
    for seg in re.split(r"[;&|\n]+", cmd):
        m = re.match(r"\s*(?:\w+=\S*\s+)*(?:sudo\s+)?(cat|head|tail|less|more|bat|nl|tac|grep|egrep|rg|sed|awk|cut|sort|uniq|strings|xxd|od|base64|jq)\b(.*)", seg)
        if not m or not re.search(r"(?<![\w/.-])" + ENV_FILE, m.group(2)):
            continue
        if m.group(1) in ("grep", "egrep", "rg") and re.search(r"(?:^|\s)-\w*[cqlL]|--count|--quiet|--files-with", m.group(2)):
            continue
        deny("Команда выводит содержимое .env в чат. Секреты не печатай. Проверить наличие ключа можно так: "
             "grep -c '^ИМЯ=.' .env или test -n \"$ИМЯ\".")
    if re.search(r"(?i)\b(echo|printf)\b[^;&|\n]*\$\{?(?!#)" + SECRET_VAR, cmd):
        deny("Команда печатает секретную переменную. Проверь наличие без вывода: test -n \"$ИМЯ\" && echo есть.")
    if re.search(r"(?:^|[;&|(\n]\s*)(printenv|env)[ \t]*(?:$|[;&|)\n])", cmd) or \
            re.search(r"(?i)(?:^|[;&|(\n]\s*)printenv\s+" + SECRET_VAR, cmd):
        deny("Команда выводит переменные окружения целиком или секрет. Запроси конкретную несекретную переменную.")
    for m in re.finditer(r"(?<![>\d])>\s*(" + ENV_FILE + ")", cmd):
        p = os.path.join(cwd, os.path.expanduser(m.group(1)))
        if os.path.exists(p):
            deny("Перезапись %s через > сотрёт ключи пользователя. Дописать пустое поле можно через >>." % m.group(1))
    if re.search(r"\bgit\b[^;&|\n]*\badd\b", cmd):
        add = re.search(r"\badd\b([^;&|\n]*)", cmd).group(1)
        if re.search(r"(?<![\w/.-])" + ENV_FILE, add):
            deny("В git не добавляй .env: там секреты.")
        if re.search(r"(?:^|\s)(-A|--all|\.|-u)(?:\s|$)", add):
            root = git_root(cwd)
            out = sh(["git", "-c", "core.quotepath=off", "status", "--porcelain", "--untracked-files=all"], cwd=root or cwd)
            bad = [l[3:] for l in out.splitlines() if re.fullmatch(ENV_FILE, os.path.basename(l[3:].strip('"')))]
            if bad:
                deny("git add захватит файлы с секретами: %s. Добавь их в .gitignore или добавляй файлы поимённо." % ", ".join(bad))


WT_RULE = ("Рабочая папка проекта одна. Worktree создавай только во временной папке (scratchpad или /tmp) "
           "через git worktree add и удаляй после себя.")
WT_WRAPPERS = ("env", "exec", "command", "nohup", "time", "caffeinate")


def native_worktree_cli(cmd):
    """Запуск claude или codex со встроенным worktree: Claude кладёт копию в .claude/worktrees проекта,
    Codex — в ~/.codex/worktrees. Слова внутри кавычек (текст коммита и т. п.) командой не считаются."""
    for seg in re.split(r"&&|\|\||[;&|\n()]", cmd):
        try:
            words = shlex.split(seg)
        except ValueError:
            words = seg.split()
        i = 0
        while i < len(words) and (re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[i]) or words[i] in WT_WRAPPERS):
            i += 1
        if i >= len(words):
            continue
        prog, args = os.path.basename(words[i]), words[i + 1:]
        if prog == "codex" and any(a == "--worktree" or a.startswith("--worktree=") for a in args):
            return "codex --worktree кладёт копию в ~/.codex/worktrees"
        if prog == "claude" and any(a in ("-w", "--worktree") or a.startswith("--worktree=") for a in args):
            return "claude --worktree кладёт копию в .claude/worktrees внутри проекта"
    return None


def guard_worktree(cmd):
    if re.search(r"\bworktree\s+add\b", cmd) and not re.search(r"/tmp/|/private/tmp/|/var/folders/|\$\{?TMPDIR|scratchpad", cmd):
        deny(WT_RULE)
    why = native_worktree_cli(cmd)
    if why:
        deny("%s. %s Исполнителю передай путь: codex exec -C <worktree>, claude в cd <worktree>." % (why, WT_RULE))


def in_temp(path):
    return nfc(path).startswith(tuple(r + "/" for r in TMP_ROOTS)) or "/scratchpad/" in path


def guard_enter_worktree(cwd, ti):
    path = ti.get("path")
    if path:
        p = nfc(os.path.realpath(os.path.join(cwd, os.path.expanduser(path))))
        inside = any(p == r or p.startswith(r + "/") for r in project_roots(cwd))
        if in_temp(p) and not inside:
            return
    deny("EnterWorktree создаёт копию в .claude/worktrees внутри проекта. %s "
         "Потом войди в неё через EnterWorktree с path." % WT_RULE)


def guard_agent_worktree(ti):
    if ti.get("isolation") == "worktree":
        deny("isolation: worktree кладёт копию субагента в .claude/worktrees внутри проекта. Юниты на один файл "
             "раздели по волнам или создай worktree во временной папке через git worktree add и дай субагенту его путь.")


STATUS_FIELDS = ("STATUS", "CHANGE", "BRANCH", "WORKTREE", "COMMIT", "ARCHIVE", "VALIDATE", "TESTS", "LIVE",
                 "REVIEW", "AGENTS", "HOOKS", "NOT_VERIFIED", "NOTES")
STATUS_VALUES = ("archived", "not_ready", "blocked")


def parse_status(message):
    """Поля блока статуса или None, если в сообщении нет строки, начинающейся с STATUS:."""
    lines = [l.lstrip() for l in message.splitlines()]
    if not any(l.startswith("STATUS:") for l in lines):
        return None
    fields = {}
    for l in lines:
        m = re.match(r"(%s):(.*)" % "|".join(STATUS_FIELDS), l)
        if m:
            fields.setdefault(m.group(1), m.group(2).strip())
    return fields


EXIT_0 = r"(?i)exit\s+0(?:[\s;,)]|$)"


def exit_zero(value):
    """Код после первого « -> » (без стрелки — в начале) — exit 0; пояснения и другие команды после него
    допустимы (`npm test -> exit 0 (250 files); npm run typecheck -> exit 0`), ненулевой exit после стрелки — нет."""
    arrows = [x.strip() for x in re.split(r"\s*->\s*", value)]
    head = arrows[1] if len(arrows) > 1 else value.strip()
    # ненулевой exit где угодно после стрелки: `-> exit 1`, `-> exit: 1`, `build -> failed (exit 1)`
    bad = r"(?i)\bexit\b(?!\s+0(?:[\s;,)]|$))"
    return bool(re.match(EXIT_0, head)) and not any(re.match(bad, a) or re.search(bad + r"\W*[1-9]", a) for a in arrows[1:])


def archived_problems(f, cwd):
    problems = ["нет поля или оно пусто: %s" % n for n in STATUS_FIELDS if not f.get(n)]
    wt = os.path.join(cwd, os.path.expanduser(f["WORKTREE"])) if f.get("WORKTREE") else git_root(cwd)
    if not wt or not os.path.exists(os.path.join(wt, ".git")):
        return problems + ["WORKTREE не рабочая копия git (папки нет или в ней нет .git): %s" % (wt or "корень git для cwd не найден")]
    wt = nfc(os.path.realpath(wt))
    head = git_strict(["git", "rev-parse", "HEAD"], cwd=wt).strip()
    commit = f.get("COMMIT", "")
    if commit and not (re.fullmatch(r"[0-9a-fA-F]{7,}", commit) and head.startswith(commit.lower())):
        problems.append("COMMIT %s не начало последнего коммита HEAD %s (нужно не меньше 7 hex-знаков)" % (commit, head))
    name = f.get("CHANGE", "")
    arch = f.get("ARCHIVE", "")
    if arch:
        a = nfc(os.path.realpath(os.path.join(wt, arch)))
        if not (os.path.isdir(a) and a.startswith(os.path.join(wt, "openspec", "changes", "archive") + "/")):
            problems.append("ARCHIVE %s не существующая папка внутри openspec/changes/archive/ в %s" % (arch, wt))
    if name and os.path.exists(os.path.join(wt, "openspec", "changes", name)):
        problems.append("в %s осталась openspec/changes/%s: change не перенесён в архив" % (wt, name))
    main = main_checkout(wt, run=git_strict)
    if name and os.path.exists(os.path.join(main, "openspec", "changes", name, "CLAIM")):
        problems.append("в основной папке %s остался CLAIM change %s: сними его" % (main, name))
    problems += ["%s: после первого « -> » должно быть «exit 0», и ни одна « -> exit » не с другим кодом; сейчас: %s" % (n, f[n])
                 for n in ("VALIDATE", "TESTS") if f.get(n) and not exit_zero(f[n])]
    return problems


def status_problems(message, cwd):
    """Расхождения статуса оркестратора с git и файлами; пустой список — всё верно или это не статус."""
    f = parse_status(message)
    if f is None:
        return []
    if f.get("STATUS") not in STATUS_VALUES:
        return ["STATUS «%s» не из допустимых: %s" % (f.get("STATUS", ""), ", ".join(STATUS_VALUES))]
    if f["STATUS"] != "archived":
        return ["нет поля или оно пусто: %s" % n for n in ("CHANGE", "NOTES") if not f.get(n)]
    return archived_problems(f, cwd)


def cmd_guard(inp):
    tool, ti = inp.get("tool_name"), inp.get("tool_input") or {}
    sid, cwd = inp.get("session_id", ""), os.path.realpath(inp.get("cwd") or os.getcwd())
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = ti.get("file_path") or ti.get("notebook_path")
        if not path:
            return
        path = os.path.join(cwd, os.path.expanduser(path))
        guard_env_write(tool, path, cwd)
        guard_override_write(tool, ti, path)
        guard_scope(sid, cwd, path)
        guard_claim(sid, path, tool, ti)
    elif tool == "Bash":
        cmd = ti.get("command") or ""
        text = command_text(cmd)
        guard_secrets_bash(text, cwd)
        guard_override_bash(cmd)
        guard_models_bash(text, cmd)
        guard_worktree(cmd)
        guard_archive(sid, cmd, cwd)
        note_claim_cmd(inp, cmd)
    elif tool == "Agent":
        guard_agent_worktree(ti)
        guard_models_agent(ti, bool(inp.get("agent_id")))
    elif tool == "EnterWorktree":
        guard_enter_worktree(cwd, ti)
    elif tool == "SubagentHandback":
        problems = status_problems(ti.get("message") or "", cwd)
        if problems:
            deny("Статус не принят хуком, расхождения:\n- " + "\n- ".join(problems) +
                 "\nЕсли устранить их нельзя, сдай `STATUS: not_ready` с причиной в `NOTES`.")


# ---------- stop: Stop ----------

def scan_transcript(path):
    edited, browser, pushed = set(), False, False
    try:
        f = open(path, "rb")
    except Exception:
        return edited, browser, pushed
    with f:
        for raw in f:
            if b'"tool_use"' not in raw and b"bashEditDiff" not in raw:
                continue
            try:
                d = json.loads(raw)
            except Exception:
                continue
            r = d.get("toolUseResult")
            if isinstance(r, dict) and isinstance(r.get("bashEditDiff"), dict):
                edited.update(r["bashEditDiff"].get("changedFiles") or [])
            if d.get("type") != "assistant":
                continue
            for p in (d.get("message") or {}).get("content") or []:
                if not isinstance(p, dict) or p.get("type") != "tool_use":
                    continue
                name, ti = p.get("name", ""), p.get("input") or {}
                if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
                    fp = ti.get("file_path") or ti.get("notebook_path")
                    if fp:
                        edited.add(fp)
                elif name.startswith(BROWSER_TOOLS):
                    browser = True
                elif name == "Skill" and str(ti.get("skill", "")).split(":")[-1] in BROWSER_SKILLS:
                    browser = True
                elif name == "Bash":
                    c = ti.get("command") or ""
                    browser = browser or bool(BROWSER_BASH.search(c))
                    pushed = pushed or bool(re.search(r"\bgit\b[^;&|\n]*\bpush\b|gh pr create", c))
    return edited, browser, pushed


def last_text(inp):
    if inp.get("last_assistant_message"):
        return inp["last_assistant_message"]
    try:
        with open(inp["transcript_path"], "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 3000000))
            lines = f.read().splitlines()
    except Exception:
        return ""
    for raw in reversed(lines):
        try:
            d = json.loads(raw)
        except Exception:
            continue
        if d.get("type") == "assistant":
            texts = [p.get("text", "") for p in (d.get("message") or {}).get("content") or []
                     if isinstance(p, dict) and p.get("type") == "text"]
            if texts:
                return "\n".join(texts)
    return ""


def not_russian(text):
    t = re.sub(r"```.*?```|`[^`]*`|https?://\S+|(?:~|\.{0,2})?/[\w./-]+", " ", text, flags=re.S)
    cyr, lat = len(re.findall(r"[а-яёА-ЯЁ]", t)), len(re.findall(r"[A-Za-z]", t))
    return cyr + lat >= 80 and cyr / float(cyr + lat) < 0.3


def dirty_paths(root):
    out = sh(["git", "status", "--porcelain", "-z"], cwd=root)
    paths, items, i = set(), out.split("\0"), 0
    while i < len(items):
        e = items[i]
        if len(e) > 3:
            paths.add(nfc(os.path.realpath(os.path.join(root, e[3:]))))
            if e[0] in "RC":
                i += 1
        i += 1
    return paths


def cmd_stop(inp):
    if inp.get("stop_hook_active"):
        return
    if any(isinstance(t, dict) and t.get("status") == "running" for t in inp.get("background_tasks") or []):
        return  # фоновые агенты ещё работают: диспетчер ждёт их, ворота не нужны
    sid, cwd = inp.get("session_id", ""), os.path.realpath(inp.get("cwd") or os.getcwd())
    tp = inp.get("transcript_path") or ""
    edited, browser, pushed = scan_transcript(tp)
    # проверку в браузере засчитываем и субагентам сессии; правки и push берём только из главного транскрипта
    for sub in glob.glob(glob.escape(re.sub(r"\.jsonl$", "", tp)) + "/subagents/agent-*.jsonl") if tp else []:
        browser = browser or scan_transcript(sub)[1]
    edited = {nfc(os.path.realpath(os.path.join(cwd, p))) for p in edited}
    edited = {p for p in edited if "/scratchpad/" not in p}
    reasons = []

    by_root = {}
    for p in edited:
        r = git_root(p)
        if r:
            by_root.setdefault(r, set()).add(p)
    for root, files in sorted(by_root.items()):
        dirty = sorted(files & dirty_paths(root))
        if dirty:
            names = ", ".join(os.path.relpath(p, root) for p in dirty[:5]) + (" …" if len(dirty) > 5 else "")
            reasons.append("В %s остались незакоммиченные правки этой сессии (%d: %s). Закоммить и запушь (/ship) "
                           "или напиши «не готово» и почему." % (root, len(dirty), names))

    for cdir in sorted({m.group(1) for m in (re.match(r"(.*/openspec/changes/(?!archive/)[^/]+)/", p) for p in edited) if m}):
        tasks = read_head(os.path.join(cdir, "tasks.md"), 200000)
        if tasks and os.path.isdir(cdir) and re.search(r"^\s*- \[[xX]\]", tasks, re.M) and not re.search(r"^\s*- \[ \]", tasks, re.M):
            reasons.append("Change %s: все задачи отмечены, но он не в архиве. Пройди verify, sync, archive и сними CLAIM, "
                           "или напиши, чего не хватает." % os.path.basename(cdir))

    root = git_root(cwd)
    if pushed and root:
        pr = sh(["gh", "pr", "view", "--json", "state,url"], cwd=root, timeout=10)
        try:
            pr = json.loads(pr) if pr else {}
        except Exception:
            pr = {}
        if pr.get("state") == "OPEN":
            reasons.append("PR %s открыт и не смёрджен. Смёрджи и обнови основную ветку (/ship), если мёрдж не запускает "
                           "прод-деплой. Если запускает — спроси пользователя." % pr.get("url"))

    ui = sorted(p for p in edited if p.endswith(UI_EXT) and not re.search(r"\.(test|spec)\.", p))
    if ui and not browser:
        reasons.append("Изменён интерфейс (%s), но в сессии не было проверки в браузере. Проверь на десктопе и телефоне "
                       "(/ui-check) или напиши, почему проверка невозможна." % ", ".join(os.path.basename(p) for p in ui[:4]))

    text = last_text(inp)
    if not_russian(text):
        reasons.append("Итоговый ответ не на русском. Перепиши его по-русски.")

    if not reasons:
        return
    key = hashlib.sha1(("\n".join(reasons) + (text if reasons[-1].startswith("Итоговый") else "")).encode()).hexdigest()
    st = load_state(sid)
    if st.get("stop_key") == key:
        return
    st["stop_key"] = key
    save_state(sid, st)
    emit({"decision": "block", "reason": "Ворота готовности (хук Stop):\n- " + "\n- ".join(reasons) +
          "\nЕсли пункт сознательно не делается, скажи это в ответе одной строкой. С тем же набором пунктов хук повторно не сработает."})


# ---------- beat / end / status ----------

def cmd_beat(inp):
    sid, ev = inp.get("session_id", ""), inp.get("hook_event_name", "")
    st = load_state(sid)
    now = time.time()
    st["cwd"] = inp.get("cwd") or st.get("cwd")
    if ev == "PreToolUse":
        ti, tool = inp.get("tool_input") or {}, inp.get("tool_name", "")
        detail = ti.get("description") or ti.get("command") or ti.get("file_path") or ti.get("skill") or ti.get("prompt") or ""
        if ti.get("file_path"):
            detail = os.path.basename(ti["file_path"])
        st.update(phase="run", tool=tool, detail=re.sub(r"\s+", " ", str(detail))[:60], since=now)
    elif ev == "PostToolUse":
        st.update(phase="done", since=now)
    elif ev == "SubagentStart" and inp.get("agent_id"):
        st.setdefault("subagents", {})[inp["agent_id"]] = inp.get("agent_type", "")
    elif ev == "SubagentStop":
        st.setdefault("subagents", {}).pop(inp.get("agent_id", ""), None)
    elif ev == "UserPromptSubmit":
        st.update(phase="think", since=now)
    elif ev == "Stop":
        st.update(phase="idle", since=now)
    save_state(sid, st)


def cmd_end(inp):
    sid = inp.get("session_id", "")
    st = load_state(sid)
    for claim in st.get("claims", []) + [l for l in claim_log(sid) if l.startswith("/")]:
        body = read_head(claim, 300) or ""
        if sid and sid in body:
            os.remove(claim)
    for p in (state_path(sid), state_path(sid, "claims"), state_path(sid, "cmds")):
        if os.path.exists(p):
            os.remove(p)
    for n in os.listdir(STATE):
        p = os.path.join(STATE, n)
        if n.endswith((".json", ".claims", ".cmds")) and time.time() - os.path.getmtime(p) > 7 * 86400:
            os.remove(p)


def fmt_age(sec):
    sec = int(sec)
    return "%dс" % sec if sec < 60 else "%dм%02dс" % (sec // 60, sec % 60) if sec < 3600 else "%dч%02dм" % (sec // 3600, sec % 3600 // 60)


def cmd_status(inp):
    st = load_state(inp.get("session_id", ""))
    model = (inp.get("model") or {}).get("display_name", "")
    folder = os.path.basename((inp.get("workspace") or {}).get("current_dir") or inp.get("cwd") or "")
    age = fmt_age(time.time() - st.get("since", time.time()))
    phase = st.get("phase")
    if phase == "run":
        now = "▶ %s: %s · %s" % (st.get("tool"), st.get("detail"), age)
    elif phase == "done":
        now = "✓ последнее действие %s назад: %s" % (age, st.get("tool"))
    elif phase == "think":
        now = "… думает %s" % age
    elif phase == "idle":
        now = "⏸ ждёт вас %s" % age
    else:
        now = ""
    subs = len(st.get("subagents") or {})
    print(" · ".join(x for x in (model, folder, now, ("субагентов: %d" % subs) if subs else "") if x))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        inp = json.load(sys.stdin)
        {"context": cmd_context, "subagent-context": cmd_subagent_context, "guard": cmd_guard, "stop": cmd_stop, "beat": cmd_beat,
         "end": cmd_end, "status": cmd_status, "claims": cmd_claims}[cmd](inp)
    except SystemExit:
        raise
    except Exception as e:
        try:
            os.makedirs(STATE, exist_ok=True)
            with open(os.path.join(STATE, "errors.log"), "a") as f:
                f.write("%s %s %r\n" % (datetime.datetime.now().isoformat(timespec="seconds"), cmd, e))
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
