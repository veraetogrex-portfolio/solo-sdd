#!/usr/bin/python3
"""Live scenario of change adaptive-init, steps 1-5: `solo-sdd init` detects the project and proposes its settings.

Every step runs the package of this tree (`python3 -m solo_sdd` with PYTHONPATH) in a temporary folder.
0. The non-interactive command of the README "First project" section runs as written in a fresh repository.
1. A clone of this repository with its real remote, the real HOME and PATH (agents installed here, `gh` with access):
   `init --yes` writes mode, agents and delivery.mode with reason comments; the mode follows the detected authors.
   1b. A toy repository with one author and a remote, no CI workflow: `mode: solo`, `delivery.mode: local`.
2. A toy repository with commits by 3 authors and `CODEOWNERS`: `mode: team`, the comment names 3 authors and CODEOWNERS.
3. The same repository in a pseudo-terminal, answers Enter, Enter, `local`: three questions shown, `delivery.mode: local`.
4. `init --set delivery.mode=cloud` in a fresh repository: exit 1, no solo-sdd/.
5. PATH=/usr/bin:/bin (no gh), a repository with a remote: `init --yes` succeeds, the comment says protection unknown.
Run from the repository root: python3 tests/stands/adaptive-init.py. Temporary folders are removed; the last line is
the summary."""
import os, pathlib, pty, re, select, shlex, shutil, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
ok = True


def step(name, good, detail):
    global ok
    ok &= bool(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail.strip().replace("\n", " | ")))


