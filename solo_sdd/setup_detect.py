"""Project detection for `solo-sdd init` and the settings proposed from it; only reads, calls only git and gh."""
import os, subprocess
from urllib.parse import quote

from solo_sdd import providers

TIMEOUT = 10
CODEOWNERS = ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS")
WORKFLOWS = ".github/workflows"


def _out(cmd, cwd):
    """stdout of a read-only command; None when it is missing, fails or runs past the timeout."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=TIMEOUT,
                           env=dict(os.environ, GH_PROMPT_DISABLED="1", GIT_TERMINAL_PROMPT="0"))
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


def protection(root):
    """`protected`, `not protected` or `unknown` for the default branch, by gh (no gh, no access: unknown)."""
    branch = (_out(["gh", "repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"], root) or "").strip()
    if not branch:
        return "unknown"
    got = _out(["gh", "api", "repos/{owner}/{repo}/branches/" + quote(branch, safe=""), "--jq", ".protected"], root)
    return {"true": "protected", "false": "not protected"}.get((got or "").strip(), "unknown")


def ci(root):
    """The first `*.yml`/`*.yaml` file directly in .github/workflows, as GitHub Actions reads it; None when the
    folder is missing, unreadable or has none."""
    try:
        names = sorted(os.listdir(os.path.join(root, WORKFLOWS)))
    except OSError:
        return None
    return next(("%s/%s" % (WORKFLOWS, n) for n in names if n.endswith((".yml", ".yaml"))
                 and os.path.isfile(os.path.join(root, WORKFLOWS, n))), None)


def detect(root, home=None):
    """{agents: [(name, why)], remote, protection, authors (None: git failed), codeowners (path or None),
    ci (workflow path or None)}."""
    remotes = (_out(["git", "remote"], root) or "").split()
    log = _out(["git", "log", "--all", "--since=90.days", "--format=%aE"], root)
    return {
        "agents": [(n, w) for n, w in ((n, providers.found(n, home)) for n in providers.ALL) if w],
        "remote": ("origin" if "origin" in remotes else remotes[0]) if remotes else None,
        "protection": protection(root) if remotes else "no remote",
        "authors": None if log is None else len({a.strip().lower() for a in log.splitlines() if a.strip()}),
        "codeowners": next((c for c in CODEOWNERS if os.path.isfile(os.path.join(root, c))), None),
        "ci": ci(root),
    }


def propose(d):
    """{key: (value, reason)} for mode, agents and delivery.mode from a detect() result."""
    n = d["authors"]
    authors = "authors unknown" if n is None else "%d author%s in 90 days" % (n, "" if n == 1 else "s")
    owners = d["codeowners"] or "no CODEOWNERS"
    branch = {"protected": "default branch protected", "not protected": "default branch not protected",
              "unknown": "branch protection unknown"}.get(d["protection"], d["protection"])
    team = (n or 0) >= 2 or d["codeowners"] or d["protection"] == "protected"
    return {
        "mode": ("team" if team else "solo", ", ".join((authors, owners, branch))),
        "agents": (", ".join(a for a, _ in d["agents"]), ", ".join("%s: %s" % a for a in d["agents"])),
        "delivery.mode": ("local", "no remote") if not d["remote"] else
                         ("pr", "remote %s, CI %s" % (d["remote"], d["ci"])) if d["ci"] else
                         ("local", "remote %s, no CI workflow in %s" % (d["remote"], WORKFLOWS)),
    }
