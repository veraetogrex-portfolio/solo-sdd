#!/usr/bin/env python3
"""Stand of the change action-first-project-repo: an analysis opens with its actions and delivers its data as a file,
and a request that names a project is worked in that project's repository.

  prepare                                 a fresh `/tmp/action-first.*` folder with the fixtures and prompts; prints
                                          `catalog:`, `empty:`, `broken:`, `analysis:`, `empty-prompt:`,
                                          `broken-prompt:`, `steps-prompt:`, `form-prompt:`, `home:`, `session:` and `repo:`; refuses
                                          before writing anything when `~/Code` holds a `zz-greeter-bot` or
                                          `zz-greeter-bot-old` folder within 3 levels
  clean <folder>                          remove a folder `prepare` made (it holds the marker), refuse any other
  --grade-analysis <answer> <project>     `actions first`, `effect named`, `file linked`, `only analysis file`
  --grade-goal <answer>                   `goal first`
  --grade-failure <answer>                `failure named`
  --grade-form <answer>                   `form kept`
  --grade-repo <home> <session> <reply>   the eight lines of the project-repo rule
  --grade-experiment <home> <session> <reply>  the same and `worktree named` (the reply names a `wt-` folder right
                                          in `/tmp` or `$TMPDIR`)
  selftest                                every reference and hostile-input check of Live Scenario step 5; the last
                                          line is `<n> of <m> checks passed`

Lines are graded after `*`, backquotes, a leading heading, quote or list marker are stripped and whitespace collapsed;
a list item is a raw line starting with `-`, `*` or `<n>.` and a space; empty lines are not counted; leading `Goal:` and
`Check:` lines are skipped unless the grade names them. An empty, truncated (inside an open code fence), non-UTF-8 or
over 1 MB answer, a missing file and a wrong argument exit 1. The graders read the trees without following links, at most
1 MB per file and 1,000 entries, and run git with the fsmonitor and hooks off. The answers come from Claude Code
subagents of the lead session, never `claude -p`."""
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
REFS = REPO / "tests/stands/action-first"
PREFIX = "action-first."
MARK = ".action-first-stand"
NAMES = ("zz-greeter-bot", "zz-greeter-bot-old")
GREETING = 'from zz-greeter-bot"'
MB = 1 << 20
GIT = ["git", "-c", "user.name=stand", "-c", "user.email=stand@example.com", "-c", "init.defaultBranch=main",
       "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", "-c", "core.fsmonitor=", "-c",
       "core.hooksPath=/dev/null"]
NO_ACTION = "no action follows:"
FAILURE = re.compile(r"\b(?:error|cannot|can't|could not|couldn't|unable|fail(?:s|ed|ure)?|unreadable|corrupt\w*|"
                     r"invalid|not a (?:valid )?(?:sqlite )?database)\b", re.I)
ITEM = re.compile(r"(?:[-*]|\d+\.)\s")
FENCE = re.compile(r"\s*(?:```|~~~)")
REQUEST = "analyse the catalog in catalog.db and tell me what to work on"
STEPS = "count the rows of catalog.db and list the five oldest items"
REPO_REQUEST = "fix the greeting typo in the zz greeter bot"
EXPERIMENT = "; try the fix in a copy of the project first, then apply it and tell me where the copy was"
FORM = "how many rows does catalog.db hold and what stands out? The first line of your answer is `rows: <n>`, nothing before it"


def fail(msg):
    sys.exit("action-first: " + msg)


def git(cwd, *args):
    p = subprocess.run(GIT + ["-C", str(cwd), "--no-optional-locks"] + list(args), capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=60)
    return p.stdout if p.returncode == 0 else None


def code_hits(home):
    """The `zz-greeter-bot*` stand folders within 3 levels of `<home>/Code`, dot folders and node_modules skipped."""
    hits, level = [], [pathlib.Path(home) / "Code"]
    for _ in range(3):
        nxt = []
        for d in level:
            try:
                entries = list(os.scandir(d))
            except OSError:
                continue
            for e in entries:
                if e.is_dir(follow_symlinks=False) and not e.name.startswith(".") and e.name != "node_modules":
                    (hits if e.name in NAMES else nxt).append(pathlib.Path(e.path))
        level = nxt
    return hits


