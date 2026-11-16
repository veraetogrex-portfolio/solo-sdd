#!/usr/bin/python3
"""Probe of the installed `claude` and `codex` for the capabilities kept in solo_sdd/providers.py.

subagents: `claude --help` names `--agents`; `codex features list` shows `multi_agent` stable and on.
hooks: a no-op hook (`touch <marker>`) on session start and prompt submit, in a temporary home, with the model
endpoint pointing at a closed local port, so no request reaches a paid model: the hook counts only if the marker appears.
Codex runs only the hooks recorded as trusted: the probe asks the Codex app server (`hooks/list`) for each hook's
`currentHash` and writes `[hooks.state."<key>"] trusted_hash = <hash>` into the temporary config.toml, as Codex records
a hook the owner reviewed.
Prints one line per agent and capability: `<agent> <version> <capability>: <version> | unverified — <evidence>`,
and whether the registry agrees. Run from the repository root: python3 tests/stands/provider-probe.py [codex].
The temporary folder is removed; the last line is the summary.

`provider-probe.py cursor`: one line per Cursor capability (rules, skills, hooks, subagents):
`cursor <version> <capability>: confirmed | absent | not run — <evidence>; registry <value>`. It installs nothing and
runs `cursor-agent` only with a temporary home and project. The steps that would confirm a capability are not written:
no Cursor was available to run them on (docs/waiting.md), so every line is `not run` and the exit code is 0."""
import json, os, pathlib, shutil, subprocess, sys, tempfile, threading

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from solo_sdd import providers  # noqa: E402

DEAD = "http://127.0.0.1:9"


