"""`solo-sdd check --point <checks|ship> [--changed]`: runs the enabled integrations of a point and records the result
by the git tree of the working copy under ~/.local/share/solo-sdd/checks/<repo>/<tree>.json; `check --point
<review|audit> [--changed] [--tag <tag>]` runs nothing and lists the material files of the point: without --tag of the
names of `integrations`, with it of every enabled integration with that tag, the bundled ones included.

An integration's command and output are foreign input: the command runs in its own process group bounded by its
`timeout`, at most MAX_OUTPUT bytes of its output are read, and the output is kept as plain text.
"""
import datetime
import fnmatch
import hashlib
import json
import os
import re
import select
import shutil
import signal
import stat
import subprocess
import tempfile
import time
import types
import unicodedata

from solo_sdd import integrations as I, process_format as pf, settings
from solo_sdd.settings import read_settings

RUN_POINTS = ("checks", "ship")
COMMANDS_FILE = "commands.json"
MAX_OUTPUT = 1 << 20
MAX_LINE = 400
GRACE = 1
DROPPED = ("Cc", "Cf", "Zl", "Zp")  # removed from output lines, tab excepted


def clean_line(line):
    return "".join(c for c in line if c == "\t" or unicodedata.category(c) not in DROPPED)[:MAX_LINE]


def plain(line):
    """True for a recorded line a run could have written: no character clean_line drops and no lone surrogate."""
    return isinstance(line, str) and not any(c != "\t" and unicodedata.category(c) in DROPPED + ("Cs",) for c in line)


def clean(data):
    """Output bytes as text lines: not UTF-8 replaced, control characters but tab removed, each line cut at MAX_LINE,
    trailing empty lines dropped."""
    lines = [clean_line(ln) for ln in data.decode("utf-8", "replace").replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


# The tree hash, the changed files and the record lookup below are copied into global/work_hooks.py (deployed alone): edit them here,
# then run python3 scripts/sync_blocks.py.
# tree-hash:begin
# needs: import hashlib, json, os, re, shutil, stat, subprocess, tempfile; read_settings of the settings block
CHECKS_DIR = os.path.join(".local", "share", "solo-sdd", "checks")
MAX_RECORD = 4 << 20
GIT_TIMEOUT = 120


class CheckError(Exception):
    pass


def git(root, *args, env=None):
    try:
        p = subprocess.run(["git", "-C", root, *args], capture_output=True, env=env, stdin=subprocess.DEVNULL,
                           timeout=GIT_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise CheckError("git %s: no answer in %d s" % (args[0], GIT_TIMEOUT))
    if p.returncode:
        raise CheckError("git %s: %s" % (args[0], p.stderr.decode("utf-8", "replace").strip()))
    return p.stdout


def tree_hash(root):
    """The git tree of the whole working copy (tracked files and untracked not ignored ones), built in a copy of the
    real index so the real one stays untouched."""
    tmp = tempfile.mkdtemp(prefix="solo-sdd-index-")
    try:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(tmp, "index"))
        real = os.path.join(root, git(root, "rev-parse", "--git-path", "index").decode().strip())
        if os.path.exists(real):  # tracked files that match an ignore pattern stay in the tree
            # copy2 keeps the index time: git rereads a file no older than the index, a fresh copy hides such an edit
            shutil.copy2(real, env["GIT_INDEX_FILE"])
        git(root, "add", "-A", env=env)
        return git(root, "write-tree", env=env).decode().strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def repo_dir(root, home):
    """The records folder of the repository: its folder name and a short digest of its absolute path."""
    path = os.path.realpath(root)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(path)) or "_"
    return os.path.join(home, CHECKS_DIR, "%s-%s" % (name, hashlib.sha256(path.encode("utf-8", "surrogateescape"))
                                                     .hexdigest()[:12]))


