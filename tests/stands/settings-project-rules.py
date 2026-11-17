#!/usr/bin/python3
"""Live scenario of change settings-project-rules, steps 1-3, on the real `solo-sdd config`.

In a temporary project whose solo-sdd/project.md has `Language: en` and `Mode: demo`, run as `python3 -m solo_sdd`
from this repository:
1. `config get project.stage` prints `demo` with `source: project.md`; `config list` has `project.stage demo project.md`.
2. `config set project.stage prod`: `config get project.stage` prints `prod` with `source: file`; project.md keeps its bytes.
3. `config set artifacts.language "Russian language"` exits 1; `config set artifacts.language ru` exits 0.
Run from the repository root: python3 tests/stands/settings-project-rules.py. The temporary folder is removed; the
last line is the summary."""
import os, pathlib, subprocess, sys, tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]


def sdd(proj, *args):
    """(code, stdout, stderr) of `python3 -m solo_sdd <args>` in proj."""
    p = subprocess.run([sys.executable, "-m", "solo_sdd"] + list(args), cwd=proj, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=str(REPO)), stdin=subprocess.DEVNULL, timeout=60)
    return p.returncode, p.stdout, p.stderr


with tempfile.TemporaryDirectory() as t:
    proj = pathlib.Path(t)
    (proj / "solo-sdd" / "changes").mkdir(parents=True)
    project_md = proj / "solo-sdd" / "project.md"
    project_md.write_bytes(b"# Project\n\nLanguage: en\nMode: demo\n\nIntent: a toy.\n")
    before = project_md.read_bytes()
    checks = []

    got = sdd(proj, "config", "get", "project.stage")
    listed = sdd(proj, "config", "list")[1].splitlines()
    checks.append(("1 the Mode line of project.md as the old source", got == (0, "demo\n", "source: project.md\n")
                   and "project.stage demo project.md" in listed, "%r %r" % (got, listed)))

    put = sdd(proj, "config", "set", "project.stage", "prod")
    got = sdd(proj, "config", "get", "project.stage")
    checks.append(("2 the file value wins, project.md unchanged", put[0] == 0 and got == (0, "prod\n", "source: file\n")
                   and project_md.read_bytes() == before, "%r %r" % (put, got)))

    bad = sdd(proj, "config", "set", "artifacts.language", "Russian language")
    good = sdd(proj, "config", "set", "artifacts.language", "ru")
    checks.append(("3 a language name refused, a code taken", bad[0] == 1 and "2 or 3 lowercase letters" in bad[1]
                   and good[0] == 0, "%r %r" % (bad, good)))

    for step, ok, why in checks:
        print("%s %s%s" % ("ok    " if ok else "FAILED", step, "" if ok else ": " + why.strip()))
    passed = sum(ok for _, ok, _ in checks)
    print("settings-project-rules: %d of %d checks passed" % (passed, len(checks)))
sys.exit(0 if passed == len(checks) else 1)