def read_head(path):
    """At most 1 MB of a regular file, never through a link; None when it cannot be read."""
    try:
        if path.is_symlink() or not path.is_file():
            return None
        with open(path, "rb") as f:
            return f.read(MB)
    except OSError:
        return None


# ---------------------------------------------------------------- prepare and clean

def project(folder, rows):
    folder.mkdir()
    (folder / "AGENTS.md").write_text("# Catalog\n\nThe catalog lives in `catalog.db` (SQLite, table `items`).\n",
                                      encoding="utf-8")
    if rows is None:
        (folder / "catalog.db").write_text("this is a note about the catalog, not a database\n", encoding="utf-8")
    else:
        db = sqlite3.connect(folder / "catalog.db")
        db.execute("create table items (name text, price real, users integer, updated text)")
        db.executemany("insert into items values (?, ?, ?, ?)", rows)
        db.commit()
        db.close()
    git(folder, "init", "-q")
    git(folder, "add", "-A")
    git(folder, "commit", "-q", "-m", "catalog")


def items():
    words = ("Atlas", "Beacon", "Cinder", "Delta", "Ember", "Fjord", "Garnet", "Harbor", "Iris", "Juniper")
    return [("%s %d" % (words[i % 10], i // 10 + 1), round(3 + (i * 7) % 40 + 0.99, 2), (i * 37) % 500,
             "202%d-%02d-%02d" % (4 + i % 3, 1 + i % 12, 1 + (i * 5) % 28)) for i in range(30)]


def greeter(folder, rules):
    folder.mkdir(parents=True)
    if rules:
        (folder / "AGENTS.md").write_text("# zz-greeter-bot\n\nEvery commit message starts with `greeter:`.\n",
                                          encoding="utf-8")
    (folder / "bot.py").write_text('GREETING = "Helo from zz-greeter-bot"\n\nprint(GREETING)\n', encoding="utf-8")
    git(folder, "init", "-q")
    git(folder, "add", "-A")
    git(folder, "commit", "-q", "-m", "greeter: first version")


def prepare():
    hits = code_hits(pathlib.Path.home())
    if hits:
        fail("refusing: %s already exists" % ", ".join(map(str, hits)))
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=PREFIX, dir="/tmp"))
    try:
        (tmp / MARK).write_text("action-first stand\n", encoding="utf-8")
        project(tmp / "catalog", items())
        project(tmp / "empty", [])
        project(tmp / "broken", None)
        rules = (REPO / "global/AGENTS.md").read_text(encoding="utf-8")
        rules = "The global rules of this computer:\n\n" + rules + "\n\n"
        bound = "Your current folder is `%s`; read nothing outside it but the paths this prompt names.\n\n"
        for name, folder, text in (("analysis", "catalog", REQUEST), ("empty-prompt", "empty", REQUEST),
                                   ("broken-prompt", "broken", REQUEST), ("steps-prompt", "catalog", STEPS),
                                   ("form-prompt", "catalog", FORM)):
            (tmp / (name + ".md")).write_text(rules + bound % (tmp / folder) + "The user's message: " + text + "\n",
                                              encoding="utf-8")
        for suffix, request in (("", REPO_REQUEST), ("-exp", REPO_REQUEST + EXPERIMENT)):
            home, session = tmp / ("home" + suffix), tmp / ("session" + suffix)
            greeter(home / "Code/x/zz-greeter-bot", True)
            greeter(home / "Code/zz-greeter-bot-old", False)
            session.mkdir()
            (tmp / ("repo%s.md" % suffix)).write_text(
                rules + "For this task `~` is `%s` and your current folder is `%s`; read nothing outside `%s` but the "
                "paths this prompt names.\n\nThe user's message: %s\n" % (home, session, home, request),
                encoding="utf-8")
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    for name in ("catalog", "empty", "broken"):
        print("%s: %s" % (name, tmp / name))
    for name in ("analysis", "empty-prompt", "broken-prompt", "steps-prompt", "form-prompt"):
        print("%s: %s" % (name, tmp / (name + ".md")))
    for suffix in ("", "-exp"):
        print("home%s: %s" % (suffix, tmp / ("home" + suffix)))
        print("session%s: %s" % (suffix, tmp / ("session" + suffix)))
        print("repo%s: %s" % (suffix, tmp / ("repo%s.md" % suffix)))


