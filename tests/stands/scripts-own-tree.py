#!/usr/bin/python3
"""Live scenario of change scripts-own-tree, steps 1-4: the hooks and scripts of this tree on a `solo-sdd/` project.

A temporary git repository with solo-sdd/ made by `solo-sdd new` and two changes; PATH is a stand bin folder with a
`solo-sdd` command (the package of this tree, every call logged), /usr/bin and /bin: no `openspec` in it.
1. work_hooks.py context lists both changes and the project intent; a CLAIM of another session refuses an edit.
2. sdd_dispatch_plan.py issues both changes and prints no line about openspec.
3. `solo-sdd archive b --yes`, then sdd_dispatch.py accept of an `archived` status block: VALIDATE ran
   `solo-sdd validate --all`; the SubagentHandback guard accepts the ARCHIVE field.
4. A copy where solo-sdd/ is renamed to openspec/: the context lists the change and carries the import hint.
Run from the repository root: python3 tests/stands/scripts-own-tree.py. Temporary folders are removed; the last line
is the summary."""
import datetime, json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOOK, PLAN, DISPATCH = (str(ROOT / "global" / n) for n in ("work_hooks.py", "sdd_dispatch_plan.py", "sdd_dispatch.py"))
PY = "/usr/bin/python3"
TODAY = datetime.date.today().isoformat()
REQ = "### Requirement: %s\nThe system SHALL %s.\n\n#### Scenario: S\n- **WHEN** a\n- **THEN** b\n"
ok = True


def step(name, good, detail):
    global ok
    ok &= good
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def put(root, rel, text):
    p = pathlib.Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def call(env, cwd, *args, inp=None):
    p = subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True, timeout=120,
                       input=inp, stdin=None if inp is not None else subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, capture_output=True,
                          text=True, stdin=subprocess.DEVNULL, timeout=60).stdout


def fill(t, cid, impact, spec):
    put(t, "solo-sdd/changes/%s/proposal.md" % cid,
        "# Proposal\n\n## Why\n\nThe toy needs %s.\n\n## What Changes\n\n- %s.\n\n## Capabilities\n\n### New Capabilities\n\n"
        "### Modified Capabilities\n- `toy`\n\n## Impact\n\n`%s`\n\n## Out of Scope\n\n- Nothing.\n\n## Depends On\n\nnone\n\n"
        "## Source\n\n\"Add %s\" (the owner).\n" % (cid, cid, impact, cid))
    put(t, "solo-sdd/changes/%s/verification.md" % cid,
        "## Live Scenario\n\nRun the toy.\n\n## Needs\n\nnone\n\n## Fallback\n\nNot needed.\n\n## Result\n\nRan the toy.\n")
    put(t, "solo-sdd/changes/%s/specs/toy/spec.md" % cid, "## ADDED Requirements\n\n" + REQ % (spec, "do " + cid))


def hook(env, sub, event):
    code, out = call(env, None, PY, HOOK, sub, inp=json.dumps(event))
    return json.loads(out) if code == 0 and out.strip() else {}


