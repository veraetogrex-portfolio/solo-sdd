#!/usr/bin/env python3
"""Runs solo-sdd's own test files: each file as its own process, files in parallel, the last failures first.

python3 tests/run.py [--jobs N] [--tier fast|slow|release] [FILE... | --failed | --affected PATH...]

Only the output of failed files is printed, one `ok`/`FAIL` line per file, a summary line and a `skipped:` line; the
code is 1 when a file fails and 2 on a usage error. --tier (default slow) sets SOLO_SDD_TESTS for every file, the
variable tests/marks.py reads; in the fast tier an unmarked test longer than 2 s fails its file. The failed files are
kept in tests/.last-failed, the map of --affected is tests/affected.json.
"""
import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STATE = HERE / ".last-failed"
MAP = HERE / "affected.json"
TIERS = ("fast", "slow", "release")
FAST_LIMIT = 2.0
# Runs a test file as `python3 <file>` would, with a timer around every unittest.TestCase.run; the rows
# `<seconds>\t<skipped 0|1>\t<test id>` go to the file SOLO_SDD_TIMES names (Python 3.9 has no unittest --durations).
BOOT = """import os, runpy, sys, time, unittest
f, out = sys.argv[1], os.environ.pop("SOLO_SDD_TIMES")
sys.argv, sys.path[0], rows, run, depth = [f], os.path.dirname(f), [], unittest.TestCase.run, [0]
def timed(self, result=None):
    n, t = len(getattr(result, "skipped", ())), time.monotonic()
    depth[0] += 1
    try:
        return run(self, result)
    finally:
        depth[0] -= 1
        if not depth[0]:  # a test case a test runs inside itself is part of that test
            rows.append("%.3f\\t%d\\t%s\\n" % (time.monotonic() - t, len(getattr(result, "skipped", ())) > n, self.id()))
unittest.TestCase.run = timed
try:
    runpy.run_path(f, run_name="__main__")
finally:
    with open(out, "w", encoding="utf-8") as h:
        h.writelines(rows)
"""


def suite():
    return sorted((HERE / p.name).relative_to(ROOT).as_posix() for p in HERE.glob("test_*.py") if p.is_file())


def read_state(path=STATE):
    """The state file text, or None when it cannot be read."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def plan(selected, state_text):
    """Each selected file once, the files the state names first."""
    failed = set((state_text or "").splitlines())
    sel = list(dict.fromkeys(selected))
    return [f for f in sel if f in failed] + [f for f in sel if f not in failed]


def next_state(files, selected, state_text, failures):
    """This run's failures plus the earlier failures of existing files this run did not select."""
    sel, known = set(selected), set(files)
    old = [f for f in dict.fromkeys((state_text or "").splitlines()) if f in known and f not in sel]
    return list(dict.fromkeys(failures)) + [f for f in old if f not in failures]


def affected(paths, files, amap):
    """The files the map gives for the paths, the always-run files and the files the map names nowhere.

    A path is a repository path; a folder takes the keys that hold it and the keys inside it."""
    keys, always = amap["map"], amap["always"]
    named = set(always) | {t for v in keys.values() for t in v}
    out = set(always) | {f for f in files if f not in named}
    for p in paths:
        p = Path(os.path.normpath(ROOT / p))  # a repository path; an absolute one stays as it is
        try:
            p = p.relative_to(ROOT).as_posix()
        except ValueError:
            return files
        hits = [k for k in keys if k == p or (k.endswith("/") and (p + "/").startswith(k)) or k.startswith(p + "/")]
        if not hits:
            return files
        for k in hits:
            out |= set(keys[k])
    return [f for f in files if f in out]


def resolve(name, files):
    for base in (Path.cwd(), ROOT):
        p = Path(os.path.abspath(base / name))
        if p.parent == HERE and p.is_file():
            r = p.relative_to(ROOT).as_posix()
            if r in files:
                return r
    return None


