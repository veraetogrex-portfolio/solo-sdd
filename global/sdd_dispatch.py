#!/usr/bin/env python3
"""sdd-dispatch.py: dispatcher mechanics: accept (status acceptance), land-local (merge in local mode)."""
import importlib.util
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys

USAGE = """usage:
  sdd-dispatch.py accept <status file>
  sdd-dispatch.py land-local <MAIN> <WORKTREE> <id> [--check <command>]...
  accept codes: 0 matches, 1 mismatches, 2 block not parsed
  land-local codes: 0 merged, 1 step failed, 2 main not clean, 3 check red with the change, 4 main red, 6 merge or transport conflict,
    8 waits for the owner («Owner only:» paths or .github/workflows) or a human merge (delivery.merge-by: human)"""
VALIDATE_CMD = "openspec validate --all --strict --no-interactive"
HERE = os.path.dirname(os.path.abspath(__file__))
NOT_FOUND = "solo-sdd not found: neither the solo-sdd command nor python3 -m solo_sdd"
DEFAULT_TIMEOUT = 600
MAX_TIMEOUT = 2147483  # about 24 days: the wait of subprocess passes milliseconds as a C int


def timeout():
    """Seconds of SDD_DISPATCH_TIMEOUT when it is a whole number of ASCII digits from 1 to MAX_TIMEOUT, else 600."""
    v = os.environ.get("SDD_DISPATCH_TIMEOUT", "")
    return int(v) if re.fullmatch(r"[0-9]+", v) and 0 < int(v) <= MAX_TIMEOUT else DEFAULT_TIMEOUT


class Timeout(Exception):
    def __init__(self, cmd, sec):
        self.sec = sec
        super().__init__("%s: timeout after %d s" % (cmd, sec))


def call(args, cwd=None, merge=False, name=None):
    """Runs args in its own process group with the timeout; on timeout the whole group is killed and Timeout raised:
    a child that keeps the output pipe open would otherwise keep the wait going after the shell ends."""
    sec = timeout()
    p = subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT if merge else subprocess.PIPE, start_new_session=True)
    try:
        out, err = p.communicate(timeout=sec)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            p.communicate(timeout=5)
        except subprocess.TimeoutExpired:  # ponytail: a grandchild in its own session still holds the pipe; left to the OS
            p.kill()
        raise Timeout(name or " ".join(args), sec)
    return subprocess.CompletedProcess(args, p.returncode, out, err)


# A copy of a block of global/work_hooks.py (this script is deployed alone): edit it there, then run
# python3 scripts/sync_blocks.py.
# process-root:begin
TREE_MARKS = ("project.md", "specs", "changes")


def process_root(project):
    """`solo-sdd` when the project holds that tree (project.md, specs/ or changes/), else `openspec`, read until import.
    solo_sdd/process_format.py (find_tree) keeps the same rule in its own form."""
    return "solo-sdd" if any(os.path.exists(os.path.join(project, "solo-sdd", n)) for n in TREE_MARKS) else "openspec"
# process-root:end


def validate_cmd(root, legacy=VALIDATE_CMD):
    """The validation command of the project's process tree: legacy on openspec/; on solo-sdd/ the solo-sdd command,
    else the module, else None (never openspec there)."""
    if process_root(root) != "solo-sdd":
        return legacy
    if shutil.which("solo-sdd"):
        return "solo-sdd validate --all"
    try:
        probe = call(["python3", "-m", "solo_sdd", "--version"], cwd=root).returncode
    except OSError:  # a Timeout goes up: the caller names it
        probe = 1
    return "python3 -m solo_sdd validate --all" if probe == 0 else None


def run(cmd, cwd=None, shell=False):
    """stdout+stderr output together, the exit code is taken from the command itself; shell: bash with pipefail.
    Raises Timeout."""
    name = cmd if shell else " ".join(map(os.path.basename, cmd[:2])) + " " + " ".join(cmd[2:3])
    p = call(["bash", "-o", "pipefail", "-c", cmd] if shell else cmd, cwd, True, name.strip())
    return p.returncode, p.stdout.decode("utf-8", "replace")


def git(main, *args):
    """A timeout is a failed git step: code 1, stderr `<command>: timeout after <n> s`."""
    try:
        p = call(["git", "-C", main] + list(args), name="git " + " ".join(args))
    except Timeout as t:
        return subprocess.CompletedProcess(args, 1, "", str(t))
    return subprocess.CompletedProcess(p.args, p.returncode, p.stdout.decode("utf-8", "replace"),
                                       p.stderr.decode("utf-8", "replace"))


# The document reader of solo_sdd/process_format.py (the validator), copied: this script is deployed alone.
# Edit it there, then run python3 scripts/sync_blocks.py.
# doc-reader:begin
FENCE_OPEN = re.compile(r"^\s*(`{3,}|~{3,})")
FENCE_CLOSE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")
H2 = re.compile(r"^##\s+(.+?)\s*$")
CODE_OR_COMMENT = re.compile(r"(`+).*?\1|<!--")


