#!/usr/bin/python3
"""Live scenario of change project-config, steps 1-5: `solo-sdd config`, the dispatch plan and the stop hook.

A temporary git repository made by `solo-sdd init`; PATH is a stand bin folder with a `solo-sdd` command running the
package of this tree, then /usr/bin and /bin. HOME is a temporary folder (the hook log goes there).
1. `config list`: every registered key with `default`; `config set mode team`: `delivery.mode pr mode`.
2. A comment line and a key in solo-sdd/config, then `config set dispatch.limit 3`: `git diff` shows one changed line.
3. `config set delivery.mode cloud`: exit 1, `local, pr`, `git diff` empty; a line without a colon: `config list`
   names `solo-sdd/config:<n>`.
4. sdd_dispatch_plan.py with `dispatch.limit: 3` and `Orchestrators: 2` in AGENTS.md: `limit: 3`; without the file: `limit: 2`.
5. The stop hook on an English last answer with `reply.language: ru`: returns the agent once with the language reason;
   without the key and with SOLO_SDD_REPLY_LANG=ru: the same.
Run from the repository root: python3 tests/stands/project-config.py. Temporary folders are removed; the last line is
the summary."""
import json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOOK, PLAN = str(ROOT / "global" / "work_hooks.py"), str(ROOT / "global" / "sdd_dispatch_plan.py")
PY = "/usr/bin/python3"
EN = "All done. The settings were moved into one file and the change is complete, tests pass, nothing else to do."
ok = True


def step(name, good, detail):
    global ok
    ok &= bool(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail.strip().replace("\n", " | ")))


def call(env, cwd, *args, inp=None):
    p = subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True, timeout=120,
                       input=inp, stdin=None if inp is not None else subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def reason(out):
    """The language line of a stop hook answer."""
    lines = json.loads(out)["reason"].splitlines() if out else ["no answer"]
    return next((l for l in lines if "not in" in l), lines[-1])


def main():
    tmp = tempfile.mkdtemp(prefix="project-config-")
    try:
        t, home, bindir = (os.path.join(tmp, n) for n in ("proj", "home", "bin"))
        for d in (t, home, bindir):
            os.makedirs(d)
        with open(os.path.join(bindir, "solo-sdd"), "w") as f:
            f.write("#!/bin/sh\nPYTHONPATH=%s exec %s -m solo_sdd \"$@\"\n" % (ROOT, PY))
        os.chmod(os.path.join(bindir, "solo-sdd"), 0o755)
        env = {"PATH": bindir + ":/usr/bin:/bin", "HOME": home, "LANG": "C.UTF-8"}
        git = lambda *a: call(env, t, "git", "-c", "user.name=t", "-c", "user.email=t@t", *a)[1]
        sdd = lambda *a: call(env, t, "solo-sdd", *a)
        git("init", "-q", "-b", "main")
        code, out = sdd("init")
        step("init", code == 0 and "created solo-sdd/changes/" in out, out)
        cfg = os.path.join(t, "solo-sdd", "config")

        code, out = sdd("config", "list")
        lines = out.splitlines()
        step("1 list", code == 0 and len(lines) == 6 and all(l.endswith(" default") for l in lines), out)
        sdd("config", "set", "mode", "team")
        out = sdd("config", "list")[1]
        step("1 team", "delivery.mode pr mode" in out.splitlines(), out)

        with open(cfg, "w") as f:
            f.write("# stand settings\nmode: team\ndispatch.limit: 2\n")
        git("add", "-A")
        git("commit", "-qm", "init")
        code, _ = sdd("config", "set", "dispatch.limit", "3")
        diff = git("diff", "-U0", "--", "solo-sdd/config")
        changed = [l for l in diff.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---"))]
        step("2 one line", code == 0 and changed == ["-dispatch.limit: 2", "+dispatch.limit: 3"], " ".join(changed))
        git("commit", "-qam", "limit")

        code, out = sdd("config", "set", "delivery.mode", "cloud")
        step("3 wrong value", code == 1 and "local, pr" in out and git("diff") == "", "exit %d: %s" % (code, out))
        with open(cfg, "a") as f:
            f.write("delivery.mode pr\n")
        code, out = sdd("config", "list")
        step("3 broken line", code == 1 and "solo-sdd/config:4" in out, "exit %d: %s" % (code, out))

        with open(cfg, "w") as f:
            f.write("dispatch.limit: 3\n")
        with open(os.path.join(t, "AGENTS.md"), "w") as f:
            f.write("# P\n\n## Working copy\n\n- Orchestrators: 2\n")
        first = call(env, None, PY, PLAN, t)[1].splitlines()[0]
        os.remove(cfg)
        second = call(env, None, PY, PLAN, t)[1].splitlines()[0]
        step("4 limit", first.startswith("limit: 3,") and second.startswith("limit: 2,"), first + " / " + second)

        stop = lambda sid, e: call(e, None, PY, HOOK, "stop", inp=json.dumps(
            {"session_id": sid, "cwd": t, "last_assistant_message": EN}))[1]
        with open(cfg, "w") as f:
            f.write("reply.language: ru\n")
        a, b = stop("stand-cfg", env), stop("stand-cfg", env)
        step("5 config", "Rewrite it in Russian" in a and b == "", reason(a))
        with open(cfg, "w") as f:
            f.write("# no language\n")
        e = dict(env, SOLO_SDD_REPLY_LANG="ru")
        a, b = stop("stand-env", e), stop("stand-env", e)
        step("5 variable", "Rewrite it in Russian" in a and b == "", reason(a))
        log = os.path.join(home, ".claude", "hook-state", "errors.log")
        step("5 no hook errors", not os.path.exists(log), open(log).read() if os.path.exists(log) else "no errors.log")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("project-config stand: %s" % ("all steps passed" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