def clean(folder):
    p = pathlib.Path(folder)
    real = p.resolve()
    if p.is_symlink() or not (p / MARK).is_file() or not real.name.startswith(PREFIX) \
            or real.parent != pathlib.Path("/tmp").resolve():
        fail("%s is not a folder prepare made" % folder)
    shutil.rmtree(p)
    print("removed %s" % p)


# ---------------------------------------------------------------- graders

def read_answer(path):
    try:
        with open(path, "rb") as f:
            data = f.read(MB + 1)
    except OSError as e:
        fail("cannot read %s: %s" % (path, e))
    if len(data) > MB:
        fail("%s is over 1 MB" % path)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        fail("%s is not UTF-8" % path)
    if not text.strip():
        fail("%s is empty" % path)
    if sum(1 for line in text.splitlines() if FENCE.match(line)) % 2:
        fail("%s ends inside an open code fence" % path)
    return text


def norm(line):
    line = line.replace("*", "").replace("`", "")
    line = re.sub(r"^\s*(?:>\s*)*(?:#+\s+)?(?:(?:[-+]|\d+[.)])\s+)?", "", line)
    return " ".join(line.split())


def lines_of(text, skip_goal=True):
    """[(raw, normalised)] of the non-empty lines, the leading `Goal:` and `Check:` lines skipped."""
    out = [(raw, norm(raw)) for raw in text.splitlines() if raw.strip()]
    for label in ("goal:", "check:"):
        if skip_goal and out and out[0][1].casefold().startswith(label):
            out = out[1:]
    return out


def actions(lines):
    """('none', [line]) for a `No action follows:` line in the window, ('items', [items]) for the first run of
    top-level list items starting in the window (sub-lines indented under an item do not break it), ('past', [items])
    when that run goes on past the window, else (None, [])."""
    window = lines[:5]
    for _, flat in window:
        if flat.casefold().startswith(NO_ACTION):
            return "none", [flat]
    for i, (raw, _) in enumerate(window):
        if ITEM.match(raw):
            run, last = [], i
            for j, (raw2, flat2) in enumerate(lines[i:], i):
                if ITEM.match(raw2):
                    run.append(flat2)
                    last = j
                elif not raw2[:1].isspace():
                    break
            return ("items" if last < 5 else "past"), run
    return None, []


def candidates(raw):
    for token in raw.split():
        if "](" in token:
            token = token.rsplit("](", 1)[1]
        token = token.strip("`*()[]<>\"',;:").rstrip(".!?")
        if token.startswith("file://"):
            token = token[len("file://"):]
        if token.endswith((".md", ".csv")):
            yield token


def linked_file(lines, project, acts):
    root = pathlib.Path(os.path.realpath(project))
    for raw, _ in lines[:5]:
        for cand in candidates(raw):
            path = pathlib.Path(cand)
            real = pathlib.Path(os.path.realpath(path if path.is_absolute() else root / path))
            if root not in real.parents or not real.is_file():
                continue
            try:
                with open(real, "rb") as f:
                    body = norm(f.read(MB).decode("utf-8", "replace").replace("\n", " "))
            except OSError:
                continue
            if acts and all(a in body for a in acts):
                return real.relative_to(root).as_posix()
    return None


def yes(ok):
    return "yes" if ok else "no"