def read_lines(path):
    text = path.read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def read_doc(path):
    """Lines of a process document with HTML comments blanked: a comment never counts as a header, task or text.
    `<!--` inside a code block or an inline code span is code, not a comment; an unclosed comment runs to the end."""
    out, comment, fence = [], False, None
    for line in read_lines(path):
        if fence:
            out.append(line)
            m = FENCE_CLOSE.match(line)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
            continue
        m = None if comment else FENCE_OPEN.match(line)
        if m:
            fence = m.group(1)
            out.append(line)
            continue
        kept, pos = "", 0
        while pos < len(line):
            if comment:
                end = line.find("-->", pos)
                comment, pos = (True, len(line)) if end < 0 else (False, end + 3)
                continue
            t = CODE_OR_COMMENT.search(line, pos)
            if not t:
                kept += line[pos:]
                break
            kept += line[pos:t.start()] if t.group() == "<!--" else line[pos:t.end()]
            comment, pos = t.group() == "<!--", t.end()
        out.append(kept)
    return out


def fence_mask(lines):
    """True for lines inside code blocks and for the fences themselves."""
    mask, ch, n = [], None, 0
    for line in lines:
        if ch is None:
            m = FENCE_OPEN.match(line)
            if m:
                ch, n = m.group(1)[0], len(m.group(1))
            mask.append(bool(m))
        else:
            mask.append(True)
            m = FENCE_CLOSE.match(line)
            if m and m.group(1)[0] == ch and len(m.group(1)) >= n:
                ch = None
    return mask


def sections(lines, mask):
    """[(## name, body lines, body lines outside code blocks)] in file order."""
    out = []
    for line, masked in zip(lines, mask):
        m = None if masked else H2.match(line)
        if m:
            out.append((m.group(1), [], []))
        elif out:
            out[-1][1].append(line)
            if not masked:
                out[-1][2].append(line)
    return out
# doc-reader:end


SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")


def live_in_scenario(path, cmd):
    """None when cmd, whitespace collapsed, equals a code span of the ## Live Scenario section read as the validator
    reads it (comments blanked, code blocks are not spans); else the mismatch line."""
    try:
        lines = read_doc(pathlib.Path(path))
    except (OSError, UnicodeDecodeError):
        lines = []
    body = {name: plain for name, _, plain in sections(lines, fence_mask(lines))}.get("Live Scenario")  # the last, as validate
    if body is None:
        return "LIVE: no Live Scenario in %s" % path
    spans = {" ".join(m.group(2).split()) for line in body for m in SPAN.finditer(line)}
    if " ".join(cmd.split()) in spans:
        return None
    return "LIVE: %s — not in the Live Scenario of %s" % (cmd, path)


def tail(text, n):
    return text.rstrip("\n").splitlines()[-n:]


def field(text, name):
    m = re.search(r"^[ \t]*%s:[ \t]*(.*?)[ \t\r]*$" % name, text, re.M)
    return m.group(1) if m else ""


def live_matches(expect, out):
    """Containment with every whitespace run collapsed to one space in both texts."""
    return " ".join(expect.split()) in " ".join(out.split())


def accept(path):
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        print("block not parsed: file not readable: %s" % e)
        return 2
    if not text.strip():
        print("block not parsed: file empty")
        return 2
    if not re.search(r"^[ \t]*STATUS:", text, re.M):
        print("block not parsed: no STATUS: line")
        return 2
    status = field(text, "STATUS")
    if status != "archived":
        print("status not archived: %s, commands not run" % status)
        return 2
    wt, validate, live, arch = (field(text, f) for f in ("WORKTREE", "VALIDATE", "LIVE", "ARCHIVE"))
    for name, val in (("WORKTREE", wt), ("VALIDATE", validate), ("LIVE", live)):
        if not val:
            print("block not parsed: field %s empty" % name)
            return 2
    live_cmd, sep, expect = live.partition(" -> ")
    if not sep or not expect.strip():
        print("block not parsed: LIVE has no ' -> ' or the text after it is empty")
        return 2
    if not os.path.isdir(wt):
        print("block not parsed: no WORKTREE folder: %s" % wt)
        return 2
    bad = 0
    try:
        vcmd = validate_cmd(wt, validate.partition(" -> ")[0])
        code, out = run(vcmd, wt, True) if vcmd else (1, "")
    except Timeout as t:
        vcmd, code, out = None, t, ""
    if isinstance(code, Timeout):
        bad = 1
        print("VALIDATE: timeout after %d s" % code.sec)
    elif not vcmd:
        bad = 1
        print("VALIDATE: " + NOT_FOUND)
    elif code:
        bad = 1
        print("VALIDATE: %s — stated exit 0, got exit %d" % (vcmd, code))
        for l in tail(out, 3):
            print("    " + l)
    expect = expect.strip()
    vpath = os.path.join(wt, arch, "verification.md")
    if not arch or not os.path.realpath(vpath).startswith(os.path.realpath(wt).rstrip("/") + "/"):
        miss = "LIVE: no Live Scenario in %s (ARCHIVE empty or outside WORKTREE)" % vpath
    else:
        miss = live_in_scenario(vpath, live_cmd)
    if miss:
        print(miss)
        return 1
    try:
        code, out = run(live_cmd, wt, True)
    except Timeout as t:
        print("LIVE: timeout after %d s" % t.sec)
        return 1
    found = live_matches(expect, out)
    if code or not found:
        bad = 1
        got = ["exit %d" % code] if code else []
        if not found:
            got.append("text missing")
        print("LIVE: %s — stated «%s», got %s" % (live_cmd, expect, ", ".join(got)))
        for l in tail(out, 3):
            print("    " + l)
    if not bad:
        print("status matches")
    return bad


