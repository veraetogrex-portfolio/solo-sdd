#!/usr/bin/env python3
"""Live scenario step 1 of change dispatch-run-decisions, without model calls.

`sync.py push` lays the repository out into a temporary HOME; the stand reads the laid-out
`~/.claude/skills/spec-dispatch/SKILL.md` and `~/.local/share/solo-sdd/templates/docs/waiting.md` and prints one
`ok` or `FAIL` line per rule. Three scratch git repositories then run the file choice the skill names, each with an earlier run's section whose
key the last section must not carry: an ignored `docs/waiting.md` is created from the laid-out template; a path git
neither tracks nor ignores, and a tracked one, send the lines to the git common folder; in all three
`git status --porcelain --untracked-files=all` stays empty, and in the second a branch that commits `docs/waiting.md`
still merges.
Run from the repository root: python3 tests/stands/run-decisions.py. The temporary folder is removed; the last line is
`run-decisions: <n> of <m> checks passed` (code 0 only when n == m)."""
import os, pathlib, re, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(("ok   " if ok else "FAIL ") + name + ("" if ok or not detail else ": " + detail))


def run(*args, cwd=ROOT, env=None):
    return subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          timeout=600)


def flat(text):
    return re.sub(r"\s+", " ", text)


def step(text, n, m):
    parts = text.split("\n%d. **" % n, 1)
    return flat(parts[1].split("\n%d. **" % m, 1)[0]) if len(parts) == 2 else ""


def has(text, *words):
    missing = [w for w in words if w not in text]
    return not missing, "missing: " + "; ".join(missing)


def decisions_file(repo):
    """The file choice of step 0, by the commands it names."""
    waiting = pathlib.Path(repo) / "docs/waiting.md"
    untracked = not run("git", "-C", repo, "ls-files", "docs/waiting.md").stdout.strip()
    if untracked and (waiting.exists() or run("git", "-C", repo, "check-ignore", "-q", "docs/waiting.md").returncode == 0):
        return waiting
    common = run("git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
    return pathlib.Path(common) / "solo-sdd/run-decisions.md"


def git(repo, *a):
    return run("git", "-c", "user.name=s", "-c", "user.email=s@s", "-c", "init.defaultBranch=main",
               "-c", "commit.gpgsign=false", *a, cwd=repo)


def scratch(t, name):
    repo = pathlib.Path(t) / name
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "README.md").write_text("x\n")
    if name == "ignored":
        (repo / ".gitignore").write_text("docs/\n")
    if name == "tracked":
        (repo / "docs").mkdir()
        (repo / "docs/waiting.md").write_text("# Waiting\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    return repo


with tempfile.TemporaryDirectory(prefix="run-decisions-") as t:
    home = pathlib.Path(t) / "home"
    env = {k: v for k, v in os.environ.items() if k != "HOME"}
    p = run(sys.executable, "sync.py", "push", env={**env, "HOME": str(home)})
    skill_path = home / ".claude/skills/spec-dispatch/SKILL.md"
    template = home / ".local/share/solo-sdd/templates/docs/waiting.md"
    check("sync.py push lays out the skill and the template", p.returncode == 0 and skill_path.is_file()
          and template.is_file(), "code %d %s" % (p.returncode, (p.stdout + p.stderr).strip()[-300:]))
    skill = skill_path.read_text(encoding="utf-8") if skill_path.is_file() else ""
    s0, s2, s9 = step(skill, 0, 1), step(skill, 2, 3), step(skill, 9, 10)

    check("answers: written before the recalculation, with the key, under the run's heading", *has(
        s9, "Every answer that changes the plan of the run", "is written at once, before the next recalculation",
        "under the run's heading", "the key it gives the planner", "shared — --shared package-lock.json",
        "marker kept — no key"))
    check("file choice: an untracked docs/waiting.md that exists or git ignores, else the git common folder", *has(
        s0, "`git -C <MAIN> ls-files docs/waiting.md` is empty and the file exists or "
        "`git -C <MAIN> check-ignore -q docs/waiting.md` succeeds", "`<MAIN>/docs/waiting.md`",
        "`solo-sdd/run-decisions.md` of the git common folder",
        "`git -C <MAIN> rev-parse --path-format=absolute --git-common-dir`"))
    check("heading at the start of the run, the file from its template when missing", *has(
        s0, "Once step 1 lets the run go on, before the first plan, append `## Run decisions <date> <start time of "
        "the run>`", "A missing ignored `docs/waiting.md` is created from "
        "`~/.local/share/solo-sdd/templates/docs/waiting.md`", "with its `solo-sdd/` folder (`mkdir -p`)",
        "the run's section is always the last `## Run decisions` section"))
    check("after a summary: the last section reread before the recalculation, earlier ones not read", *has(
        s2, "After a context summary, before the next recalculation, reread the last `## Run decisions` section",
        "pass every key it holds", "Earlier sections are not read"))
    report = skill.split("## Report", 1)[-1]
    check("report form has the run decisions line",
          *has(report, "Run decisions: <file> — <lines of the run's section> | none"))
    tpl = template.read_text(encoding="utf-8") if template.is_file() else ""
    check("laid-out template names the section below the table", *has(tpl, "`## Run decisions <date> <time>`"))

    older = "\n## Run decisions 2026-11-14 09:00\n\n- 09:03 a: ignore b — --ignore-dep a:b\n"
    for name, where in (("ignored", "docs/waiting.md"), ("plain", ".git/solo-sdd/run-decisions.md"),
                        ("tracked", ".git/solo-sdd/run-decisions.md")):
        repo = scratch(t, name)
        f = decisions_file(repo)
        if not f.exists():  # step 0: the template for docs/waiting.md, an empty file with mkdir -p otherwise
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(tpl + older if f.name == "waiting.md" else older, encoding="utf-8")
        with f.open("a", encoding="utf-8") as h:
            h.write("\n## Run decisions 2026-11-15 14:02\n\n- 14:05 package-lock.json: shared — --shared package-lock.json\n")
        dirty = git(repo, "status", "--porcelain", "--untracked-files=all").stdout.strip()
        last = f.read_text(encoding="utf-8").rsplit("\n## Run decisions ", 1)[-1]
        keys = re.findall(r"— (--\S+ \S+)$", last, re.M)
        made = (repo / "docs/waiting.md").exists() == (name != "plain")
        check("%s docs/waiting.md: the line in %s, the last section's keys %s, the main folder clean"
              % (name, where, keys), str(f).endswith(where) and made and not dirty
              and keys == ["--shared package-lock.json"], "file %s, status %r" % (f, dirty))
        if name == "plain":  # a branch that commits docs/waiting.md still merges: no untracked copy in the way
            git(repo, "checkout", "-qb", "change/x")
            (repo / "docs").mkdir()
            (repo / "docs/waiting.md").write_text("# Waiting\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "change")
            git(repo, "checkout", "-q", "main")
            m = git(repo, "merge", "--no-ff", "-qm", "merge", "change/x")
            check("plain: a branch that commits docs/waiting.md merges", m.returncode == 0, m.stdout + m.stderr)

print("run-decisions: %d of %d checks passed" % (sum(checks), len(checks)))
sys.exit(0 if all(checks) else 1)
