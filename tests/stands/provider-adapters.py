#!/usr/bin/python3
"""Live scenario of change provider-adapters, steps 1-4, on temporary homes with the package of this tree.

PATH is a stand bin folder (fake `claude`/`codex` only where a step says so), then /usr/bin and /bin.
1. HOME a: `install --agents codex` -> no SKILL.md under ~/.claude, skills in ~/.codex/skills and ~/.agents/skills,
   `status` lists no ~/.claude copy, `doctor` prints `warn agent codex: no hooks`.
2. HOME b, fake `claude` and `codex` in PATH: `install` without flags deploys for both; spec-dispatch only in ~/.claude/skills.
3. HOME b: `uninstall` removes every copy recorded in the state.
4. HOME c, a git repository: `install --agents copilt` -> exit 1 with the known names, `git status` unchanged.
Run from the repository root: python3 tests/stands/provider-adapters.py. Temporary folders are removed; the last
line is the summary."""
import json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
ok = True


def step(name, good, detail):
    global ok
    ok &= bool(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail.strip().replace("\n", " | ")))


def call(home, path, *args, cwd=None):
    env = dict(os.environ, HOME=home, PATH=path + ":/usr/bin:/bin", PYTHONPATH=str(ROOT))
    p = subprocess.run(list(args), cwd=cwd or str(ROOT), env=env, capture_output=True, text=True, timeout=300,
                       stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def sdd(home, path, *args):
    return call(home, path, sys.executable, "-m", "solo_sdd", *args)


def skills(home, root):
    base = os.path.join(home, root)
    return sorted(d for d in os.listdir(base) if os.path.isfile(os.path.join(base, d, "SKILL.md"))) if os.path.isdir(base) else []


def count(home, sub):
    return sum(f == "SKILL.md" for _, _, fs in os.walk(os.path.join(home, sub)) for f in fs)


def main():
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="provider-adapters-"))
    try:
        empty, fake = os.path.join(tmp, "bin-empty"), os.path.join(tmp, "bin-agents")
        os.makedirs(empty)
        os.makedirs(fake)
        for name in ("claude", "codex"):
            with open(os.path.join(fake, name), "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(os.path.join(fake, name), 0o755)
        a, b, c = (os.path.join(tmp, n) for n in "abc")
        for h in (a, b, c):
            os.makedirs(h)

        code, out = sdd(a, empty, "install", "--agents", "codex")
        status = sdd(a, empty, "status")[1]
        doctor = sdd(a, empty, "doctor")[1]
        line = next((l for l in doctor.splitlines() if l.startswith(("ok agent codex", "warn agent codex"))), "no line")
        step("1 install --agents codex", code == 0 and count(a, ".claude") == 0 and skills(a, ".codex/skills")
             and skills(a, ".agents/skills") and "~/.claude" not in status and line.startswith("warn agent codex: no hooks"),
             "exit %s; SKILL.md under ~/.claude %d, ~/.codex/skills %d, ~/.agents/skills %d; status ~/.claude lines %d; %s"
             % (code, count(a, ".claude"), len(skills(a, ".codex/skills")), len(skills(a, ".agents/skills")),
                status.count("~/.claude"), line))

        code, out = sdd(b, fake, "install")
        with open(os.path.join(b, ".local/share/solo-sdd/state.json")) as f:
            agents = json.load(f).get("_agents")
        where = [r for r in (".claude/skills", ".codex/skills", ".agents/skills") if "spec-dispatch" in skills(b, r)]
        step("2 install, claude and codex in PATH", code == 0 and agents == ["claude", "codex", "other"]
             and skills(b, ".claude/skills") and skills(b, ".codex/skills") and where == [".claude/skills"],
             "exit %s; chosen %s; skills claude %d, codex %d, other %d; spec-dispatch in %s"
             % (code, ",".join(agents or []), len(skills(b, ".claude/skills")), len(skills(b, ".codex/skills")),
                len(skills(b, ".agents/skills")), ", ".join(where)))

        code, out = sdd(b, fake, "uninstall")
        with open(os.path.join(b, ".local/share/solo-sdd/state.json")) as f:
            left = [k for k in json.load(f) if not k.startswith("_")]
        total = count(b, "")
        step("3 uninstall", code == 0 and total == 0 and not left,
             "exit %s; %s; SKILL.md left %d, state entries left %d" % (code, out.strip().splitlines()[-1], total, len(left)))

        call(c, empty, "git", "init", "-q", cwd=c)
        before = call(c, empty, "git", "status", "--porcelain", "--untracked-files=all", cwd=c)[1]
        code, out = sdd(c, empty, "install", "--agents", "copilt")
        after = call(c, empty, "git", "status", "--porcelain", "--untracked-files=all", cwd=c)[1]
        step("4 install --agents copilt", code == 1 and "known: claude, codex, cursor, other" in out and before == after,
             "exit %s; %s; git status %s" % (code, out.strip(), "unchanged" if before == after else "changed: " + after))
    finally:
        shutil.rmtree(tmp, True)
    print("summary: %s" % ("all 4 steps passed" if ok else "a step FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
