#!/usr/bin/python3
"""Live scenario of change english-keywords, steps 1-3 and 5, on the scripts of this checkout.

A temporary git repository with two ready changes: the English AGENTS.md gives limit 3; the pre-English one
(built from the migration table) gives the default limit 2, the migrate line and `warn agents:`;
`migrate-agents` prints a diff, `--write` rewrites, a repeat changes nothing; the Stop hook checks the reply
language only with SOLO_SDD_REPLY_LANG. Temporary folders are removed; the last line is the summary.
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from solo_sdd import keywords  # noqa: E402

PY = "/usr/bin/python3"
OLD = {n: o for o, n in list(keywords.OLD_SECTIONS.items()) + [p for v in keywords.OLD_ITEMS.values() for p in v]}
NEW_AGENTS = "# Stand\n\n## Working copy\n\n- Orchestrators: 3\n\n## Delivery\n\n- Mode: local\n"
OLD_AGENTS = "# Stand\n\n## %s\n\n- %s 3\n\n## %s\n\n- %s local\n" % (
    OLD["Working copy"], OLD["Orchestrators:"], OLD["Delivery"], OLD["Mode:"])
EN_REPLY = "All done. The change is archived, every test passed and the live scenario printed the expected lines."


def run(args, cwd, env):
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout, p.stderr


def cyrillic(text):
    return any(0x400 <= ord(c) < 0x500 for c in text)


def main():
    tmp = tempfile.mkdtemp(prefix="english-keywords-")
    env = dict(os.environ, HOME=os.path.join(tmp, "home"), PYTHONPATH=ROOT)
    env.pop("SOLO_SDD_REPLY_LANG", None)
    os.makedirs(env["HOME"])
    repo = os.path.join(tmp, "repo")
    checks = []

    def check(name, ok, detail=""):
        checks.append(ok)
        print("%s %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else ": " + detail))

    try:
        os.makedirs(repo)
        run(["git", "init", "-q"], repo, env)
        for cid in ("alpha", "beta"):
            d = os.path.join(repo, "openspec", "changes", cid)
            os.makedirs(d)
            with open(os.path.join(d, "proposal.md"), "w") as f:
                f.write("## Why\n\nw\n\n## Impact\n\n`src/%s.py`\n\n## Depends On\n\nnone\n" % cid)
        agents = os.path.join(repo, "AGENTS.md")

        def write_agents(text):
            with open(agents, "w", encoding="utf-8") as f:
                f.write(text)

        def plan():
            return run([PY, os.path.join(ROOT, "global", "sdd_dispatch_plan.py"), repo], repo, env)

        write_agents(NEW_AGENTS)
        run(["git", "add", "-A"], repo, env)
        run(["git", "-c", "user.email=s@s", "-c", "user.name=s", "commit", "-qm", "stand"], repo, env)

        code, out, err = plan()
        print(out.strip())
        check("step 1: English AGENTS.md gives limit 3, no Cyrillic",
              [ln for ln in out.splitlines() if not ln.startswith("loopback: ")][:2]
              == ["limit: 3, running: 0, waiting for merge: 0", "launch: alpha beta"]
              and not cyrillic(out + err), out + err)

        write_agents(OLD_AGENTS)
        code, out, err = plan()
        _, doc, _ = run([PY, "-m", "solo_sdd", "doctor"], repo, env)
        warn = [ln for ln in doc.splitlines() if ln.startswith("warn agents: ")]
        print(out.splitlines()[0])
        print(err.strip())
        print(warn[0] if warn else "no warn agents line")
        check("step 2: old keywords: default limit 2, migrate line, warn agents",
              out.splitlines()[0] == "limit: 2, running: 0, waiting for merge: 0" and agents in err
              and "solo-sdd migrate-agents" in err and bool(warn) and "solo-sdd migrate-agents" in warn[0], out + err + doc)

        _, dry, _ = run([PY, "-m", "solo_sdd", "migrate-agents", repo], repo, env)
        unchanged = open(agents, encoding="utf-8").read() == OLD_AGENTS
        _, wrote, _ = run([PY, "-m", "solo_sdd", "migrate-agents", repo, "--write"], repo, env)
        rewritten = open(agents, encoding="utf-8").read() == NEW_AGENTS
        _, again, _ = run([PY, "-m", "solo_sdd", "migrate-agents", repo], repo, env)
        code, out, err = plan()
        print(wrote.strip().splitlines()[-1])
        print(again.strip())
        check("step 3: diff, --write, repeat says nothing changed, limit 3 is back",
              "+## Working copy" in dry and unchanged and rewritten and again.strip().endswith("nothing to change")
              and out.splitlines()[0] == "limit: 3, running: 0, waiting for merge: 0", dry + wrote + again + out)

        stop = {"session_id": "stand-unset", "cwd": tmp, "last_assistant_message": EN_REPLY}
        hook = [PY, os.path.join(ROOT, "global", "work_hooks.py"), "stop"]
        p = subprocess.run(hook, input=json.dumps(stop), capture_output=True, text=True, env=env)
        check("step 5a: SOLO_SDD_REPLY_LANG unset accepts an English reply", p.stdout.strip() == "", p.stdout + p.stderr)
        stop["session_id"] = "stand-ru"
        p = subprocess.run(hook, input=json.dumps(stop), capture_output=True, text=True,
                           env=dict(env, SOLO_SDD_REPLY_LANG="ru"))
        reason = json.loads(p.stdout or "{}").get("reason", "")
        print(reason.splitlines()[1] if len(reason.splitlines()) > 1 else reason)
        check("step 5b: SOLO_SDD_REPLY_LANG=ru asks for Russian", "Rewrite it in Russian" in reason, p.stdout + p.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("english-keywords stand: %d of %d checks passed" % (sum(checks), len(checks)))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
