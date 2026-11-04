#!/usr/bin/env python3
"""sdd-pr.py: PR для spec-dispatch: open, wait (CI), merge. Все вызовы gh идут по URL PR."""
import json
import re
import subprocess
import sys
import time
from urllib.parse import quote

USAGE = """использование:
  sdd-pr.py open <WORKTREE> <основная ветка> <заголовок>
  sdd-pr.py wait <url> [--timeout <сек>] [--interval <сек>] [--stuck <сек>]
  sdd-pr.py merge <url> <squash|merge|rebase> <hash> [--title <заголовок>]
  коды merge: 0 слит, 1 ошибка, 5 основная ушла вперёд (PR отстаёт)"""
SIGNS = ("FAIL:", "ERROR:", "FAILED", "AssertionError", "failed")
NO_CHECKS_SEC = 180
STUCK_SEC = 300
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


def gh_json(*cmd):
    p = sh("gh", *cmd)
    if p.returncode:
        raise ValueError(p.stderr)
    return json.loads(p.stdout)


def required_checks(url):
    """Обязательные проверки основной ветки PR или None, если правила не прочитались."""
    try:
        repo = re.search(r"github\.com/([^/]+/[^/]+)/pull/", url).group(1)
        branch = quote(gh_json("pr", "view", url, "--json", "baseRefName")["baseRefName"], safe="/")
        # ponytail: одна страница, больше 100 активных правил на ветку не бывает на практике
        rules = gh_json("api", f"repos/{repo}/rules/branches/{branch}?per_page=100")
        names = [c["context"] for r in rules if r["type"] == "required_status_checks"
                 for c in r["parameters"]["required_status_checks"]]
        protection = gh_json("api", f"repos/{repo}/branches/{branch}").get("protection") or {}
        classic = protection.get("required_status_checks") or {}  # /protection требует прав администратора
        names += [c["context"] for c in classic.get("checks") or []] + (classic.get("contexts") or [])
        if not all(isinstance(x, str) for x in names):
            raise ValueError
        return set(names)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def stuck_checks(rows, required):
    """Обязательные, которых нет или которые не начались, когда остальным ждать нечего."""
    # ponytail: внешний CI на статусах коммита (state PENDING) неотличим от не начавшейся проверки
    pending = {r.get("name") for r in rows if r.get("bucket") == "pending"}
    running = any(r.get("bucket") == "pending" and r.get("state") == "IN_PROGRESS" for r in rows)
    if running or pending - required:
        return []
    return sorted(required - ({r.get("name") for r in rows} - pending))


def ci_verdict(rows, required, stuck_sec, limit):
    """Итог проверок: "bad", "green", "stuck" или None, если ждать дальше."""
    if any(r.get("bucket") in ("fail", "cancel") for r in rows):
        return "bad"
    if stuck_checks(rows, required):
        return "stuck" if stuck_sec >= limit else None
    return "green" if rows and not any(r.get("bucket") == "pending" for r in rows) else None


def cmd_wait(url, timeout, interval, limit=STUCK_SEC):
    n = number(url)
    head = f"PR #{n} {url} CI: "
    required = required_checks(url)
    if required is None:
        print("предупреждение: правила ветки не прочитались, обязательные проверки не сверены", file=sys.stderr)
        required = set()
    start = time.monotonic()  # срок — на CI, чтение правил в него не входит
    since = None  # с какого опроса ждать больше нечего, кроме застрявших
    while True:
        rows = checks(url)
        now = time.monotonic()
        elapsed = now - start
        stuck = stuck_checks(rows, required)
        since = (since or now) if stuck else None
        verdict = ci_verdict(rows, required, now - since if stuck else 0, limit)
        if verdict == "green":
            print(head + "green")
            return 0
        if verdict == "bad":  # упавшая — итог сразу
            test, lines = failed_log([r for r in rows if r.get("bucket") in ("fail", "cancel")])
            print(head + ("red" if test else "infra"))
            print("\n".join(lines))
            return 3 if test else 4
        if verdict == "stuck" or elapsed >= timeout or (not rows and elapsed >= min(NO_CHECKS_SEC, timeout)):
            print(head + "infra")
            print("\n".join(f"не стартовала обязательная проверка {x}" for x in stuck)
                  or ("нет проверок" if not rows else "timeout: проверки не завершились"))
            return 4
        time.sleep(interval)


def view(url):
    p = sh("gh", "pr", "view", url, "--json", "headRefOid,headRefName,baseRefName,state,title,isCrossRepository")
    if p.returncode:
        die("gh pr view: " + p.stderr.strip())
    try:
        return json.loads(p.stdout)
    except ValueError:
        die("gh pr view: не JSON: " + p.stdout[:200])


def cmd_merge(url, how, sha, title=None):
    n, v = number(url), view(url)
    if v["state"] == "MERGED":
        print(f"PR #{n} merged (уже)")
        return 0
    if v["headRefOid"] != sha:
        die(f"hash {sha} не голова PR ({v['headRefOid']})")
    if how != "rebase":
        title = (v.get("title", "") if title is None else title).strip()
        if not title:
            die(f"PR #{n}: пустой заголовок коммита (передайте --title)")
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
    rows = checks(url)
    bad = [f"{r.get('name')} ({r.get('bucket')})" for r in rows if r.get("bucket") not in ("pass", "skipping")]
    if not rows or bad:
        die(f"PR #{n} CI не зелёный: " + (", ".join(bad) or "нет проверок"))
    repo = owner_repo.group(1)
    extra = ["-f", f"commit_title={title} (#{n})"] if how != "rebase" else []
    p = sh("gh", "api", "-X", "PUT", f"repos/{repo}/pulls/{n}/merge", "-f", f"merge_method={how}", "-f", f"sha={sha}", *extra)
    if p.returncode:
        die((p.stderr or p.stdout).strip() or "merge отказан")
    print(f"PR #{n} {url} merged ({how})")
    if v.get("isCrossRepository"):  # ветка живёт в форке: такое же имя в базовом репозитории — чужая ветка
        return 0
    branch = v["headRefName"]
    p = sh("gh", "api", "-X", "DELETE", f"repos/{repo}/git/refs/heads/{branch}")
    if p.returncode and not any(c in p.stderr for c in ("HTTP 404", "HTTP 422")):
        print(f"ветка {branch} не удалена: " + (p.stderr or p.stdout).strip())
    return 0


def main(a):
    if a[:1] == ["open"] and len(a) == 4:
        return cmd_open(*a[1:])
    if a[:1] == ["merge"] and len(a) in (4, 6) and a[2] in ("squash", "merge", "rebase") \
            and (len(a) == 4 or a[4] == "--title"):
        return cmd_merge(*a[1:4], *a[5:])
    if a[:1] == ["wait"] and len(a) >= 2:
        opt, rest = {"--timeout": 1200.0, "--interval": 15.0, "--stuck": float(STUCK_SEC)}, a[2:]
        try:  # ValueError ловится только при разборе аргументов: сбой gh внутри команды — код 1, не 2
            while rest:
                if rest[0] not in opt or len(rest) < 2:
                    raise ValueError
                opt[rest[0]], rest = float(rest[1]), rest[2:]
        except ValueError:
            die(USAGE, 2)
        return cmd_wait(a[1], opt["--timeout"], opt["--interval"], opt["--stuck"])
    die(USAGE, 2)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
