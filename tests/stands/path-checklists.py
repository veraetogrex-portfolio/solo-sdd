#!/usr/bin/env python3
"""Live scenario of path-checklists and checklist-review-gate without a GitHub repository (Fallback): the real
global/sdd_pr.py and global/sdd_worktree.py, real git, a bare repository instead of the remote. Only gh is faked (first
in PATH): the fake of tests/stands/delivery-branches.py, wrapped to keep PR bodies in a file, to answer the PR file list
from the bare repository and the PR reviews from a file. The person's ticks and the second account's approval are
written by the stand itself, outside the agent session; the PR author is "owner".

Usage: python3 tests/stands/path-checklists.py (from the repository root)
Code 0: every step matched. The stand creates and removes its temporary folder itself."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "global/sdd_pr.py"
WT = ROOT / "global/sdd_worktree.py"
_spec = importlib.util.spec_from_file_location("delivery_stand", Path(__file__).with_name("delivery-branches.py"))
base_stand = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base_stand)

ITEMS = "- [ ] Amounts are in minor units\n- [ ] A repeated charge is idempotent\n- [ ] The charge is logged\n"

# bodies.json: {PR number: body}; reviews.json: {PR number: [{login, state, commit_id}]}; pr view adds the body and
# the author; the PR files come from the bare repository
WRAP = f"""#!{sys.executable}
import json, os, re, subprocess, sys
a, d = sys.argv[1:], os.environ["STAND_D"]
shared = [sys.executable, d + "/bin/gh-shared"]
bodies = json.load(open(d + "/bodies.json"))
def save():
    json.dump(bodies, open(d + "/bodies.json", "w"))
def num(x):
    return x if x.isdigit() else re.search(r"/pulls?/(\\d+)", x).group(1)
def opt(name):
    return a[a.index(name) + 1] if name in a else None
if a[:2] == ["pr", "view"]:
    open(d + "/gh.log", "a").write(json.dumps(a) + "\\n")
    n = num(a[2])
    p = subprocess.run(shared + ["pr", "view", "https://github.com/o/stand/pull/" + n], capture_output=True, text=True)
    out = dict(json.loads(p.stdout), body=bodies.get(n, ""), author={{"login": "owner"}})
    print(json.dumps(out))
elif a[:2] == ["pr", "edit"]:
    open(d + "/gh.log", "a").write(json.dumps(a) + "\\n")
    bodies[num(a[2])] = opt("--body")
    save()
elif a[:2] == ["pr", "create"]:
    p = subprocess.run(shared + a, capture_output=True, text=True)
    bodies[num(p.stdout.strip())] = opt("--body")
    save()
    sys.stdout.write(p.stdout)
elif a[:1] == ["api"] and a[1].endswith("/reviews"):
    open(d + "/gh.log", "a").write(json.dumps(a) + "\\n")
    for row in json.load(open(d + "/reviews.json")).get(num(a[1]), []):
        print(json.dumps(row))
elif a[:2] == ["api", "--paginate"] and a[2].endswith("/files"):
    open(d + "/gh.log", "a").write(json.dumps(a) + "\\n")
    p = next(x for x in json.load(open(d + "/state.json"))["prs"] if x["n"] == int(num(a[2])))
    bare = os.environ["STAND_BARE"]
    names = subprocess.run(["git", "--git-dir", bare, "diff", "--name-only", "--no-renames",
                            p["base"] + "..." + p["head"]], capture_output=True, text=True).stdout.split()
    for f in names:
        print(json.dumps({{"filename": f, "previous_filename": None, "patch": "@@ x"}}))
else:
    os.execv(sys.executable, shared + a)