def worktree_script():
    for n in ("sdd-worktree.py", "sdd_worktree.py"):
        p = os.path.join(HERE, n)
        if os.path.exists(p):
            return p
    return os.path.join(HERE, "sdd-worktree.py")


def load_pr():
    """Shared owner-path functions from sdd-pr.py next to the script, or None."""
    for n in ("sdd-pr.py", "sdd_pr.py"):
        p = os.path.join(HERE, n)
        if os.path.exists(p):
            try:
                spec = importlib.util.spec_from_file_location("sdd_pr_shared", p)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
            except Exception as e:
                print("sdd-pr.py not loaded: %s" % e)
                return None
    return None


def owner_wait(pr, main, wt, branch):
    """(code, message): 1 on diff failure, 8 on owner paths, else (0, '')."""
    try:
        r = call(["git", "-C", main, "diff", "--name-only", "-z", "--no-renames", "HEAD..." + branch],
                 name="git diff HEAD..." + branch)
    except Timeout as t:
        return 1, "not merged: diff: %s" % t
    if r.returncode:
        return 1, "not merged: diff: " + r.stderr.decode("utf-8", "replace").strip()
    files = [f for f in r.stdout.decode("utf-8", "replace").split("\0") if f]
    text = pr.read_text(os.path.join(main, "AGENTS.md"))
    found = pr.migrate_agents(text or "")[1]
    if found:
        print(pr.migrate_hint(os.path.join(main, "AGENTS.md"), found), file=sys.stderr)
    rule = pr.owner_rule(text)
    hits = pr.owner_hits(files, pr.owner_patterns(rule))
    if pr.OWNER in found:  # old item: not read, paths not opened silently
        hits.append(pr.OLD_OWNER_HIT)
    if text is not None:
        shown = git(main, "show", branch + ":AGENTS.md")
        theirs = pr.owner_rule(shown.stdout) if "AGENTS.md" in files and not shown.returncode else None
        changed = ("AGENTS.md" in files and theirs != rule) or pr.owner_rule(pr.read_text(os.path.join(wt, "AGENTS.md"))) != rule
        if changed:
            hits.append("AGENTS.md («%s»)" % pr.OWNER)
    if hits:
        return 8, "not merged: waits for the owner: " + ", ".join(hits)
    return 0, ""


def wt_run(sub, main, wt):
    try:
        code, out = run([sys.executable, worktree_script(), sub, main, wt])
    except Timeout as t:
        code, out = 1, str(t)
    if out.strip():
        print(out.rstrip("\n"))
    return code, out


def rollback(main, wt, prev):
    """reset --keep to the commit before merge, then undo the transfer. Returns the error text or ''."""
    r = git(main, "reset", "--keep", prev)
    if r.returncode:
        return "reset: " + r.stderr.strip()
    try:
        code, out = run([sys.executable, worktree_script(), "undo", main, wt])
    except Timeout as t:
        code, out = 1, str(t)
    if code:
        return "undo: " + out.strip()
    return ""


def stuck(main, err):
    print("merged %s, rollback failed: %s" % (git(main, "rev-parse", "HEAD").stdout.strip(), err))
    return 1


def run_check(cmd, main):
    """A check timeout is a red check: code 1 and the timeout line as its output."""
    try:
        return run(cmd, main, True)
    except Timeout as t:
        return 1, str(t)


