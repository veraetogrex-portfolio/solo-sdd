#!/usr/bin/python3
"""Live scenario of change light-path (Fallback: no actor subagents), PATH=/usr/bin:/bin.

1. `HOME=$T/home solo-sdd install --agents claude,codex --global-rules`: the deployed global rules (Claude and Codex) and ALGORITHM.md hold the light path
   rule once, with its `solo-sdd config get` keys; the deployed spec-plan, work-status and report hold their lines.
2. A stand project whose main spec `buttons` describes the Save button: config gives `on` and `3`; the Cancel label
   is in no main spec, the Save button is; the light path edit (one file, the tests, a `light:` commit) leaves no
   folder in `solo-sdd/changes/`.
3. `solo-sdd config set process.light-path off` -> `config get` prints `off`.
4. The deployed spec-plan's `git log` command finds the item 1 commit; with two archived changes and five `light:`
   commits the deployed report's command counts 5, the archive 2.
Run from the repository root: python3 tests/stands/light-path.py. The temporary folder is removed; the last line
is the summary."""
import os, pathlib, re, shlex, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BARE = {k: v for k, v in os.environ.items() if k not in ("PATH", "HOME")}
BARE.update(PATH="/usr/bin:/bin", PYTHONPATH=str(ROOT))
results = []


def step(name, good, detail):
    results.append(good)
    print("%s %s: %s" % ("ok" if good else "FAILED", name, detail))


def run(cmd, cwd, **env):
    p = subprocess.run(cmd, cwd=cwd, env={**BARE, **env}, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=300)
    return p.returncode, (p.stdout + p.stderr).strip()


def sdd(cwd, *args):
    return run([sys.executable, "-m", "solo_sdd", *args], cwd)


def get(cwd, key):
    """The value `config get` prints: its first line; the `source:` line follows on stderr."""
    return (sdd(cwd, "config", "get", key)[1].splitlines() or [""])[0]


def git(cwd, *args):
    return run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd)[1]


def put(root, rel, text):
    p = pathlib.Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def command(text):
    """The `git log … --grep='^light:'…` command a deployed text names, as argv; a `<placeholder>` date is 2000-01-01."""
    m = re.search(r"`(git log --oneline --grep='\^light:'[^`]*)`", text)
    return shlex.split(re.sub(r"<[^>]+>", "2000-01-01", m.group(1))) if m else None


with tempfile.TemporaryDirectory() as t:
    t = pathlib.Path(t)
    home, proj = t / "home", t / "proj"
    code, out = run([sys.executable, "-m", "solo_sdd", "install", "--agents", "claude,codex", "--global-rules"], ROOT,
                    HOME=str(home))
    read = lambda rel: (home / rel).read_text(encoding="utf-8") if (home / rel).is_file() else ""
    rules = [read(".claude/CLAUDE.md"), read(".codex/AGENTS.md"), read(".local/share/solo-sdd/ALGORITHM.md")]
    once = [sum("process.light-path.max-files" in l for l in r.splitlines()) for r in rules]
    step("1 deployed rules", code == 0 and once == [1, 1, 1] and all("light: <the request>" in r for r in rules)
         and "solo-sdd config get process.light-path" in rules[0],
         "CLAUDE.md, AGENTS.md, ALGORITHM.md: the rule %s time(s); install code %d" % (once, code))
    plan, status, report = (read(".claude/skills/%s/SKILL.md" % s) for s in ("spec-plan", "work-status", "report"))
    order = [plan.find(s) for s in ("**Light path.** Before any unit", "**Units.**", "**Creation.**")]
    step("1 deployed skills", "An item already closed by a `light:` commit" in plan and -1 < order[0] < order[1] < order[2]
         and "A bug in behaviour a main spec describes always gets a bug fix change" in plan
         and bool(command(status) and command(report)), "spec-plan: the light path step before units, the bug fix line; the work-status and report count")

    proj.mkdir()
    git(proj, "init", "-q", "-b", "main")
    put(proj, "solo-sdd/project.md", "# Project\n\nLanguage: en\nMode: demo\n\nIntent: a toy form.\n")
    put(proj, "solo-sdd/specs/buttons/spec.md", "# buttons Specification\n\n## Purpose\nThe Save button of the form.\n\n"
        "## Requirements\n\n### Requirement: Save\nThe Save button SHALL store the form.\n\n#### Scenario: Click\n"
        "- **WHEN** Save is clicked\n- **THEN** the form is stored\n")
    put(proj, "solo-sdd/changes/archive/.keep", "")
    put(proj, "form.py", "LABELS = {'save': 'Save', 'cancel': 'Sumbit'}\n")
    put(proj, "test_form.py", "from form import LABELS\nassert LABELS['cancel'] != 'Sumbit', LABELS\n")
    git(proj, "add", "-A")
    git(proj, "commit", "-qm", "init")
    on, limit = get(proj, "process.light-path"), get(proj, "process.light-path.max-files")
    specs = (proj / "solo-sdd/specs/buttons/spec.md").read_text(encoding="utf-8")
    before = run([sys.executable, "test_form.py"], proj)[0]
    put(proj, "form.py", "LABELS = {'save': 'Save', 'cancel': 'Cancel'}\n")
    after = run([sys.executable, "test_form.py"], proj)[0]
    git(proj, "commit", "-qam", "light: fix the typo 'Sumbit' on the Cancel button label")
    files = git(proj, "diff", "--name-only", "HEAD~1").split()
    changes = [p.name for p in (proj / "solo-sdd/changes").iterdir() if p.name != "archive"]
    step("2 light path", on == "on" and limit == "3" and "Cancel" not in specs and "Save" in specs
         and before == 1 and after == 0 and len(files) <= int(limit) and not changes,
         "config %s/%s; Cancel in a spec: %s, Save: %s; tests %d -> %d; %d file(s), changes/: %s"
         % (on, limit, "Cancel" in specs, "Save" in specs, before, after, len(files), changes or "empty"))

    code, out = sdd(proj, "config", "set", "process.light-path", "off")
    got = get(proj, "process.light-path")
    step("3 off", code == 0 and got == "off", "config set code %d, get prints %s" % (code, got))

    found = run(command(plan) or ["false"], proj)[1].splitlines()
    head = git(proj, "rev-parse", "--short", "HEAD")
    step("4 coverage", len(found) == 1 and found[0].startswith(head), "item 1 -> `light:` %s" % (found or ["none"])[0])
    for i in range(4):
        put(proj, "n%d.txt" % i, "x\n")
        git(proj, "add", "-A")
        git(proj, "commit", "-qm", "light: edit %d" % i)
    for cid in ("2026-11-01-one", "2026-11-02-two"):
        put(proj, "solo-sdd/changes/archive/%s/tasks.md" % cid, "- [x] 1.1\n")
    git(proj, "add", "-A")
    git(proj, "commit", "-qm", "two (#2)")
    light = len(run(command(report) or ["false"], proj)[1].splitlines())
    archived = len([p for p in (proj / "solo-sdd/changes/archive").iterdir() if p.is_dir()])
    step("4 report count", light == 5 and archived == 2, "archived changes %d, light: commits %d" % (archived, light))

print("stand: %d of %d steps passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
