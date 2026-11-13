#!/usr/bin/env python3
"""sdd-pr.py: PRs for spec-dispatch: open, wait (CI and code scanning alerts), merge, ship, land, promote.
Every gh call goes by the PR URL."""
import collections
import json
import os
import re
import shlex
import subprocess
import sys
import time
from urllib.parse import quote

USAGE = """usage:
  sdd-pr.py open <WORKTREE> <main branch> <title>
  sdd-pr.py wait <url> [--timeout <sec>] [--interval <sec>] [--stuck <sec>]
  sdd-pr.py merge <url> <squash|merge|rebase> <hash> [--title <title>]
  sdd-pr.py ship <MAIN> <WORKTREE> <main branch> <title>
  sdd-pr.py land <MAIN> <WORKTREE> <url> <squash|merge|rebase>
  sdd-pr.py land <MAIN> <WORKTREE> <url> --after-merge
  sdd-pr.py promote <from> <to>
  delivery.merge-by: human in solo-sdd/config: merge and land never merge (code 8 «waits for human merge: <url>»);
    land --after-merge, after a person merged, pulls, transports and removes the worktree; an open PR: code 8
  checklist.<name>.paths and .file of solo-sdd/config: open and ship add «## Checklist: <name>» with the file's items
    to a PR touching the paths; merge and land: code 8 «checklist <name>: <n> open items» while an item is unticked,
    then «checklist <name>: no approval on <sha>» until another account than the PR author approved the head commit
  delivery.base of solo-sdd/config in the main folder replaces <main branch>; broken settings: code 1
  promote opens (or prints the open) PR <from> -> <to> and never merges it; <to> `release/*`: the newest release/ branch
  wait codes: 0 green, 3 red, 4 infra, 8 codeql (checks passed, code scanning alerts are open)
  merge codes: 0 merged, 1 error, 5 main moved ahead (PR is behind), 8 waits for the owner («Owner only:» paths or .github/workflows), a human merge or checklist items
  ship codes: 0 green, 1 step failed, 3 red, 4 infra, 6 conflict, 8 codeql
  land codes: 0 all done, 1 merge failed, 5 main moved ahead, 7 merged, a step after merge failed, 8 waits for the owner («Owner only:» paths or .github/workflows), a human merge or checklist items"""
SIGNS = ("FAIL:", "ERROR:", "FAILED", "AssertionError", "failed")
NO_CHECKS_SEC = 180
STUCK_SEC = 300
REVIEWS_SEC = 60
LOG_LINES = 20
LOG_RETRY_SEC = 5
SCAN_OFF = re.compile(r"advanced security|code scanning", re.I)  # 403 of disabled scanning
SCAN_UNCHECKED = "code scanning alerts not checked"
CI_PATTERN = ".github/workflows/**"
OWNER = "Owner only:"
HUMAN = "waits for human merge"
AFTER = "--after-merge"
CHECKLIST = "## Checklist:"
ITEM = re.compile(r"\s*[-*]\s+\[([ xX])\]\s+(.*)")
HEADING = re.compile(r"#{1,6}(?:\s|$)")
OLD_OWNER_HIT = "AGENTS.md (pre-English «Owner only:» item: run solo-sdd migrate-agents)"


# keywords:begin
# Pre-English AGENTS.md headings and items -> English. The old names live only here, as \u escapes,
# so the repository holds no Cyrillic letter. Scripts read only the English names.
OLD_SECTIONS = {
    "\u0420\u0430\u0431\u043e\u0447\u0430\u044f \u043a\u043e\u043f\u0438\u044f": "Working copy",
    "\u041f\u043e\u0441\u0442\u0430\u0432\u043a\u0430": "Delivery",
    "\u041a\u043e\u043c\u0430\u043d\u0434\u044b": "Commands",
}
OLD_ITEMS = {  # English section -> ((old item, English item), ...)
    "Working copy": (
        ("\u041f\u0443\u0442\u0438:", "Paths:"),
        ("\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430:", "Prepare:"),
        ("\u041f\u043e\u0441\u043b\u0435 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f:", "After refresh:"),
        ("\u041e\u0431\u0449\u0438\u0435:", "Shared:"),
        ("\u041e\u0440\u043a\u0435\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u043e\u0432:", "Orchestrators:"),
        ("\u041e\u0440\u043a\u0435\u0441\u0442\u0440\u0430\u0442\u043e\u0440: \u0441\u0430\u043c", "Orchestrator: solo"),
    ),
    "Delivery": (
        ("\u0420\u0435\u0436\u0438\u043c:", "Mode:"),
        ("\u0417\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a PR:", "PR title:"),
        ("\u0414\u0435\u043f\u043b\u043e\u0439:", "Deploy:"),
        ("\u0422\u043e\u043b\u044c\u043a\u043e \u0432\u043b\u0430\u0434\u0435\u043b\u0435\u0446:", "Owner only:"),
    ),
    "Commands": (("\u0422\u0435\u0441\u0442\u044b", "Tests"),),  # row of the commands table
}


