#!/usr/bin/env python3
"""Live scenario of change own-debugging, without model calls.

The plugin name and its skill name are read from git history, never written here: the backquoted `plugin:name` of
`skills/relay/SKILL.md` in the commit before this change. A temporary denylist holds them; the shared local denylist
of the git folder is not touched.
1. No tracked file outside solo-sdd/changes/ names either word.
2. tests/test_public_tree.py on a temporary copy of the tree with the temporary denylist: code 0.
3. The same with the README.md of the commit before this change (git show): code 1, README.md named.
4. `sync.py push --global-rules` into a temporary HOME: the deployed debug-profile has the code bug path steps in
   order and its description names a failing test.
5. The deployed relay and global rules name /debug-profile; none of the three deployed texts names a backquoted
   `plugin:name` or either word.
Run from the repository root: python3 tests/stands/own-debugging.py. The temporary folder is removed; the last line
is "SUMMARY: all steps passed" (code 0) or "SUMMARY: N of M steps failed" (code 1)."""
import os, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLUGIN = re.compile(r"`([a-z][a-z0-9-]*):([a-z0-9-]+)[^`]*`")  # `file:line` is a place, not a plugin
ENV = {k: v for k, v in os.environ.items() if k != "HOME"}
results = []


def step(name, good, detail):
    results.append(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def run(*args, cwd=ROOT, env=None):
    return subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          timeout=600)


def git(*args, cwd=ROOT):
    return run("git", *args, cwd=cwd).stdout


def plugins(text):
    return [m for m in PLUGIN.finditer(text) if m.group(1) != "file"]


base = "4c47e68303daa613e2d8df30c782eb6e6de797db"  # main before this change: pinned, so the stand runs the same after the merge
found = plugins(git("show", base + ":skills/relay/SKILL.md"))
if not found:
    print("SUMMARY: the commit %s is not in this clone or names no plugin skill in skills/relay/SKILL.md" % base[:7])
    sys.exit(1)
words = [found[0].group(1), found[0].group(2)]
deny = [re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)", re.I) for w in words]  # the rule of load_denylist
print("words from %s: %d, a plugin and its skill" % (base[:7], len(words)))

files = [f for f in git("ls-files", "-c", "-o", "--exclude-standard").splitlines()
         if not f.startswith("solo-sdd/changes/") and (ROOT / f).is_file()]
hits = ["%s:%d" % (f, n) for f in files
        for n, l in enumerate((ROOT / f).read_text(encoding="utf-8", errors="ignore").splitlines(), 1)
        if any(rx.search(l) for rx in deny)]
step("1 tracked files", not hits, "%d files, naming either word: %s" % (len(files), ", ".join(hits) or "none"))


# test_public_tree.py imports hypothesis: the first interpreter that has it (the system one when PATH starts with another)
PY = next((py for py in (sys.executable, "/usr/bin/python3")
           if os.path.exists(py) and run(py, "-c", "import hypothesis").returncode == 0), None)
print("public tree runs under: %s" % (PY or "no interpreter with hypothesis (python3 -m pip install --user hypothesis)"))


def public_tree(t, readme=None):
    """test_public_tree.py on a copy of the tree with the temporary denylist: (code, the files it names)."""
    copy = pathlib.Path(t) / "copy"
    shutil.rmtree(copy, ignore_errors=True)
    for f in files:
        (copy / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, copy / f)
    if readme is not None:
        (copy / "README.md").write_text(readme, encoding="utf-8")
    run("git", "init", "-q", cwd=copy)
    run("git", "add", "-A", cwd=copy)
    (copy / ".git/info").mkdir(exist_ok=True)
    (copy / ".git/info/public-denylist.txt").write_text("\n".join(words) + "\n", encoding="utf-8")
    if PY is None:
        return -1, [], "no interpreter with hypothesis: %s, /usr/bin/python3" % sys.executable
    p = run(PY, "tests/test_public_tree.py", cwd=copy)
    named = sorted(set(re.findall(r"^([\w./-]+):\d+: ", p.stdout + p.stderr, re.M)))
    return p.returncode, named, " | ".join(p.stderr.strip().splitlines()[-3:])


with tempfile.TemporaryDirectory() as t:
    code, named, tail = public_tree(t)
    good = code == 0
    step("2 public tree, this tree", good,
         "code %d, files named: %s%s" % (code, ", ".join(named) or "none", "" if good else "; stderr: " + tail))
    code, named, tail = public_tree(t, git("show", base + ":README.md"))
    good = code == 1 and named == ["README.md"]
    step("3 public tree, the README before", good,
         "code %d, files named: %s%s" % (code, ", ".join(named) or "none", "" if good else "; stderr: " + tail))

    home = pathlib.Path(t) / "home"
    p = run(sys.executable, "sync.py", "push", "--global-rules", env={**ENV, "HOME": str(home)})
    read = lambda rel: (home / rel).read_text(encoding="utf-8") if (home / rel).is_file() else ""
    dp, relay, rules = (read(r) for r in (".claude/skills/debug-profile/SKILL.md", ".claude/skills/relay/SKILL.md",
                                          ".claude/CLAUDE.md"))
    path = dp.split("## 3. A bug in code", 1)[-1].split("\n## ", 1)[0] if "## 3. A bug in code" in dp else ""
    at = [path.find(s) for s in ("a failing test", "call chain", "working example", "One hypothesis", "Bug fix")]
    desc = dp.split("description:", 1)[-1].split("\n", 1)[0]
    step("4 deployed debug-profile", p.returncode == 0 and -1 not in at and at == sorted(at)
         and "a failing test" in desc and "docs/debug-profile.md" not in path,
         "push code %d, code bug steps at %s, description names a failing test: %s"
         % (p.returncode, at, "a failing test" in desc))
    texts = {".claude/skills/debug-profile/SKILL.md": dp, ".claude/skills/relay/SKILL.md": relay,
             ".claude/CLAUDE.md": rules}
    bad = ["%s: %s" % (r, m.group()) for r, x in texts.items() for m in plugins(x)]
    bad += ["%s: a denylisted word" % r for r, x in texts.items() if any(rx.search(x) for rx in deny)]
    step("5 deployed relay and rules", "`/debug-profile`" in relay and "debug through `/debug-profile`" in rules
         and not bad, "plugin skills or words: %s" % (", ".join(bad) or "none"))

failed = results.count(False)
print("SUMMARY: all steps passed" if not failed else "SUMMARY: %d of %d steps failed" % (failed, len(results)))
sys.exit(1 if failed else 0)
