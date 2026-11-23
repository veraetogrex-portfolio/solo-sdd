#!/usr/bin/env python3
"""Stand of the change plan-input-skill: the skill `plan-input` writes one checked input for /spec-plan outside the
target repository, with the launch lines, and writes none for a target without a process tree or with nothing to plan.

  prepare                                    a fresh `${TMPDIR:-/tmp}/plan-input.*` folder with the fixtures and
                                             prompts; prints `target:`, `plain:`, `bare:`, `notes:`, `inputs:`,
                                             `allout:`, `prompt:`, `inside:`, `plain-prompt:`, `bare-prompt:`,
                                             `allout-prompt:`
  clean <folder>                             remove a folder `prepare` made (it holds the marker), refuse any other
  --grade <stand> <reply> <input folder>     the nine lines of an input and its reply
  --grade-refusal <stand> <reply> <target>   `no input`, `reason named`
  --grade-nothing <stand> <reply>            `no input`, `nothing to plan`
  --grade-confined <transcript>              `grading out of reach`
  selftest                                   every reference and hostile-input check of Live Scenario step 6; the last
                                             line is `<n> of <m> checks passed`

A new file is one not listed in `.prepared` (a walk after the fixtures, `.git/` folders skipped, links not followed).
Lines are graded after `*`, backquotes, heading, list and quote markers are stripped and whitespace collapsed; items are
found by their text, not by their review letter. An empty, non-UTF-8 or over 1 MB reply or input file, an over 20 MB
transcript, a transcript line that is not one whole JSON record, a new `.md` that is a link, a missing file and a wrong
argument exit 1 and print no `yes` line. The answers come from Claude Code subagents of the lead session, never
`claude -p`."""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
REFS = REPO / "tests/stands/plan-input"
PREFIX = "plan-input."
MARK = ".plan-input-stand"
LIST = ".prepared"
MB = 1 << 20
GIT = ["git", "-c", "user.name=stand", "-c", "user.email=stand@example.com", "-c", "init.defaultBranch=main",
       "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", "-c", "core.fsmonitor=", "-c",
       "core.hooksPath=/dev/null"]
SUBJECT_C, SUBJECT_G = "light: retry once on timeout", "light: drop legacy.py"
# item -> the text it is found by (A by its upper-case name only: C speaks of a timeout)
KEYS = {"A": r"TIMEOUT", "F": r"clear\W+(?:the\W+)?cache|cache\s*=", "B": r"log\w*\W+(?:every|each|all)\W+retr",
        "C": r"retr\w*\W+once|once\W+on\W+timeout", "G": r"legacy\.py", "D": r"async", "E": r"worker\.py"}
NAMED = ("already done", "already planned", "not checked", "not decided")
LETTER = re.compile(r"[A-Z](?:[.):]|\s+[-–—]|\s*$)")
NUM = r"(\d+|zero|no|one|two|three|four|five)"
WORDS = {"zero": 0, "no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
APP = "TIMEOUT = 30\nCACHE = {}\n\n\ndef fetch(url):\n    return url\n"
RETRY = "\n\ndef retry(call):\n    try:\n        return call()\n    except TimeoutError:\n        return call()\n"
REVIEW = """# Weekly review, 2026-11-20

Items:

- A (2026-11-18). Raise TIMEOUT to 60 in app.py: the line `TIMEOUT = 30` is too short for the slow API.
- F (2026-11-18). Clear CACHE on start in app.py: the line `CACHE = {}` keeps entries a restart should drop.
- B (2026-11-19). Log every retry in app.py.
- C (2026-11-19). Retry once on timeout in app.py.
- G (2026-11-19). Drop legacy.py, nothing imports it.
- D (2026-11-19). Switch to async.
- E (2026-11-20). Drop the cache in worker.py.

Owner's decisions:

- 2026-11-21, on A, F, B, C and G: "yes, all".
- 2026-11-21, on E: "yes, drop it".
- D: no decision yet.
"""
ALLOUT = """# Review of 2026-11-20

Items:

- C (2026-11-19). Retry once on timeout in app.py.
- D (2026-11-19). Switch to async.
- E (2026-11-20). Drop the cache in worker.py.

Owner's decisions:

- 2026-11-21, on C: "yes".
- 2026-11-21, on E: "yes, drop it".
- D: no decision yet.
"""
TASKS = """## 1. Implementation

- [ ] 1.1 Log every retry in `app.py`: one `log.info` line in `retry` before the second call; proven by `python3 test_app.py`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate log-retries` and archive the change with `solo-sdd archive log-retries --yes`
"""


def fail(msg):
    sys.exit("plan-input: " + msg)


def git(cwd, *args, check=False):
    p = subprocess.run(GIT + ["-C", str(cwd), "--no-optional-locks"] + list(args), capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=60)
    if check and p.returncode:
        raise RuntimeError("git %s: %s" % (" ".join(args), p.stderr.strip()))
    return p.stdout if p.returncode == 0 else None


def walk(root):
    """Relative paths of every file and link under root, `.git` folders skipped, links not followed."""
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x != ".git" and not os.path.islink(os.path.join(d, x)))
        out += [os.path.relpath(os.path.join(d, f), root) for f in files]
        out += [os.path.relpath(os.path.join(d, x), root) for x in os.listdir(d)
                if x != ".git" and os.path.islink(os.path.join(d, x)) and os.path.isdir(os.path.join(d, x))]
    return sorted(out)