def read_json(path):
    """The object of a JSON file; {} for a missing, truncated, too large, too deep or non-JSON file, one that is not
    an object, or one that is not a regular file (a FIFO is not waited on)."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_RECORD:
                return {}
            with os.fdopen(fd, "rb") as f:
                fd = None
                data = json.loads(f.read(MAX_RECORD + 1))
        finally:
            if fd is not None:
                os.close(fd)
    except (OSError, ValueError, RecursionError):
        return {}
    return data if isinstance(data, dict) else {}


def base_ref(root):
    """The merge base of HEAD with the base branch (delivery.base, else origin's default branch), else HEAD, else None
    for a repository without commits."""
    base = read_settings(root)["delivery.base"][0]
    for ref in (["origin/" + base, base] if base else ["refs/remotes/origin/HEAD"]):
        try:
            return git(root, "merge-base", "HEAD", ref).decode().strip()
        except CheckError:
            pass
    try:
        git(root, "rev-parse", "--verify", "-q", "HEAD")
        return "HEAD"
    except CheckError:
        return None


def changed_files(root):
    """Sorted paths from the root that differ between the working copy and base_ref, untracked not ignored included."""
    ref = base_ref(root)
    out = git(root, "diff", "--name-only", "-z", "--relative", ref) if ref else git(root, "ls-files", "-z")
    out += git(root, "ls-files", "--others", "--exclude-standard", "-z")
    return sorted({os.fsdecode(p) for p in out.split(b"\0") if p})
# tree-hash:end


def write_json(path, data):
    """Writes data through a new file and a rename; an existing target that is not writable is refused like a plain
    write. False with the reason printed when it fails."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.lexists(path) and not os.access(path, os.W_OK):
            raise PermissionError("not writable")
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1, sort_keys=True)
            os.replace(tmp, path)
        except BaseException:
            os.unlink(tmp)
            raise
    except OSError as e:
        print("record not written: %s: %s" % (path, e.strerror or e))
        return False
    return True


def last_runs(root, home):
    """{name: (status, date)} of each integration's newest PASS or FAIL in the records of the repository at root: a
    point's result is dated by the point's `time`, or by its file's write in a record without one; a SKIP is not a
    run. The date is local."""
    folder, best = repo_dir(root, home), {}
    try:
        names = [n for n in os.listdir(folder) if n.endswith(".json") and n != COMMANDS_FILE]
    except OSError:
        return {}
    for n in names:
        path = os.path.join(folder, n)
        try:
            written = os.stat(path).st_mtime
        except OSError:
            continue
        points = read_json(path).get("points")
        for point in (points.values() if isinstance(points, dict) else ()):
            if not isinstance(point, dict) or not isinstance(point.get("results"), list):
                continue
            when = point.get("time")
            when = when if type(when) in (int, float) and 0 <= when < 1e11 else written
            for r in point["results"]:
                if isinstance(r, dict) and isinstance(r.get("name"), str) and r.get("status") in ("PASS", "FAIL"):
                    if r["name"] not in best or when > best[r["name"]][0]:
                        best[r["name"]] = (when, r["status"])
    return {k: (status, datetime.date.fromtimestamp(when).isoformat()) for k, (when, status) in best.items()}


RESULT = "Result"
LINE_BREAK = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+\Z")  # the lines of read_lines, each with its break


def result_line(point, tree, results):
    return "Integrations %s (tree %s): %s" % (point, tree, ", ".join("%s %s" % (r["name"], r["status"]) for r in results))


def put_line(text, point, line):
    """text with `line` as the only `Integrations <point> (tree ` line of its ## Result section: the first such line
    replaced in place and the others removed, else the line added after the section's last non-blank line. Sections,
    code blocks and comments are read by the doc reader. Raises ValueError when there is no ## Result section, a line
    of the point holds a comment, or the added line would stand inside a comment or a code block."""
    def view(t):  # the doc reader on a text, not a file
        return pf.read_doc(types.SimpleNamespace(read_text=lambda encoding=None: t[1:] if t[:1] == "\ufeff" else t))

    segs, lines = LINE_BREAK.findall(text), view(text)
    mask = pf.fence_mask(lines)
    heads = [i for i in range(len(segs)) if not mask[i] and pf.H2.match(lines[i])]
    start = next((i for i in heads if pf.H2.match(lines[i]).group(1) == RESULT), None)
    if start is None:
        raise ValueError("no ## %s section" % RESULT)
    end = next((i for i in heads if i > start), len(segs))
    prefix = "Integrations %s (tree " % point
    mine = [k for k in range(start + 1, end) if not mask[k] and lines[k].startswith(prefix)]
    mixed = [k for k in mine if segs[k].rstrip("\r\n") != lines[k]]
    if mixed:
        raise ValueError("line %d: an %s line holds a comment" % (mixed[0] + 1, prefix.split(" (")[0]))
    if mine:
        k = mine[0]
        segs[k] = line + segs[k][len(segs[k].rstrip("\r\n")):]
        for j in reversed(mine[1:]):
            del segs[j]
        return "".join(segs)
    brk = segs[start][len(segs[start].rstrip("\r\n")):] or "\n"
    k = max([j for j in range(start + 1, end) if segs[j].strip()] or [start]) + 1
    if not segs[k - 1].endswith(("\n", "\r")):
        segs[k - 1] += brk
    segs.insert(k, line + brk)
    out = "".join(segs)
    after = view(out)
    if pf.fence_mask(after)[k] or after[k] != line:
        raise ValueError("a line added to ## %s would stand inside a comment or a code block" % RESULT)
    return out