def overwritten(main, branch):
    """Untracked files of MAIN that the branch adds, edits or retypes: (paths, error text). Git treats an ignored file as
    expendable, so such a merge (a branch cut before an ignore line that touches an archived file) overwrites MAIN's
    copy, and `merge --abort` or the rollback reset deletes it, whatever its content."""
    base = git(main, "merge-base", "HEAD", branch)
    if base.returncode:
        return [], "merge-base: " + base.stderr.strip()
    diff = git(main, "diff", "--name-only", "-z", "--no-renames", "--diff-filter=d", base.stdout.strip(), branch)
    if diff.returncode:
        return [], "diff: " + diff.stderr.strip()
    ls = git(main, "ls-files", "-z")
    if ls.returncode:
        return [], "ls-files: " + ls.stderr.strip()
    tracked = set(ls.stdout.split("\0"))
    return [f for f in diff.stdout.split("\0") if f and f not in tracked and os.path.lexists(os.path.join(main, f))], ""


def land_local(main, wt, cid, checks):
    main, wt = os.path.abspath(main), os.path.abspath(wt)
    branch = "change/" + cid
    r = git(main, "status", "--porcelain", "--untracked-files=no")
    if r.returncode:
        print("not merged: status: " + r.stderr.strip())
        return 1
    dirty = [l[3:] for l in r.stdout.splitlines()]
    if dirty:
        print("not merged: main folder not clean: " + ", ".join(dirty))
        return 2
    pr = load_pr()
    if pr is None:
        print("not merged: no sdd-pr.py next to the script")
        return 1
    try:
        human = pr.read_settings(main)["delivery.merge-by"][0] == "human"
    except (OSError, ValueError) as e:
        print("not merged: settings: %s" % e)
        return 1
    if human:  # a person merges the branch; it and the worktree stay
        print("not merged: %s: branch %s" % (pr.HUMAN, branch))
        return 8
    code, msg = owner_wait(pr, main, wt, branch)
    if code:
        print(msg)
        return code
    r = git(main, "rev-parse", "HEAD")
    if r.returncode:
        print("not merged: rev-parse: " + r.stderr.strip())
        return 1
    prev = r.stdout.strip()
    over, err = overwritten(main, branch)
    if err:
        print("not merged: " + err)
        return 1
    if over:
        print("not merged: merge would overwrite untracked files: " + ", ".join(over))
        return 6
    r = git(main, "merge", "-q", "--no-ff", "--no-edit", branch)
    if r.returncode:
        files = git(main, "diff", "--name-only", "--diff-filter=U").stdout.split()
        if files:
            git(main, "merge", "--abort")
            print("not merged: merge conflict: " + ", ".join(files))
            return 6
        # any other failure, a timeout or a hook included: back to prev from whatever git left (a merge commit,
        # a staged tree, MERGE_HEAD); MAIN was clean before the merge and nothing was transported yet
        git(main, "merge", "--quit")
        r2 = git(main, "reset", "--merge", prev)
        print("not merged: merge: " + (r.stderr.strip() or r.stdout.strip()))
        return stuck(main, "reset: " + r2.stderr.strip()) if r2.returncode else 1
    code, out = wt_run("transport", main, wt)
    if code:
        if code == 3:
            m = re.search(r"conflict, MAIN not changed: (.*)", out)
            reason, rc = "not merged: transport conflict: " + (m.group(1).strip() if m else ""), 6
            r = git(main, "reset", "--keep", prev)  # on conflict transport did not change MAIN
            err = "reset: " + r.stderr.strip() if r.returncode else ""
        else:
            reason, rc = "not merged: transport: " + out.strip(), 1
            err = rollback(main, wt, prev)
        print(reason)
        if err:
            return stuck(main, err)
        return rc
    try:
        vcmd, why = validate_cmd(main), NOT_FOUND
    except Timeout as t:
        vcmd, why = None, str(t)
    if vcmd is None:
        err = rollback(main, wt, prev)
        print("not merged: " + why)
        return stuck(main, err) if err else 1
    for cmd in checks + [vcmd]:
        code, out = run_check(cmd, main)
        if not code:
            continue
        err = rollback(main, wt, prev)
        if err:
            print("check red: " + cmd)
            for l in tail(out, 20):
                print("    " + l)
            return stuck(main, err)
        code2, out2 = run_check(cmd, main)
        if code2:
            print("main red: " + cmd)
            lines = tail(out2, 20)
            rc = 4
        else:
            print("not merged: check red with the change: " + cmd)
            lines = tail(out, 20)
            rc = 3
        for l in lines:
            print("    " + l)
        return rc
    r = git(main, "rev-parse", "HEAD")
    if r.returncode:
        print("merged, not cleaned: rev-parse: " + r.stderr.strip())
        return 1
    h = r.stdout.strip()
    code, out = wt_run("remove", main, wt)
    if code:
        print("merged %s, not cleaned: remove: %s" % (h, out.strip()))
        return 1
    r = git(main, "branch", "-d", branch)
    if r.returncode:
        print("merged %s, not cleaned: branch -d: %s" % (h, r.stderr.strip()))
        return 1
    print("merged " + h)
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
