#!/usr/bin/env python3
"""Live scenario of merge-by-human without a GitHub repository (Fallback): the real global/sdd_pr.py,
global/sdd_worktree.py and the stop hook of global/work_hooks.py, real git, a bare repository instead of the remote.
Only gh is faked (first in PATH), the same fake as tests/stands/delivery-branches.py: PRs in a file, a merge
squashes the PR into its base in a helper clone. The person's merge is that fake's merge API called by the stand.

Usage: python3 tests/stands/merge-by-human.py (from the repository root)
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
HOOK = ROOT / "global/work_hooks.py"
_spec = importlib.util.spec_from_file_location("delivery_stand", Path(__file__).with_name("delivery-branches.py"))
base_stand = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base_stand)

# `gh pr view --json …` without a URL (the stop hook) answers for the newest PR; the rest goes to the shared fake
WRAP = f"""#!{sys.executable}
import json, os, sys
a, d = sys.argv[1:], os.environ["STAND_D"]
if a[:2] == ["pr", "view"] and a[2:3] and a[2].startswith("--"):
    p = json.load(open(d + "/state.json"))["prs"][-1]
    print(json.dumps({{"state": p["state"], "url": "https://github.com/o/stand/pull/%d" % p["n"]}}))
    sys.exit(0)
os.execv(sys.executable, [sys.executable, d + "/bin/gh-shared", *a])
"""


def main():
    tmp = Path(tempfile.mkdtemp(prefix="stand-merge-by-")).resolve()
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

    def puts():
        log = tmp / "gh.log"
        return [c for c in map(json.loads, log.read_text().splitlines()) if c[:3] == ["api", "-X", "PUT"]]

    def state(url):
        return json.loads(subprocess.run(["gh", "pr", "view", url, "--json", "state"], capture_output=True, text=True,
                                         env=env).stdout)["state"]

    def stop(sid):
        tr = tmp / (sid + ".jsonl")
        tr.write_text(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "git push -u origin HEAD"}}]}}) + "\n")
        p = subprocess.run([sys.executable, str(HOOK), "stop"], capture_output=True, text=True, env=env,
                           input=json.dumps({"session_id": sid, "cwd": str(main), "transcript_path": str(tr),
                                             "last_assistant_message": "Done, the PR is green."}))
        return p.stdout.strip()

    def change(cid):
        wt = tmp / ("wt-" + cid)
        g(main, "fetch", "-q", "origin")
        g(main, "worktree", "add", "-q", "-b", "change/" + cid, str(wt), "origin/main")
        tool(WT, "setup", main, wt)
        write(cid + ".txt", "t\n", wt)
        g(wt, "add", "-A")
        g(wt, "commit", "-qm", cid + " change")
        sh = tool(PR, "ship", main, wt, "main", cid)
        return wt, sh, (sh.stdout.split()[2] if sh.stdout.startswith("PR #") else "")

    results = []

    def check(name, good, ok_text, detail):
        results.append(good)
        print(f"ok {name}: {ok_text}" if good else f"FAILED {name}: {detail}")

    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True, env=env)
    subprocess.run(["git", "init", "-q", "-b", "main", str(main)], check=True, env=env)
    write(".gitignore", "solo-sdd/\n")
    write("README.md", "r\n")
    g(main, "add", "-A")
    g(main, "commit", "-qm", "init")
    g(main, "remote", "add", "origin", str(bare))
    g(main, "push", "-q", "-u", "origin", "main")
    write("solo-sdd/config", "mode: team\n")  # the team default: delivery.merge-by: human
    write("solo-sdd/changes/toy/tasks.md", "- [x] 1.1 toy\n")

    # 1. ship gives a green PR; land refuses with code 8, the PR stays open, the worktree stays
    wt, sh, url = change("toy")
    check("ship", sh.returncode == 0 and "CI: green" in sh.stdout, sh.stdout.strip(), f"code {sh.returncode} {sh.stderr!r}")
    ld = tool(PR, "land", main, wt, url, "squash")
    check("land refuses", ld.returncode == 8 and ld.stdout.strip() == f"PR #1 waits for human merge: {url}"
          and state(url) == "OPEN" and wt.is_dir() and not puts(),
          f"code 8, {ld.stdout.strip()}, gh pr view: {state(url)}, the worktree stays",
          f"code {ld.returncode} {ld.stdout!r} {ld.stderr!r}")

    # 2. the stop hook lets the session end with the open PR; under merge-by: agent it returns the agent
    quiet = stop("human")
    write("solo-sdd/config", "mode: team\ndelivery.merge-by: agent\n")
    loud = stop("agent")
    write("solo-sdd/config", "mode: team\n")
    check("stop hook", quiet == "" and "is open and not merged" in loud,
          "human: no return; agent: the open PR returns the agent", f"human {quiet!r} agent {loud!r}")

    # 3. a person merges on the server, then land --after-merge finishes
    early = tool(PR, "land", main, wt, url, "--after-merge")
    subprocess.run(["gh", "api", "-X", "PUT", "repos/o/stand/pulls/1/merge", "-f", "merge_method=squash",
                    "-f", "commit_title=toy (#1)"], check=True, env=env, capture_output=True)
    am = tool(PR, "land", main, wt, url, "--after-merge")
    gone = not wt.exists() and g(main, "branch", "--list", "change/toy") == ""
    synced = (main / "toy.txt").exists() and g(main, "rev-parse", "HEAD") == g(main, "rev-parse", "origin/main")
    check("after merge", early.returncode == 8 and am.returncode == 0 and gone and synced and len(puts()) == 1,
          f"open PR: code {early.returncode}; merged by the person: code 0, {am.stdout.strip().splitlines()[-1]}, "
          "the main folder pulled, the worktree and branch removed",
          f"early {early.returncode} code {am.returncode} gone {gone} synced {synced} {am.stdout!r} {am.stderr!r}")

    # 4. merge-by: agent merges as before
    write("solo-sdd/config", "mode: team\ndelivery.merge-by: agent\n")
    wt2, sh2, url2 = change("two")
    ld2 = tool(PR, "land", main, wt2, url2, "squash")
    check("agent mode", sh2.returncode == 0 and ld2.returncode == 0 and state(url2) == "MERGED" and not wt2.exists()
          and (main / "two.txt").exists(), f"code 0, {ld2.stdout.strip().splitlines()[-1]}",
          f"ship {sh2.returncode} land {ld2.returncode} {ld2.stdout!r} {ld2.stderr!r}")

    print("stand: %d of %d steps passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
