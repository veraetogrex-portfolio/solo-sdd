#!/usr/bin/env python3
"""Live scenario of change settings-gitignore: `solo-sdd ignore`, `config set git.ignore` and `init` on real git.

In a temporary git project with solo-sdd/ and a .gitignore holding node_modules:
1. `solo-sdd ignore` lists the four default items and writes nothing.
2. `ignore --write` keeps node_modules first and adds the block; git hides .env and .env.local, not .env.example; a repeat: no change.
3. `config set git.ignore ".claude/worktrees/, docs/waiting.md"` with docs/waiting.md tracked: the hint; `ignore --write`
   names `git rm --cached -r -- docs/waiting.md`, the file stays tracked, the block has no .env line.
4. `config set git.ignore solo-sdd/` and `"*.md"`: exit 1, the second naming AGENTS.md, solo-sdd/config unchanged.
5. `git init` of a new folder, `solo-sdd init <folder> --yes`: its .gitignore holds the block of the four defaults.
Run from the repository root: python3 tests/stands/settings-gitignore.py. The program runs as a separate process with a
temporary HOME, an empty global git config and no system config; the temporary folder is removed. Last line: the summary.
"""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULTS = [".claude/worktrees/", ".env", ".env.*", "!.env.example"]
BLOCK = "".join(ln + "\n" for ln in ["# solo-sdd:begin"] + DEFAULTS + ["# solo-sdd:end"])

with tempfile.TemporaryDirectory() as t:
    t = os.path.realpath(t)
    home, proj, fresh = (os.path.join(t, n) for n in ("home", "proj", "fresh"))
    os.makedirs(home)
    globalconfig = os.path.join(t, "gitconfig")
    open(globalconfig, "w").close()
    env = dict(os.environ, HOME=home, GIT_CONFIG_GLOBAL=globalconfig, GIT_CONFIG_NOSYSTEM="1", LC_ALL="C",
               PYTHONPATH=ROOT)

    def git(cwd, *args):
        return subprocess.run(["git", "-c", "init.defaultBranch=main", "-c", "user.name=t", "-c", "user.email=t@t",
                               "-c", "commit.gpgsign=false", *args], cwd=cwd, env=env, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=60)

    def sdd(cwd, *args):
        p = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=cwd, env=env, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=120)
        return p.returncode, p.stdout + p.stderr

    def read(path):
        with open(path, encoding="utf-8", newline="") as f:
            return f.read()

    os.makedirs(os.path.join(proj, "solo-sdd", "specs"))
    os.makedirs(os.path.join(proj, "docs"))
    git(t, "init", "-q", proj)
    gitignore, config = os.path.join(proj, ".gitignore"), os.path.join(proj, "solo-sdd", "config")
    with open(gitignore, "w") as f:
        f.write("node_modules\n")
    checks = []

    code, out = sdd(proj, "ignore")
    checks.append(("1 the dry run lists the defaults, .gitignore unchanged", code == 0
                   and out.splitlines()[:4] == DEFAULTS and read(gitignore) == "node_modules\n", out))

    code, out = sdd(proj, "ignore", "--write")
    hidden, kept, local = (git(proj, "check-ignore", "-q", p).returncode for p in (".env", ".env.example", ".env.local"))
    again = sdd(proj, "ignore", "--write")
    checks.append(("2 the block written after node_modules, .env and .env.local hidden, .env.example kept, a repeat: no change",
                   code == 0 and read(gitignore) == "node_modules\n" + BLOCK and (hidden, kept, local) == (0, 1, 0)
                   and again[1].splitlines()[-1:] == ["no change"], out + again[1]))

    with open(os.path.join(proj, "docs", "waiting.md"), "w") as f:
        f.write("# Waiting\n")
    git(proj, "add", "docs/waiting.md")
    git(proj, "commit", "-q", "-m", "waiting")
    code, said = sdd(proj, "config", "set", "git.ignore", ".claude/worktrees/, docs/waiting.md")
    wcode, out = sdd(proj, "ignore", "--write")
    block = read(gitignore).split("# solo-sdd:begin\n", 1)[-1]
    checks.append(("3 the hint, the git rm --cached line, docs/waiting.md still tracked, no .env in the block",
                   code == 0 and "run: solo-sdd ignore --write" in said.splitlines() and wcode == 0
                   and "git rm --cached -r -- docs/waiting.md" in out
                   and git(proj, "ls-files", "docs/waiting.md").stdout == "docs/waiting.md\n"
                   and ".env\n" not in block and "docs/waiting.md\n" in block, said + out))

    before = read(config)
    a, out_a = sdd(proj, "config", "set", "git.ignore", "solo-sdd/")
    b, out_b = sdd(proj, "config", "set", "git.ignore", "*.md")
    checks.append(("4 solo-sdd/ and *.md refused, *.md naming AGENTS.md, solo-sdd/config unchanged",
                   (a, b) == (1, 1) and "solo-sdd/" in out_a and "AGENTS.md" in out_b and read(config) == before,
                   out_a + out_b))

    git(t, "init", "-q", fresh)
    code, out = sdd(t, "init", fresh, "--yes")
    made = read(os.path.join(fresh, ".gitignore")) if os.path.exists(os.path.join(fresh, ".gitignore")) else ""
    checks.append(("5 init writes the block of the four defaults", code == 0 and made == BLOCK, out))

    for step, good, why in checks:
        print("%s %s%s" % ("ok    " if good else "FAILED", step, "" if good else ": " + why.strip()[-600:]))
    passed = sum(g for _, g, _ in checks)
    print("settings-gitignore: %d of %d checks passed" % (passed, len(checks)))
sys.exit(0 if passed == len(checks) else 1)
