#!/usr/bin/python3
"""Live scenario of change change-cli, steps 1-5: `solo-sdd new`, `list` and `archive` with PATH=/usr/bin:/bin.

1-4. A temporary git repository with solo-sdd/project.md and the main spec `export` of two requirements: `new add-csv`,
   `list`, the filled change archived, a change modifying a missing requirement refused with a clean `git status`,
   `list --specs --json`.
5. Replay: archived changes of this repository with MODIFIED deltas, applied by `solo-sdd archive` to the main specs
   as they were before their commit, give the main specs that OpenSpec wrote in that commit.
Run from the repository root: python3 tests/stands/change-cli.py. Temporary folders are removed; the last line is
the summary."""
import datetime, json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BARE = {k: v for k, v in os.environ.items() if k != "PATH"}
BARE.update(PATH="/usr/bin:/bin", PYTHONPATH=str(ROOT))
TODAY = datetime.date.today().isoformat()
REPLAY = ("openspec-standalone", "lead-writes-code", "pr-wait-codeql")
REQ = "### Requirement: %s\nThe system SHALL %s.\n\n#### Scenario: S\n- **WHEN** a\n- **THEN** b\n"
FILLED = {
    "proposal.md": ("# Proposal\n\n## Why\n\nCSV export is missing.\n\n## What Changes\n\n- CSV.\n\n## Capabilities\n\n"
                    "### New Capabilities\n- `import`\n\n### Modified Capabilities\n- `export`\n\n## Impact\n\n`export.py`.\n\n"
                    "## Out of Scope\n\n- XML.\n\n## Depends On\n\nnone\n\n## Source\n\n\"Add CSV\" (the owner).\n"),
    "verification.md": "## Live Scenario\n\nExport a CSV.\n\n## Needs\n\nnone\n\n## Fallback\n\nNot needed.\n\n## Result\n\nExported.\n",
    "specs/export/spec.md": ("## ADDED Requirements\n\n" + REQ % ("Csv", "write CSV") +
                             "\n## MODIFIED Requirements\n\n" + REQ % ("Export", "export every row")),
    "specs/import/spec.md": ("## Purpose\n\nImports rows into the toy project from the CSV files it exported.\n\n"
                             "## ADDED Requirements\n\n" + REQ % ("Read", "read CSV")),
}
ok = True


def step(name, good, detail):
    global ok
    ok &= good
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def sdd(cwd, *args):
    p = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=cwd, env=BARE, capture_output=True,
                       text=True, stdin=subprocess.DEVNULL, timeout=120)
    return p.returncode, p.stdout


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, capture_output=True,
                          text=True, stdin=subprocess.DEVNULL, timeout=60).stdout


def put(root, rel, text):
    p = pathlib.Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