def migrate_agents(text):
    """(text with the old headings and items renamed to English, English names found in order).

    Items are renamed only inside their section, at the start of a list item or a table row;
    every other byte stays as it was."""
    out, found, section = [], [], None
    for line in re.split(r"(?<=\n)", text):  # lines end only at \n, as in the file
        if line.startswith("## "):
            title = line[3:].strip()
            if title in OLD_SECTIONS:
                line = line.replace(title, OLD_SECTIONS[title], 1)
                title = OLD_SECTIONS[title]
                found.append(title)
            section = title
        else:
            for old, new in OLD_ITEMS.get(section, ()):
                m = re.match(r"(\s*(?:[-*]\s+|\|\s*))" + re.escape(old) + r"(?!\w)", line)
                if m:
                    line = m.group(1) + new + line[m.end():]
                    found.append(new)
                    break
        out.append(line)
    return "".join(out), list(dict.fromkeys(found))


def migrate_hint(path, found):
    """One line for a reader of an AGENTS.md with old keywords: the file, what was found, the command."""
    return "%s: pre-English keywords (%s) are ignored; run: solo-sdd migrate-agents %s" % (
        path, ", ".join(found), os.path.dirname(os.path.abspath(path)))
# keywords:end


# settings:begin
# solo-sdd/config: one `key: value` per line, lines starting with # are comments, list values are separated by commas.
SETTINGS_FILE = "solo-sdd/config"
# key -> (type: choice | int | list | names, allowed values (None: any), default, default under `mode: team` (None: the same));
# a key with the default "" takes an empty value, read as "not set"
REGISTRY = {
    "mode": ("choice", ("solo", "team"), "solo", None),
    "delivery.mode": ("choice", ("local", "pr"), "local", "pr"),
    "delivery.merge": ("choice", ("squash", "merge", "rebase"), "squash", None),
    "delivery.merge-by": ("choice", ("agent", "human"), "agent", "human"),  # who merges into the base
    "delivery.base": ("choice", None, "", None),  # "": the remote's default branch
    "delivery.promote": ("list", None, "", None),  # branches after the base in order; `release/*`: the newest by version
    "dispatch.limit": ("int", None, "2", None),
    "process.review-rounds": ("int", None, "3", None),
    "process.light-path": ("choice", ("on", "off"), "on", None),  # off: every code edit goes through a change
    "process.light-path.max-files": ("int", None, "3", None),
    "reply.language": ("choice", ("ru", "en", "off"), "off", None),
    "agents": ("list", ("claude", "codex", "cursor", "other"), "claude, codex, other", None),
    "rules.scope": ("choice", ("project", "global"), "project", None),  # project: init writes the rules block into AGENTS.md
    "integrations": ("names", None, "", None),  # the enabled integrations, by folder name (solo_sdd/integrations.py)
    "integrations.off": ("names", None, "", None),  # the bundled integrations switched off, by folder name
}
# pattern keys: <name> is lowercase letters, digits and -, not starting with -; set keys show in `config list` as `file`
PATTERNS = {
    "checklist.<name>.paths": ("paths", None, "", None),  # globs of the files a person checks by the list
    "checklist.<name>.file": ("path", None, "", None),  # a markdown file of `- [ ]` items, from the repository root
}
NAME_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789-"


class SettingsError(ValueError):
    pass


def bad_name(name):
    """A value of a key without a fixed list git would refuse or read as an option (`*` stays: release/*)."""
    return name.startswith(("-", "+")) or ".." in name or any(c in name for c in " \t~^:?[\\")


def bad_path(path):
    """A path value outside the repository or one the lists would split: absolute, `..`, spaces, backslashes."""
    return path.startswith(("/", "-")) or ".." in path.split("/") or any(c in path for c in " \t\\")


def good_name(name):
    """A <name>: lowercase ASCII letters, digits and -, not starting with -."""
    return bool(name) and name[0] != "-" and all(c in NAME_CHARS for c in name)


def entry(key, registry=REGISTRY):
    """The registry tuple of a fixed or a pattern key; None when the key is unknown."""
    if key in registry:
        return registry[key]
    for pattern, value in PATTERNS.items():
        head, tail = pattern.split("<name>")
        name = key[len(head):len(key) - len(tail)] if key.startswith(head) and key.endswith(tail) else ""
        if good_name(name):
            return value
    return None


def check_value(key, value, registry=REGISTRY):
    """The normalized value, or SettingsError naming the allowed values."""
    kind, allowed, default = entry(key, registry)[:3]
    v = value.strip()
    if kind == "int":
        if not (v.isascii() and v.isdigit()) or int(v) < 1:
            raise SettingsError("%s takes a whole number from 1, not %r" % (key, v))
        return str(int(v))
    items = [i.strip() for i in v.split(",")] if kind in ("list", "paths", "names") else [v]
    items = [i for i in items if i]
    if not items and default == "":
        return ""
    paths = kind in ("path", "paths")
    bad = [i for i in items if (bad_path(i) if paths else not good_name(i) if kind == "names" else
                                i not in allowed if allowed else bad_name(i))]
    if kind == "names" and len(set(items)) < len(items):
        raise SettingsError("%s takes each name once, not %r" % (key, v))
    if bad or not items:
        what = ", ".join(allowed) if allowed else (
            "relative paths (no spaces, \\ or .., not starting with / or -)" if paths else
            "names (lowercase letters, digits and -, not starting with -)" if kind == "names" else
            "branch names (no spaces, ~^:?[\\ or .., not starting with - or +)") + (
            ", separated by commas" if kind in ("list", "paths", "names") else "")
        raise SettingsError("%s takes %s, not %r" % (key, what, v))
    return ", ".join(items)


