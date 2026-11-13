#!/usr/bin/python3
"""Live scenario of change hooks-test-unittest.

Counts by `ast` the assertions of the last script version of tests/test_work_hooks.py (the newest commit whose version
has no unittest.TestCase) and of the current module; runs each mutant of a fixed list of global/work_hooks.py copies
against both (the module with failfast, one guard mutant in full to see two failures reported); counts the entry-point
runs per command with a counting copy of the hook; runs one test alone by `python3 -m unittest`; runs the module in this
folder with its own TMPDIR and lists `wh-home-*` there before and after; runs it in a temporary git worktree under
$TMPDIR; prints the seconds of the script and of the module. Every temporary folder and the worktree are removed.
Run from the repository root: python3 tests/stands/hooks-test-unittest.py; the last line is the summary.
"""
import ast, concurrent.futures, glob, os, re, shutil, subprocess, sys, tempfile, time, warnings

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
HOOK_REL, TEST_REL = "global/work_hooks.py", "tests/test_work_hooks.py"
ONE = "test_work_hooks.Secrets.test_secrets_in_bash_and_writes"
# (name, family, the text of global/work_hooks.py, its replacement): a guard rule switched off or a command emptied
GUARD_LINES = [("secret writes", "guard_env_write(tool, path, cwd)"), ("profile writes", "guard_override_write(tool, ti, path)"),
               ("write scope", "guard_scope(sid, cwd, path)"), ("claims", "guard_claim(sid, path, tool, ti)"),
               ("secret reads", "guard_env_read(ti, cwd)"), ("secrets in Bash", "guard_secrets_bash(text, cwd, cmd)"),
               ("profile edits in Bash", "guard_override_bash(cmd)"), ("models in Bash", "guard_models_bash(text, cmd)"),
               ("worktree", "guard_worktree(cmd, cwd)"), ("merge", "guard_merge(text, cwd, cmd)"),
               ("archive", "guard_archive(sid, text, cwd, inp)"), ("subagent models and roles", 'guard_models_agent(ti, bool(inp.get("agent_id")))')]
MUTANTS = [("guard: " + n, "guard", "        %s\n" % line, "        pass  # mutant\n") for n, line in GUARD_LINES]
MUTANTS.append(("guard: status handback", "guard", 'problems = status_problems(ti.get("message") or "", cwd)', "problems = []"))
FULL_RUN = "guard: secrets in Bash"
TMP = tempfile.mkdtemp(prefix="hooks-test-unittest-")
results = []


def step(name, good, detail):
    results.append(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail), flush=True)


def git(*a, cwd=ROOT):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True, check=True).stdout


def python():
    """The first interpreter that imports hypothesis: this one, then /usr/bin/python3."""
    for p in (sys.executable, "/usr/bin/python3"):
        if subprocess.run([p, "-c", "import hypothesis"], capture_output=True).returncode == 0:
            return p
    raise SystemExit("FAILED no interpreter imports hypothesis")


def base_script():
    for c in git("rev-list", "HEAD", "--", TEST_REL).split():
        text = git("show", "%s:%s" % (c, TEST_REL))
        if "unittest.TestCase" not in text:
            return c, text
    raise SystemExit("FAILED no script version of %s in the history" % TEST_REL)


def assertions(text):
    """assert statements plus self.assert*/self.fail calls."""
    n = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)  # the script's "\\;" literal on Python 3.12+
        tree_ = ast.parse(text)
    for node in ast.walk(tree_):
        if isinstance(node, ast.Assert):
            n += 1
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                and node.func.value.id == "self" and (node.func.attr.startswith("assert") or node.func.attr == "fail"):
            n += 1
    return n