def result_file(tree, name, point):
    """The verification.md path of the open change `name` when a line of `point` can be put into its ## Result
    section; raises CheckError naming the change otherwise."""
    folder = tree / "changes" / name
    if not pf.CHANGE_ID.fullmatch(name) or name == "archive" or not folder.is_dir():
        raise CheckError("no change %s in %s/changes" % (name, pf.TREE))
    path = folder / "verification.md"
    try:
        if not path.is_file():
            raise ValueError("no such file")
        put_line(path.read_bytes().decode("utf-8"), point, "Integrations %s (tree x): x PASS" % point)
    except (OSError, ValueError) as e:  # UnicodeDecodeError is a ValueError
        raise CheckError("change %s: %s/changes/%s/verification.md: %s" % (name, pf.TREE, name, e))
    return path


def write_result(path, point, tree, entry, root, home):
    """Puts the line of this run (entry: the point's record) into the ## Result section; the line changes the working
    tree, so the point is recorded under the new tree too, which the `stop` hook and a repeated run look up. False with
    the reason printed when it fails."""
    try:
        text = put_line(path.read_bytes().decode("utf-8"), point, result_line(point, tree, entry["results"]))
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
    except (OSError, ValueError) as e:
        print("Result line not written: %s: %s" % (path, e))
        return False
    try:
        new = tree_hash(root)
    except (OSError, CheckError) as e:
        print("Result line written, not recorded under the new tree: %s" % e)
        return False
    if new != tree:
        alias = os.path.join(repo_dir(root, home), new + ".json")
        record = read_json(alias)
        record["tree"] = new
        record["points"] = dict(record["points"] if isinstance(record.get("points"), dict) else {}, **{point: entry})
        write_json(alias, record)
    return True


def stop(group):
    """Kills a process group; a group already gone is fine."""
    try:
        os.killpg(group, signal.SIGKILL)
    except OSError:
        pass


