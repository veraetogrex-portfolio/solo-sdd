#!/usr/bin/env python3
"""Live scenario of change owner-traces-in-rules, without model calls.

The owner-tool names are read from git history, never written here: each is the word a pattern finds in a text of
the commit before this change. A temporary denylist holds them; the shared local denylist of the git folder is not
touched.
1. No file outside solo-sdd/changes/ names any of them.
2. tests/test_public_tree.py on a temporary copy of the tree with the temporary denylist: code 0.
3. The same with skills/context-resume/SKILL.md and ALGORITHM.md of the commit before (git show): code 1, only those
   two files named, among them context-resume line 20 and ALGORITHM.md line 15.
4. `sync.py push --global-rules` into a temporary HOME: the deployed context-resume names "a notes vault, if the
   project names one" and "chat search, if the agent has it"; the deployed context-resume, spec-next, debug-profile
   and global rules name no denylisted word.
Run from the repository root: python3 tests/stands/owner-traces-in-rules.py. The temporary folder is removed; the last
line is "SUMMARY: all steps passed" (code 0) or "SUMMARY: N of M steps failed" (code 1)."""
import os, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENV = {k: v for k, v in os.environ.items() if k not in ("HOME", "SOLO_SDD_TESTS")}
BASE = "51600a0eed8c0d1081ce7a3a4fde3840b2e63c25"  # main before this change: pinned, so the stand runs the same after the merge
# (file of the base commit, a pattern whose groups are the names): the patterns hold none of the names
SOURCES = [
    ("skills/context-resume/SKILL.md", r"- (\w+): start with `(\w+)\.md`"),  # the notes app and its index file
    ("skills/context-resume/SKILL.md", r"first `(\w+)` for every such chat"),  # a chat tool function
    ("skills/context-resume/SKILL.md", r"chat search \(`(\w+)`\)"),  # a chat tool function
    ("skills/debug-profile/SKILL.md", r"URL, (\w+) workflow>"),  # the workflow service
    ("global/AGENTS.md", r"compatibility with tests and (\w+) before"),  # the desktop framework
    ("global/AGENTS.md", r"can be about code, a (\w+), logs"),  # the job-search word
]
results = []


def step(name, good, detail):
    results.append(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def run(*args, cwd=ROOT, env=None):
    return subprocess.run(list(args), cwd=cwd, env=env or ENV, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=600)


def git(*args, cwd=ROOT):
    return run("git", *args, cwd=cwd).stdout


words = []
for rel, pattern in SOURCES:
    m = re.search(pattern, git("show", "%s:%s" % (BASE, rel)))
    if not m:
        print("SUMMARY: the commit %s is not in this clone or %s has no line for %s" % (BASE[:7], rel, pattern))
        sys.exit(1)
    words += m.groups()
deny = [re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)", re.I) for w in words]  # the rule of load_denylist
print("words from %s: %d" % (BASE[:7], len(words)))

files = [f for f in git("ls-files", "-c", "-o", "--exclude-standard").splitlines()
         if not f.startswith("solo-sdd/changes/") and (ROOT / f).is_file()]
hits = ["%s:%d" % (f, n) for f in files
        for n, l in enumerate((ROOT / f).read_text(encoding="utf-8", errors="ignore").splitlines(), 1)
        if any(rx.search(l) for rx in deny)]
step("1 files", not hits, "%d files, naming a word: %s" % (len(files), ", ".join(hits) or "none"))

# test_public_tree.py imports hypothesis: the first interpreter that has it (the system one when PATH starts with another)
PY = next((py for py in (sys.executable, "/usr/bin/python3")
           if os.path.exists(py) and run(py, "-c", "import hypothesis").returncode == 0), None)
print("public tree runs under: %s" % (PY or "no interpreter with hypothesis (python3 -m pip install --user hypothesis)"))


def public_tree(t, old=()):
    """test_public_tree.py on a copy of the tree with the temporary denylist, the files `old` taken from BASE:
    (code, {file: [lines]} it names, stderr tail)."""
    copy = pathlib.Path(t) / "copy"
    shutil.rmtree(copy, ignore_errors=True)
    for f in files:
        (copy / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, copy / f)
    for rel in old:
        (copy / rel).write_text(git("show", "%s:%s" % (BASE, rel)), encoding="utf-8")
    run("git", "init", "-q", cwd=copy)
    run("git", "add", "-A", cwd=copy)
    (copy / ".git/info").mkdir(exist_ok=True)
    (copy / ".git/info/public-denylist.txt").write_text("\n".join(words) + "\n", encoding="utf-8")
    if PY is None:
        return -1, {}, "no interpreter with hypothesis: %s, /usr/bin/python3" % sys.executable
    p = run(PY, "tests/test_public_tree.py", cwd=copy)
    named = {}
    for f, n in re.findall(r"([\w./-]+):(\d+)", p.stdout + p.stderr):
        if (copy / f).is_file():
            named.setdefault(f, set()).add(int(n))
    return p.returncode, named, " | ".join(p.stderr.strip().splitlines()[-3:])


def show(named):
    return ", ".join("%s %s" % (f, sorted(n)) for f, n in sorted(named.items())) or "none"


with tempfile.TemporaryDirectory() as t:
    code, named, tail = public_tree(t)
    step("2 public tree, this tree", code == 0,
         "code %d, named: %s%s" % (code, show(named), "" if code == 0 else "; stderr: " + tail))
    old = ("skills/context-resume/SKILL.md", "ALGORITHM.md")
    code, named, tail = public_tree(t, old)
    good = code == 1 and set(named) == set(old) and 20 in named[old[0]] and 15 in named[old[1]]
    step("3 public tree, context-resume and ALGORITHM.md before", good,
         "code %d, named: %s%s" % (code, show(named), "" if good else "; stderr: " + tail))

    home = pathlib.Path(t) / "home"
    p = run(sys.executable, "sync.py", "push", "--global-rules", env={**ENV, "HOME": str(home)})
    read = lambda rel: (home / rel).read_text(encoding="utf-8") if (home / rel).is_file() else ""
    texts = {r: read(r) for r in (".claude/skills/context-resume/SKILL.md", ".claude/skills/spec-next/SKILL.md",
                                  ".claude/skills/debug-profile/SKILL.md", ".claude/CLAUDE.md")}
    cr = texts[".claude/skills/context-resume/SKILL.md"]
    kinds = ["a notes vault, if the project names one" in cr, "chat search, if the agent has it" in cr]
    bad = ["%s: %s" % (r, m.group()) for r, x in texts.items() for rx in deny for m in rx.finditer(x)]
    empty = [r for r, x in texts.items() if not x]
    step("4 deployed texts", p.returncode == 0 and all(kinds) and not bad and not empty,
         "push code %d, context-resume sources by kind: %s, denylisted words: %s, missing: %s"
         % (p.returncode, kinds, ", ".join(bad) or "none", ", ".join(empty) or "none"))

failed = results.count(False)
print("SUMMARY: all steps passed" if not failed else "SUMMARY: %d of %d steps failed" % (failed, len(results)))
sys.exit(1 if failed else 0)