def grade_analysis(answer, proj):
    if not pathlib.Path(proj).is_dir():
        fail("%s is not a folder" % proj)
    lines = lines_of(read_answer(answer))
    kind, acts = actions(lines)
    first = kind == "none" or (kind == "items" and 1 <= len(acts) <= 3)
    effect = first and (kind == "none" or all(" — " in a and a.split(" — ", 1)[1].strip() for a in acts))
    rel = linked_file(lines, proj, acts) if first else None
    only = False
    if rel:
        status = git(proj, "status", "--porcelain", "--untracked-files=all")
        if status is not None and status.strip():
            only = [l[:2] + l[3:].strip('"') for l in status.splitlines()] == ["??" + rel] and commits(proj) == 1
        elif status is not None:
            count = git(proj, "rev-list", "--count", "HEAD")
            names = git(proj, "show", "--name-only", "--format=", "HEAD")
            only = count is not None and count.strip() == "2" and names is not None and names.split() == [rel]
    print("actions first: %s" % yes(first))
    print("effect named: %s" % yes(effect))
    print("file linked: %s" % yes(rel))
    print("only analysis file: %s" % yes(only))


def grade_goal(answer):
    lines = lines_of(read_answer(answer), skip_goal=False)
    ok = len(lines) >= 3 and lines[0][1].casefold().startswith("goal:") and lines[1][1].casefold().startswith(
        "check:") and (ITEM.match(lines[2][0]) is not None or lines[2][1].casefold().startswith(NO_ACTION))
    print("goal first: %s" % yes(ok))


def grade_failure(answer):
    text = read_answer(answer)
    named = any("catalog.db" in flat and FAILURE.search(flat) for _, flat in lines_of(text)[:5])
    hidden = any(flat.casefold().startswith(NO_ACTION) for _, flat in lines_of(text, skip_goal=False))
    print("failure named: %s" % yes(named and not hidden))


def grade_form(answer):
    lines = lines_of(read_answer(answer), skip_goal=False)
    print("form kept: %s" % yes(lines[0][1].casefold().startswith("rows:")))


def copy_in(session):
    """True when a file under `session` is named `bot.py` or holds the greeting in its first 1 MB; links are not
    followed and at most 1,000 entries are read."""
    seen, stack = 0, [pathlib.Path(session)]
    while stack and seen < 1000:
        try:
            entries = list(os.scandir(stack.pop()))
        except OSError:
            continue
        for e in entries:
            seen += 1
            if seen > 1000:
                break
            if e.name == "bot.py":
                return True
            if e.is_dir(follow_symlinks=False):
                stack.append(pathlib.Path(e.path))
            elif e.is_file(follow_symlinks=False):
                head = read_head(pathlib.Path(e.path))
                if head and GREETING.encode() in head:
                    return True
    return False


def commits(folder):
    out = git(folder, "rev-list", "--count", "HEAD")
    return int(out) if out and out.strip().isdigit() else 0


def clean_status(folder):
    out = git(folder, "status", "--porcelain", "--untracked-files=all")
    return out is not None and not out.strip()


def grade_repo(home, session, reply, experiment=False):
    text = read_answer(reply)
    for p in (home, session):
        if not pathlib.Path(p).is_dir():
            fail("%s is not a folder" % p)
    proj, old = pathlib.Path(home) / "Code/x/zz-greeter-bot", pathlib.Path(home) / "Code/zz-greeter-bot-old"
    bot = read_head(proj / "bot.py") or b""
    two = clean_status(proj) and commits(proj) == 2
    message = git(proj, "log", "-1", "--format=%s") or ""
    print("edit in project: %s" % yes(b'"Hello from zz-greeter-bot"' in bot))
    print("other untouched: %s" % yes(commits(old) == 1 and clean_status(old)))
    print("others named: %s" % yes("zz-greeter-bot-old" in text))
    print("no copy in session: %s" % yes(not copy_in(session)))
    print("committed: %s" % yes(two))
    print("project rules: %s" % yes(two and message.startswith("greeter:")))
    print("real Code untouched: %s" % yes(not code_hits(pathlib.Path.home())))
    trees = git(proj, "worktree", "list", "--porcelain")
    print("no worktree left: %s" % yes(trees is not None and trees.count("worktree ") == 1))
    if experiment:
        tmpdirs = {os.path.realpath(d) for d in ("/tmp", os.environ.get("TMPDIR") or "/tmp")}
        named = re.findall(r"(/[^\s`'\"()]*?)/wt-[^\s`'\"()/]+", text)
        print("worktree named: %s" % yes(any(os.path.realpath(d) in tmpdirs for d in named)))


