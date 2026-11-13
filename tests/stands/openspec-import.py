#!/usr/bin/python3
"""Live scenario of change openspec-import, steps 1-5, on a git copy of this repository's openspec/ tree
(since repo-own-format, the tree of the last commit that had it).

1. `import openspec` prints counts equal to the tree, `git status --short` stays empty.
2. `--write`: specs identical, changes identical except no `.openspec.yaml` and `Specs: none` lines; project.md holds
   the context with `Language: en` and `Mode: prod`. 3. `validate --all` with PATH=/usr/bin:/bin exits 0.
4. A second `--write` prints `nothing to import`, git status unchanged. 5. A folder without openspec/ exits 1.
Run from the repository root: python3 tests/stands/openspec-import.py. The temporary folder is removed; the last
line is the summary."""
import filecmp, io, os, pathlib, shutil, subprocess, sys, tarfile, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENV = dict(os.environ, PYTHONPATH=str(ROOT))
BARE = dict(ENV, PATH="/usr/bin:/bin")
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


def sh(cwd, *args, env=ENV):
    p = subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)
    return p.returncode, p.stdout + p.stderr


def solo(cwd, *args, env=ENV):
    return sh(cwd, sys.executable, "-m", "solo_sdd", *args, env=env)


def git(cwd, *args):
    return sh(cwd, "git", "-c", "user.name=t", "-c", "user.email=t@t", *args)[1]


def tree_diff(a, b):
    """Relative paths that differ between folders a and b: (only in a, only in b, differing)."""
    out = ([], [], [])

    def walk(c, rel):
        out[0].extend(rel + n for n in c.left_only)
        out[1].extend(rel + n for n in c.right_only)
        out[2].extend(rel + n for n in c.diff_files)
        for n, sub in c.subdirs.items():
            walk(sub, rel + n + "/")
    walk(filecmp.dircmp(a, b, ignore=[]), "")
    return out


with tempfile.TemporaryDirectory() as t:
    T = pathlib.Path(t)
    legacy_openspec(T)
    first = sorted(d for d in (T / "openspec/changes").iterdir() if (d / ".openspec.yaml").is_file() and d.name != "archive")[0]
    with open(first / ".openspec.yaml", "a") as f:
        f.write("skip_specs: true\n")  # exercises the Specs: none marking on a real proposal
    git(T, "init", "-q")
    git(T, "add", ".")
    git(T, "commit", "-qm", "init")
    src = T / "openspec"
    specs = len([d for d in (src / "specs").iterdir() if d.is_dir()])
    open_ = len([d for d in (src / "changes").iterdir() if d.is_dir() and d.name != "archive"])
    archived = len([d for d in (src / "changes" / "archive").iterdir() if d.is_dir()])
    code, out = solo(T, "import", "openspec")
    want = "%d specs, %d open changes, %d archived changes" % (specs, open_, archived)
    status = git(T, "status", "--short")
    step("1. plan", code == 0 and want in out and "plan only" in out and status == "",
         "exit %d, %s; git status %s" % (code, out.splitlines()[0], "empty" if not status else "not empty"))

    code, out = solo(T, "import", "openspec", "--write")
    d_specs = tree_diff(src / "specs", T / "solo-sdd/specs")
    only_src, only_dst, differ = tree_diff(src / "changes", T / "solo-sdd/changes")
    yaml = [p for p in only_src if p.endswith(".openspec.yaml")]
    marked = all({l for l in (T / "solo-sdd/changes" / p).read_text().splitlines()}
                 - {l for l in (src / "changes" / p).read_text().splitlines()} == {"Specs: none"} for p in differ)
    project = (T / "solo-sdd/project.md").read_text()
    good = (code == 0 and d_specs == ([], [], []) and len(yaml) == len(only_src) and not only_dst and marked
            and differ == ["%s/proposal.md" % first.name]
            and "Language: en\nMode: prod\n" in project and "Intent:" in project
            and "delete openspec/" in out.strip().splitlines()[-1])
    step("2. write", good, "exit %d; specs identical: %s; changes: %d .openspec.yaml not copied, %d with Specs: none, "
         "%d other differences; project.md: %s" % (code, d_specs == ([], [], []), len(yaml), len(differ) if marked else 0,
                                                   len(only_src) - len(yaml) + len(only_dst) + (0 if marked else len(differ)),
                                                   " | ".join(project.splitlines()[2:4])))

    code, out = solo(T, "validate", "--all", env=BARE)
    step("3. validate --all, PATH=/usr/bin:/bin", code == 0, "exit %d, %s" % (code, out.strip().splitlines()[-1]))

    before = git(T, "status", "--short")
    code, out = solo(T, "import", "openspec", "--write")
    step("4. repeat", code == 0 and "nothing to import" in out and git(T, "status", "--short") == before,
         "exit %d, %s" % (code, out.strip()))

    (T / "empty").mkdir()
    code, out = solo(T / "empty", "import", "openspec")
    step("5. no openspec/", (code, out.strip()) == (1, "no openspec/ tree"), "exit %d, %s" % (code, out.strip()))

print("openspec-import stand: %s" % ("all steps passed" if ok else "FAILED"))
sys.exit(0 if ok else 1)