def parse_settings(text, registry=REGISTRY, name=SETTINGS_FILE):
    """{key: value} of the file text; SettingsError names <name>:<line> and the reason."""
    found = {}
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        key, colon, value = s.partition(":")
        key, where = key.strip(), "%s:%d" % (name, n)
        if not colon or not key:
            raise SettingsError("%s: not \"key: value\": %s" % (where, s))
        if entry(key, registry) is None:
            raise SettingsError("%s: unknown key %s; known: %s" % (where, key, ", ".join(list(registry) + list(PATTERNS))))
        if key in found:
            raise SettingsError("%s: %s is set twice" % (where, key))
        try:
            found[key] = check_value(key, value, registry)
        except SettingsError as e:
            raise SettingsError("%s: %s" % (where, e))
    return found


def effective(found, registry=REGISTRY, agents=None):
    """{key: (value, source)}: source `file`, else `AGENTS.md` (agents: agents_delivery), else `mode` (the team default
    under `mode: team`), else `default`."""
    team = found.get("mode") == "team"
    agents = agents or {}
    out = {}
    for key, (_, _, default, team_default) in registry.items():
        if key in found:
            out[key] = (found[key], "file")
        elif key in agents:
            out[key] = (agents[key], "AGENTS.md")
        elif team and team_default is not None:
            out[key] = (team_default, "mode")
        else:
            out[key] = (default, "default")
    out.update((key, (value, "file")) for key, value in found.items() if key not in registry)  # pattern keys
    return out


def read_settings_text(root):
    """The file text of the project at root, "" when there is no file."""
    try:
        with open(os.path.join(root, SETTINGS_FILE), encoding="utf-8", newline="") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def agents_delivery(root, registry=REGISTRY):
    """{key: value} of the first allowed «Mode:» and «Merge:» items of the «## Delivery» section of AGENTS.md at root,
    the old source of delivery.mode and delivery.merge; a file that cannot be opened: {}."""
    try:
        with open(os.path.join(root, "AGENTS.md"), encoding="utf-8", errors="replace") as f:  # other readers own the encoding
            lines = f.read().splitlines()
    except OSError:
        return {}
    out, inside = {}, False
    for ln in lines:
        if ln.startswith("## "):
            inside = ln.strip() == "## Delivery"
            continue
        s = ln.strip().lstrip("-* ").strip()
        for key, item in (("delivery.mode", "Mode:"), ("delivery.merge", "Merge:")):
            words = s[len(item):].split() if inside and s.startswith(item) else []
            v = words[0].strip("`.,;").lower() if words else ""
            if v in registry[key][1]:
                out.setdefault(key, v)
    return out


def read_settings(root, registry=REGISTRY):
    """Settings in effect of the project at root; no file means all defaults; a broken file raises SettingsError."""
    return effective(parse_settings(read_settings_text(root), registry), registry, agents_delivery(root, registry))
# settings:end


def delivery(root):
    """(delivery.base, delivery.promote as a list) of the project at root; base "" is the default branch passed in.
    Broken settings: exit 1 naming the line, never a silent fall back to the default branch."""
    try:
        s = read_settings(root)
    except (OSError, ValueError) as e:
        die("settings: %s" % e)
    return s["delivery.base"][0], [x.strip() for x in s["delivery.promote"][0].split(",") if x.strip()]


def merge_by(root):
    """delivery.merge-by of the project at root: agent or human; broken settings: exit 1 naming the line."""
    try:
        return read_settings(root)["delivery.merge-by"][0]
    except (OSError, ValueError) as e:
        die("settings: %s" % e)


def checklists(root):
    """{name: (globs with the checklist's own file and the settings file, items)} of the project at root. Broken settings, a checklist with
    one of its two keys, or a file unreadable or without `- [ ]` items: exit 1 naming it, never a silently open gate."""
    try:
        values = read_settings(root)
    except (OSError, ValueError) as e:
        die("settings: %s" % e)
    keys = {}
    for key, (value, _) in values.items():
        if key.startswith("checklist.") and value:
            name, _, part = key[len("checklist."):].rpartition(".")
            keys.setdefault(name, {})[part] = value
    out = {}
    for name, parts in sorted(keys.items()):
        if len(parts) < 2:
            die(f"checklist {name}: set both checklist.{name}.paths and checklist.{name}.file")
        rel = parts["file"]
        text = read_text(os.path.join(root, rel))
        items = [" ".join(m.group(2).split()) for m in map(ITEM.fullmatch, (text or "").splitlines()) if m and m.group(2).strip()]
        if not items:
            die(f"checklist {name}: {rel} " + ("not readable" if text is None else "holds no `- [ ]` item"))
        out[name] = ([x.strip() for x in parts["paths"].split(",")] + [rel, SETTINGS_FILE], items)
    return out


def section_items(body):
    """{name: [(ticked, text), ...]} of the «## Checklist: <name>» sections of a PR body; a section ends at the next
    heading; a heading without a name is no section; item texts with whitespace collapsed."""
    out, name = {}, None
    for line in (body if isinstance(body, str) else "").splitlines():
        if HEADING.match(line):
            name = (line[len(CHECKLIST):].strip() or None) if line.startswith(CHECKLIST) else None
            if name is not None:
                out.setdefault(name, [])
        elif name is not None:
            m = ITEM.fullmatch(line)
            if m:
                out[name].append((m.group(1) != " ", " ".join(m.group(2).split())))
    return out


