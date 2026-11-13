#!/usr/bin/python3
"""Live scenario of change init-ci-detect, steps 1-3a: `solo-sdd init --yes` proposes `delivery.mode: pr` only with CI.

Each step is a temporary git repository with a bare remote; `python3 -m solo_sdd` of this tree runs with stdin closed.
1. A remote and `.github/workflows/test.yml`: `delivery.mode: pr`, the comment names the remote and CI.
2. A remote, no workflow: `delivery.mode: local`, the comment and the printed line name the missing CI.
3. No remote: `delivery.mode: local`, comment `no remote`.
3a. A remote, no workflow, `--delivery pr`: `delivery.mode: pr`, the printed line names the missing CI.
Run from the repository root: python3 tests/stands/init-ci-detect.py. The temporary folder is removed; the last line
is the summary."""
import os, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", PYTHONPATH=str(ROOT))
NO_CI = "pr needs a CI workflow"


def run(cwd, *args):
    p = subprocess.run(args, cwd=cwd, env=ENV, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def project(tmp, name, remote, workflow):
    path = os.path.join(tmp, name)
    os.makedirs(path)
    run(path, "git", "init", "-q", "-b", "main")
    if remote:
        bare = path + ".git"
        run(tmp, "git", "init", "-q", "--bare", bare)
        run(path, "git", "remote", "add", "origin", bare)
    if workflow:
        os.makedirs(os.path.join(path, ".github", "workflows"))
        with open(os.path.join(path, ".github", "workflows", "test.yml"), "w") as f:
            f.write("on: push\n")
    return path


def init(path, *flags):
    """Exit code, output and the (comment, value) of delivery.mode after `init --yes` with stdin closed."""
    code, out = run(tmp_root, "/bin/sh", "-c", 'exec "$0" -m solo_sdd init "$@" <&-', sys.executable, path, "--yes",
                    *flags)
    try:
        with open(os.path.join(path, "solo-sdd", "config"), encoding="utf-8") as f:
            m = re.search(r"^# delivery\.mode: (.*)\ndelivery\.mode: (.*)$", f.read(), re.M)
    except OSError:
        m = None
    return code, out, (m.groups() if m else ("no comment", "no value"))


def main():
    global tmp_root
    tmp_root = tempfile.mkdtemp(prefix="init-ci-detect-")
    ok = True
    try:
        cases = (("1 remote and CI", True, True, (), "pr", "remote origin, CI .github/workflows/test.yml", False),
                 ("2 remote, no CI", True, False, (), "local", "remote origin, no CI workflow in .github/workflows",
                  True),
                 ("3 no remote", False, False, (), "local", "no remote", False),
                 ("3a pr chosen, no CI", True, False, ("--delivery", "pr"), "pr",
                  "chosen; proposed local: remote origin, no CI workflow in .github/workflows", True))
        for name, remote, workflow, flags, want, why, warned in cases:
            code, out, (got_why, got) = init(project(tmp_root, name.split()[0], remote, workflow), *flags)
            good = code == 0 and got == want and got_why == why and (NO_CI in out) == warned
            ok &= good
            line = next((l for l in out.splitlines() if NO_CI in l), "no CI line")
            print("%s %s: exit %d, delivery.mode: %s (%s); printed: %s" % ("ok " if good else "FAILED", name, code,
                                                                           got, got_why, line))
    finally:
        shutil.rmtree(tmp_root, True)
    print("init-ci-detect stand: %s" % ("all steps passed" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
