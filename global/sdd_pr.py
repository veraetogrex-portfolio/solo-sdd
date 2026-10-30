#!/usr/bin/env python3
"""sdd-pr.py: PR для spec-dispatch: open, wait (CI), merge. Все вызовы gh идут по URL PR."""
import json
import re
import subprocess
import sys
import time

USAGE = """использование:
  sdd-pr.py open <WORKTREE> <основная ветка> <заголовок>
  sdd-pr.py wait <url> [--timeout <сек>] [--interval <сек>]
  sdd-pr.py merge <url> <squash|merge|rebase> <hash>
  коды merge: 0 слит, 1 ошибка, 5 основная ушла вперёд (PR отстаёт)"""
SIGNS = ("FAIL:", "ERROR:", "FAILED", "AssertionError", "failed")
NO_CHECKS_SEC = 180
LOG_LINES = 20
LOG_RETRY_SEC = 5


def sh(*cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, cwd=cwd)


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def number(url):
    m = re.search(r"/pull/(\d+)", url)
    return m.group(1) if m else "?"


def cmd_open(wt, base, title):
    p = sh("git", "-C", wt, "push", "-u", "origin", "HEAD")
    if p.returncode:
        die("push: " + p.stderr.strip())
    branch = sh("git", "-C", wt, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    p = sh("gh", "pr", "list", "--head", branch, "--state", "open", "--json", "number,url", cwd=wt)  # репозиторий gh берёт из папки
    if p.returncode:
        die("gh pr list: " + p.stderr.strip())
    prs = json.loads(p.stdout or "[]")
    if prs:
        n, url = prs[0]["number"], prs[0]["url"]
    else:
        p = sh("gh", "pr", "create", "--base", base, "--head", branch, "--title", title,
               "--body", f"Ветка {branch}, открыт sdd-pr.py", cwd=wt)
        if p.returncode:
            die("gh pr create: " + p.stderr.strip())
        url = p.stdout.strip().splitlines()[-1]
        n = number(url)
    print(f"PR #{n} {url}")
    return 0


def checks(url):
    p = sh("gh", "pr", "checks", url, "--json", "name,state,bucket,link")
    try:
        return json.loads(p.stdout)
    except ValueError:
        return []  # gh без проверок печатает ошибку, не JSON


def failed_log(rows):
    out = []
    for r in rows:
        m = re.search(r"github\.com/([^/]+/[^/]+)/actions/runs/(\d+)", r.get("link", ""))
        if m:
            for _ in range(3):  # журнал появляется через секунды после завершения проверки
                log = sh("gh", "run", "view", m.group(2), "-R", m.group(1), "--log-failed").stdout
                if log.strip():
                    break
                time.sleep(LOG_RETRY_SEC)
            out += log.splitlines()
    clean = []
    for line in out:
        line = line.split("\t")[-1]  # без имени job и шага
        clean.append(re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ?", "", line))
    hits = {i for i, s in enumerate(clean) if any(k in s for k in SIGNS)}
    keep = sorted({j for i in hits for j in (i - 1, i, i + 1) if 0 <= j < len(clean)})
    return bool(hits), [clean[i] for i in (keep or range(len(clean)))][-LOG_LINES:]  # итог тестов — в конце журнала


def cmd_wait(url, timeout, interval):
    n, start = number(url), time.monotonic()
    head = f"PR #{n} {url} CI: "
    while True:
        rows = checks(url)
        elapsed = time.monotonic() - start
        bad = [r for r in rows if r.get("bucket") in ("fail", "cancel")]
        if bad or (rows and not any(r.get("bucket") == "pending" for r in rows)):  # упавшая — итог сразу
            if not bad:
                print(head + "green")
                return 0
            test, lines = failed_log(bad)
            print(head + ("red" if test else "infra"))
            print("\n".join(lines))
            return 3 if test else 4
        if elapsed >= timeout or (not rows and elapsed >= min(NO_CHECKS_SEC, timeout)):
            print(head + "infra")
            print("нет проверок" if not rows else "timeout: проверки не завершились")
            return 4
        time.sleep(interval)


def view(url):
    p = sh("gh", "pr", "view", url, "--json", "headRefOid,baseRefName,state")
    if p.returncode:
        die("gh pr view: " + p.stderr.strip())
    try:
        return json.loads(p.stdout)
    except ValueError:
        die("gh pr view: не JSON: " + p.stdout[:200])


def cmd_merge(url, how, sha):
    n, v = number(url), view(url)
    if v["state"] == "MERGED":
        print(f"PR #{n} merged (уже)")
        return 0
    if v["headRefOid"] != sha:
        die(f"hash {sha} не голова PR ({v['headRefOid']})")
    owner_repo = re.search(r"github\.com/([^/]+/[^/]+)/pull/", url)
    if not owner_repo:
        die("не разобрать owner/repo из url: " + url)
    p = sh("gh", "api", f"repos/{owner_repo.group(1)}/compare/{v['baseRefName']}...{v['headRefOid']}",
           "--jq", ".behind_by")
    if p.returncode:
        die("gh api compare: " + p.stderr.strip())
    try:
        behind = int(p.stdout.strip() or 0)
    except ValueError:
        die("gh api compare: не число: " + p.stdout[:200])
    if behind > 0:
        print(f"PR #{n} behind {behind}: основная ушла вперёд")
        return 5
    p = sh("gh", "pr", "merge", url, "--" + how, "--match-head-commit", sha, "--delete-branch")
    if p.returncode:
        q = sh("gh", "pr", "view", url, "--json", "state")  # merge мог пройти, а упасть на удалении ветки
        if q.returncode or json.loads(q.stdout or "{}").get("state") != "MERGED":
            die((p.stderr or p.stdout).strip() or "gh pr merge отказал")
    print(f"PR #{n} {url} merged ({how})")
    return 0


def main(a):
    if a[:1] == ["open"] and len(a) == 4:
        return cmd_open(*a[1:])
    if a[:1] == ["merge"] and len(a) == 4 and a[2] in ("squash", "merge", "rebase"):
        return cmd_merge(*a[1:])
    if a[:1] == ["wait"] and len(a) >= 2:
        opt, rest = {"--timeout": 1200.0, "--interval": 15.0}, a[2:]
        try:  # ValueError ловится только при разборе аргументов: сбой gh внутри команды — код 1, не 2
            while rest:
                if rest[0] not in opt or len(rest) < 2:
                    raise ValueError
                opt[rest[0]], rest = float(rest[1]), rest[2:]
        except ValueError:
            die(USAGE, 2)
        return cmd_wait(a[1], opt["--timeout"], opt["--interval"])
    die(USAGE, 2)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