def execute(command, root, env, stdin, timeout):
    """(exit code, output bytes, why it was stopped or None): `/bin/sh -c command` in root, stdin bytes on stdin,
    stdout and stderr together. The run's process group is led by a keeper process that is reaped only after the
    group is killed, so the group id is never free (and never someone else's) when it is killed. Over timeout or
    MAX_OUTPUT the whole group is killed; once the command exits its leftover children are killed too, and a pipe
    still held from outside the group is read for at most GRACE seconds more."""
    keeper = subprocess.Popen(["/bin/sh", "-c", "read x"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, preexec_fn=os.setpgrp)
    try:
        group = keeper.pid
        with tempfile.TemporaryFile() as inp:
            inp.write(stdin)
            inp.seek(0)
            p = subprocess.Popen(["/bin/sh", "-c", command], cwd=root, env=env, stdin=inp, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, preexec_fn=lambda: os.setpgid(0, group))
        end, out, why, grace, eof = time.monotonic() + timeout, bytearray(), None, None, False
        try:
            fd = p.stdout.fileno()
            while True:
                now = time.monotonic()
                if now >= end:
                    why = "timeout %ds" % timeout
                    break
                if grace is None and p.poll() is not None:
                    stop(group)
                    grace = now + GRACE
                if grace is not None and (eof or now >= grace):
                    break
                if eof:
                    time.sleep(min(0.05, end - now))
                elif select.select([fd], [], [], min(end - now, 0.1))[0]:
                    chunk = os.read(fd, min(65536, MAX_OUTPUT + 1 - len(out)))
                    eof = not chunk
                    out += chunk
                    if len(out) > MAX_OUTPUT:
                        del out[MAX_OUTPUT:]
                        why = "output over %d bytes" % MAX_OUTPUT
                        break
        finally:
            stop(group)
            p.stdout.close()
            p.wait()
    finally:
        stop(keeper.pid)
        keeper.stdin.close()
        keeper.wait()
    return p.returncode, bytes(out), why


def digest(entry):
    """The digest of an enabled description: its source and read fields, or its error."""
    data = {"source": entry["source"], "fields": entry["fields"], "error": entry["error"]} if entry else "not found"
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def run_one(name, entry, point, root, files):
    """(status, lines, exit code, stopped) of one integration."""
    if entry is None:
        return "FAIL", ["FAIL %s: not found" % name], None, False
    if entry["error"]:
        return "FAIL", ["FAIL %s: %s" % (name, entry["error"])], None, False
    f = entry["fields"]
    if f["requires"] and shutil.which(f["requires"]) is None:
        status = "SKIP" if f["missing"] == "warn" else "FAIL"
        return status, ["%s %s: %s not found" % (status, name, f["requires"])], None, False
    env = dict(os.environ, SOLO_SDD_INTEGRATION_DIR=os.path.abspath(entry["dir"]), SOLO_SDD_POINT=point)
    stdin = b"".join(os.fsencode(p) + b"\n" for p in files)
    code, out, why = execute(f["command"], root, env, stdin, f["timeout"])
    lines = clean(out)
    while lines and not lines[0].strip():
        lines.pop(0)
    status = "PASS" if code == 0 and why is None else "FAIL"
    head = why or (lines.pop(0).strip() if lines else "exit %d" % code)
    rest = ["  " + ln for ln in lines[:f["output"]]] if status == "FAIL" else []
    return status, ["%s %s: %s" % (status, name, head)] + rest, code, why is not None


def applies(entry, files):
    """True when an integration's applies (empty: any) matches one of files."""
    return any(fnmatch.fnmatchcase(p, g) for p in files for g in (entry["fields"]["applies"] or ["*"]))


def material(chosen, changed, root):
    """The exit code of `check --point <review|audit> [--changed]`: one `MATERIAL <name>: <absolute path>` line per
    chosen integration, no command started; a missing name, a broken description or a missing file is a FAIL."""
    if changed:
        try:
            files = changed_files(root)
        except (CheckError, OSError, ValueError) as e:
            print(e)
            return 1
        chosen = {n: e for n, e in chosen.items() if not (e and e["fields"]) or applies(e, files)}
        if not chosen:
            print("no integration applies to the changed files")
            return 0
    code = 0
    for name in sorted(chosen):
        e = chosen[name]
        path = e and e["fields"] and os.path.abspath(os.path.join(e["dir"], e["fields"]["material"]))
        why = "not found" if e is None else e["error"] or (
            None if os.path.isfile(path) else "material %s not found" % e["fields"]["material"])
        print("FAIL %s: %s" % (name, why) if why else "MATERIAL %s: %s" % (name, path))
        code = code or (1 if why else 0)
    return code


def tagged(point, tag, root, cwd, home):
    """The exit code of `check --point <review|audit> --tag <tag>`: the material of every enabled integration of the
    point with the tag, in the project at root, or of the bundled ones when root is None (cwd: the folder it runs in;
    an owner folder shadows a bundled one there too, and is not enabled without a project).
    An enabled name with no readable description is a FAIL, since its tags cannot be read."""
    try:
        found = settings.parse_settings(settings.read_settings_text(root)) if root else {}
    except (OSError, ValueError) as e:
        print(e)
        return 1
    entries = I.find_integrations(root or cwd, home, I.all_sources()[0 if root else 1:])
    unread = [e for e in entries if not e["name"]]  # a source it cannot list may hold a shadowing copy
    if unread:
        for e in unread:
            print("FAIL -: %s" % e["error"])
        return 1
    used = {e["name"]: e for e in entries if e["name"] and not e["shadowed"]}
    chosen = {n: used.get(n) for n in I.enabled_names(entries, found)
              if n not in used or used[n]["error"] or (point in used[n]["fields"]["points"]
                                                       and tag in used[n]["fields"]["tags"])}
    if not chosen:
        print("no integrations enabled with the point %s and the tag %s" % (point, tag))
        return 0
    return material(chosen, False, root)


def check(point, changed, root, home, result=None):
    """The exit code of `check --point <point> [--changed]` in the project at root; prints the lines. With result (a
    verification.md path from result_file) the line of the run goes into its ## Result section."""
    try:
        listed = I.listed_names(settings.parse_settings(settings.read_settings_text(root)).get(I.LISTED, ""))
    except (OSError, ValueError) as e:
        print(e)
        return 1
    found = {e["name"]: e for e in I.find_integrations(root, home, I.all_sources()) if e["name"] and not e["shadowed"]}
    listed = [n for n in listed if n not in found or found[n]["source"] != "bundled"]  # integrations.off switches those
    if not listed:
        print("no integrations enabled")
        return 0
    chosen = {n: found.get(n) for n in listed
              if n not in found or found[n]["error"] or point in found[n]["fields"]["points"]}
    if not chosen:
        print("no enabled integration has the point %s" % point)
        return 0
    if point not in RUN_POINTS:
        return material(chosen, changed, root)
    try:
        files, tree = changed_files(root), tree_hash(root)
    except (CheckError, OSError, ValueError) as e:
        print(e)
        return 1
    odd = [p for p in files if "\n" in p]
    if odd:
        print("a changed path holds a newline and cannot be passed one per line: %s" % ascii(odd[0]))
        return 1
    if changed:
        chosen = {n: e for n, e in chosen.items() if not (e and e["fields"]) or applies(e, files)}
        if not chosen:
            print("no integration applies to the changed files")
            return 0
    key = {"changed": changed, "files": hashlib.sha256("\n".join(files).encode("utf-8", "surrogateescape"))
           .hexdigest(), "descriptions": {n: digest(e) for n, e in chosen.items()}}
    folder = repo_dir(root, home)
    path = os.path.join(folder, tree + ".json")
    record = read_json(path)
    old = record.get("points", {}).get(point) if isinstance(record.get("points"), dict) else None
    if (isinstance(old, dict) and old.get("key") == key and isinstance(old.get("lines"), list)
            and all(plain(ln) for ln in old["lines"]) and type(old.get("code")) is int
            and isinstance(old.get("results"), list)
            and all(isinstance(r, dict) and r.get("status") in ("PASS", "FAIL") and r.get("name") in chosen
                    and not r.get("stopped") for r in old["results"])):
        for ln in old["lines"]:
            print(ln)
        print("reused %s" % tree)
        return old["code"] if result is None or write_result(result, point, tree, old, root, home) else 1
    shown_path = os.path.join(folder, COMMANDS_FILE)
    shown = read_json(shown_path)
    code, lines, results = 0, [], []
    for name in sorted(chosen):
        e = chosen[name]
        if e and e["fields"] and e["source"] == "project" and shown.get(name) != e["fields"]["command"]:
            print("command %s: %s" % (name, e["fields"]["command"]))
            shown[name] = e["fields"]["command"]
        status, out, exit_code, stopped = run_one(name, e, point, root, files)
        for ln in out:
            print(ln)
        lines += out
        results.append({"name": name, "status": status, "exit": exit_code, "stopped": stopped})
        gate = not (e and e["fields"]) or e["fields"]["mode"] == "gate" or (exit_code is None and not stopped)
        if status == "FAIL" and gate:
            code = 1
    record["tree"] = tree
    if not isinstance(record.get("points"), dict):
        record["points"] = {}
    record["points"][point] = {"key": key, "lines": lines, "code": code, "results": results, "time": time.time()}
    write_json(path, record)
    write_json(shown_path, shown)
    return code if result is None or write_result(result, point, tree, record["points"][point], root, home) else 1


def run(args, cwd=".", home=None):
    """`check --point <point> [--changed] [--change <id>] [--tag <tag>]` arguments after `check` (--change only for
    checks and ship, --tag only for review and audit, not with --changed); the exit code, or None on bad arguments."""
    change = tag = None
    for flag in ("--change", "--tag"):
        if args.count(flag) > 1:
            return None
        if flag in args:
            i = args.index(flag)
            if i + 1 == len(args):
                return None
            value, args = args[i + 1], args[:i] + args[i + 2:]
            change, tag = (value, tag) if flag == "--change" else (change, value)
    rest = [a for a in args if a != "--changed"]
    if len(args) - len(rest) > 1 or len(rest) != 2 or rest[0] != "--point" or rest[1] not in I.INTEGRATION_POINTS:
        return None
    if change is not None and rest[1] not in RUN_POINTS:
        return None  # --change records a run, and the material points run nothing
    if tag is not None and (rest[1] in RUN_POINTS or "--changed" in args or not I.integration_name(tag)):
        return None
    home = home if home is not None else os.path.expanduser("~")
    tree = pf.find_tree(cwd)
    if tag is not None:
        return tagged(rest[1], tag, str(tree.parent) if tree else None, cwd, home)
    if tree is None:
        print("no solo-sdd/ tree")
        return 1
    try:
        result = None if change is None else result_file(tree, change, rest[1])
    except CheckError as e:
        print(e)
        return 1
    return check(rest[1], "--changed" in args, str(tree.parent), home, result)