"""


def main():
    tmp = Path(tempfile.mkdtemp(prefix="stand-checklists-")).resolve()
    try:
        return run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(tmp):
    env = dict(os.environ, **base_stand.GITENV, PATH=f"{tmp / 'bin'}:{os.environ['PATH']}", STAND_D=str(tmp),
               STAND_BARE=str(tmp / "origin.git"), HOME=str(tmp / "home"))
    (tmp / "bin").mkdir()
    (tmp / "home").mkdir()
    for name, text in (("gh-shared", base_stand.GH), ("gh", WRAP)):
        (tmp / "bin" / name).write_text(text)
        (tmp / "bin" / name).chmod(0o755)
    (tmp / "state.json").write_text(json.dumps({"prs": []}))
    (tmp / "bodies.json").write_text("{}")
    (tmp / "reviews.json").write_text("{}")
    bare, main = tmp / "origin.git", tmp / "main"

    def g(cwd, *a):
        p = subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
        if p.returncode:
            raise RuntimeError(f"git {a}: {p.stderr}")
        return p.stdout.strip()

    def write(rel, text, base=main):
        p = Path(base) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def tool(script, *a):
        return subprocess.run([sys.executable, str(script), *map(str, a)], capture_output=True, text=True, env=env,
                              stdin=subprocess.DEVNULL, timeout=120, cwd=main)

    def gh(*a):
        return subprocess.run(["gh", *a], capture_output=True, text=True, env=env, cwd=main, stdin=subprocess.DEVNULL)

    def body(url):
        return json.loads(gh("pr", "view", url, "--json", "body").stdout)["body"]

    def state(url):
        return json.loads(gh("pr", "view", url, "--json", "state").stdout)["state"]

    def approve(n, sha, login="person"):  # a review by another account on GitHub, outside the agent session
        rows = json.loads((tmp / "reviews.json").read_text())
        rows.setdefault(str(n), []).append({"login": login, "state": "APPROVED", "commit_id": sha})
        (tmp / "reviews.json").write_text(json.dumps(rows))

    def change(cid, rel):
        wt = tmp / ("wt-" + cid)
        g(main, "fetch", "-q", "origin")
        g(main, "worktree", "add", "-q", "-b", "change/" + cid, str(wt), "origin/main")
        tool(WT, "setup", main, wt)
        write(rel, "x = 1\n", wt)
        g(wt, "add", "-A")
        g(wt, "commit", "-qm", cid + " change")
        sh = tool(PR, "ship", main, wt, "main", cid)
        return wt, sh, next((w for w in sh.stdout.split() if w.startswith("https://")), "")

    results = []

    def check(name, good, ok_text, detail):
        results.append(good)
        print(f"ok {name}: {ok_text}" if good else f"FAILED {name}: {detail}")

    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True, env=env)
    subprocess.run(["git", "init", "-q", "-b", "main", str(main)], check=True, env=env)
    write(".gitignore", "solo-sdd/\n")
    write("README.md", "r\n")
    write("docs/checklists/money-safety.md", "# Money safety\n\n" + ITEMS)
    g(main, "add", "-A")
    g(main, "commit", "-qm", "init")
    g(main, "remote", "add", "origin", str(bare))
    g(main, "push", "-q", "-u", "origin", "main")
    write("solo-sdd/config", "delivery.merge-by: agent\nchecklist.money-safety.paths: billing/**\n"
          "checklist.money-safety.file: docs/checklists/money-safety.md\n")

    # 1. a change editing billing/charge.py: ship adds the section with three unticked items, land refuses with code 8
    wt, sh, url = change("pay", "billing/charge.py")
    b = body(url) if url else ""
    section = "## Checklist: money-safety\n\n" + ITEMS
    check("ship adds the section", sh.returncode == 0 and section in b and b.count("- [ ] ") == 3,
          f"code 0, {sh.stdout.splitlines()[0]}, the body has «## Checklist: money-safety» with 3 unticked items",
          f"code {sh.returncode} {sh.stdout!r} {sh.stderr!r} body {b!r}")
    ld = tool(PR, "land", main, wt, url, "squash")
    check("land refuses", ld.returncode == 8 and ld.stdout.strip() == "PR #1 checklist money-safety: 3 open items"
          and state(url) == "OPEN" and wt.is_dir(), f"code 8, {ld.stdout.strip()}, the PR open, the worktree stays",
          f"code {ld.returncode} {ld.stdout!r} {ld.stderr!r}")

    # 2. a person ticks the items (outside the agent session), no review: land refuses, no approval on the head
    gh("pr", "edit", url, "--body", b.replace("- [ ] ", "- [x] "))
    head = g(wt, "rev-parse", "HEAD")
    ld = tool(PR, "land", main, wt, url, "squash")
    check("ticked, not approved", ld.returncode == 8 and ld.stdout.strip() == f"PR #1 checklist money-safety: no approval on {head}"
          and state(url) == "OPEN" and wt.is_dir(), f"code 8, {ld.stdout.strip()}", f"code {ld.returncode} {ld.stdout!r} {ld.stderr!r}")

    # 3. an approval before a new commit and the author's own approval of the new head do not count
    approve(1, head)
    write("billing/charge.py", "x = 2\n", wt)
    g(wt, "commit", "-qam", "pay fix")
    sh = tool(PR, "ship", main, wt, "main", "pay")
    new = g(wt, "rev-parse", "HEAD")
    approve(1, new, "owner")
    ld = tool(PR, "land", main, wt, url, "squash")
    check("approval before a new commit", sh.returncode == 0 and ld.returncode == 8 and ld.stdout.strip() ==
          f"PR #1 checklist money-safety: no approval on {new}" and state(url) == "OPEN" and "- [ ] " not in body(url),
          f"ship code 0, the ticks kept, land code 8, {ld.stdout.strip()}",
          f"ship {sh.returncode} {sh.stderr!r} land {ld.returncode} {ld.stdout!r} {ld.stderr!r}")

    # 4. another account approves the head commit: land merges
    approve(1, new)
    ld = tool(PR, "land", main, wt, url, "squash")
    check("land after the approval", ld.returncode == 0 and state(url) == "MERGED" and (main / "billing/charge.py").exists()
          and not wt.exists(), f"code 0, {ld.stdout.strip().splitlines()[-1]}",
          f"code {ld.returncode} {ld.stdout!r} {ld.stderr!r}")

    # 5. a change not touching billing/: no section, no review needed, land merges
    wt2, sh2, url2 = change("docs", "docs/guide.md")
    b2 = body(url2) if url2 else "?"
    ld2 = tool(PR, "land", main, wt2, url2, "squash")
    check("no checklist path", sh2.returncode == 0 and "## Checklist:" not in b2 and ld2.returncode == 0
          and state(url2) == "MERGED", f"no section, land code 0, {ld2.stdout.strip().splitlines()[-1] if ld2.stdout else ''}",
          f"ship {sh2.returncode} land {ld2.returncode} body {b2!r} {ld2.stdout!r} {ld2.stderr!r}")

    print("stand: %d of %d steps passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