with tempfile.TemporaryDirectory() as tmp:
    t, home, bin_dir = (os.path.join(tmp, n) for n in ("proj", "home", "bin"))
    for d in (t, home, bin_dir):
        os.makedirs(d)
    log = os.path.join(tmp, "solo-sdd.calls")
    put(bin_dir, "solo-sdd", '#!/bin/sh\necho "solo-sdd $*" >> "%s"\nPYTHONPATH="%s" exec %s -m solo_sdd "$@"\n'
        % (log, ROOT, PY))
    os.chmod(os.path.join(bin_dir, "solo-sdd"), 0o755)
    env = {k: v for k, v in os.environ.items() if k not in ("PATH", "PYTHONPATH", "CLAUDE_PROJECT_DIR")}
    env.update(PATH=os.pathsep.join([bin_dir, "/usr/bin", "/bin"]), HOME=home)
    no_openspec = shutil.which("openspec", path=env["PATH"]) is None

    git(t, "init", "-q", "-b", "main")
    put(t, "solo-sdd/project.md", "Intent: a toy project of the scripts-own-tree stand.\n")
    put(t, "solo-sdd/specs/toy/spec.md", "# toy Specification\n\n## Purpose\nA toy.\n\n## Requirements\n\n"
        + REQ % ("Base", "exist"))
    made = [call(env, t, "solo-sdd", "new", cid)[0] for cid in ("a", "b")]
    fill(t, "a", "a.py", "Alpha")
    fill(t, "b", "b.py", "Beta")
    put(t, "solo-sdd/changes/a/tasks.md", "## 1. Acceptance\n\n- [x] 1.1 Live\n- [ ] 1.2 Archive\n")
    git(t, "add", "-A")
    git(t, "commit", "-qm", "init")

    ctx = hook(env, "context", {"session_id": "S1", "cwd": t}).get("hookSpecificOutput", {}).get("additionalContext", "")
    claim = os.path.join(t, "solo-sdd/changes/a/CLAIM")
    put(t, "solo-sdd/changes/a/CLAIM", "claude %s session=OTHER\n" % TODAY)
    edit = {"session_id": "S1", "cwd": t, "tool_name": "Edit", "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": os.path.join(t, "solo-sdd/changes/a/tasks.md"), "old_string": "x", "new_string": "y"}}
    why = hook(env, "guard", edit).get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    os.remove(claim)
    step("1 context and CLAIM", made == [0, 0] and no_openspec and "Intent: a toy project" in ctx
         and "- a — tasks 1/2" in ctx and "- b — tasks 0/2" in ctx and "openspec" not in ctx
         and "taken by another agent" in why,
         "no openspec in PATH: %s; context: %s; edit refused: %s" % (
             no_openspec, " | ".join(l for l in ctx.splitlines() if l.startswith("- ")), why.split(":")[0]))

    code, out = call(env, t, PY, PLAN, t)
    step("2 dispatch plan", code == 0 and "launch: a b" in out and "openspec" not in out, out.strip().replace("\n", " | "))

    code, out = call(env, t, "solo-sdd", "archive", "b", "--yes")
    archive = "solo-sdd/changes/archive/%s-b" % TODAY
    vp = pathlib.Path(t, archive, "verification.md")  # accept takes LIVE from a code span of its Live Scenario
    vp.write_text("## Live Scenario\n\n1. `echo ok` prints ok.\n" + vp.read_text(encoding="utf-8").replace("## Live Scenario\n", "", 1),
                  encoding="utf-8")
    git(t, "add", "-A")
    git(t, "commit", "-qm", "archive b")
    st = os.path.join(tmp, "status.txt")
    pathlib.Path(st).write_text("STATUS: archived\nCHANGE: b\nWORKTREE: %s\n"
                                "VALIDATE: openspec validate --all --strict --no-interactive -> exit 0\n"
                                "LIVE: echo ok -> ok\nARCHIVE: %s\n" % (t, archive))
    if os.path.exists(log):
        os.remove(log)
    acode, aout = call(env, t, PY, DISPATCH, "accept", st)
    calls = pathlib.Path(log).read_text().splitlines() if os.path.exists(log) else []
    fields = dict(STATUS="archived", CHANGE="b", BRANCH="main", WORKTREE=t, COMMIT=git(t, "rev-parse", "HEAD").strip(),
                  ARCHIVE=archive, VALIDATE="solo-sdd validate --all -> exit 0", TESTS="all -> exit 0",
                  LIVE="python3 x.py -> ok", REVIEW="done", AGENTS="none", HOOKS="none", NOT_VERIFIED="nothing", NOTES="none")
    hb = hook(env, "guard", {"session_id": "S1", "cwd": t, "tool_name": "SubagentHandback",
                             "tool_input": {"message": "\n".join("%s: %s" % kv for kv in fields.items())}})
    step("3 archive and accept", code == 0 and acode == 0 and aout.strip() == "status matches"
         and calls == ["solo-sdd validate --all"] and not hb,
         "archive exit %d (%s); accept exit %d «%s», VALIDATE ran %s; handback %s" % (
             code, out.strip().splitlines()[-1], acode, aout.strip(), calls,
             "accepted" if not hb else hb["hookSpecificOutput"]["permissionDecisionReason"]))

    t2 = os.path.join(tmp, "legacy")
    shutil.copytree(t, t2, symlinks=True)
    os.rename(os.path.join(t2, "solo-sdd"), os.path.join(t2, "openspec"))
    ctx = hook(env, "context", {"session_id": "S2", "cwd": t2}).get("hookSpecificOutput", {}).get("additionalContext", "")
    step("4 legacy tree", "- a — tasks 1/2" in ctx and "process in openspec/: run solo-sdd import openspec" in ctx,
         " | ".join(l for l in ctx.splitlines() if l.startswith("- ") or "import openspec" in l))

print("scripts-own-tree stand: %s" % ("all steps passed" if ok else "FAILED"))
sys.exit(0 if ok else 1)