def sections(body):
    """{name: unticked items} of the checklist sections of a PR body."""
    return {name: sum(not t for t, _ in rows) for name, rows in section_items(body).items()}


def matched(files, lists):
    return [name for name, (globs, _) in lists.items() if owner_hits(files, globs)]


def add_checklists(url, n, lists):
    """Appends a section for every checklist the PR files match and the body lacks; an existing section is never rewritten."""
    if not lists:
        return
    repo = re.search(r"github\.com/([^/]+/[^/]+)/pull/", url)
    if not repo:
        die("cannot parse owner/repo from url: " + url)
    files = pr_files(repo.group(1), n, "checklist")[0]
    try:
        body = gh_json("pr", "view", url, "--json", "body").get("body")
    except (ValueError, AttributeError) as e:
        die("checklist: gh pr view: " + str(e).strip())
    have = sections(body)
    add = [x for x in matched(files, lists) if x not in have]
    if not add:
        return
    old = body.rstrip() if isinstance(body, str) and body.strip() else None
    text = "\n\n".join(([old] if old else []) + [
        "\n".join([f"{CHECKLIST} {x}", ""] + ["- [ ] " + i for i in lists[x][1]]) for x in add]) + "\n"
    p = sh("gh", "pr", "edit", url, "--body", text)
    if p.returncode:
        die("checklist: gh pr edit: " + p.stderr.strip())
    for x in add:
        print(f"PR #{n} checklist {x}: {len(lists[x][1])} open items")


def read_reviews(repo, n):
    """(reviews as [{login, state, commit_id}] in GitHub's order, None) or (None, why they were not read): a failed or
    late call, or any row that is not an object with a string state and a string or null login and commit_id. A null
    login (a deleted account) is no account and is skipped; a null commit_id (a commit gone after a force-push) is kept
    as that account's review and never matches the head."""
    try:
        p = sh("gh", "api", f"repos/{repo}/pulls/{n}/reviews", "--paginate",
               "--jq", ".[] | {login: .user.login, state, commit_id}", timeout=REVIEWS_SEC)
    except subprocess.TimeoutExpired:
        return None, f"gh api: no answer in {REVIEWS_SEC} s"
    if p.returncode:
        return None, brief(p.stderr or p.stdout) or "gh api failed"
    out = []
    for line in p.stdout.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            return None, "not JSON: " + line[:100]
        if not isinstance(row, dict) or not isinstance(row.get("state"), str) or not all(
                k in row and (row[k] is None or isinstance(row[k], str)) for k in ("login", "commit_id")):
            return None, "not a review: " + line[:100]
        if row["login"] is not None:
            out.append(row)
    return out, None


def approved(reviews, author, sha):
    """Some account other than the author has, as its latest review, an APPROVED one on sha."""
    latest = {r["login"]: r for r in reviews}
    return any(a != author and r["state"] == "APPROVED" and r["commit_id"] == sha for a, r in latest.items())


def approval_gate(repo, n, names, author, sha):
    """Lines «checklist <name>: no approval on <sha>» for the checklists of a PR without a person's approval: GitHub
    refuses an author's approval of their own PR, so the agent pushing as the author cannot give it."""
    if not names:
        return []
    reviews, why = read_reviews(repo, n) if author else (None, "no PR author")
    if reviews is not None and approved(reviews, author, sha):
        return []
    tail = f" (reviews not read: {why})" if why else ""
    return [f"checklist {name}: no approval on {sha}{tail}" for name in sorted(names)]


def checklist_gate(repo, n, body, root):
    """{name: open items} of the PR's checklists. A matching checklist counts its file's items, not the marks the body
    holds: an item is closed only when the section has it ticked with the file's text, so a section emptied, cut or
    replaced by an agent stays open; an extra unticked line in the section is open too."""
    lists, rows = checklists(root), section_items(body)
    have = {name: sum(not t for t, _ in r) for name, r in rows.items()}
    if lists:
        for name in matched(pr_files(repo, n)[0], lists):
            items, got = lists[name][1], rows.get(name, [])
            need, done = collections.Counter(items), collections.Counter(x for t, x in got if t)
            have[name] = sum((need - done).values()) + sum(not t and x not in need for t, x in got)
    return have


def sh(*cmd, cwd=None, timeout=None):
    return subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, cwd=cwd, timeout=timeout)


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def number(url):
    m = re.search(r"/pull/(\d+)", url)
    return m.group(1) if m else "?"