with tempfile.TemporaryDirectory() as t:
    git(t, "init", "-q", "-b", "main")
    put(t, "solo-sdd/project.md", "Intent: a toy exporter.\n")
    put(t, "solo-sdd/specs/export/spec.md", "# export Specification\n\n## Purpose\nExports rows.\n\n## Requirements\n\n"
        + REQ % ("Export", "export rows") + "\n" + REQ % ("Format", "keep the format"))
    git(t, "add", "-A")
    git(t, "commit", "-qm", "init")

    code, out = sdd(t, "new", "add-csv")
    files = sorted(p.name for p in (pathlib.Path(t) / "solo-sdd/changes/add-csv").iterdir())
    listed = sdd(t, "list")
    step("1 new and list", code == 0 and files == ["proposal.md", "tasks.md", "verification.md"]
         and listed == (0, "add-csv 0/2\n"), "new -> %d %s; list -> %r" % (code, files, listed[1]))

    for rel, text in FILLED.items():
        put(t, "solo-sdd/changes/add-csv/" + rel, text)
    git(t, "add", "-A")
    git(t, "commit", "-qm", "change")
    code, out = sdd(t, "archive", "add-csv", "--yes")
    export = (pathlib.Path(t) / "solo-sdd/specs/export/spec.md").read_text()
    imp = pathlib.Path(t) / "solo-sdd/specs/import/spec.md"
    git(t, "add", "-A")
    stat = sorted(l.split()[1] for l in git(t, "diff", "--cached", "--name-status", "--no-renames").splitlines())
    expected = ["solo-sdd/changes/add-csv/" + n for n in ("proposal.md", "specs/export/spec.md", "specs/import/spec.md",
                                                          "tasks.md", "verification.md")]
    expected += ["solo-sdd/changes/archive/%s-add-csv/%s" % (TODAY, n[len("solo-sdd/changes/add-csv/"):]) for n in expected]
    expected = sorted(expected + ["solo-sdd/specs/export/spec.md", "solo-sdd/specs/import/spec.md"])
    good = (code == 0 and export.count("SHALL write CSV") == 1 and export.count("SHALL export every row") == 1
            and "export rows." not in export and imp.is_file() and "Imports rows" in imp.read_text()
            and (pathlib.Path(t) / ("solo-sdd/changes/archive/%s-add-csv" % TODAY)).is_dir() and stat == expected)
    step("2 archive", good, "exit %d, %d changed paths, only the specs and the moved change" % (code, len(stat)))
    git(t, "commit", "-qm", "archived")

    put(t, "solo-sdd/changes/bad/proposal.md", FILLED["proposal.md"])
    put(t, "solo-sdd/changes/bad/verification.md", FILLED["verification.md"])
    put(t, "solo-sdd/changes/bad/tasks.md", "## 1. Acceptance\n\n- [ ] 1.1 Live\n- [ ] 1.2 Archive\n")
    put(t, "solo-sdd/changes/bad/specs/export/spec.md", "## MODIFIED Requirements\n\n" + REQ % ("Missing", "x"))
    git(t, "add", "-A")
    git(t, "commit", "-qm", "bad")
    code, out = sdd(t, "archive", "bad", "--yes")
    status = git(t, "status", "--short")
    step("3 refused", code == 1 and status == "" and "Missing" in out,
         "exit %d, git status %r, %s" % (code, status, out.splitlines()[0]))

    code, out = sdd(t, "list", "--specs", "--json")
    step("4 list --specs --json", code == 0 and json.loads(out) == [{"id": "export", "requirements": 3},
                                                                     {"id": "import", "requirements": 1}], out.replace("\n", " "))

shallow = git(ROOT, "rev-parse", "--is-shallow-repository").strip() == "true"
for cid in REPLAY:
    if shallow:
        step("5 replay " + cid, False, "shallow clone: run git fetch --unshallow")
        continue
    arch = [p for p in git(ROOT, "log", "--format=%H", "--diff-filter=A", "--", "openspec/changes/archive/").split()
            if any(n.split("/")[3].endswith("-" + cid) for n in git(ROOT, "show", "--name-only", "--format=", p).split()
                   if n.startswith("openspec/changes/archive/2"))]
    commit = arch[-1]
    folder = next(n.split("/")[3] for n in git(ROOT, "show", "--name-only", "--format=", commit).split()
                  if n.startswith("openspec/changes/archive/2") and n.split("/")[3].endswith("-" + cid))
    with tempfile.TemporaryDirectory() as t:
        tree = pathlib.Path(t) / "solo-sdd"
        put(t, "solo-sdd/project.md", "Intent: replay.\n")
        caps = []
        for n in git(ROOT, "ls-tree", "-r", "--name-only", commit, "openspec/changes/archive/" + folder).split():
            rel = n.split("/", 4)[4]
            put(t, "solo-sdd/changes/%s/%s" % (cid, rel), git(ROOT, "show", "%s:%s" % (commit, n)))
            if rel.startswith("specs/"):
                caps.append(rel.split("/")[1])
        for cap in caps:
            before = git(ROOT, "show", "%s^:openspec/specs/%s/spec.md" % (commit, cap))
            if before:  # no main spec before the commit: a new capability
                put(t, "solo-sdd/specs/%s/spec.md" % cap, before)
        code, out = sdd(t, "archive", cid, "--yes", "--force")  # replays the deltas; old changes predate the gate
        same = []
        for cap in caps:
            got = (tree / "specs" / cap / "spec.md").read_text().splitlines()
            want = git(ROOT, "show", "%s:openspec/specs/%s/spec.md" % (commit, cap)).splitlines()
            same.append([l.rstrip() for l in got] == [l.rstrip() for l in want])
        step("5 replay " + cid, code == 0 and all(same),
             "commit %s, exit %d, %d of %d specs equal" % (commit[:7], code, sum(same), len(same)))

print("change-cli stand: %s" % ("all steps passed" if ok else "FAILED"))
sys.exit(0 if ok else 1)
