#!/usr/bin/python3
"""Live scenario of change skills-own-cli with PATH=/usr/bin:/bin (no openspec).

1. `HOME=$T/home solo-sdd install` lays out the skills; no deployed skill, ALGORITHM.md or global AGENTS.md line names
   OpenSpec except `solo-sdd import openspec`; `tests/test_skill_commands.py` passes.
2-3. By the deployed `spec-plan` "Writing rules": `solo-sdd new add-version-flag`, the artifacts filled by those rules
   only, `solo-sdd validate --all` passes on its first call, `solo-sdd archive --yes` moves the change to the archive.
4. A copy of the project with `solo-sdd/` renamed to `openspec/`: the deployed spec-plan, spec-next, spec-analyze and
   spec-dispatch hold the stop line with `solo-sdd import openspec`; `git status --short` of the copy is empty.
Run from the repository root: python3 tests/stands/skills-own-cli.py. Temporary folders are removed; the last line
is the summary."""
import os, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from test_skill_commands import HINT, LEGACY_SKILLS, legacy_stop  # noqa: E402

BARE = {k: v for k, v in os.environ.items() if k not in ("PATH", "HOME")}
BARE.update(PATH="/usr/bin:/bin", PYTHONPATH=str(ROOT))
REQ = "### Requirement: %s\nThe system SHALL %s.\n\n#### Scenario: %s\n- **WHEN** %s\n- **THEN** %s\n"
ok = True


def step(name, good, detail):
    global ok
    ok &= good
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def run(cmd, cwd, **env):
    p = subprocess.run(cmd, cwd=cwd, env={**BARE, **env}, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=300)
    return p.returncode, p.stdout + p.stderr


def sdd(cwd, *args):
    return run([sys.executable, "-m", "solo_sdd", *args], cwd)


def git(cwd, *args):
    return run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd)[1]


def put(root, rel, text):
    p = pathlib.Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def fill(change):
    """The artifacts of a toy change written by the spec-plan Writing rules: section names, Purpose, Acceptance."""
    put(change, "proposal.md", "# Proposal\n\n## Why\n\n`app.py` has no way to print its version.\n\n## What Changes\n\n"
        "- `python3 app.py --version` prints the version.\n\n## Capabilities\n\n### New Capabilities\n"
        "- `app-version`: the version flag.\n\n### Modified Capabilities\n\n## Impact\n\n`app.py`, `tests/test_app.py`.\n\n"
        "## Out of Scope\n\n- A `--help` text.\n\n## Depends On\n\nnone\n\n## Source\n\n"
        "\"add a `--version` flag to `app.py`\" (the owner)\n")
    put(change, "specs/app-version/spec.md", "## Purpose\n\nLets a user of the toy app see which version of `app.py` "
        "is installed.\n\n## ADDED Requirements\n\n" + REQ % (
            "Version flag", "print the version and exit 0 on `--version`", "The flag",
            "`python3 app.py --version` runs", "it prints `1.0.0` and exits 0"))
    put(change, "verification.md", "## Live Scenario\n\n1. `python3 app.py --version` -> `1.0.0`, code 0.\n\n## Needs\n\n"
        "none\n\n## Fallback\n\nNot needed: nothing in Needs.\n\n## Result\n\n2026: `1.0.0` printed.\n\n## Not Verified\n\n"
        "nothing\n\n## Decisions Without Owner\n\nnone\n")
    tasks = (change / "tasks.md").read_text(encoding="utf-8")
    tasks = re.sub(r"<!-- - \[ \] 1\.1.*?-->", "- [x] 1.1 `--version` in `app.py`; check: `python3 app.py --version`", tasks)
    put(change, "tasks.md", tasks.replace("- [ ]", "- [x]"))


with tempfile.TemporaryDirectory() as t:
    t = pathlib.Path(t)
    proj, home = t / "proj", t / "home"
    proj.mkdir()
    git(proj, "init", "-q", "-b", "main")
    put(proj, "solo-sdd/project.md", "# Project\n\nLanguage: en\nMode: demo\n\nIntent: a toy app.\n")
    put(proj, "app.py", "print('app')\n")
    git(proj, "add", "-A")
    git(proj, "commit", "-qm", "init")

    code, out = run([sys.executable, "-m", "solo_sdd", "install"], ROOT, HOME=str(home))
    skills = home / ".claude" / "skills"
    texts = sorted(skills.glob("*/SKILL.md")) + [home / ".local/share/solo-sdd/ALGORITHM.md", home / ".claude/CLAUDE.md"]
    texts = [p for p in texts if p.is_file()]
    bad = ["%s:%d" % (p.relative_to(home), n) for p in texts
           for n, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
           if re.search("openspec", l, re.I) and HINT not in l]
    hint = sum(HINT in p.read_text(encoding="utf-8") for p in texts)
    step("1 deployed texts", len(texts) > 20 and not bad,
         "%d files, %d with the import hint, lines naming OpenSpec: %s; install code %d (%s)"
         % (len(texts), hint, ", ".join(bad) or "none", code, out.strip().splitlines()[-1][:60]))
    code, out = run([sys.executable, "tests/test_skill_commands.py"], ROOT)
    step("1 test_skill_commands", code == 0, out.strip().splitlines()[-1])

    plan = (skills / "spec-plan/SKILL.md").read_text(encoding="utf-8")
    step("2 rules in deployed spec-plan", all(s in plan for s in ("## Writing rules", "`solo-sdd new <name>`",
                                                                  "`solo-sdd validate --all`", "Specs: none")),
         "Writing rules, solo-sdd new, solo-sdd validate --all, Specs: none")
    code, out = sdd(proj, "new", "add-version-flag")
    change = proj / "solo-sdd/changes/add-version-flag"
    fill(change)
    code, out = sdd(proj, "validate", "--all")
    step("2 validate --all on the first call", code == 0, out.strip().splitlines()[-1])
    code, out = sdd(proj, "archive", "add-version-flag", "--yes")
    arch = sorted((proj / "solo-sdd/changes/archive").glob("*-add-version-flag"))
    spec = proj / "solo-sdd/specs/app-version/spec.md"
    step("3 archive", code == 0 and arch and not change.exists() and spec.is_file(),
         "%s, main spec %s" % (arch[0].relative_to(proj) if arch else "none", "written" if spec.is_file() else "missing"))
    nxt = (skills / "spec-next/SKILL.md").read_text(encoding="utf-8")
    step("3 spec-next steps", "openspec-after-update" not in nxt and "sync.py push" not in nxt
         and "`solo-sdd archive <id> --yes`" in nxt, "no openspec-after-update.py, no sync.py push, solo-sdd archive")

    legacy = t / "legacy"
    shutil.copytree(proj, legacy, symlinks=True)
    (legacy / "solo-sdd").rename(legacy / "openspec")
    git(legacy, "add", "-A")
    git(legacy, "commit", "-qm", "legacy tree")
    missing = [s for s in LEGACY_SKILLS if not legacy_stop((skills / s / "SKILL.md").read_text(encoding="utf-8"))]
    code, out = sdd(legacy, "validate", "--all")
    status = git(legacy, "status", "--short")
    step("4 legacy tree", not missing and not status.strip(),
         "stop line with `%s` in %s; validate: %s; git status --short: %s"
         % (HINT, ", ".join(s for s in LEGACY_SKILLS if s not in missing), out.strip(), status.strip() or "empty"))

print("summary: %s" % ("all steps passed" if ok else "FAILED"))
sys.exit(0 if ok else 1)