# ---------------------------------------------------------------- selftest

def selftest():
    me = [sys.executable, str(pathlib.Path(__file__).resolve())]
    results = []

    def run(*args, env=None):
        p = subprocess.run(me + [str(a) for a in args], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                           timeout=120, env=env)
        return p.returncode, p.stdout.splitlines()

    def check(name, ok):
        results.append(ok)
        print("%s %s" % ("ok  " if ok else "FAIL", name))

    def grades(name, args, want):
        code, out = run(*args)
        check("%s -> %s" % (name, ", ".join(want)), code == 0 and all(w in out for w in want))

    def refused(name, args):
        code, _ = run(*args)
        check("%s -> exit 1" % name, code == 1)

    before = set(pathlib.Path("/tmp").glob(PREFIX + "*"))
    code, out = run("prepare")
    paths = dict(line.split(": ", 1) for line in out if ": " in line)
    if code != 0 or "catalog" not in paths:
        check("prepare", False)
        print("0 of 1 checks passed")
        return 1
    tmp = pathlib.Path(paths["catalog"]).parent
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="action-first-self."))
    try:
        catalog, home, session = pathlib.Path(paths["catalog"]), pathlib.Path(paths["home"]), pathlib.Path(paths["session"])
        shutil.copy(REFS / "expected-analysis.md", catalog / "catalog-analysis.md")
        grades("expected-analysis.md", ["--grade-analysis", REFS / "expected-analysis.md", catalog],
               ["actions first: yes", "effect named: yes", "file linked: yes", "only analysis file: yes"])
        grades("wrong-analysis.md", ["--grade-analysis", REFS / "wrong-analysis.md", catalog],
               ["actions first: no", "file linked: no"])
        for ref, want in (("list-zero.md", "no"), ("list-four.md", "no"), ("heading-first.md", "yes"),
                          ("sub-bullet.md", "yes")):
            grades(ref, ["--grade-analysis", REFS / ref, catalog], ["actions first: %s" % want])
        outside = tmp / "outside.md"
        outside.write_text("- Raise the price of the five most used items — about +$1,200 a month\n",
                           encoding="utf-8")
        os.symlink(outside, catalog / "link.md")
        hostile = scratch / "hostile.md"
        hostile.write_text((REFS / "hostile-path.md").read_text(encoding="utf-8").replace("{outside}", str(outside)),
                           encoding="utf-8")
        grades("hostile-path.md (../, absolute, link out)", ["--grade-analysis", hostile, catalog],
               ["actions first: yes", "file linked: no"])
        (scratch / "empty.md").write_text("\n  \n", encoding="utf-8")
        (scratch / "truncated.md").write_text("- Do it — gain\n\n```\nrows\n", encoding="utf-8")
        (scratch / "latin1.md").write_bytes(b"- Caf\xe9 - gain\n")
        for name in ("empty.md", "truncated.md", "latin1.md"):
            refused("%s answer" % name, ["--grade-analysis", scratch / name, catalog])
        (scratch / "big.md").write_text("- A — e\n" + "x" * MB + "\n", encoding="utf-8")
        refused("an answer over 1 MB", ["--grade-analysis", scratch / "big.md", catalog])
        refused("missing answer", ["--grade-analysis", scratch / "none.md", catalog])
        refused("wrong argument", ["--grade-analysis", REFS / "expected-analysis.md"])
        (scratch / "run.md").write_text("*`" * 51200 + "\n", encoding="utf-8")
        start = time.monotonic()
        code, out = run("--grade-analysis", scratch / "run.md", catalog)
        check("100 KB of unclosed * and backquotes graded within 1 s",
              code == 0 and "actions first: no" in out and time.monotonic() - start < 1)
        for name, text, args, want in (
                ("five lines, the third action on line 6", "See [data](catalog-analysis.md)\nThe catalog.\nIn short.\n"
                 "- A — e1\n- B — e2\n- C — e3\n", ["--grade-analysis"], "actions first: no"),
                ("a trailing full stop after the file", "- Raise the price of the 5 most used items under $10 — about "
                 "+$1,200 a month at today's users\n\nData: catalog-analysis.md.\n", ["--grade-analysis"],
                 "file linked: yes"),
                ("a ./ link to the file", "- Raise the price of the 5 most used items under $10 — about "
                 "+$1,200 a month at today's users\n\nData: [file](./catalog-analysis.md)\n", ["--grade-analysis"],
                 "file linked: yes"),
                ("a lone Check: line skipped", "Check: 30 rows\n- A — e1\n", ["--grade-analysis"], "actions first: yes"),
                ("Goal, Check, a heading, then actions", "Goal: x\nCheck: 1\n## Actions\n- A — e1\n", ["--grade-goal"],
                 "goal first: no"),
                ("Goal, Check, then actions", "Goal: x\nCheck: 1\n- A — e1\n", ["--grade-goal"], "goal first: yes"),
                ("catalog.db named with its error", "catalog.db cannot be read: file is not a database\n",
                 ["--grade-failure"], "failure named: yes"),
                ("catalog.db named without an error", "catalog.db looks fine.\n- Grow — more users\n",
                 ["--grade-failure"], "failure named: no"),
                ("a failure hidden as No action follows:", "catalog.db: error, not a database\nNo action follows: no data\n",
                 ["--grade-failure"], "failure named: no"),
                ("the prescribed first line", "rows: 30\n- Grow — more users\n", ["--grade-form"], "form kept: yes"),
                ("actions before the prescribed line", "- Grow — more users\nrows: 30\n", ["--grade-form"],
                 "form kept: no")):
            answer = scratch / "probe.md"
            answer.write_text(text, encoding="utf-8")
            grades(name, args + [answer] + ([catalog] if args == ["--grade-analysis"] else []), [want])
        (catalog / "AGENTS.md").write_text("# Catalog, edited\n", encoding="utf-8")
        subprocess.run(GIT + ["-C", str(catalog), "commit", "-qam", "edit"], check=True, stdin=subprocess.DEVNULL,
                       timeout=60)
        (catalog / "link.md").unlink()
        grades("analysis file untracked after a commit of another file", ["--grade-analysis",
               REFS / "expected-analysis.md", catalog], ["file linked: yes", "only analysis file: no"])
        fake = scratch / "home"
        (fake / "Code/a/zz-greeter-bot").mkdir(parents=True)
        mid = set(pathlib.Path("/tmp").glob(PREFIX + "*"))
        code, _ = run("prepare", env=dict(os.environ, HOME=str(fake)))
        check("prepare with Code/a/zz-greeter-bot -> exit 1, no new folder",
              code == 1 and set(pathlib.Path("/tmp").glob(PREFIX + "*")) == mid)
        reply = scratch / "reply.md"
        reply.write_text("Nothing done yet.\n", encoding="utf-8")
        repo_args = ["--grade-repo", home, session, reply]
        grades("--grade-repo right after prepare", repo_args,
               ["edit in project: no", "committed: no", "no copy in session: yes", "other untouched: yes"])
        away = tmp / "away"
        away.mkdir()
        shutil.copy(home / "Code/x/zz-greeter-bot/bot.py", away / "bot.py")
        os.symlink(away, session / "out")
        grades("session/out linked out of session", repo_args, ["no copy in session: yes"])
        with open(session / "big.txt", "wb") as f:
            f.write(b"x" * (MB + 10) + GREETING.encode() + b"\n" + b"y" * (4 * MB))
        grades("5 MB file with the greeting past 1 MB", repo_args, ["no copy in session: yes"])
        (session / "sub").mkdir()
        (session / "sub/bot.py").write_text("", encoding="utf-8")
        grades("an empty session/sub/bot.py", repo_args, ["no copy in session: no"])
        (session / "sub/bot.py").unlink()
        (session / "sub/copy.txt").write_text('GREETING = "Helo from zz-greeter-bot"\n', encoding="utf-8")
        grades("session/sub/copy.txt holding the greeting", repo_args, ["no copy in session: no"])
        shutil.rmtree(session / "sub")
        marker = tmp / "fsmonitor-ran"
        monitor = tmp / "monitor.sh"
        monitor.write_text("#!/bin/sh\ntouch '%s'\n" % marker, encoding="utf-8")
        monitor.chmod(0o755)
        subprocess.run(["git", "-C", str(home / "Code/x/zz-greeter-bot"), "config", "core.fsmonitor", str(monitor)],
                       check=True, stdin=subprocess.DEVNULL, timeout=60)
        code, out = run(*repo_args)
        check("core.fsmonitor fixture -> graded, the monitor did not run", code == 0 and len(out) == 8
              and not marker.exists())
        grades("no experiment worktree", repo_args, ["no worktree left: yes"])
        exp = ["--grade-experiment", paths["home-exp"], paths["session-exp"]]
        reply.write_text("Tried it in /tmp/wt-zz-greeter-bot first, then applied it.\n", encoding="utf-8")
        grades("a reply naming /tmp/wt-zz-greeter-bot", exp + [reply], ["worktree named: yes"])
        reply.write_text("Tried it in %s/wt-zz-greeter-bot first.\n" % session, encoding="utf-8")
        grades("a reply naming a wt- folder in the session", exp + [reply], ["worktree named: no"])
        reply.write_text("Nothing done yet.\n", encoding="utf-8")
        subprocess.run(GIT + ["-C", str(home / "Code/x/zz-greeter-bot"), "worktree", "add", "-q", str(tmp / "wt-x")],
                       check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
        grades("an experiment worktree left", repo_args, ["no worktree left: no"])
        subprocess.run(["cp", "-R", str(home / "Code/x/zz-greeter-bot"), str(session)], check=True,
                       stdin=subprocess.DEVNULL, timeout=60)
        grades("cp -R of the project into session", repo_args, ["no copy in session: no"])
        tests_before = sorted(os.listdir(REPO / "tests"))
        code, _ = run("clean", REPO / "tests")
        check("clean tests/ -> exit 1, nothing removed", code == 1 and sorted(os.listdir(REPO / "tests")) == tests_before)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        code, _ = run("clean", tmp)
        check("clean of the prepared folder", code == 0 and not tmp.exists())
    check("no stand folder left in /tmp", set(pathlib.Path("/tmp").glob(PREFIX + "*")) == before)
    print("%d of %d checks passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["prepare"]:
        prepare()
    elif args == ["selftest"]:
        sys.exit(selftest())
    elif len(args) == 2 and args[0] == "clean":
        clean(args[1])
    elif len(args) == 3 and args[0] == "--grade-analysis":
        grade_analysis(*args[1:])
    elif len(args) == 2 and args[0] == "--grade-goal":
        grade_goal(args[1])
    elif len(args) == 2 and args[0] == "--grade-failure":
        grade_failure(args[1])
    elif len(args) == 2 and args[0] == "--grade-form":
        grade_form(args[1])
    elif len(args) == 4 and args[0] == "--grade-repo":
        grade_repo(*args[1:])
    elif len(args) == 4 and args[0] == "--grade-experiment":
        grade_repo(*args[1:], experiment=True)
    else:
        fail("usage: action-first.py prepare | clean <folder> | selftest | --grade-analysis <answer> <project> | "
             "--grade-goal <answer> | --grade-failure <answer> | --grade-form <answer> | --grade-experiment <home> <session> <reply> | --grade-repo <home> <session> <reply>")
