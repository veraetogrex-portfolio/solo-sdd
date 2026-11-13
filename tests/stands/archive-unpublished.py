#!/usr/bin/env python3
"""Live scenario of change archive-unpublished: the change archive outside git, on temporary clones only.

1. The transition: a clone where the archive is still tracked (the commit before this change, rebuilt from this tree and
   the archive on disk) and a worktree whose branch removes the archive from the index; `sdd-dispatch.py land-local`
   with a check that is red with the change rolls back with every archive file tracked and on disk and a clean
   `git status`; with the checks green it merges, the archive is untracked and every file is on disk, byte for byte.
2. After it: a change archived in a worktree by `sdd-worktree.py setup`, `solo-sdd archive --yes` and `land-local`
   lands in the main folder's `solo-sdd/changes/archive/`, the archived folders that were there stay.
3. A fresh clone (no archive on disk) passes the `Changelog` tests of `tests/test_release.py`.
4. The publication step of `docs/release.md`, run against a temporary bare repository (never GitHub), gives one commit
   with no archive path; after it local `main` is the public commit, the old `main` is `history-private`, and the
   installed `pre-push` guard refuses the old history and a tag on a blob and passes a new branch and a deletion.
Run from the repository root: python3 tests/stands/archive-unpublished.py. It needs `solo-sdd/changes/archive/` on
disk (the author's working folder or a worktree the dispatcher prepared). The temporary folder is removed; the last
line is "SUMMARY: all steps passed", code 0, or "SUMMARY: <n> failed", code 1."""
import filecmp
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
ARCH = "solo-sdd/changes/archive"
DISPATCH = ROOT / "global/sdd_dispatch.py"
WORKTREE = ROOT / "global/sdd_worktree.py"
results = []


def python():
    """The first interpreter that imports hypothesis (tests/test_release.py needs it)."""
    for p in (sys.executable, "/usr/bin/python3"):
        if subprocess.run([p, "-c", "import hypothesis"], capture_output=True, stdin=subprocess.DEVNULL).returncode == 0:
            return p
    return sys.executable


PY = python()


def step(name, good, detail):
    results.append(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def sh(args, cwd, env, timeout=300):
    return subprocess.run(args, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL)


def files(base):
    p = pathlib.Path(base, ARCH)
    return sorted(str(f.relative_to(p)) for f in p.rglob("*") if f.is_file()) if p.is_dir() else []


def same_archive(a, b):
    fa = files(a)
    return fa == files(b) and all(filecmp.cmp(os.path.join(a, ARCH, f), os.path.join(b, ARCH, f), shallow=False)
                                  for f in fa)


CHANGE = {
    "proposal.md": "# Proposal\n\n## Why\n\nA stand change.\n\n## What Changes\n\n- Nothing.\n\n## Capabilities\n\n"
                   "Specs: none\n\n## Impact\n\nnone\n\n## Out of Scope\n\nnone\n\n## Depends On\n\nnone\n\n"
                   "## Source\n\nthe stand\n",
    "tasks.md": "## 1. Implementation\n\n- [x] 1.1 Nothing\n\n## 2. Acceptance\n\n- [x] 2.1 Nothing\n",
    "verification.md": "## Live Scenario\n\n1. `true` → code 0.\n\n## Needs\n\nnone\n\n## Fallback\n\nnone\n\n"
                       "## Result\n\nThe stand ran.\n\n## Not Verified\n\nnothing\n\n## Decisions Without Owner\n\nnone\n",
}


def main():
    if not files(ROOT):
        print("FAILED setup: no %s on disk in %s" % (ARCH, ROOT))
        print("SUMMARY: 1 failed")
        return 1
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="archive-unpublished-")).resolve()
    try:
        return run(tmp)
    finally:
        subprocess.run(["git", "-C", str(tmp / "main"), "worktree", "prune"], capture_output=True,
                       stdin=subprocess.DEVNULL)
        shutil.rmtree(tmp, ignore_errors=True)