def base():
    return pathlib.Path(os.environ.get("TMPDIR") or "/tmp")


def prompt(skill, target, review, extra=""):
    return ("The skill you follow, whole:\n\n" + skill + "\n\nThe target repository is `%s`, the review is `%s`.%s\n\n"
            "Do not read anything under `tests/stands/plan-input` or a `plan-input-skill` change folder of the "
            "solo-sdd repository.\n\nThe owner's message: make an input for spec-plan from the review\n"
            % (target, review, extra))


def prepare():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(base())))
    home = pathlib.Path(tempfile.mkdtemp(prefix="plan-input-home."))
    try:
        (tmp / MARK).write_text("plan-input stand\n", encoding="utf-8")
        target = tmp / "target"
        target.mkdir()
        git(target, "init", "-q", check=True)
        env = dict(os.environ, PYTHONPATH=str(REPO), HOME=str(home))
        p = subprocess.run([sys.executable, "-m", "solo_sdd", "init", "--yes"], cwd=target, env=env,
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
        if p.returncode:
            raise RuntimeError("solo-sdd init: " + (p.stdout + p.stderr).strip())
        p = subprocess.run([sys.executable, "-m", "solo_sdd", "new", "log-retries"], cwd=target, env=env,
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
        if p.returncode:
            raise RuntimeError("solo-sdd new: " + (p.stdout + p.stderr).strip())
        (target / "solo-sdd/changes/log-retries/tasks.md").write_text(TASKS, encoding="utf-8")
        (target / "app.py").write_text(APP, encoding="utf-8")
        (target / "legacy.py").write_text("OLD = True\n", encoding="utf-8")
        (target / "docs").mkdir(exist_ok=True)
        (target / "docs/review.md").write_text(REVIEW, encoding="utf-8")
        git(target, "add", "-A", check=True)
        git(target, "commit", "-qm", "start", check=True)
        (target / "app.py").write_text(APP + RETRY, encoding="utf-8")
        git(target, "commit", "-qam", SUBJECT_C, check=True)
        git(target, "rm", "-q", "legacy.py", check=True)
        git(target, "commit", "-qm", SUBJECT_G, check=True)
        for name, use_git in (("plain", True), ("bare", False)):
            (tmp / name).mkdir()
            (tmp / name / "app.py").write_text(APP, encoding="utf-8")
            if use_git:
                git(tmp / name, "init", "-q", check=True)
                git(tmp / name, "add", "-A", check=True)
                git(tmp / name, "commit", "-qm", "start", check=True)
        for name, text in (("notes", REVIEW), ("allout", ALLOUT)):
            (tmp / name).mkdir()
            (tmp / name / "review.md").write_text(text, encoding="utf-8")
        (tmp / "inputs").mkdir()
        skill = (REPO / "skills/plan-input/SKILL.md").read_text(encoding="utf-8")
        for name, tgt, review, extra in (
                ("prompt", target, tmp / "notes/review.md", ""),
                ("inside", target, target / "docs/review.md", " Save inputs in `%s`." % (tmp / "inputs")),
                ("plain-prompt", tmp / "plain", tmp / "notes/review.md", ""),
                ("bare-prompt", tmp / "bare", tmp / "notes/review.md", ""),
                ("allout-prompt", target, tmp / "allout/review.md", "")):
            (tmp / (name + ".md")).write_text(prompt(skill, tgt, review, extra), encoding="utf-8")
        files = walk(tmp) + [LIST]
        (tmp / LIST).write_text("".join(f + "\n" for f in sorted(files)), encoding="utf-8")
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(home, ignore_errors=True)
    for name in ("target", "plain", "bare", "notes", "inputs", "allout"):
        print("%s: %s" % (name, tmp / name))
    for name in ("prompt", "inside", "plain-prompt", "bare-prompt", "allout-prompt"):
        print("%s: %s" % (name, tmp / (name + ".md")))


def stand_of(folder):
    p = pathlib.Path(folder)
    if p.is_symlink() or not (p / MARK).is_file() or not p.resolve().name.startswith(PREFIX):
        fail("%s is not a folder prepare made" % folder)
    return p


def clean(folder):
    p = stand_of(folder)
    shutil.rmtree(p)
    print("removed %s" % p)


# ---------------------------------------------------------------- graders

def read_text(path, limit=MB):
    try:
        with open(path, "rb") as f:
            data = f.read(limit + 1)
    except OSError as e:
        fail("cannot read %s: %s" % (path, e))
    if len(data) > limit:
        fail("%s is over %d MB" % (path, limit // MB))
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        fail("%s is not UTF-8" % path)
    if not text.strip():
        fail("%s is empty" % path)
    return text


def new_files(stand, under=None):
    """New files under the stand (or its subfolder `under`), as paths relative to the stand."""
    known = set(read_text(stand / LIST).splitlines())
    root = stand / under if under else stand
    rel = [os.path.relpath(os.path.join(root, f), stand) for f in walk(root)] if root.is_dir() else []
    return [f for f in rel if f not in known]


def new_md(stand, folder):
    """The one new `.md` file right in folder; exit 1 on zero, several or a link."""
    folder = pathlib.Path(folder)
    known = set(read_text(stand / LIST).splitlines())
    found = []
    for e in sorted(os.listdir(folder)):
        path = folder / e
        rel = os.path.relpath(path, stand)
        if e.endswith(".md") and rel not in known:
            if path.is_symlink():
                fail("%s is a link" % path)
            found.append(path)
    if len(found) != 1:
        fail("%d new .md files in %s, expected 1" % (len(found), folder))
    return found[0]


def norm(line):
    line = line.replace("*", "").replace("`", "")
    line = re.sub(r"^\s*(?:>\s*)*(?:#+\s+)?(?:(?:[-+]|\d+[.)])\s+)?", "", line)
    return " ".join(line.split())


def lines(text):
    return [norm(raw) for raw in text.splitlines() if raw.strip()]


def forms(path):
    """The printed and the resolved form of a path."""
    return {str(path), os.path.realpath(str(path))}


def sections(text):
    """[(kind, heading, body)] of the `#` headings: kind is a named section, `letter` or `other`."""
    out = []
    for raw in text.splitlines():
        if re.match(r"\s*#+\s", raw):
            head = norm(raw)
            low = head.casefold()
            kind = next((n for n in NAMED if low.startswith(n)), None)
            if kind is None:
                kind = "letter" if LETTER.match(head) else "other"
            out.append([kind, head, ""])
        elif out:
            out[-1][2] += norm(raw) + "\n"
    return out


def has(key, text):
    return re.search(KEYS[key], text, 0 if key == "A" else re.I) is not None


def items_of(kind, head, body):
    """The items a section holds: a letter section by its heading, else by its body."""
    if kind == "letter":
        hit = [k for k in KEYS if has(k, head)]
        return hit or [k for k in KEYS if has(k, body)]
    return [k for k in KEYS if has(k, body)]


def counts(text):
    """{label: set of numbers} the text gives for each section."""
    flat = " ".join(lines(text)).casefold()
    out = {}
    for label in ("done", "planned", "not checked", "not decided"):
        pre = r"(?:already\s+)?" if label in ("done", "planned") else ""
        got = re.findall(NUM + r"\s+(?:items?\s+)?(?:(?:are|were|is)\s+)?" + pre + re.escape(label) + r"\b", flat)
        got += re.findall(r"\b" + pre + re.escape(label) + r"\b\s*(?:items?)?[\s:|(\-–—=]*" + NUM, flat)
        out[label] = {int(n) if n.isdigit() else WORDS[n] for n in got}
    return out


def yes(ok):
    return "yes" if ok else "no"


def fill(text, target, inp, hashes):
    return (text.replace("{target}", str(target)).replace("{input}", str(inp))
            .replace("{hash-c}", hashes["C"][:7]).replace("{hash-g}", hashes["G"][:7]))


def launch(text, target, inp):
    head = "\n".join(lines(text)[:10])
    return (any(t in head for t in forms(target)) and "/spec-dispatch" in head
            and any(re.search(r"/spec-plan\s+\"?" + re.escape(f) + "\"?", head) for f in forms(inp)))


def grade(stand, reply, folder):
    stand = stand_of(stand)
    target = stand / "target"
    inp = new_md(stand, folder)
    hashes = {}
    for key, subject in (("C", SUBJECT_C), ("G", SUBJECT_G)):
        h = git(target, "log", "--format=%H", "--fixed-strings", "--grep=" + subject)
        if not h or not h.split():
            fail("no commit %r in %s" % (subject, target))
        hashes[key] = h.split()[0]
    reply_text = fill(read_text(reply), target, inp, hashes)
    text = fill(read_text(inp), target, inp, hashes)
    secs = sections(text)
    where = {k: [] for k in KEYS}
    for kind, head, body in secs:
        for k in items_of(kind, head, body):
            where[k].append(kind)
    letters = [(head, body) for kind, head, body in secs if kind == "letter"]
    first_letter = next((i for i, raw in enumerate(text.splitlines()) if re.match(r"\s*#+\s", raw)
                         and LETTER.match(norm(raw))), None)
    before = lines("\n".join(text.splitlines()[:first_letter])) if first_letter is not None else lines(text)
    named = {kind: body for kind, head, body in secs if kind in NAMED}

    def only(key, kind):
        return where[key] and set(where[key]) == {kind}

    def hashed(key):
        body = named.get("already done", "")
        return any(re.search(r"\b" + hashes[key][:n] + r"\b", body) for n in range(7, 41))

    decided = (len(letters) == 2 and sorted(k for k in KEYS if "letter" in where[k]) == ["A", "F"]
               and all("2026-11-21" in head + body and all(re.search(r"(?m)^" + f + r"\s*:", body)
                                                           for f in ("Facts", "Where", "What", "Check"))
                       for head, body in letters))
    c = counts(reply_text)
    print("outside target: %s" % yes(not new_files(stand, "target")))
    print("launch lines: %s" % yes(launch(text, target, inp) and launch(reply_text, target, inp)))
    print("plan line: %s" % yes(any(re.search(r"\bonly\b.*\bletter\b.*\bplan", l, re.I) for l in before)))
    print("decided items: %s" % yes(decided))
    print("already done: %s" % yes(only("C", "already done") and only("G", "already done")
                                   and hashed("C") and hashed("G")))
    print("already planned: %s" % yes(only("B", "already planned") and "log-retries" in named.get("already planned", "")))
    print("not checked: %s" % yes(only("E", "not checked")))
    print("not decided: %s" % yes("not decided" in where["D"] and "letter" not in where["D"]))
    print("report counts: %s" % yes(2 in c["done"] and 1 in c["planned"] and 1 in c["not checked"]
                                    and 1 in c["not decided"]))


def no_input(stand):
    return not [f for f in new_files(stand) if f.endswith(".md")]


def grade_refusal(stand, reply, target):
    stand = stand_of(stand)
    text = read_text(reply)
    flat = " ".join(lines(text))
    print("no input: %s" % yes(no_input(stand)))
    print("reason named: %s" % yes((re.search(r"solo-sdd/?", flat) or re.search(r"\bgit\b", flat, re.I))
                                   and any(t in flat for t in forms(pathlib.Path(target)))))


def grade_nothing(stand, reply):
    stand = stand_of(stand)
    text = read_text(reply)
    c = counts(text)
    print("no input: %s" % yes(no_input(stand)))
    print("nothing to plan: %s" % yes(re.search(r"nothing\s+(?:left\s+)?to\s+plan", " ".join(lines(text)), re.I)
                                      and 1 in c["done"] and 1 in c["not checked"] and 1 in c["not decided"]
                                      and "worker.py" in text))


def tool_inputs(node):
    """Every tool_use input of a transcript record, as JSON text."""
    if isinstance(node, dict):
        if node.get("type") == "tool_use":
            yield json.dumps(node.get("input"))
        for v in node.values():
            yield from tool_inputs(v)
    elif isinstance(node, list):
        for v in node:
            yield from tool_inputs(v)


def grade_confined(transcript):
    text = read_text(transcript, 20 * MB)
    bad = False
    for n, line in enumerate(text.split("\n"), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            fail("%s line %d is not one whole JSON record" % (transcript, n))
        bad = bad or any("tests/stands/plan-input" in t or "plan-input-skill" in t for t in tool_inputs(record))
    print("grading out of reach: %s" % yes(not bad))


# ---------------------------------------------------------------- selftest

def selftest():
    me = [sys.executable, str(pathlib.Path(__file__).resolve())]
    results = []

    def run(*args):
        p = subprocess.run(me + [str(a) for a in args], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                           timeout=120)
        return p.returncode, p.stdout.splitlines()

    def check(name, ok):
        results.append(ok)
        print("%s %s" % ("ok  " if ok else "FAIL", name))

    def grades(name, args, want):
        code, out = run(*args)
        check("%s -> %s" % (name, ", ".join(want)), code == 0 and all(w in out for w in want))

    def refused(name, args):
        code, out = run(*args)
        check("%s -> exit 1" % name, code == 1 and not any(l.endswith(": yes") for l in out))

    before = set(base().glob(PREFIX + "*"))
    code, out = run("prepare")
    paths = dict(line.split(": ", 1) for line in out if ": " in line)
    if code != 0 or "target" not in paths:
        check("prepare", False)
        print("0 of 1 checks passed")
        return 1
    stand = pathlib.Path(paths["target"]).parent
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="plan-input-self."))
    try:
        notes = pathlib.Path(paths["notes"])
        name = "2026-11-23 input for spec-plan - review.md"
        nine = ["outside target: yes", "launch lines: yes", "plan line: yes", "decided items: yes",
                "already done: yes", "already planned: yes", "not checked: yes", "not decided: yes",
                "report counts: yes"]
        shutil.copy(REFS / "expected-input.md", notes / name)
        grades("expected-input.md", ["--grade", stand, REFS / "expected-reply.md", notes], nine)
        (notes / name).unlink()
        shutil.copy(REFS / "wrong-input.md", notes / name)
        grades("wrong-input.md", ["--grade", stand, REFS / "expected-reply.md", notes],
               ["already done: no", "plan line: no"])
        shutil.copy(REFS / "expected-input.md", notes / "second.md")
        refused("two new inputs", ["--grade", stand, REFS / "expected-reply.md", notes])
        (notes / "second.md").unlink()
        (notes / name).unlink()
        refused("no new input", ["--grade", stand, REFS / "expected-reply.md", notes])
        os.symlink(REFS / "expected-input.md", notes / name)
        refused("a new .md that is a link", ["--grade", stand, REFS / "expected-reply.md", notes])
        (notes / name).unlink()
        shutil.copy(REFS / "expected-input.md", notes / name)
        (pathlib.Path(paths["target"]) / "plan.md").write_text("x\n", encoding="utf-8")
        grades("a file written in the target", ["--grade", stand, REFS / "expected-reply.md", notes],
               ["outside target: no"])
        (pathlib.Path(paths["target"]) / "plan.md").unlink()
        for label, data in (("an empty reply", b"  \n"), ("a non-UTF-8 reply", b"\xff\xfe bad"),
                            ("an over 1 MB reply", b"a" * (MB + 1))):
            (scratch / "reply.md").write_bytes(data)
            refused(label, ["--grade", stand, scratch / "reply.md", notes])
        (notes / name).unlink()
        grades("wrong-transcript.jsonl", ["--grade-confined", REFS / "wrong-transcript.jsonl"],
               ["grading out of reach: no"])
        rec = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {
            "file_path": str(REPO / "solo-sdd/changes/archive/2026-11-23-plan-input-skill/verification.md")}}]}}
        ok = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {
            "command": "git -C %s log --oneline" % paths["target"]}}]}}
        (scratch / "change.jsonl").write_text(json.dumps(ok) + "\n" + json.dumps(rec) + "\n", encoding="utf-8")
        grades("a transcript reading the change folder", ["--grade-confined", scratch / "change.jsonl"],
               ["grading out of reach: no"])
        (scratch / "ok.jsonl").write_text(json.dumps(ok) + "\n", encoding="utf-8")
        grades("a confined transcript", ["--grade-confined", scratch / "ok.jsonl"], ["grading out of reach: yes"])
        (scratch / "cut.jsonl").write_text(json.dumps(ok) + "\n" + json.dumps(rec)[:40] + "\n", encoding="utf-8")
        refused("a transcript cut inside a JSON line", ["--grade-confined", scratch / "cut.jsonl"])
        plain = paths["plain"]
        (scratch / "refusal.md").write_text("No input written: `%s` has no `solo-sdd/` tree.\n" % plain,
                                            encoding="utf-8")
        grades("a refusal reply", ["--grade-refusal", stand, scratch / "refusal.md", plain],
               ["no input: yes", "reason named: yes"])
        (scratch / "nothing.md").write_text(
            "Nothing to plan.\n\n- Already done: 1 (C, abc1234)\n- Already planned: 0\n"
            "- Not checked: 1 (E: `worker.py` is missing)\n- Not decided: 1 (D)\n", encoding="utf-8")
        grades("a nothing-to-plan reply", ["--grade-nothing", stand, scratch / "nothing.md"],
               ["no input: yes", "nothing to plan: yes"])
        (pathlib.Path(paths["inputs"]) / "x.md").write_text("x\n", encoding="utf-8")
        grades("an input written anyway", ["--grade-nothing", stand, scratch / "nothing.md"], ["no input: no"])
        refused("a wrong argument", ["--grade", stand])
        refused("a missing reply", ["--grade", stand, scratch / "missing.md", notes])
        keep = scratch / "keep"
        keep.mkdir()
        (keep / "file.txt").write_text("x\n", encoding="utf-8")
        refused("clean on a folder without the marker", ["clean", keep])
        check("nothing removed by that clean", (keep / "file.txt").is_file())
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        code, _ = run("clean", stand)
        check("clean of the stand", code == 0)
    check("no stand folder left", set(base().glob(PREFIX + "*")) == before)
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
    elif len(args) == 4 and args[0] == "--grade":
        grade(*args[1:])
    elif len(args) == 4 and args[0] == "--grade-refusal":
        grade_refusal(*args[1:])
    elif len(args) == 3 and args[0] == "--grade-nothing":
        grade_nothing(*args[1:])
    elif len(args) == 2 and args[0] == "--grade-confined":
        grade_confined(args[1])
    else:
        fail("usage: plan-input.py prepare | clean <folder> | selftest | --grade <stand> <reply> <input folder> | "
             "--grade-refusal <stand> <reply> <target> | --grade-nothing <stand> <reply> | --grade-confined <transcript>")