def call(args, env=None, cwd=None, timeout=120):
    try:
        p = subprocess.run(args, env=env, cwd=cwd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        return p.returncode, p.stdout + p.stderr
    except (OSError, subprocess.SubprocessError) as e:
        return None, str(e)


def version(cmd, env=None, cwd=None):
    out = call([cmd, "--version"], env=env, cwd=cwd)[1]
    return next((w for w in out.replace("-", " ").split() if w[:1].isdigit() and w.count(".") == 2), "?")


def hooks_claude(tmp):
    marks = [os.path.join(tmp, "claude-start"), os.path.join(tmp, "claude-prompt")]
    h = {"hooks": {e: [{"hooks": [{"type": "command", "command": "touch '%s'" % m}]}]
                   for e, m in zip(("SessionStart", "UserPromptSubmit"), marks)}}
    home = os.path.join(tmp, "claude-home")
    os.makedirs(home)
    env = dict(os.environ, HOME=home, ANTHROPIC_API_KEY="probe-invalid", ANTHROPIC_BASE_URL=DEAD)
    call(["claude", "-p", "probe", "--settings", json.dumps(h)], env=env, cwd=tmp)
    return [os.path.basename(m) for m in marks if os.path.exists(m)], None


def trust_codex(env, cwd):
    """Records every hook Codex lists as untrusted as trusted, the way Codex records a reviewed hook; returns the reason
    when the app server gave no list, else None."""
    p = subprocess.Popen(["codex", "app-server"], env=env, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True)
    timer = threading.Timer(60, p.kill)  # only this child: an app server that never answers is stopped
    timer.start()
    try:
        for msg in ({"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "provider-probe", "version": "0"}}},
                    {"method": "initialized"}, {"id": 2, "method": "hooks/list", "params": {"cwds": [cwd]}}):
            p.stdin.write(json.dumps(dict(msg, jsonrpc="2.0")) + "\n")
        p.stdin.flush()
        answer = None
        for line in p.stdout:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("id") == 2:
                answer = d
                break
    finally:
        timer.cancel()
        p.stdin.close()
        p.kill()
        p.wait()
    if not answer or "result" not in answer:
        return "codex app-server hooks/list gave %s" % (json.dumps((answer or {}).get("error")) if answer else "no answer")
    found = [h for c in answer["result"].get("data", []) for h in c.get("hooks", [])]
    with open(os.path.join(env["CODEX_HOME"], "config.toml"), "a") as f:
        for h in found:
            if h.get("trustStatus") != "trusted":
                f.write('[hooks.state.%s]\ntrusted_hash = %s\n' % (json.dumps(h["key"]), json.dumps(h["currentHash"])))
    return None if found else "codex app-server listed no hook"


def hooks_codex(tmp):
    marks = [os.path.join(tmp, "codex-start"), os.path.join(tmp, "codex-prompt")]
    home = os.path.join(tmp, "codex-home")
    os.makedirs(home)
    with open(os.path.join(home, "hooks.json"), "w") as f:
        json.dump({"hooks": {e: [{"hooks": [{"type": "command", "command": "touch '%s'" % m}]}]
                             for e, m in zip(("SessionStart", "UserPromptSubmit"), marks)}}, f)
    with open(os.path.join(home, "config.toml"), "w") as f:
        f.write('model_provider = "probe"\n[model_providers.probe]\nname = "probe"\nbase_url = "%s/v1"\n'
                'wire_api = "responses"\nrequest_max_retries = 0\nstream_max_retries = 0\n'
                '[projects."%s"]\ntrust_level = "trusted"\n' % (DEAD, tmp))
    env = dict(os.environ, HOME=tmp, CODEX_HOME=home)
    why = trust_codex(env, tmp)
    call(["codex", "exec", "--skip-git-repo-check", "probe"], env=env, cwd=tmp)
    return [os.path.basename(m) for m in marks if os.path.exists(m)], why


def subagents(name):
    if name == "claude":
        out = call(["claude", "--help"])[1]
        return "--agents" in out, "claude --help names --agents" if "--agents" in out else "claude --help lacks --agents"
    out = call(["codex", "features", "list"])[1]
    row = next((l.split() for l in out.splitlines() if l.split()[:1] == ["multi_agent"]), [])
    good = row[1:] == ["stable", "true"]
    return good, "codex features list: %s" % (" ".join(row) or "no multi_agent")


def cursor():
    p = providers.PROVIDERS["cursor"]
    kept = {"rules": p["project_rules"], "skills": p["skills"], **p["caps"]}
    if shutil.which("cursor-agent") is None:
        v, why = "-", "cursor-agent not in PATH"
    else:
        tmp = os.path.realpath(tempfile.mkdtemp(prefix="provider-probe-"))
        try:
            v = version("cursor-agent", env=dict(os.environ, HOME=tmp), cwd=tmp)
        finally:
            shutil.rmtree(tmp, True)
        why = "probe steps for an installed Cursor are not written yet"
    for cap in ("rules", "skills", "hooks", "subagents"):
        print("cursor %s %s: not run — %s; registry %s" % (v, cap, why, kept[cap] or "unverified"))
    print("summary: cursor not probed")
    return 0


def main():
    if sys.argv[1:] == ["cursor"]:
        return cursor()
    names = sys.argv[1:] or ["claude", "codex"]
    if any(n not in ("claude", "codex") for n in names):
        print("usage: provider-probe.py [claude | codex | cursor]")
        return 2
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="provider-probe-"))
    agree = True
    try:
        for name, probe in (("claude", hooks_claude), ("codex", hooks_codex)):
            if name not in names:
                continue
            if shutil.which(name) is None:
                for cap in ("hooks", "subagents"):
                    print("%s - %s: unverified — %s not in PATH; registry %s" % (
                        name, cap, name, providers.PROVIDERS[name]["caps"].get(cap, "absent")))
                continue
            v = version(name)
            fired, why = probe(tmp)
            ran = "no-op hook ran: %s" % (", ".join(fired) or "none") + ("" if fired or not why else " (%s)" % why)
            found = {"hooks": (bool(fired), ran), "subagents": subagents(name)}
            for cap, (good, evidence) in found.items():
                kept = providers.PROVIDERS[name]["caps"].get(cap, "absent")
                want = v if good else "unverified"
                same = kept == want
                agree &= same
                print("%s %s %s: %s — %s; registry %s%s" % (name, v, cap, want, evidence, kept,
                                                             "" if same else " (differs: %s)" % want))
    finally:
        shutil.rmtree(tmp, True)
    print("summary: registry %s the probe" % ("matches" if agree else "differs from"))
    return 0 if agree else 1


if __name__ == "__main__":
    sys.exit(main())
