#!/usr/bin/python3
"""Live scenario of change provider-cursor, its Fallback (no Cursor on the machine), on a temporary home.

PATH is an empty stand bin folder, then /usr/bin and /bin: no `cursor-agent`.
1. `tests/stands/provider-probe.py cursor` -> exit 0, every capability line `not run`, the home untouched.
2. `install --agents cursor` -> skills in ~/.agents/skills, nothing under ~/.cursor, ~/.claude, ~/.codex;
   the output says that project rules come from `solo-sdd init`.
3. `doctor` -> `warn agent cursor: unverified:` naming skills, then `no hooks:` and `no subagents:` with what is not enforced.
Run from the repository root: python3 tests/stands/provider-cursor.py. The temporary folder is removed; the last
line is the summary."""
import os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
ok = True


def step(name, good, detail):
    global ok
    ok &= bool(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail.strip().replace("\n", " | ")))


def call(home, path, *args):
    env = dict(os.environ, HOME=home, PATH=path + ":/usr/bin:/bin", PYTHONPATH=str(ROOT))
    p = subprocess.run(list(args), cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=300,
                       stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def main():
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="provider-cursor-"))
    try:
        empty, home = os.path.join(tmp, "bin"), os.path.join(tmp, "home")
        os.makedirs(empty)
        os.makedirs(home)
        code, out = call(home, empty, sys.executable, str(ROOT / "tests" / "stands" / "provider-probe.py"), "cursor")
        lines = [l for l in out.splitlines() if l.startswith("cursor ")]
        step("1 probe cursor", code == 0 and len(lines) == 4 and all(": not run" in l for l in lines) and not os.listdir(home),
             "exit %s; %d of 4 lines not run; home %s" % (code, sum(": not run" in l for l in lines),
                                                          "untouched" if not os.listdir(home) else os.listdir(home)))

        code, out = call(home, empty, sys.executable, "-m", "solo_sdd", "install", "--agents", "cursor")
        agents = os.path.join(home, ".agents", "skills")
        n = sum(os.path.isfile(os.path.join(agents, d, "SKILL.md")) for d in os.listdir(agents)) if os.path.isdir(agents) else 0
        others = [d for d in (".cursor", ".claude", ".codex") if os.path.exists(os.path.join(home, d))]
        said = "project rules come from solo-sdd init" in out
        step("2 install --agents cursor", code == 0 and n > 0 and not others and said,
             "exit %s; ~/.agents/skills %d skills; other agent folders %s; init named %s" % (code, n, others or "none", said))

        code, out = call(home, empty, sys.executable, "-m", "solo_sdd", "doctor")
        line = next((l for l in out.splitlines() if l.startswith("warn agent cursor:")), "")
        step("3 doctor", all(w in line for w in ("unverified: skills", "no hooks: CLAIM guard", "no subagents: ")), line or "no cursor line")
    finally:
        shutil.rmtree(tmp, True)
    print("summary: %s" % ("all 3 steps passed" if ok else "a step FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