def jobs(text):
    if not (text.isascii() and text.isdigit()) or int(text) < 1:
        raise argparse.ArgumentTypeError(f"not a whole number above 0: {text!r}")
    return int(text)


def read_times(path):
    """The (seconds, skipped, test id) rows of the timer; a row it cannot read is left out."""
    rows = []
    for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        secs, skipped, tid = (ln.split("\t", 2) + ["", ""])[:3]
        try:
            rows.append((float(secs), skipped == "1", tid[len("__main__."):] if tid.startswith("__main__.") else tid))
        except ValueError:
            pass
    return rows


def run_one(f, tier="slow"):
    """Code, output, seconds and per-test timer rows of one file run in the tier."""
    fd, times = tempfile.mkstemp(prefix="solo-sdd-times-")
    os.close(fd)
    try:
        start = time.monotonic()
        p = subprocess.run([sys.executable, "-c", BOOT, str(ROOT / f)], cwd=ROOT, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           env=dict(os.environ, SOLO_SDD_TESTS=tier, SOLO_SDD_TIMES=times))
        secs = time.monotonic() - start
        return f, p.returncode, p.stdout, secs, read_times(times)
    finally:
        os.unlink(times)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tests/run.py", description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*", help="test files to run alone")
    ap.add_argument("--jobs", type=jobs, default=os.cpu_count() or 1, help="files at once (default: the cores)")
    ap.add_argument("--tier", choices=TIERS, default="slow", help="the marked tests to run (default: slow)")
    ap.add_argument("--failed", action="store_true", help="only the files that failed before")
    ap.add_argument("--affected", nargs="+", metavar="PATH", help="only the files the map gives for these paths")
    a = ap.parse_args(argv)
    if sum((bool(a.files), a.failed, a.affected is not None)) > 1:
        ap.error("file names, --failed and --affected exclude each other")
    files = suite()
    state = read_state()
    if a.files:
        bad = [n for n in a.files if resolve(n, files) is None]
        if bad:
            ap.error("not a test_*.py file of " + HERE.relative_to(ROOT).as_posix() + "/: " + ", ".join(bad))
        selected = [resolve(n, files) for n in a.files]
    elif a.failed:
        selected = [f for f in files if f in set((state or "").splitlines())]
    elif a.affected:
        try:
            amap = json.loads(MAP.read_text(encoding="utf-8"))
            selected = affected(a.affected, files, amap)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
            print(f"map {MAP.name} unreadable ({type(e).__name__}): the whole suite runs", file=sys.stderr)
            selected = files
    else:
        selected = files
    order = plan(selected, state)
    failures, skipped, start, out = [], 0, time.monotonic(), sys.stdout.buffer
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        for fut in concurrent.futures.as_completed([pool.submit(run_one, f, a.tier) for f in order]):
            f, code, text, secs, rows = fut.result()
            skipped += sum(1 for _, k, _ in rows if k)
            over = [(s, t) for s, k, t in rows if a.tier == "fast" and not k and s > FAST_LIMIT]
            if over:
                text = (text if code else b"") + "".join(
                    f"{t} took {s:.1f} s, over the {FAST_LIMIT:.0f} s of the fast tier: mark it slow (tests/marks.py)\n"
                    for s, t in over).encode()
                code = code or 1
            if code:
                failures.append(f)
                out.write(text if text.endswith(b"\n") or not text else text + b"\n")
            out.write(f"{'FAIL' if code else 'ok'} {f} ({secs:.1f} s)\n".encode())
            out.flush()
    out.write(f"files: {len(order)}, failed: {len(failures)}, seconds: {time.monotonic() - start:.1f}\n".encode())
    out.write(f"skipped: {skipped}\n".encode())
    try:
        STATE.write_text("".join(f + "\n" for f in next_state(files, order, state, failures)), encoding="utf-8")
    except OSError as e:
        print(f"state {STATE.name} not written: {e}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
