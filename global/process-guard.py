#!/usr/bin/python3
"""Extra protection against accidentally stopping other processes in Claude Code."""
import json
import os
import re
import shlex
import sys

# a name followed by `.` or `/` is part of a file name (docs/kill.md, src/shutdown/x.py), not a program
FORBIDDEN = re.compile(r"(?<![\w-])(?:pkill|killall|kill|osascript|launchctl|shutdown)(?![\w./-])")
REASON = (
    "Process control through the shell is forbidden. Stop the task with the built-in stop "
    "by its id; after a timeout, check the task state first. "
    "An arbitrary kill, even by a numeric PID, is not allowed."
)


# A copy of a block of global/work_hooks.py (this script is deployed alone): edit it there, then run
# python3 scripts/sync_blocks.py.
# shell:begin
# a heredoc body is text only if one of these programs reads it; any other receiver (shell, wrapper) means commands
TEXT_SINKS = {"cat", "tee", "head", "tail", "wc", "sort", "uniq", "grep", "egrep", "rg", "jq", "cut", "tr", "nl",
              "column", "fold", "fmt", "paste", "rev", "tac", "comm", "diff", "less", "more", "base64", "od", "xxd",
              "shasum", "md5", "python", "python3", "node"}
WRAPPERS = {"sudo", "env", "command", "exec", "nohup", "time", "timeout", "gtimeout", "nice", "caffeinate", "npx"}
GREPS = {"grep", "egrep", "rg", "ag"}
VALUE_OPTS = {"-A", "-B", "-C", "-m", "-g", "-t", "-f", "--file", "--include", "--exclude", "--glob", "--type", "--pre"}
SED_VALUE_OPTS = {"-f", "--file", "-l", "--line-length"}
HEREDOC = re.compile(r"(?<![<\\])<<(?!<)(-?)\s*([\"']?)([A-Za-z_]\w*)\2")


def split_cmd(text):
    """Splits a command into parts on ; && || | & and newline outside quotes: [part, separator, part, ...]."""
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
    """Open quote at the end of the text (None, ' or \")."""
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
    """Index of the program word: skips leading ( { !, keywords, assignments, wrappers and their numbers/options."""
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
    w = re.split(r"[<>]", seg, 1)[0].split()  # `bash<<EOF`: the program is before the redirection
    i = cmd_start(w)
    return os.path.basename(w[i].strip("'\"")) if i < len(w) else ""


def runs_text(parts, k):
    """Text of part k goes to a process: it, or the pipeline command after it, is not a text reader, or has <(…), >(…)."""
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
            line, i = line[:-1] + lines[i], i + 1  # a `\` continuation is the same command, the body starts after it
        out.append(line)
        if q:  # continuation of a quoted line: no heredoc here
            q = quote_end(line, q)
            continue
        found = [m for m in HEREDOC.finditer(line) if quote_end(line[:m.start()]) is None]
        q = quote_end(line)
        if not found:
            continue
        parts = split_cmd(line)
        starts = [sum(len(p) for p in parts[:k]) for k in range(len(parts))]
        for m in found:
            # the body is read by the receiver of this heredoc and the pipeline commands after it
            shell = runs_text(parts, max(k for k in range(0, len(parts), 2) if starts[k] <= m.start()))
            body = []
            while i < len(lines) and (lines[i].lstrip("\t") if m.group(1) else lines[i]) != m.group(3):
                body.append(lines[i])
                i += 1
            # unquoted marker: the shell performs substitutions in the body
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


GIT_GLOBAL_VALUED = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
MESSAGE_OPTS = {"git": ("commit", "tag"), "gh": ("pr", "issue")}


def git_sub(w, i):
    """Index of the git subcommand after the program word i, past the global options."""
    j = i + 1
    while j < len(w) and w[j].startswith("-"):
        j += 2 if w[j] in GIT_GLOBAL_VALUED else 1
    return j


def strip_message(w, i):
    """Replaces in place the message values of git commit/tag (-m, --message) and gh pr/issue (-t, --title, -b, --body):
    text for a person, not a command. A value with a substitution stays. True if anything was replaced."""
    prog = os.path.basename(w[i])
    j = git_sub(w, i) if prog == "git" else i + 1
    if prog not in MESSAGE_OPTS or w[j:j + 1] == [] or w[j] not in MESSAGE_OPTS[prog]:
        return False
    short, longs = ("m", ("--message",)) if prog == "git" else ("tb", ("--title", "--body"))
    text, hit, j = lambda x: not substitution(x), False, j + 1
    while j < len(w):
        a = w[j]
        if a == "--":
            break
        long_eq = next((o for o in longs if a.startswith(o + "=")), None)
        if a in longs or re.fullmatch(r"-[A-Za-z]*[%s]" % short, a) and (prog == "git" or len(a) == 2):
            if j + 1 < len(w) and text(w[j + 1]):
                w[j + 1], hit = "MESSAGE", True
            j += 2
            continue
        if long_eq and text(a):
            w[j], hit = long_eq + "=MESSAGE", True
        elif re.fullmatch(r"-[%s].+" % short, a) and text(a):
            w[j], hit = a[:2] + "MESSAGE", True
        j += 1
    return hit


# $'…', a word starting with # and any ${ other than a plain parameter expansion (${NAME}, ${NAME:-/tmp}, ${#NAME}:
# only the characters of this allowlist up to the first }) are read by the shell differently from this parser and shlex:
# anywhere on the line they can move quote boundaries, so nothing is cut; zsh runs the command inside =(…) (process
# substitution into a file), which this parser does not read, so =( anywhere, an array assignment A=(x) included, cuts nothing
UNCUT = re.compile(r"\$'|=\(|\$\{(?![A-Za-z0-9_#:=+?%/.@*!,^~-]*\})|(?:^|[\s;&|()])#")


def strip_patterns(cmd):
    if UNCUT.search(cmd):
        return cmd
    parts = split_cmd(cmd)
    for k in range(0, len(parts), 2):
        w = split_words(parts[k])
        i = cmd_start(w)
        if i >= len(w):
            continue
        prog = os.path.basename(w[i])
        if strip_message(w, i):
            parts[k] = " ".join(shlex.quote(x) for x in w)
            continue
        if prog == "git" and w[i + 1:i + 2] == ["grep"]:
            i, prog = i + 1, "grep"
        sed = prog == "sed"
        if not sed and prog not in GREPS or parts[k + 1:k + 2] == ["|"] and runs_text(parts, k + 2):
            continue  # search output goes to the shell: the pattern stays for checking
        # a sed script with r/w commands reads and writes files: do not cut it
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
                has_e = has_e or a in ("-f", "--file")  # patterns in a file: all positionals are paths
                j += 2
                continue
            elif sed and a == "-i" and rest[j + 1:j + 2] == [""]:
                j += 2  # macOS: an empty argument after -i is the backup suffix
                continue
            elif not a.startswith("-") and pat is None:
                pat = j
            j += 1
        if pat is not None and not has_e and text(rest[pat]):
            rest[pat] = "PATTERN"
        if rest != w[i + 1:]:  # rebuild only on replacement: shlex quoting breaks <(…) and $(…)
            parts[k] = " ".join(shlex.quote(x) for x in w[:i + 1] + rest)
    return "".join(parts)
# shell:end


def forbidden(command):
    # shortcut: heredoc bodies for shells are checked as text; computed names and scripts in files are not analysed.
    try:
        text = strip_patterns(strip_heredocs(command))
    except Exception:
        text = command  # not parsed: check everything as before
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
        print("Run forbidden: the guard hook got a malformed event.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
