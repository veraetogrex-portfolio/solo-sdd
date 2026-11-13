#!/usr/bin/python3
"""Live scenario of change repo-own-format, steps 1-4: this repository runs on its own `solo-sdd/` tree.

A fresh `git clone` of this repository's HEAD in a temporary folder; PATH is /usr/bin:/bin (no `openspec`).
1. The clone has no `openspec/`; `python3 -m solo_sdd validate --all` prints `0 errors`.
2. `python3 -m solo_sdd list` names `drop-openspec` with its progress; every folder of `openspec/changes/archive`
   in the last commit that had `openspec/` is in `solo-sdd/changes/archive`.
3. Main specs that name `openspec`: only cli, foreign-import, process-tree, schema-build, skill-commands.
4. The SessionStart hook of `global/work_hooks.py` in the clone lists the open changes and has no import hint
   (the line `process in openspec/: run solo-sdd import openspec`).
Run from the repository root: python3 tests/stands/repo-own-format.py. The temporary folder is removed; the last line
is the summary."""
import json, os, pathlib, re, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
SUBJECT = ["cli", "foreign-import", "process-tree", "schema-build", "skill-commands"]
ok = True


def step(name, good, detail):
    global ok
    ok &= good
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def call(env, cwd, *args, inp=None):
    p = subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True, timeout=120,
                       input=inp, stdin=None if inp is not None else subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


with tempfile.TemporaryDirectory() as tmp:
    clone, home = os.path.join(tmp, "clone"), os.path.join(tmp, "home")
    os.makedirs(home)
    env = {k: v for k, v in os.environ.items() if k not in ("PATH", "PYTHONPATH", "CLAUDE_PROJECT_DIR")}
    env.update(PATH="/usr/bin:/bin", HOME=home, PYTHONPATH=clone)
    call(env, tmp, "git", "clone", "-q", str(ROOT), clone)

    code, out = call(env, clone, PY, "-m", "solo_sdd", "validate", "--all")
    step("1 no openspec/, validate", not os.path.exists(os.path.join(clone, "openspec")) and code == 0
         and out.strip().endswith("0 errors"), "openspec/ exists: %s; validate exit %d: %s" % (
             os.path.exists(os.path.join(clone, "openspec")), code, out.strip().splitlines()[-1] if out.strip() else ""))

    code, listing = call(env, clone, PY, "-m", "solo_sdd", "list")
    opened = [l.split()[0] for l in listing.splitlines() if l.strip()]
    last = call(env, clone, "git", "rev-list", "-n", "1", "HEAD", "--", "openspec")[1].strip()
    _, old = call(env, clone, "git", "ls-tree", "--name-only", "%s^:openspec/changes/archive" % last)
    old = set(old.split())
    new = set(os.listdir(os.path.join(clone, "solo-sdd/changes/archive")))
    drop = next((l.strip() for l in listing.splitlines() if l.startswith("drop-openspec ")), "")
    step("2 list and archive", code == 0 and bool(drop) and bool(old) and old <= new,
         "%d open changes, %s; archive: %d of %d old folders kept, new: %s" % (
             len(opened), drop or "no drop-openspec", len(old & new), len(old), " ".join(sorted(new - old)) or "none"))

    specs = pathlib.Path(clone, "solo-sdd/specs")
    named = sorted(p.parent.name for p in specs.glob("*/spec.md") if "openspec" in p.read_text(encoding="utf-8"))
    step("3 specs naming openspec", named == SUBJECT, " ".join(named))

    event = {"session_id": "repo-own-format-stand", "cwd": clone, "hook_event_name": "SessionStart"}
    code, out = call(env, None, PY, os.path.join(clone, "global", "work_hooks.py"), "context", inp=json.dumps(event))
    ctx = json.loads(out).get("hookSpecificOutput", {}).get("additionalContext", "") if code == 0 and out.strip() else ""
    lines = [l for l in ctx.splitlines() if re.match(r"- \S+ — tasks \d+/\d+", l)]
    listed = all(any(l.startswith("- %s " % c) for l in lines) for c in opened)
    hint = "process in openspec/" in ctx
    step("4 SessionStart context", bool(opened) and listed and not hint,
         "%d change lines, all open changes listed: %s, import hint: %s" % (len(lines), listed, hint))

print("summary: %s" % ("all 4 steps passed" if ok else "FAILED"))
sys.exit(0 if ok else 1)