def open_pr(wt, base, title, root):
    lists = checklists(root)  # a broken checklist stops before the push
    p = sh("git", "-C", wt, "push", "-u", "origin", "HEAD")
    if p.returncode:
        die("push: " + p.stderr.strip())
    branch = sh("git", "-C", wt, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    p = sh("gh", "pr", "list", "--head", branch, "--state", "open", "--json", "number,url", cwd=wt)  # gh takes the repository from the folder
    if p.returncode:
        die("gh pr list: " + p.stderr.strip())
    prs = json.loads(p.stdout or "[]")
    if prs:
        n, url = prs[0]["number"], prs[0]["url"]
    else:
        p = sh("gh", "pr", "create", "--base", base, "--head", branch, "--title", title,
               "--body", f"Branch {branch}, opened by sdd-pr.py", cwd=wt)
        if p.returncode:
            die("gh pr create: " + p.stderr.strip())
        url = p.stdout.strip().splitlines()[-1]
        n = number(url)
    add_checklists(url, n, lists)
    return n, url


def cmd_open(wt, base, title):
    root = main_folder(wt) or wt
    n, url = open_pr(wt, delivery(root)[0] or base, title, root)
    print(f"PR #{n} {url}")
    return 0


def brief(text):
    return "\n".join(text.strip().splitlines()[-LOG_LINES:])


def checks(url):
    p = sh("gh", "pr", "checks", url, "--json", "name,state,bucket,link")
    try:
        return json.loads(p.stdout)
    except ValueError:
        return []  # gh without checks prints an error, not JSON


def failed_log(rows):
    out = []
    for r in rows:
        m = re.search(r"github\.com/([^/]+/[^/]+)/actions/runs/(\d+)", r.get("link", ""))
        if m:
            for _ in range(3):  # the log appears seconds after the check finishes
                log = sh("gh", "run", "view", m.group(2), "-R", m.group(1), "--log-failed").stdout
                if log.strip():
                    break
                time.sleep(LOG_RETRY_SEC)
            out += log.splitlines()
    clean = []
    for line in out:
        line = line.split("\t")[-1]  # without the job and step name
        clean.append(re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ?", "", line))
    hits = {i for i, s in enumerate(clean) if any(k in s for k in SIGNS)}
    keep = sorted({j for i in hits for j in (i - 1, i, i + 1) if 0 <= j < len(clean)})
    return bool(hits), [clean[i] for i in (keep or range(len(clean)))][-LOG_LINES:]  # the test summary is at the end of the log


def gh_json(*cmd):
    p = sh("gh", *cmd)
    if p.returncode:
        raise ValueError(p.stderr)
    return json.loads(p.stdout)


def required_checks(url):
    """Required checks of the PR base branch, or None if the rules could not be read."""
    try:
        repo = re.search(r"github\.com/([^/]+/[^/]+)/pull/", url).group(1)
        branch = quote(gh_json("pr", "view", url, "--json", "baseRefName")["baseRefName"], safe="/")
        # ponytail: one page, more than 100 active rules per branch does not happen in practice
        rules = gh_json("api", f"repos/{repo}/rules/branches/{branch}?per_page=100")
        names = [c["context"] for r in rules if r["type"] == "required_status_checks"
                 for c in r["parameters"]["required_status_checks"]]
        protection = gh_json("api", f"repos/{repo}/branches/{branch}").get("protection") or {}
        classic = protection.get("required_status_checks") or {}  # /protection needs admin rights
        names += [c["context"] for c in classic.get("checks") or []] + (classic.get("contexts") or [])
        if not all(isinstance(x, str) for x in names):
            raise ValueError
        return set(names)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def alert_line(a):
    """One line "#<number> <rule> <file>:<line> <text>"; newlines in fields collapsed."""
    inst = a.get("most_recent_instance") or {}
    loc, rule = inst.get("location") or {}, a.get("rule") or {}
    text = (inst.get("message") or {}).get("text") or rule.get("description") or ""
    line = f"#{a.get('number', '?')} {rule.get('id') or rule.get('name') or '?'} " \
           f"{loc.get('path') or '?'}:{loc.get('start_line') or '?'} {text}"
    return " ".join(line.split())


def scan_alerts(url):
    """Lines of open code scanning alerts for the PR: [] means none or scanning is off, None means not checked."""
    m = re.search(r"github\.com/([^/]+/[^/]+)/pull/(\d+)", url)
    if not m:
        return None
    # ref of the PR merge commit, as in the GitHub docs; one page: the summary needs only "some or none", at most 20 lines
    p = sh("gh", "api", f"repos/{m.group(1)}/code-scanning/alerts?ref=refs/pull/{m.group(2)}/merge&state=open&per_page=100")
    if p.returncode:
        off = "(HTTP 404)" in p.stderr or ("(HTTP 403)" in p.stderr and SCAN_OFF.search(p.stderr))
        return [] if off else None  # the text is checked on stderr: the response body has a link to the code-scanning docs
    try:
        alerts = json.loads(p.stdout)
        if not isinstance(alerts, list):
            raise ValueError
        return [alert_line(a) for a in alerts]
    except (ValueError, TypeError, AttributeError):
        return None


def stuck_checks(rows, required):
    """Required checks that are missing or have not started, when there is nothing else to wait for."""
    # ponytail: external CI on commit statuses (state PENDING) cannot be told apart from a check that has not started
    pending = {r.get("name") for r in rows if r.get("bucket") == "pending"}
    running = any(r.get("bucket") == "pending" and r.get("state") == "IN_PROGRESS" for r in rows)
    if running or pending - required:
        return []
    return sorted(required - ({r.get("name") for r in rows} - pending))


def ci_verdict(rows, required, stuck_sec, limit):
    """Checks summary: "bad", "green", "stuck" or None to keep waiting."""
    if any(r.get("bucket") in ("fail", "cancel") for r in rows):
        return "bad"
    if stuck_checks(rows, required):
        return "stuck" if stuck_sec >= limit else None
    return "green" if rows and not any(r.get("bucket") == "pending" for r in rows) else None


def cmd_wait(url, timeout=1200.0, interval=15.0, limit=STUCK_SEC):
    n = number(url)
    head = f"PR #{n} {url} CI: "
    required = required_checks(url)
    if required is None:
        print("warning: branch rules not read, required checks not checked", file=sys.stderr)
        required = set()
    start = time.monotonic()  # the deadline is for CI, reading the rules is not part of it
    since = None  # from which poll there is nothing to wait for but the stuck ones
    while True:
        rows = checks(url)
        now = time.monotonic()
        elapsed = now - start
        stuck = stuck_checks(rows, required)
        since = (since or now) if stuck else None
        verdict = ci_verdict(rows, required, now - since if stuck else 0, limit)
        if verdict == "green":
            alerts = scan_alerts(url)
            if alerts:
                print(head + "codeql")
                print("\n".join(alerts[:LOG_LINES]))
                return 8
            print(head + "green")
            if alerts is None:
                print(SCAN_UNCHECKED)
            return 0
        if verdict == "bad":  # a failed check is the summary at once
            test, lines = failed_log([r for r in rows if r.get("bucket") in ("fail", "cancel")])
            print(head + ("red" if test else "infra"))
            print("\n".join(lines))
            return 3 if test else 4
        if verdict == "stuck" or elapsed >= timeout or (not rows and not required and elapsed >= min(NO_CHECKS_SEC, timeout)):
            print(head + "infra")
            print("\n".join(f"required check did not start: {x}" for x in stuck)
                  or ("no checks" if not rows else "timeout: checks did not finish"))
            return 4
        time.sleep(interval)


def view(url):
    p = sh("gh", "pr", "view", url, "--json", "headRefOid,headRefName,baseRefName,state,title,isCrossRepository,body,author")
    if p.returncode:
        die("gh pr view: " + p.stderr.strip())
    try:
        return json.loads(p.stdout)
    except ValueError:
        die("gh pr view: not JSON: " + p.stdout[:200])


def owner_rule(text):
    """Lines of the «Owner only:» item of the «## Delivery» section (all of them, newline-separated) or None."""
    if text is None:
        return None
    inside, found = False, []
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Delivery"
        elif inside and line.strip().lstrip("-* ").startswith(OWNER):
            found.append(line.strip())
    return "\n".join(found) or None


def owner_patterns(rule):
    """Patterns from backquotes; a path ending in `/` is the whole directory."""
    pats = (re.sub(r"^(\./|/)+", "", y) for y in re.findall(r"`([^`]*)`", rule or ""))
    return [CI_PATTERN] + [x + "**" if x.endswith("/") else x for x in pats if x]


def glob_re(pat):
    """`*` within a name, `**` across folders; runs of asterisks collapsed (no catastrophic backtracking)."""
    parts = re.split(r"(\*+)", pat)
    out = []
    for i, x in enumerate(parts):
        if not x.startswith("*"):
            out.append(re.escape(x))
        elif len(x) == 1:
            out.append("[^/]*")
        elif i + 1 < len(parts) and parts[i + 1].startswith("/"):
            out.append("(?:.*/)?")  # `**/` includes zero depth
            parts[i + 1] = parts[i + 1][1:]
        else:
            out.append(".*")
    return re.compile("".join(out))


def owner_hits(files, patterns):
    res = [glob_re(x) for x in patterns]
    return sorted({f for f in files if any(r.fullmatch(f) for r in res)})


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def main_folder(cwd=None):
    p = sh("git", "rev-parse", "--path-format=absolute", "--git-common-dir", cwd=cwd)
    return os.path.dirname(p.stdout.strip()) if p.returncode == 0 and p.stdout.strip() else None


def pr_files(repo, n, step="not merged"):
    """PR file names (including previous ones) and each file's patch; a failure or broken response means die."""
    p = sh("gh", "api", "--paginate", f"repos/{repo}/pulls/{n}/files",
           "--jq", ".[] | {filename, previous_filename, patch}")
    if p.returncode:
        die(f"{step}: PR files: " + (p.stderr or p.stdout).strip())
    names, patches = [], {}
    for line in p.stdout.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            name = row["filename"]
        except (ValueError, TypeError, KeyError):
            die(f"{step}: PR files: not JSON: " + line[:200])
        if not isinstance(name, str):
            die(f"{step}: PR files: no filename: " + line[:200])
        names.append(name)
        patches[name] = row.get("patch")
        if isinstance(row.get("previous_filename"), str):
            names.append(row["previous_filename"])
    return names, patches


def rule_touched(patch):
    """An AGENTS.md edit touched the «Owner only:» item: no patch (too large) or the item is in added/removed lines."""
    if not patch:
        return True
    return any(l[:1] in ("+", "-") and not l.startswith(("+++", "---")) and OWNER in l for l in patch.splitlines())


def owner_gate(repo, n, main, wt):
    """Paths that wait for the owner (list of lines); empty means merge is allowed."""
    files, patches = pr_files(repo, n)
    main = main_folder() if main is None else main
    text = read_text(os.path.join(main, "AGENTS.md")) if main else None
    found = migrate_agents(text or "")[1]
    if found:
        print(migrate_hint(os.path.join(main, "AGENTS.md"), found), file=sys.stderr)
    rule = owner_rule(text)
    hits = owner_hits(files, owner_patterns(rule))
    if OWNER in found:  # the old item is not read, but its paths are not opened silently either: the owner decides
        hits.append(OLD_OWNER_HIT)
    if text is not None and ("AGENTS.md" in patches and rule_touched(patches["AGENTS.md"])
                             or wt is not None and owner_rule(read_text(os.path.join(wt, "AGENTS.md"))) != rule):
        hits.append(f"AGENTS.md («{OWNER}»)")
    return hits


def cmd_merge(url, how, sha, title=None, main=None, wt=None):
    n, v = number(url), view(url)
    if v["state"] == "MERGED":
        print(f"PR #{n} merged (already)")
        return 0
    if merge_by(main or main_folder() or ".") == "human":  # a person merges: the PR stays open
        print(f"PR #{n} {HUMAN}: {url}")
        return 8
    if v["headRefOid"] != sha:
        die(f"hash {sha} is not the PR head ({v['headRefOid']})")
    if how != "rebase":
        title = (v.get("title", "") if title is None else title).strip()
        if not title:
            die(f"PR #{n}: empty commit title (pass --title)")
    owner_repo = re.search(r"github\.com/([^/]+/[^/]+)/pull/", url)
    if not owner_repo:
        die("cannot parse owner/repo from url: " + url)
    hits = owner_gate(owner_repo.group(1), n, main, wt)
    if hits:
        print(f"PR #{n} waits for the owner: " + ", ".join(hits))
        return 8
    have = checklist_gate(owner_repo.group(1), n, v.get("body"), main or main_folder() or ".")
    lines = [f"checklist {name}: {k} open items" for name, k in sorted(have.items()) if k]
    author = v.get("author")
    lines = lines or approval_gate(owner_repo.group(1), n, have, author.get("login") if isinstance(author, dict) else None,
                                   v["headRefOid"])
    if lines:  # a person ticks the items in the PR body and approves the head commit
        print("\n".join(f"PR #{n} {x}" for x in lines))
        return 8
    p = sh("gh", "api", f"repos/{owner_repo.group(1)}/compare/{v['baseRefName']}...{v['headRefOid']}",
           "--jq", ".behind_by")
    if p.returncode:
        die("gh api compare: " + p.stderr.strip())
    try:
        behind = int(p.stdout.strip() or 0)
    except ValueError:
        die("gh api compare: not a number: " + p.stdout[:200])
    if behind > 0:
        print(f"PR #{n} behind {behind}: main moved ahead")
        return 5
    rows = checks(url)
    bad = [f"{r.get('name')} ({r.get('bucket')})" for r in rows if r.get("bucket") not in ("pass", "skipping")]
    if not rows or bad:
        die(f"PR #{n} CI not green: " + (", ".join(bad) or "no checks"))
    repo = owner_repo.group(1)
    extra = ["-f", f"commit_title={title} (#{n})"] if how != "rebase" else []
    p = sh("gh", "api", "-X", "PUT", f"repos/{repo}/pulls/{n}/merge", "-f", f"merge_method={how}", "-f", f"sha={sha}", *extra)
    if p.returncode:
        die((p.stderr or p.stdout).strip() or "merge refused")
    print(f"PR #{n} {url} merged ({how})")
    if v.get("isCrossRepository"):  # the branch lives in a fork: the same name in the base repository is someone else's branch
        return 0
    branch = v["headRefName"]
    p = sh("gh", "api", "-X", "DELETE", f"repos/{repo}/git/refs/heads/{branch}")
    if p.returncode and not any(c in p.stderr for c in ("HTTP 404", "HTTP 422")):
        print(f"branch {branch} not deleted: " + (p.stderr or p.stdout).strip())
    return 0


def worktree_script():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("sdd-worktree.py", "sdd_worktree.py"):
        if os.path.exists(os.path.join(here, name)):
            return os.path.join(here, name)
    return None


def cmd_ship(main, wt, base, title):
    base = delivery(main)[0] or base
    p = sh("git", "-C", wt, "fetch", "-q", "origin")
    if p.returncode:
        die("fetch: " + brief(p.stderr))
    p = sh("git", "-C", wt, "merge", "-q", "--no-edit", "origin/" + base)
    if p.returncode:
        files = sh("git", "-C", wt, "diff", "--name-only", "--diff-filter=U").stdout.split("\n")
        files = [f for f in files if f]
        if not files:
            die("merge: " + brief(p.stderr or p.stdout))
        if sh("git", "-C", wt, "merge", "--abort").returncode:
            die("merge --abort: conflict not aborted: " + ", ".join(files))
        die("conflict on update: " + ", ".join(files), 6)
    script = worktree_script()
    if not script:
        die("refresh: no sdd-worktree.py next to the script")
    p = sh(sys.executable, script, "refresh", main, wt)
    if p.returncode == 3:
        die(brief(p.stdout), 6)
    if p.returncode:
        # stderr before stdout: the command summary line "After update:" stays last in the tail
        die("refresh: " + brief("\n".join(x for x in (p.stderr, p.stdout) if x.strip())))
    n, url = open_pr(wt, base, title, main)
    return cmd_wait(url)


def cmd_land(main, wt, url, how):
    base, promote = delivery(main)
    n, v = number(url), view(url)
    if v["state"] != "MERGED" and (how == AFTER or merge_by(main) == "human"):  # before Land after green: nothing merges
        print(f"PR #{n} {HUMAN}: {url}")
        return 8
    if v["state"] != "MERGED":  # the head is read only here: after merge the WORKTREE folder may be gone
        sha = sh("git", "-C", wt, "rev-parse", "HEAD").stdout.strip()
        title = sh("git", "-C", wt, "log", "-1", "--first-parent", "--no-merges", "--diff-filter=ACDMRTB",
                   "--format=%s").stdout.strip()
        if not sha or not title:
            die("not merged: merge: no title in the last own commit of the branch")
        try:
            code = cmd_merge(url, how, sha, title, main, wt)
        except SystemExit:
            die("not merged: merge")  # cmd_merge already printed the reason
        if code:
            return code

    def fail(step, p):
        out, err = p.stdout.strip(), p.stderr.strip()
        why = (out or err) if step in ("transport", "remove") else (err or out)
        die(f"PR #{n} merged, not finished: {step}: " + brief(why), 7)

    target = v["baseRefName"]
    if sh("git", "-C", main, "branch", "--show-current").stdout.strip() == target:
        update = ("merge --ff-only", ("merge", "--ff-only", "-q", "origin/" + target))
    else:  # the main folder is on another branch: move only the local base branch, and only forward
        update = ("fetch " + target, ("fetch", "-q", "origin", "%s:%s" % (target, target)))
    for step, cmd in (("fetch", ("fetch", "-q", "origin")), update):
        p = sh("git", "-C", main, *cmd)
        if p.returncode:
            fail(step, p)
    if os.path.isdir(wt):
        script = worktree_script()
        for sub in ("transport", "remove"):
            if not script:
                die(f"PR #{n} merged, not finished: {sub}: no sdd-worktree.py next to the script", 7)
            p = sh(sys.executable, script, sub, main, wt)
            if p.returncode:
                fail(sub, p)
            if sub == "transport":
                print(p.stdout, end="")  # the dispatcher reads the «not transported: …» line
    branch = v["headRefName"]
    if branch.startswith("change/") and sh("git", "-C", main, "show-ref", "--verify", "--quiet",
                                           "refs/heads/" + branch).returncode == 0:
        p = sh("git", "-C", main, "branch", "-D", branch)
        if p.returncode:
            fail("branch -D", p)
    print(f"PR #{n} {url} land: done")
    if promote and (base or target) == target:
        print(promotion(target, promote[0]))
    return 0


def promotion(base, nxt):
    """The report line of the next promotion step; the command is for the user, nothing runs it."""
    return f"promotion: {base} → {nxt}: sdd-pr.py promote {shlex.quote(base)} {shlex.quote(nxt)}"


def version(rest):
    """Sort key of the part after the prefix: the leading dotted number, then a plain release above a suffix (-rc1)."""
    m = re.match(r"v?(\d+(?:\.\d+)*)(.*)", rest)
    return (tuple(int(x) for x in m.group(1).split(".")), not m.group(2), rest) if m else ((), False, rest)


def resolve(to):
    """<to> itself, or for `<prefix>*` the newest origin branch with that prefix by version; none: exit 1."""
    if not to.endswith("*"):
        return to
    p = sh("git", "ls-remote", "--heads", "origin", to)
    if p.returncode:
        die("git ls-remote: " + p.stderr.strip())
    names = [ln.split("refs/heads/", 1)[1] for ln in p.stdout.splitlines() if "refs/heads/" in ln]
    names = [x for x in names if x.startswith(to[:-1])]
    if not names:
        die(f"no branch matches {to} on origin")
    return max(names, key=lambda x: version(x[len(to) - 1:]))


def cmd_promote(frm, to):
    bad = [x for x in (frm, to) if bad_name(x)]
    if bad:
        die("not a branch name: " + ", ".join(bad))
    to = resolve(to)
    p = sh("gh", "pr", "list", "--head", frm, "--base", to, "--state", "open", "--json", "number,url")
    if p.returncode:
        die("gh pr list: " + p.stderr.strip())
    try:
        prs = json.loads(p.stdout or "[]")
        n, url = (prs[0]["number"], prs[0]["url"]) if prs else (None, None)
    except (ValueError, TypeError, KeyError, IndexError):
        die("gh pr list: not JSON: " + p.stdout[:200])
    if not prs:
        p = sh("gh", "pr", "create", "--base", to, "--head", frm, "--title", f"Promote {frm} to {to}",
               "--body", f"Promotion {frm} → {to}, opened by sdd-pr.py; merged by a person")
        if p.returncode:
            die("gh pr create: " + p.stderr.strip())
        url = p.stdout.strip().splitlines()[-1]
        n = number(url)
    print(f"PR #{n} {url} {frm} → {to}: open, not merged")
    return 0


def main(a):
    if a[:1] == ["ship"] and len(a) == 5:
        return cmd_ship(*a[1:])
    if a[:1] == ["land"] and len(a) == 5 and a[4] in ("squash", "merge", "rebase", AFTER):
        return cmd_land(*a[1:])
    if a[:1] == ["promote"] and len(a) == 3:
        return cmd_promote(*a[1:])
    if a[:1] == ["open"] and len(a) == 4:
        return cmd_open(*a[1:])
    if a[:1] == ["merge"] and len(a) in (4, 6) and a[2] in ("squash", "merge", "rebase") \
            and (len(a) == 4 or a[4] == "--title"):
        return cmd_merge(*a[1:4], *a[5:])
    if a[:1] == ["wait"] and len(a) >= 2:
        opt, rest = {"--timeout": 1200.0, "--interval": 15.0, "--stuck": float(STUCK_SEC)}, a[2:]
        try:  # ValueError is caught only while parsing arguments: a gh failure inside the command is code 1, not 2
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
