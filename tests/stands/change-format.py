#!/usr/bin/python3
"""Live scenario of change change-format, steps 1-4: `solo-sdd validate` with PATH=/usr/bin:/bin (no openspec).

1. The OpenSpec process of this repository (main specs and open changes, project.md from the config context; since
   repo-own-format from the last commit that had openspec/) copied into a temporary solo-sdd/ tree passes;
   `openspec validate --all --strict` passes on that openspec/ tree.
2. A toy tree with one violation of each rule gives 11 error lines and `11 errors`; `--json` the same 11 triples.
3. `validate <one change>` gives only that change's errors. 4. A folder without solo-sdd/ gives `no solo-sdd/ tree`.
Run from the repository root: python3 tests/stands/change-format.py. Temporary folders are removed; the last line
is the summary."""
import io, json, os, pathlib, re, shutil, subprocess, sys, tarfile, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BARE = {k: v for k, v in os.environ.items() if k != "PATH"}
BARE.update(PATH="/usr/bin:/bin", PYTHONPATH=str(ROOT))

PROPOSAL = ("## Why\n\nA reason.\n\n## What Changes\n\n- A change.\n\n## Capabilities\n\n- `foo`\n\n## Impact\n\n`foo.py`.\n\n"
            "## Out of Scope\n\n- `other`.\n\n## Depends On\n\nnone\n\n## Source\n\n\"Do it\" (the owner).\n")
VERIFICATION = "## Live Scenario\n\nRun it.\n\n## Needs\n\nnone\n\n## Fallback\n\nNot needed.\n"
TASKS = "## 1. Code\n\n- [ ] 1.1 Code\n\n## 2. Acceptance\n\n- [ ] 2.1 Live\n- [ ] 2.2 Archive\n"
REQ = "### Requirement: %s\nThe system SHALL %s.\n\n#### Scenario: S\n- **WHEN** a\n- **THEN** b\n\n"
MAIN = "# foo\n\n## Purpose\n\nFoo.\n\n## Requirements\n\n" + REQ % ("Y", "do y")
ok = True


def legacy_openspec(parent):
    """Put this repository's openspec/ tree into `parent`: the folder itself, or, since repo-own-format moved it to
    solo-sdd/, the tree of the last commit that had it. Returns `parent/openspec`."""
    dest = pathlib.Path(parent) / "openspec"
    if (ROOT / "openspec").is_dir():
        shutil.copytree(ROOT / "openspec", dest)
        return dest
    run = dict(cwd=ROOT, capture_output=True, stdin=subprocess.DEVNULL, timeout=120)
    gone = subprocess.run(["git", "rev-list", "-n", "1", "HEAD", "--", "openspec"], text=True, **run).stdout.strip()
    data = subprocess.run(["git", "archive", "--format=tar", gone + "^", "openspec"], check=True, **run).stdout
    tarfile.open(fileobj=io.BytesIO(data)).extractall(parent)
    return dest


def step(name, good, detail):
    global ok
    ok &= good
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def validate(cwd, *args):
    p = subprocess.run([sys.executable, "-m", "solo_sdd", "validate", *args], cwd=cwd, env=BARE,
                       capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
    return p.returncode, p.stdout


def put(root, rel, text):
    p = pathlib.Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def change(root, cid, **over):
    files = {"proposal.md": PROPOSAL, "verification.md": VERIFICATION, "tasks.md": TASKS,
             "specs/foo/spec.md": "## ADDED Requirements\n\n" + REQ % ("X", "do x")}
    files.update(over)
    for rel, text in files.items():
        if text is not None:
            put(root, "solo-sdd/changes/%s/%s" % (cid, rel), text)


legacy_dir = tempfile.TemporaryDirectory()
legacy = legacy_openspec(legacy_dir.name)
with tempfile.TemporaryDirectory() as t:
    tree = pathlib.Path(t) / "solo-sdd"
    shutil.copytree(legacy / "specs", tree / "specs")
    for c in sorted((legacy / "changes").iterdir()):
        if c.is_dir() and c.name != "archive":
            shutil.copytree(c, tree / "changes" / c.name, ignore=shutil.ignore_patterns("CLAIM", "WAITING"))
    config = (legacy / "config.yaml").read_text(encoding="utf-8")
    context = re.search(r"^context: \|\n((?:  .*\n|\n)+)", config, re.M).group(1)
    put(t, "solo-sdd/project.md", "\n".join(l[2:] for l in context.splitlines()) + "\n")
    n = len(list((tree / "changes").iterdir()))
    code, out = validate(t, "--all")
    step("1. copy of the current process (%d open changes), PATH=/usr/bin:/bin" % n, (code, out) == (0, "0 errors\n"),
         "exit %d, %s" % (code, out.strip().splitlines()[-1] if out.strip() else "no output"))
openspec = shutil.which("openspec")
if openspec:
    p = subprocess.run([openspec, "validate", "--all", "--strict", "--no-interactive"], cwd=legacy.parent, capture_output=True,
                       text=True, stdin=subprocess.DEVNULL, timeout=300)
    step("1. openspec validate --all --strict on the repository", p.returncode == 0,
         "exit %d, %s" % (p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1]))
else:
    step("1. openspec validate --all --strict on the repository", False, "openspec not in PATH")
legacy_dir.cleanup()

with tempfile.TemporaryDirectory() as u:
    put(u, "solo-sdd/project.md", "Intent: a toy.\n")
    put(u, "solo-sdd/specs/foo/spec.md", MAIN)
    delta = ("## ADDED Requirements\n\n" + REQ % ("Long", "a" * 483) + (REQ % ("Fine", "x")).replace("- **THEN** b\n", "")
             + (REQ % ("Spaceless", "x")).replace("### R", "###R") + "## DEPRECATED Requirements\n\n" + REQ % ("Old", "x"))
    tasks = "## 1. Code\n\n" + "".join("- [ ] 1.%d t\n" % i for i in range(11)) + "\n## 2. Docs\n"
    change(u, "a", **{"verification.md": None, "tasks.md": tasks, "specs/foo/spec.md": delta,
                      "proposal.md": PROPOSAL.split("## Source")[0].replace("- `other`.", "<!-- template -->")})
    change(u, "b", **{"specs/foo/spec.md": None, "specs/new-thing/spec.md": "## ADDED Requirements\n\n" + REQ % ("N", "n")})
    change(u, "c", **{"specs/foo/spec.md": None})
    code, out = validate(u, "--all")
    lines = out.splitlines()
    step("2. toy tree with one violation of each rule", code == 1 and len(lines) == 12 and lines[-1] == "11 errors",
         "exit %d, %d error lines, %s" % (code, len(lines) - 1, lines[-1] if lines else "no output"))
    for line in lines[:-1]:
        print("    " + line)
    code, out = validate(u, "--all", "--json")
    got = ["%s: %s: %s" % (e["file"], e["rule"], e["item"]) for e in json.loads(out)]
    step("2. --json", code == 1 and got == lines[:-1], "exit %d, %d objects with the same file, rule, item" % (code, len(got)))
    code, out = validate(u, "b")
    step("3. validate b", code == 1 and out.splitlines()[-1] == "1 errors" and "changes/b/" in out and "changes/a/" not in out,
         "exit %d, %s" % (code, " | ".join(out.splitlines())))
with tempfile.TemporaryDirectory() as e:
    code, out = validate(e)
    step("4. folder without solo-sdd/", (code, out) == (1, "no solo-sdd/ tree\n"), "exit %d, %s" % (code, out.strip()))

print("total: %s" % ("all steps as expected" if ok else "there are failures"))
sys.exit(0 if ok else 1)