def run(tmp):
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    # land-local validates a solo-sdd/ tree by the solo-sdd command: the one of the folder it runs in
    (bin_dir / "solo-sdd").write_text('#!/bin/sh\nPYTHONPATH="$PWD" exec "%s" -m solo_sdd "$@"\n' % PY)
    (bin_dir / "solo-sdd").chmod(0o755)
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"], GIT_AUTHOR_NAME="t",
               GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    env.pop("SOLO_SDD_TESTS", None)
    main, wt = tmp / "main", tmp / "wt"
    git = lambda repo, *a: sh(["git", "-C", str(repo), *a], repo, env)

    # 1. The transition. MAIN before the change: this tree with the archive tracked and without the ignore line.
    git(tmp, "clone", "-q", str(ROOT), str(main))
    git(main, "checkout", "-q", "-B", "main")
    shutil.copytree(ROOT / ARCH, main / ARCH, dirs_exist_ok=True)
    ignore = (main / ".gitignore").read_text(encoding="utf-8")
    (main / ".gitignore").write_text(ignore.replace("solo-sdd/changes/archive/\n", ""), encoding="utf-8")
    git(main, "add", "-A", "-f", ".gitignore", ARCH)
    git(main, "commit", "-q", "-m", "before: the archive tracked")
    tracked = git(main, "ls-files", ARCH).stdout.split()
    git(main, "worktree", "add", "-q", "-b", "change/au-sim", str(wt))
    r = sh([PY, str(WORKTREE), "setup", str(main), str(wt)], main, env)
    (wt / ".gitignore").write_text(ignore, encoding="utf-8")
    git(wt, "rm", "-r", "-q", "--cached", ARCH)
    new = ARCH + "/2026-11-11-au-sim"  # not a real archived name: the real one is in the copied archive
    pathlib.Path(wt, new).mkdir()
    pathlib.Path(wt, new, "tasks.md").write_text("t\n", encoding="utf-8")
    git(wt, "add", "-A")
    git(wt, "commit", "-q", "-m", "archive-unpublished")
    step("before", len(tracked) == len(files(ROOT)) and r.returncode == 0 and not git(wt, "ls-files", ARCH).stdout,
         "MAIN tracks %d archive files, the branch none" % len(tracked))
    head = git(main, "rev-parse", "HEAD").stdout
    land = lambda cid, *checks: sh([PY, str(DISPATCH), "land-local", str(main), str(wt), cid, *checks], main, env, 600)
    r = land("au-sim", "--check", "test ! -d " + new)
    status = git(main, "status", "--porcelain").stdout
    step("rollback", r.returncode == 3 and git(main, "rev-parse", "HEAD").stdout == head
         and git(main, "ls-files", ARCH).stdout.split() == tracked and same_archive(main, ROOT) and status == "",
         "code %d, tracked %d, on disk %d of %d, git status %s" % (
             r.returncode, len(git(main, "ls-files", ARCH).stdout.split()), len(files(main)), len(files(ROOT)),
             "clean" if not status else "%d lines" % len(status.splitlines())))
    r = land("au-sim")
    landed = pathlib.Path(main, new, "tasks.md").is_file()
    shutil.rmtree(main / new, ignore_errors=True)
    step("merge", r.returncode == 0 and not git(main, "ls-files", ARCH).stdout and landed and same_archive(main, ROOT)
         and git(main, "status", "--porcelain").stdout == "",
         "code %d, tracked %d, on disk %d of %d plus the new folder: %s" % (
             r.returncode, len(git(main, "ls-files", ARCH).stdout.split()), len(files(main)), len(files(ROOT)), landed))

    # 2. After the change: a change archived in a worktree lands in MAIN's ignored archive.
    for name, text in CHANGE.items():
        pathlib.Path(main, "solo-sdd/changes/stand-x").mkdir(parents=True, exist_ok=True)
        pathlib.Path(main, "solo-sdd/changes/stand-x", name).write_text(text, encoding="utf-8")
    git(main, "add", "solo-sdd/changes/stand-x")
    git(main, "commit", "-q", "-m", "stand-x")
    before = files(main)
    git(main, "worktree", "add", "-q", "-b", "change/stand-x", str(wt))
    r1 = sh([PY, str(WORKTREE), "setup", str(main), str(wt)], main, env)
    r2 = sh([PY, "-m", "solo_sdd", "archive", "stand-x", "--yes"], wt, dict(env, PYTHONPATH=str(wt)))
    git(wt, "add", "-A")
    git(wt, "commit", "-q", "-m", "stand-x: archive")
    in_git = git(wt, "ls-files", ARCH).stdout
    r = land("stand-x")
    added = sorted(set(files(main)) - set(before))
    step("archive in a worktree", r1.returncode == 0 and r2.returncode == 0 and not in_git and r.returncode == 0
         and set(before) <= set(files(main)) and len(added) == 3 and all(re.match(r"\d{4}-\d{2}-\d{2}-stand-x/", f)
                                                                          for f in added)
         and not git(main, "ls-files", ARCH).stdout,
         "setup %d, archive %d, land %d, new files %s, the %d earlier files stay" % (
             r1.returncode, r2.returncode, r.returncode, ", ".join(added) or "none", len(before)))

    # 3. A fresh clone has no archive on disk and passes the Changelog tests.
    fresh = tmp / "fresh"
    git(tmp, "clone", "-q", str(main), str(fresh))
    r = sh([PY, str(fresh / "tests/test_release.py"), "Changelog"], fresh, env)
    step("fresh clone", not (fresh / ARCH).exists() and r.returncode == 0,
         "archive on disk: %s, Changelog tests code %d %s" % ((fresh / ARCH).exists(), r.returncode,
                                                              (r.stderr.strip().splitlines() or [""])[-1]))

    # 4. The publication step of docs/release.md against a temporary bare repository.
    shutil.copytree(ROOT / ARCH, fresh / ARCH, dirs_exist_ok=True)  # the owner's clone holds the archive on disk
    doc = (fresh / "docs/release.md").read_text(encoding="utf-8")
    part = doc.split("## Publication without the private history", 1)[-1].split("\n## ", 1)[0]
    blocks = re.findall(r"```sh\n(.*?)```", part, re.S)  # in their order: the guard and the remotes, then the push
    public = tmp / "public.git"
    git(tmp, "init", "-q", "--bare", str(public))
    codes = []
    old_main = git(fresh, "rev-parse", "main").stdout.strip()
    for line in "".join(blocks).splitlines():
        codes.append(sh(["sh", "-c", line.replace("<public URL>", str(public))], fresh, env).returncode)
    pub = tmp / "pub"
    git(tmp, "clone", "-q", str(public), str(pub))
    refs = git(public, "for-each-ref", "--format=%(refname)").stdout.split()
    count = git(pub, "rev-list", "--count", "--all").stdout.strip()
    paths = git(pub, "log", "--all", "--name-only", "--format=").stdout.split()
    leaked = [p for p in paths if p.startswith(ARCH + "/")]
    step("publication", bool(blocks) and codes and not any(codes) and refs == ["refs/heads/main"] and count == "1"
         and not leaked and "solo-sdd/specs/publication/spec.md" in paths,
         "commands %s, refs %s, commits %s, archive paths %d" % (codes, refs, count, len(leaked)))

    # Work after the publication: main is the public commit, the old main is history-private, the guard holds.
    rev = lambda *a: git(fresh, "rev-parse", "-q", "--verify", *a).stdout.strip()
    public_main = git(public, "rev-parse", "refs/heads/main").stdout.strip()
    upstream = git(fresh, "rev-parse", "--abbrev-ref", "main@{upstream}").stdout.strip()
    private = git(fresh, "remote", "get-url", "private").stdout.strip()
    step("work after the publication", rev("main") == public_main != "" and upstream == "origin/main"
         and rev("refs/heads/history-private") == old_main != "" and private.endswith("/solo-sdd-private.git"),
         "main %s public, upstream %s, history-private %s the old main, private %s" % (
             "is" if rev("main") == public_main else "is not", upstream or "none",
             "is" if rev("refs/heads/history-private") == old_main else "is not", private or "none"))
    git(fresh, "branch", "old-cut", "history-private")
    cut = git(fresh, "commit-tree", rev("history-private^{tree}"), "-p", "history-private", "-m", "cut").stdout.strip()
    refused = []
    for spec, name in (("history-private", "refs/heads/history-private"),
                       ("history-private:refs/heads/fresh-name", "refs/heads/fresh-name"),
                       ("old-cut:refs/heads/old-cut", "refs/heads/old-cut"), (cut + ":refs/heads/cut", "refs/heads/cut")):
        r = git(fresh, "push", "origin", spec)
        refused.append(r.returncode != 0 and "pre-push: refused" in r.stderr and " to %s: " % name in r.stderr)
    r = git(fresh, "push", "--dry-run", "origin", "history-private")  # the check docs/release.md names
    refused.append(r.returncode != 0 and "pre-push: refused" in r.stderr)
    refs = git(public, "for-each-ref", "--format=%(refname)").stdout.split()
    step("an old branch pushed", all(refused) and refs == ["refs/heads/main"],
         "refused and named %s, remote refs %s" % (refused, refs))
    new = git(fresh, "commit-tree", rev("main^{tree}"), "-p", "main", "-m", "new").stdout.strip()
    git(fresh, "branch", "change/new", new)
    pushed = git(fresh, "push", "origin", "change/new").returncode
    deleted = git(fresh, "push", "origin", ":refs/heads/change/new").returncode
    refs = git(public, "for-each-ref", "--format=%(refname)").stdout.split()
    step("a new change branch", pushed == 0 and deleted == 0 and refs == ["refs/heads/main"],
         "push %d, delete %d, remote refs %s" % (pushed, deleted, refs))
    blob = sh(["git", "hash-object", "-w", "--stdin"], fresh, env).stdout.strip()  # stdin closed: an empty blob
    git(fresh, "tag", "on-blob", blob)
    r = git(fresh, "push", "origin", "refs/tags/on-blob")
    refs = git(public, "for-each-ref", "--format=%(refname)").stdout.split()
    step("a tag on a blob", r.returncode != 0 and "pre-push: refused for refs/tags/on-blob" in r.stderr
         and refs == ["refs/heads/main"], "code %d, %s, remote refs %s" % (
             r.returncode, (r.stderr.strip().splitlines() or [""])[0], refs))

    failed = results.count(False)
    print("SUMMARY: all steps passed" if not failed else "SUMMARY: %d failed" % failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