def tree(name, hook_text, base_text):
    """A folder with global/ (the hook text given), solo_sdd/, tests/ with the module, marks.py and the base script."""
    d = os.path.join(TMP, re.sub(r"\W+", "-", name))
    shutil.copytree(os.path.join(ROOT, "global"), os.path.join(d, "global"), ignore=shutil.ignore_patterns("__pycache__"))
    open(os.path.join(d, HOOK_REL), "w").write(hook_text)
    # work_hooks_settings.py imports the solo_sdd package from the folder above global/
    shutil.copytree(os.path.join(ROOT, "solo_sdd"), os.path.join(d, "solo_sdd"), ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(os.path.join(d, "tests"))
    for f in ("test_work_hooks.py", "marks.py"):
        shutil.copy(os.path.join(ROOT, "tests", f), os.path.join(d, "tests", f))
    open(os.path.join(d, "tests/base_work_hooks.py"), "w").write(base_text)
    os.makedirs(os.path.join(d, "tmp"))
    return d


def run(args, cwd, tmpdir=None, timeout=540):
    env = {k: v for k, v in os.environ.items() if k not in ("SOLO_SDD_TESTS", "SOLO_SDD_EXPENSIVE_OK", "SOLO_SDD_REPLY_LANG")}
    if tmpdir:
        env["TMPDIR"] = tmpdir
    t = time.monotonic()
    try:
        p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        return p.returncode, p.stdout + p.stderr, time.monotonic() - t
    except subprocess.TimeoutExpired:
        return -1, "timeout after %d s" % timeout, time.monotonic() - t


def failed_tests(out):
    m = re.search(r"FAILED \(([^)]*)\)", out)
    return sum(int(x) for x in re.findall(r"(?:failures|errors)=(\d+)", m.group(1))) if m else 0


try:
    PYX = python()
    hook = open(os.path.join(ROOT, HOOK_REL)).read()
    base_commit, base = base_script()
    new = open(os.path.join(ROOT, TEST_REL)).read()
    old_n, new_n = assertions(base), assertions(new)
    step("1 assertions", new_n >= old_n and "unittest.TestCase" in new,
         "assertions: %d >= %d (script of %s)" % (new_n, old_n, base_commit[:7]))

    # the commands main dispatches, read from the hook
    commands = re.findall(r'"([\w-]+)": cmd_\w+', hook[hook.index("def main("):])
    for c in commands:
        MUTANTS.append(("command: " + c, c, '"%s": cmd_' % c, '"%s": (lambda inp: None) or cmd_' % c))
    trees = {}
    for name, _, old, rep in MUTANTS:
        if hook.count(old) != 1:
            raise SystemExit("FAILED mutant %r: its text occurs %d times in the hook" % (name, hook.count(old)))
        trees[name] = tree(name, hook.replace(old, rep), base)
    log = os.path.join(TMP, "entry-runs.log")
    counting = hook.replace("\n", '\nimport sys as _c\nif __name__ == "__main__":\n    open(%r, "a").write((_c.argv[1:] or [""])[0] + "\\n")\n' % log, 1)
    trees["count"] = tree("count", counting, base)
    trees["base"] = tree("base", hook, base)
    wt = os.path.join(TMP, "wt")
    git("worktree", "add", "--detach", wt, "HEAD")
    shutil.copytree(os.path.join(ROOT, "global"), os.path.join(wt, "global"), dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("test_work_hooks.py", "marks.py"):
        shutil.copy(os.path.join(ROOT, "tests", f), os.path.join(wt, "tests", f))
    own_tmp = os.path.join(TMP, "main-tmp")
    os.makedirs(own_tmp)

    jobs = {("base", "full"): ([PYX, "tests/base_work_hooks.py"], trees["base"])}
    for name, *_ in MUTANTS:
        jobs[(name, "base")] = ([PYX, "tests/base_work_hooks.py"], trees[name])
        jobs[(name, "new")] = ([PYX, "-m", "unittest"] + ([] if name == FULL_RUN else ["-f"]) + ["test_work_hooks"], os.path.join(trees[name], "tests"))
    jobs[("count", "new")] = ([PYX, "-m", "unittest", "test_work_hooks"], os.path.join(trees["count"], "tests"))
    jobs[("worktree", "new")] = ([PYX, TEST_REL], wt)
    jobs[("main", "new")] = ([PYX, TEST_REL], ROOT)
    before = set(glob.glob(os.path.join(own_tmp, "wh-home-*")))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        # each run has its own TMPDIR: a failing script leaves its wh-home-* there, and the main run's folder shows its own
        tmpdirs = {k: own_tmp if k == ("main", "new") else os.path.join(trees[k[0]], "tmp") if k[0] in trees else None for k in jobs}
        futs = {k: pool.submit(run, args, cwd, tmpdirs[k]) for k, (args, cwd) in jobs.items()}
        out = {k: f.result() for k, f in futs.items()}
    after = set(glob.glob(os.path.join(own_tmp, "wh-home-*")))

    # 2 mutants
    # caught: the script stops on a check (a traceback), the module reports a failed test; a timeout is not a catch
    caught = [n for n, *_ in MUTANTS if out[(n, "base")][0] > 0 and "Traceback (most recent call last)" in out[(n, "base")][1]
              and out[(n, "new")][0] > 0 and failed_tests(out[(n, "new")][1]) >= 1]
    missed = ["%s (script exit %d, module exit %d)" % (n, out[(n, "base")][0], out[(n, "new")][0]) for n, *_ in MUTANTS if n not in caught]
    families = sorted({f for _, f, *_ in MUTANTS})
    step("2 mutants", not missed, "mutants failed: %d of %d (families: %s)%s" % (len(caught), len(MUTANTS), ", ".join(families),
                                                                                  "; missed: " + "; ".join(missed) if missed else ""))
    two = failed_tests(out[(FULL_RUN, "new")][1])
    step("3 two failures", two >= 2, "mutant %r in a full run: %d failed tests reported" % (FULL_RUN, two))

    # 4 entry-point runs per command
    runs = open(log).read().split() if os.path.exists(log) else []
    per = {c: runs.count(c) for c in commands}
    step("4 entry-point runs", out[("count", "new")][0] == 0 and all(1 <= n <= 3 for n in per.values()) and set(runs) <= set(commands),
         "per command: " + ", ".join("%s %d" % kv for kv in per.items()))

    # 5 one test alone
    code, text, _ = run([PYX, "-m", "unittest", ONE], os.path.join(ROOT, "tests"))
    step("5 one test alone", code == 0 and re.search(r"^Ran 1 test in", text, re.M) is not None,
         "%s: %s" % (ONE, (re.findall(r"^Ran .*", text, re.M) or ["no Ran line"])[0]))

    # 6 leftovers, 7 location, 8 seconds
    mcode, mtext, msec = out[("main", "new")]
    # the script's own run in the same kind of TMPDIR shows the folder is where the HOMEs go: it leaves its one
    script_left = len(glob.glob(os.path.join(trees["base"], "tmp", "wh-home-*")))
    step("6 wh-home folders", mcode == 0 and not (after - before) and script_left >= 1,
         "module: before %d, after %d in its TMPDIR; the script left %d in its own" % (len(before), len(after), script_left))
    wcode = out[("worktree", "new")][0]
    step("7 main folder and worktree", mcode == 0 and wcode == 0, "main folder exit %d, worktree under %s exit %d (%s)"
         % (mcode, tempfile.gettempdir(), wcode, (re.findall(r"^Ran .*", mtext, re.M) or ["no Ran line"])[0]))
    bcode, _, bsec = out[("base", "full")]
    step("8 seconds", bcode == 0 and mcode == 0, "script %.0f s (exit %d), module %.0f s, side by side with the mutant runs" % (bsec, bcode, msec))
finally:
    if os.path.isdir(os.path.join(TMP, "wt")):
        subprocess.run(["git", "-C", ROOT, "worktree", "remove", "--force", os.path.join(TMP, "wt")], capture_output=True)
    shutil.rmtree(TMP, ignore_errors=True)

print("SUMMARY: all steps passed" if results and all(results) else "SUMMARY: %d of %d steps failed" % (results.count(False), len(results)))
sys.exit(0 if results and all(results) else 1)
