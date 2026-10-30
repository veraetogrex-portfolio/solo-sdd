#!/usr/bin/python3
"""Дополнительная защита от случайной остановки чужих процессов в Claude Code."""
import json
import os
import re
import shlex
import sys

FORBIDDEN = re.compile(r"(?<![\w-])(?:pkill|killall|kill|osascript|launchctl|shutdown)(?![\w-])")
REASON = (
    "Управление процессами через shell запрещено. Используй штатную остановку задачи "
    "по её идентификатору; после таймаута сначала проверь состояние задачи. "
    "Произвольный kill, даже по числовому PID, не разрешён."
)


# Копия блока из work_hooks.py (скрипт раскладывается отдельно): правь оба места.
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


def forbidden(command):
    # shortcut: тела heredoc для оболочек проверяются как текст; вычисляемые имена и скрипты в файлах не анализируются.
    try:
        text = strip_patterns(strip_heredocs(command))
    except Exception:
        text = command  # не разобрали — проверяем всё как раньше
    normalized = text.replace("\\\n", "")
    normalized = re.sub(r"\\(.)", r"\1", normalized)
    normalized = normalized.replace("'", "").replace('"', "")
    return bool(FORBIDDEN.search(normalized))


def main():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict) or not isinstance(data.get("tool_name"), str):
            raise ValueError("invalid event")
        if data["tool_name"] not in ("Bash", "Monitor"):
            return 0
        command = data["tool_input"]["command"]
        if not isinstance(command, str) or not command.strip():
            raise ValueError("invalid command")
        if forbidden(command):
            print(REASON, file=sys.stderr)
            return 2
        return 0
    except (ValueError, KeyError, TypeError):
        print("Запуск запрещён: защитный хук получил некорректное событие.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