def run(cwd, args, env=None):
    p = subprocess.run(args, cwd=cwd, env=env or os.environ, capture_output=True, text=True, timeout=120,
                       stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def sdd(cwd, *args, env=None):
    env = dict(env or os.environ, PYTHONPATH=str(ROOT))
    return run(cwd, [sys.executable, "-m", "solo_sdd", *args], env)


def repo(path, authors=("Ann",), remote=None, codeowners=False):
    os.makedirs(path)
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    run(path, ["git", "init", "-q", "-b", "main"], env)
    for a in authors:
        run(path, ["git", "-c", "user.name=" + a, "-c", "user.email=%s@example.com" % a.lower(), "commit", "-q",
                   "--allow-empty", "-m", a], env)
    if remote:
        run(path, ["git", "remote", "add", "origin", remote], env)
    if codeowners:
        with open(os.path.join(path, "CODEOWNERS"), "w") as f:
            f.write("* @ann\n")
    return path


def config(path):
    with open(os.path.join(path, "solo-sdd", "config"), encoding="utf-8") as f:
        return f.read()


def comment(text, key):
    """The comment line and the value line of key."""
    m = re.search(r"^# %s: (.*)\n%s: (.*)$" % (re.escape(key), re.escape(key)), text, re.M)
    return m.groups() if m else ("no comment", "no value")


def pty_init(cwd, answers):
    """init in a pseudo-terminal; the answers are sent after the first question; (exit code, output)."""
    master, slave = pty.openpty()
    p = subprocess.Popen([sys.executable, "-m", "solo_sdd", "init"], cwd=cwd, stdin=slave, stdout=slave, stderr=slave,
                         env=dict(os.environ, PYTHONPATH=str(ROOT)))
    os.close(slave)
    out, sent, end = b"", False, time.time() + 90
    while time.time() < end:
        if not sent and b"]: " in out:
            os.write(master, answers)
            sent = True
        if select.select([master], [], [], 0.2)[0]:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
        elif p.poll() is not None:
            break
    p.wait(30)
    os.close(master)
    return p.returncode, out.decode("utf-8", "replace")


def main():
    tmp = tempfile.mkdtemp(prefix="adaptive-init-")
    try:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        first = readme[readme.index("## First project"):]
        cmd = next(l.strip() for l in first.splitlines() if l.strip().startswith("solo-sdd init --"))
        t0 = repo(os.path.join(tmp, "readme"))
        code, out = sdd(t0, *shlex.split(cmd)[1:])
        v = config(t0) if code == 0 else ""
        step("0 README command", code == 0 and "mode: team\n" in v and "dispatch.limit: 3\n" in v,
             "%s -> exit %d, %s" % (cmd, code, " ".join(l for l in v.splitlines() if not l.startswith("#"))))

        t1 = os.path.join(tmp, "clone")
        run(tmp, ["git", "clone", "-q", str(ROOT), t1])
        run(t1, ["git", "remote", "set-url", "origin", run(ROOT, ["git", "remote", "get-url", "origin"])[1].strip()])
        if os.path.exists(os.path.join(t1, "solo-sdd", "config")):
            os.remove(os.path.join(t1, "solo-sdd", "config"))
        code, out = sdd(tmp, "init", t1, "--yes")  # cwd outside the clone: its own solo_sdd/ must not be imported
        v = config(t1) if code == 0 else out
        (mwhy, mode), (awhy, agents), (dwhy, delivery) = (comment(v, k) for k in ("mode", "agents", "delivery.mode"))
        n = int(re.match(r"(\d+) author", mwhy).group(1)) if re.match(r"\d+ author", mwhy) else -1
        real = len({a.lower() for a in run(t1, ["git", "log", "--all", "--since=90.days", "--format=%aE"])[1].split()})
        want = "team" if n >= 2 or "no CODEOWNERS" not in mwhy or mwhy.endswith(", default branch protected") else "solo"
        step("1 this repository", code == 0 and n == real and mode == want and delivery == "pr" and "default branch" in mwhy
             and "other" in agents and awhy.endswith("other: always"),
             "mode: %s (%s); agents: %s (%s); delivery.mode: %s (%s)" % (mode, mwhy, agents, awhy, delivery, dwhy))
        t1b = repo(os.path.join(tmp, "solo"), remote="https://example.com/solo.git")
        code, out = sdd(t1b, "init", "--yes")
        v = config(t1b) if code == 0 else ""
        step("1b one author", code == 0 and comment(v, "mode")[1] == "solo" and comment(v, "delivery.mode")[1] == "local"
             and "no CI workflow" in comment(v, "delivery.mode")[0],
             "mode: %s (%s); delivery.mode: %s" % (comment(v, "mode")[::-1] + (comment(v, "delivery.mode")[1],)))

        team = lambda name: repo(os.path.join(tmp, name), ("Ann", "Bob", "Cid"), "https://example.com/team.git", True)
        t2 = team("team")
        code, out = sdd(t2, "init", "--yes")
        why, mode = comment(config(t2), "mode") if code == 0 else ("", "")
        step("2 three authors", mode == "team" and "3 authors in 90 days" in why and "CODEOWNERS" in why
             and "no CODEOWNERS" not in why, "mode: %s (%s)" % (mode, why))

        t3 = team("team-pty")
        code, out = pty_init(t3, b"\n\nlocal\n")
        prompts = re.findall(r"^\S+ \([^)]*\) \[[^\]]*\]: ", out, re.M)
        delivery = comment(config(t3), "delivery.mode") if code == 0 else ("", "")
        step("3 terminal", code == 0 and len(prompts) == 3 and delivery[1] == "local",
             "%s; delivery.mode: %s (%s)" % ("; ".join(p.strip() for p in prompts), delivery[1], delivery[0]))

        t4 = repo(os.path.join(tmp, "wrong"))
        code, out = sdd(t4, "init", "--set", "delivery.mode=cloud")
        step("4 wrong set", code == 1 and "local, pr" in out and not os.path.exists(os.path.join(t4, "solo-sdd")),
             "exit %d, %s, solo-sdd/ %s" % (code, out.strip(), "exists" if os.path.exists(os.path.join(t4, "solo-sdd")) else "absent"))

        t5 = repo(os.path.join(tmp, "nogh"), remote="https://github.com/veraetogrex-portfolio/solo-sdd.git")
        code, out = sdd(t5, "init", "--yes", env=dict(os.environ, PATH="/usr/bin:/bin"))
        why = comment(config(t5), "mode")[0] if code == 0 else out
        step("5 no gh", code == 0 and "branch protection unknown" in why, "exit %d, mode comment: %s" % (code, why))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("adaptive-init stand: %s" % ("all steps passed" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
