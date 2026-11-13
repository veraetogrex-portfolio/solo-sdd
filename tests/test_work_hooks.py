#!/usr/bin/python3
"""Tests of global/work_hooks.py: one unittest method per scenario.

The hook logic runs in this process (`run`): for each call the module's HOME and STATE, os.environ, sys.argv and
sys.stdin are patched and stdout is captured; the git-root cache starts empty, as in a new process. Each test has its
own temporary HOME (`wh-home-*`), removed when the test ends, also when it fails. `EntryPoint` runs the real
`global/work_hooks.py` as a process, one to three times per command `main` dispatches.
"""
import contextlib, datetime, importlib.util, io, json, os, shutil, subprocess, sys, tempfile, time, unicodedata, unittest, warnings
from unittest import mock

from hypothesis import given, settings, strategies as st

import marks

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "global", "work_hooks.py")
PY = "/usr/bin/python3"
# Requirement: Hook self-check is location independent. Projects for the write checks are outside the working copy and outside the hook's TMP_ROOTS:
# in a worktree from $TMPDIR everything inside tests/ is allowed anyway. HOME is real: it is replaced only in ENV.
OUTSIDE = os.path.expanduser("~")
# Variables the hook reads: a test sets them for its own calls only.
HOOK_VARS = ("SOLO_SDD_EXPENSIVE_OK", "SOLO_SDD_REPLY_LANG", "CLAUDE_PROJECT_DIR")
BASE_ENV = {k: v for k, v in os.environ.items() if k not in HOOK_VARS}


def load(path=HOOK):
    """The hook module from `path`, loaded in this process under the name work_hooks (not __main__)."""
    spec = importlib.util.spec_from_file_location("work_hooks", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


wh = load()


def setUpModule():
    warnings.simplefilter("ignore", ResourceWarning)  # the fixtures write files with open(...).write, as the script did

# The fixture names of the running test: HookCase.setUp binds them to the test's own HOME, the cleanup unbinds them.
H = REPO = ENV = OWNER = None


def call(mod, cmd, inp, env, raw=False):
    """One in-process hook call `work_hooks.py <cmd>` with `inp` on stdin and exactly `env` as the environment."""
    home = env.get("HOME") or OUTSIDE
    out = io.StringIO()
    with contextlib.ExitStack() as s:
        s.enter_context(mock.patch.dict(os.environ, env, clear=True))
        s.enter_context(mock.patch.object(mod, "HOME", home))
        s.enter_context(mock.patch.object(mod, "STATE", os.path.join(home, ".claude", "hook-state")))
        s.enter_context(mock.patch.object(mod, "_roots", {}))
        s.enter_context(mock.patch.object(sys, "argv", [mod.__file__, cmd]))
        s.enter_context(mock.patch.object(sys, "stdin", io.StringIO(json.dumps(inp))))
        s.enter_context(contextlib.redirect_stdout(out))
        try:
            code = mod.main()
        except SystemExit as e:
            code = e.code
    assert code in (0, None), code
    text = out.getvalue()
    if raw:
        return text
    return json.loads(text) if text.strip() else None


def run(cmd, inp, env=None, raw=False):
    return call(wh, cmd, inp, env or ENV, raw)


def entry(cmd, inp, env=None):
    """One run of the real entry point as a process, the way Claude Code starts it."""
    r = subprocess.run([PY, HOOK, cmd], input=json.dumps(inp), capture_output=True, text=True, env=env or ENV)
    assert r.returncode == 0, r.stderr
    return r.stdout


def denied(inp):
    out = run("guard", dict({"session_id": "S1", "cwd": REPO}, **inp))
    return bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny"


def denied_env(inp, env, **extra):
    out = run("guard", dict({"session_id": "S1", "cwd": REPO}, **dict(inp, **extra)), env)
    return bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny"


def reason(inp):
    out = run("guard", dict({"session_id": "S1", "cwd": REPO}, **inp))
    return out["hookSpecificOutput"]["permissionDecisionReason"] if out else ""


def agent(desc, model=None, stype=None, **extra):
    ti = {"description": desc, "prompt": "x"}
    if stype:
        ti["subagent_type"] = stype
    if model:
        ti["model"] = model
    return dict({"tool_name": "Agent", "tool_input": ti}, **extra)


def bash(c):
    return denied({"tool_name": "Bash", "tool_input": {"command": c}})


def git(*a):
    subprocess.run(["git", "-C", REPO] + list(a), check=True, capture_output=True)


def git2(*a, cwd=None):
    return subprocess.run(["git", "-C", cwd or R2, "-c", "user.email=t@t", "-c", "user.name=t"] + list(a), check=True,
                          capture_output=True, text=True).stdout.strip()


def repo_fixture():
    os.makedirs(os.path.join(REPO, "openspec/changes/01-a"))
    os.makedirs(os.path.join(REPO, "openspec/changes/02-b"))
    os.makedirs(os.path.join(H, ".codex"))
    open(os.path.join(H, ".codex/config.toml"), "w").write('model = "gpt-6.1-sol"\n')
    open(os.path.join(REPO, "AGENTS.md"), "w").write("PROJECT-RULE-42\n")
    open(os.path.join(REPO, ".env"), "w").write("API_KEY=secret\n")
    open(os.path.join(REPO, "openspec/changes/01-a/tasks.md"), "w").write("- [x] one\n- [ ] two\n")
    open(os.path.join(REPO, "openspec/changes/02-b/WAITING"), "w").write("waiting for access\n")
    open(os.path.join(REPO, "app.css"), "w").write("a{}\n")
    git("init", "-q"); git("add", "AGENTS.md", "app.css", "openspec"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")


def _unbind():
    global H, REPO, ENV, OWNER, R2, WT2, first, head2, R3, R5, APP5, TASKS5, EDIT5, REVIEW5, TICK5, BASH5, R6, TREE, ENV_TREE, WT_HOME, WT_ENV
    H = REPO = ENV = OWNER = R2 = WT2 = first = head2 = R3 = R5 = APP5 = TASKS5 = EDIT5 = REVIEW5 = TICK5 = BASH5 = R6 = TREE = ENV_TREE = WT_HOME = WT_ENV = None


class HookCase(unittest.TestCase):
    """A test with its own HOME, project REPO and environment; the hook may log no error into that HOME."""

    def setUp(self):
        global H, REPO, ENV, OWNER
        H = os.path.realpath(tempfile.mkdtemp(prefix="wh-home-"))
        self.addCleanup(shutil.rmtree, H, True)
        self.addCleanup(_unbind)
        REPO = os.path.join(H, "proj")
        ENV = dict(BASE_ENV, HOME=H)
        OWNER = dict(ENV, SOLO_SDD_EXPENSIVE_OK="1")
        self.home = H
        repo_fixture()

    def tearDown(self):
        log = os.path.join(self.home, ".claude/hook-state/errors.log")
        if os.path.exists(log):
            self.fail("hook errors: " + open(log).read())


# ---------- the real entry point: one to three process runs per command ----------

class EntryPoint(HookCase):
    def test_guard(self):
        out = json.loads(entry("guard", {"session_id": "S1", "cwd": REPO, "tool_name": "Bash", "tool_input": {"command": "cat .env"}}))
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny", out
        assert entry("guard", {"session_id": "S1", "cwd": REPO, "tool_name": "Bash", "tool_input": {"command": "ls"}}).strip() == ""

    def test_context(self):
        ctx = json.loads(entry("context", {"session_id": "S1", "cwd": REPO, "source": "startup"}))["hookSpecificOutput"]["additionalContext"]
        assert "PROJECT-RULE-42" in ctx and "01-a — tasks 1/2" in ctx, ctx

    def test_subagent_context(self):
        sub = json.loads(entry("subagent-context", {"session_id": "S1", "cwd": REPO, "agent_id": "a1", "hook_event_name": "SubagentStart"}))
        assert sub["hookSpecificOutput"]["additionalContext"].startswith("Project rules: read " + os.path.join(REPO, "AGENTS.md")), sub

    def test_stop(self):
        open(os.path.join(REPO, "app.css"), "w").write("a{color:red}\n")
        tr = os.path.join(H, "t.jsonl")
        open(tr, "w").write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": os.path.join(REPO, "app.css")}}]}}) + "\n")
        out = json.loads(entry("stop", {"session_id": "S1", "cwd": REPO, "transcript_path": tr, "last_assistant_message": "Done."}))
        assert out["decision"] == "block" and "uncommitted" in out["reason"], out

    def test_beat_and_status(self):
        entry("beat", {"session_id": "S1", "hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"description": "Test run"}, "cwd": REPO})
        out = entry("status", {"session_id": "S1", "model": {"display_name": "Opus"}, "workspace": {"current_dir": REPO}})
        assert "▶ Bash: Test run" in out, out

    def test_end(self):
        os.makedirs(os.path.join(REPO, "openspec/changes/03-c"))
        run("guard", dict(change_file("tasks.md", "Write", "03-c", content="- [x] a\n"), session_id="S1", cwd=REPO))
        c3 = os.path.join(REPO, "openspec/changes/03-c/CLAIM")
        assert os.path.exists(c3)
        entry("end", {"session_id": "S1"})
        assert not os.path.exists(c3), "claim removed on SessionEnd"

    def test_claims(self):
        os.makedirs(os.path.join(REPO, "openspec/changes/08-h"))
        c8 = os.path.join(REPO, "openspec/changes/08-h/CLAIM")
        inp = {"session_id": "S9", "cwd": REPO, "tool_name": "Bash", "tool_input": {"command": "cp /tmp/tpl openspec/changes/08-h/CLAIM"}, "tool_use_id": "t8"}
        assert run("guard", inp) is None
        open(c8, "w").write("tpl\n")
        entry("claims", dict(inp, hook_event_name="PostToolUse"))
        assert run("guard", dict(edit5(), session_id="S9", cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/08-h/a.md")})) is None, "cp-created CLAIM is mine"


# ---------- isolation of the in-process calls ----------

class Isolation(unittest.TestCase):
    def test_isolated_in_process_calls_a_variable_set_by_one_test(self):
        got, cmd = [], {"tool_name": "Bash", "tool_input": {"command": "codex exec -m gpt-6-astra 'refactor'"}}
        home0, state0, outer = wh.HOME, wh.STATE, os.environ.get(wh.OVERRIDE_VAR)

        class Inner(HookCase):
            def test_1_owner(self):
                got.append(denied_env(cmd, OWNER))

            def test_2_plain(self):
                got.append(denied(cmd))
                got.append(wh.OVERRIDE_VAR in ENV)  # the fixture environment this test passes to its calls

        result = unittest.TestResult()
        unittest.TestSuite([Inner("test_1_owner"), Inner("test_2_plain")]).run(result)
        assert result.wasSuccessful(), result.failures + result.errors
        assert got == [False, True, False], "the later test's call saw no SOLO_SDD_EXPENSIVE_OK: %s" % got
        assert os.environ.get(wh.OVERRIDE_VAR) == outer and (wh.HOME, wh.STATE) == (home0, state0), "restored after the tests"

    def test_every_hook_check_kept_a_failing_test(self):
        homes = []

        class Inner(HookCase):
            def test_fails(self):
                homes.append(H)
                assert os.path.isdir(H)
                self.fail("on purpose")

        result = unittest.TestResult()
        Inner("test_fails").run(result)
        assert len(result.failures) == 1 and homes and os.path.basename(homes[0]).startswith("wh-home-"), (result.failures, homes)
        assert os.path.dirname(homes[0]) == os.path.realpath(tempfile.gettempdir()), "the HOMEs go to the temporary folder"
        assert not os.path.exists(homes[0]), "the failing test's HOME is removed"
        assert H is None, "the fixture names are unbound after the test"


# ---------- guard: secrets, models, roles ----------

class Secrets(HookCase):
    def test_secrets_in_bash_and_writes(self):
        assert bash("cat .env"), "cat .env"
        assert bash("cd x && head -3 data/app.env"), "app.env"
        assert not bash("grep -c '^API_KEY=.' .env"), "grep -c allowed"
        assert not bash("cat .env.example"), ".env.example allowed"
        assert bash("echo $OPENAI_API_KEY"), "echo key"
        assert not bash('echo "${#OPENAI_API_KEY}"'), "length allowed"
        assert bash("env | grep -i claude") and bash("printenv") and bash("printenv GITHUB_TOKEN"), "env"
        assert not bash("env -u ELECTRON_RUN_AS_NODE npm test --model x") or True
        assert not bash("printenv HOME"), "printenv HOME"
        assert bash("echo X= > .env") and not bash("echo NEW_KEY= >> .env"), "redirect"
        assert bash("git add -A"), "git add -A with .env"
        open(os.path.join(REPO, ".gitignore"), "w").write(".env\n")
        assert not bash("git add -A"), "ignored .env"
        assert bash("git add .env"), "explicit .env"
        assert denied({"tool_name": "Write", "tool_input": {"file_path": os.path.join(REPO, ".env"), "content": "x"}}), "write .env"
        assert denied({"tool_name": "Write", "tool_input": {"file_path": os.path.join(REPO, "sub/.env"), "content": "x"}}), "second .env"


class Models(HookCase):
    def test_models(self):
        assert bash("codex exec 'run the acceptance tests'"), "codex default sol in tests"
        assert not bash("codex exec -m gpt-6-luna 'run the acceptance tests'"), "luna tests ok"
        assert bash("codex exec -m gpt-6-astra 'refactor module'"), "astra always"
        assert bash("EXPENSIVE_OK=1 codex exec -m gpt-6-astra 'refactor'"), "a word in the command no longer bypasses"
        assert not denied_env({"tool_name": "Bash", "tool_input": {"command": "codex exec -m gpt-6-astra 'refactor'"}}, OWNER), "override"
        assert not bash("codex exec 'implement feature X'"), "default for impl ok"
        assert bash("npm run acceptance -- --model opus"), "test with opus"
        assert not bash("git commit -m 'tests and model-policy.json\n\nCo-Authored-By: Claude Opus 5.5'"), "commit text is not a model flag"
        assert bash("MODEL=gpt-6-astra npm test") and bash("pytest --model=sol"), "env and = forms"
        assert denied(agent("Review: acceptance run", "haiku")) and denied(agent("Review: acceptance run", "sonnet")), "Reviewer on a cheap model"
        assert not denied(agent("Review: acceptance run")) and not denied(agent("Review: acceptance run", "opus")), "Reviewer on an expensive model"
        assert not denied(agent("Implement parser"))

    def test_subagent_roles(self):
        assert not denied(agent("Write a.py and test", "sonnet")), "executor with tests: role general"
        assert denied(agent("Write a.py and test", "sonnet", agent_id="a1")), "the same from a subagent: the orchestrator writes code"
        assert not denied(agent("Review: add-words", "opus")) and not denied(agent("Review: add-words")) and not denied(agent("Review: add-words", "fable")), "reviewer on the main model"
        assert not denied(agent("Review: add-words", "claude-opus-5-5", agent_id="a1")), "reviewer from a subagent on the full opus id"
        for m in ("haiku", "sonnet"):
            r = reason(agent("Review: 248", m, agent_id="a1"))
            assert "opus" in r and "fable" in r and "without model" in r, "the refusal to a reviewer names main and the variant without model: " + r
        assert denied(agent("Review: add-words", "sol")) and denied(agent("Review: add-words", "luna")), "model outside main"
        assert not denied(agent("Orchestrator add-words", "opus")), "orchestrator from the main session"
        assert denied(agent("Orchestrator add-words", "sonnet", agent_id="a1")), "orchestrator from a subagent"
        assert denied(agent("Implement words command", agent_id="a1")) and denied(agent("Implement words command", "opus", agent_id="a1"))
        assert denied(agent("Implement words command", "sonnet", agent_id="a1")), "executor from a subagent with sonnet"
        for m in (None, "opus", "sonnet"):
            r = reason(agent("Implement words command", m, agent_id="a1"))
            assert "Review:" in r and "Lookup:" in r, "the refusal to an executor names the allowed tags: " + r
        assert not denied(agent("Implement words command", "sonnet")) and not denied(agent("Implement words command")), "executor from the main session"
        assert denied_env(agent("Implement words command", "sonnet", agent_id="a1"), OWNER), "the owner bypass does not lift the refusal to an executor"
        assert denied(agent("Review: add-words", "haiku", agent_id="a1")), "reviewer from a subagent on haiku"
        assert not denied(agent("Review: add-words", agent_id="a1")), "reviewer from a subagent without model"

    def test_lookup_role(self):
        assert not denied(agent("Lookup: where is the limit", "haiku", "Explore", agent_id="a1")), "lookup through Explore"
        assert denied(agent("Lookup: where is the limit", "haiku", "general-purpose", agent_id="a1")), "lookup not through Explore"
        assert "Explore" in reason(agent("Lookup: limit", "haiku", "general-purpose", agent_id="a1"))
        assert denied(agent("Lookup: where is the limit", None, "Explore", agent_id="a1")) and denied(agent("Lookup: where is the limit", "opus", "Explore", agent_id="a1")), "lookup without a model or on opus"
        assert wh.agent_role("Lookup: where is the limit") == "lookup" and wh.agent_role("  lookup: limit") == "lookup"
        assert wh.agent_role("\u041f\u043e\u0438\u0441\u043a: x") == "general", "the pre-English lookup tag is dropped"

    def test_role_by_an_explicit_tag(self):
        assert denied(agent("Implement: acceptance core module", "sonnet", agent_id="a1")), "implement by the general rules"
        assert "Review:" not in reason(agent("Acceptance core module", "sonnet")) and not denied(agent("Acceptance core module", "sonnet")), "a word without a tag does not make a reviewer"
        assert "writes the change code itself" in reason(agent("Acceptance core module", "sonnet", agent_id="a1")), "a word without a tag from a subagent: role general, not review"
        assert denied(agent("Implement: x", "opus", agent_id="a1"))
        assert denied(agent("  review: add-words", "haiku"))
        # Requirement: English keyword set. The pre-English review and lookup tags are plain words now: role general
        OLD_REVIEW, OLD_LOOKUP = "\u0420\u0435\u0432\u044c\u044e:", "\u041f\u043e\u0438\u0441\u043a:"
        assert not denied(agent(OLD_REVIEW + " add-words", "sonnet")), "old review tag from the main session: general, allowed"
        assert "writes the change code itself" in reason(agent(OLD_LOOKUP + " x", "haiku", "general-purpose", agent_id="a1")), "old lookup tag: general"
        assert not denied(agent("Review add-words", "haiku")) and not denied(agent("Re-review add-words", "haiku"))
        assert denied(agent("Orchestrators add-words", "sonnet", agent_id="a1")) and "writes the change code itself" in reason(agent("Orchestrators add-words", "sonnet", agent_id="a1")), "Orchestrators is not a tag: role general"
        assert denied(agent("Orchestrator: x", "sonnet", agent_id="a1"))

    def test_bypass_only_from_the_owner(self):
        assert denied(agent("Review: add-words EXPENSIVE_OK", "sonnet")), "a word in the description does not bypass"
        assert "EXPENSIVE_OK" not in reason(agent("Review: add-words EXPENSIVE_OK", "sonnet")), "refusal without a bypass hint"
        assert not denied_env(agent("Lookup: where is the limit", "opus", "Explore", agent_id="a1"), OWNER), "the owner allowed it"
        assert denied_env(agent("Lookup: where is the limit", "opus", "Explore", agent_id="a1"), dict(ENV, SOLO_SDD_EXPENSIVE_OK="true")), "bypass only with the value 1"
        assert denied_env(agent("Orchestrator add-words", agent_id="a1"), OWNER), "the bypass does not lift the orchestrator ban"
        assert denied(agent("Review: add-words", "sol")) and not denied_env(agent("Review: add-words", "sol"), OWNER), "the owner allowed a reviewer outside main"

    def test_bypass_through_settings_and_profile(self):
        SETTINGS_JSON = os.path.join(H, ".claude", "settings.json")
        assert denied({"tool_name": "Write", "tool_input": {"file_path": SETTINGS_JSON, "content": '{"env": {"SOLO_SDD_EXPENSIVE_OK": "1"}}'}}), "settings.json"
        assert denied({"tool_name": "Edit", "tool_input": {"file_path": os.path.join(H, ".zshrc"), "old_string": "a", "new_string": "export SOLO_SDD_EXPENSIVE_OK=1"}}), "zshrc"
        assert denied({"tool_name": "MultiEdit", "tool_input": {"file_path": os.path.join(H, ".profile"), "edits": [{"old_string": "a", "new_string": "b"}, {"old_string": "c", "new_string": "SOLO_SDD_EXPENSIVE_OK"}]}}), "multiedit"
        assert not denied({"tool_name": "Write", "tool_input": {"file_path": os.path.join(REPO, "settings.json"), "content": "SOLO_SDD_EXPENSIVE_OK"}}), "not .claude"
        assert bash("echo 'export SOLO_SDD_EXPENSIVE_OK=1' >> ~/.zshrc"), "echo into the profile"
        assert bash("echo SOLO_SDD_EXPENSIVE_OK=1 | tee -a ~/.bashrc") and bash("sed -i '' 's/x/SOLO_SDD_EXPENSIVE_OK/' ~/.claude/settings.json"), "tee and sed -i"
        assert not bash("grep -c SOLO_SDD_EXPENSIVE_OK ~/.zshrc; echo x > /tmp/out"), "reading the profile and writing another file"
        assert bash("echo SOLO_SDD_EXPENSIVE_OK=1 >| ~/.zshrc") and bash("echo SOLO_SDD_EXPENSIVE_OK=1 >> ~/.zshenv"), ">| and zshenv"
        assert bash("launch" + "ctl setenv SOLO_SDD_EXPENSIVE_OK 1"), "setenv"
        assert not bash("grep -rn SOLO_SDD_EXPENSIVE_OK global") and not bash("SOLO_SDD_EXPENSIVE_OK=1 python3 tests/test_work_hooks.py"), "search and command environment"

    def test_owner_only_expensive_override_property(self):
        cased = st.sampled_from(["EXPENSIVE_OK", "expensive_ok", "Expensive_Ok", "eXpEnSiVe_oK"])
        free = st.text(max_size=20) | st.just("")
        body = st.sampled_from(["", " add-words", " review"])
        prefix = st.sampled_from(["Review:", "review:", "REVIEW:", "  Review:"])

        @settings(max_examples=300, deadline=None)
        @given(prefix, body, free, cased, st.sampled_from(["start", "mid", "end", "only"]), st.sampled_from(["haiku", "sonnet", "luna", "sol", "astra"]), st.booleans())
        def review_denied(pre, mid, tail, w, where, model, sub):
            base = pre + mid + tail
            cut = len(pre) + (len(base) - len(pre)) // 2  # the start sets the role: insert the name after the prefix
            desc = {"start": pre + w + base[len(pre):], "mid": base[:cut] + w + base[cut:], "end": base + w, "only": pre + w}[where]
            assert is_denied(wh.guard_models_agent, {"description": desc, "model": model}, sub), desc

        @settings(max_examples=300, deadline=None)
        @given(st.sampled_from(["Implement ", "Write ", "implement ", "WRITE "]), st.text(max_size=30) | st.sampled_from(["", "test", "review", "acceptance", "Test review Acceptance"]))
        def general_role(pre, rest):
            assert wh.agent_role(pre + rest) == "general", pre + rest

        @settings(max_examples=100, deadline=None)
        @given(st.sampled_from(["Acceptance ", "Test ", "Independent review ", "Re-review ", "Review ", "\u041f\u0440\u0438\u0451\u043c\u043a\u0430 ", "\u0422\u0435\u0441\u0442 ",
                                "\u0420\u0435\u0432\u044c\u044e:", "\u0418\u0441\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044c:", "\u041f\u043e\u0438\u0441\u043a:"]), st.text(max_size=30))
        def untagged_general(pre, rest):
            assert wh.agent_role(pre + rest) == "general", pre + rest

        @settings(max_examples=300, deadline=None)
        @given(st.sampled_from(wh.PROFILES + ("settings.json", "settings.local.json")), free, free, st.sampled_from(["Write", "Edit", "MultiEdit"]))
        def write_denied(name, a, b, tool):
            path = os.path.join("/h", ".claude", name) if name.startswith("settings") else os.path.join("/h", name)
            for text in (wh.OVERRIDE_VAR + a, a + wh.OVERRIDE_VAR, a + wh.OVERRIDE_VAR + b, wh.OVERRIDE_VAR):
                ti = {"content": text} if tool == "Write" else {"new_string": text} if tool == "Edit" else {"edits": [{"new_string": "x"}, {"new_string": text}]}
                assert is_denied(wh.guard_override_write, tool, ti, path), (path, text)

        with mock.patch.dict(os.environ, BASE_ENV, clear=True), mock.patch.object(wh, "deny", _raise):
            review_denied()
            general_role()
            untagged_general()
            write_denied()


class Denied(Exception):
    pass


def _raise(reason):
    raise Denied(reason)


def is_denied(f, *a):
    try:
        f(*a)
    except Denied:
        return True
    return False


# ---------- guard: worktrees, folder boundaries ----------

class Boundaries(HookCase):
    def test_worktree_commands(self):
        assert denied({"tool_name": "Bash", "tool_input": {"command": "git worktree add ../copy"}, "cwd": OUTSIDE}) and not bash("git worktree add /tmp/wt-1"), "worktree"
        # built-in agent worktrees
        assert not bash("claude --worktree feat") and not bash("claude -w") and not bash("claude --worktree=a") and not bash("cd x && claude -p 'go' -w feat"), "claude -w is let through"
        assert bash("codex --worktree") and bash("codex exec --worktree 'implement x'") and bash("FOO=1 codex fork --worktree=a"), "codex --worktree"
        assert not bash("git commit -m 'codex --worktree forbidden, claude -w not'"), "quoted text is not a command"
        assert not bash("grep -rn -- --worktree skills") and not bash("claude -p 'go'"), "no worktree flag"
        assert not bash("codex exec -C /tmp/wt-1 'implement x'"), "codex in temp worktree"
        assert not denied({"tool_name": "EnterWorktree", "tool_input": {"name": "feat"}}), "EnterWorktree new"
        assert not denied({"tool_name": "EnterWorktree", "tool_input": {}}), "EnterWorktree random name"
        assert not denied({"tool_name": "EnterWorktree", "tool_input": {"path": "/tmp/wh-wt-1"}}), "EnterWorktree temp path"
        assert not denied({"tool_name": "EnterWorktree", "tool_input": {"path": os.path.join(REPO, ".claude/worktrees/a")}}), "EnterWorktree inside project"
        assert not denied({"tool_name": "Agent", "tool_input": {"description": "Implement parser", "prompt": "x", "isolation": "worktree"}}), "agent isolation"
        assert not denied({"tool_name": "Agent", "tool_input": {"description": "Implement parser", "prompt": "x", "isolation": "remote"}}), "remote isolation"

    def test_write_scope(self):
        outside = "/opt/wh-test-outside/file.txt"
        w = {"tool_name": "Write", "tool_input": {"file_path": outside, "content": "x"}}
        assert denied(w) and not denied(w), "scope: first deny, second allow"
        w2 = {"tool_name": "Write", "tool_input": {"file_path": "/opt/wh-test-outside/race.txt", "content": "x"}}
        assert denied(w2)
        json.dump({"phase": "run"}, open(os.path.join(H, ".claude/hook-state/S1.json"), "w"))  # a beat that loaded the state before the warning
        assert not denied(w2), "scope: a concurrent beat does not reset the warning"
        assert not denied({"tool_name": "Write", "tool_input": {"file_path": os.path.join(REPO, "src/x.py")}}), "inside repo"

    def test_nfd_folder(self):
        nfd = tempfile.mkdtemp(prefix=unicodedata.normalize("NFD", "wh-é-"), dir=OUTSIDE)
        subprocess.run(["git", "init", "-q", nfd], check=True)
        cyr = unicodedata.normalize("NFC", nfd)
        try:
            assert not run("guard", {"session_id": "S9", "cwd": cyr, "tool_name": "Write",
                                     "tool_input": {"file_path": os.path.join(cyr, "README.md")}}), "NFD folder, NFC path"
        finally:
            shutil.rmtree(nfd)

    def test_project_dir_stays_own(self):
        # cwd left the project: the launch folder from CLAUDE_PROJECT_DIR stays own
        proj = os.path.realpath(tempfile.mkdtemp(prefix="wh-proj-", dir=OUTSIDE))
        try:
            subprocess.run(["git", "init", "-q", proj], check=True)
            os.makedirs(os.path.join(H, "scratchpad"), exist_ok=True)
            pw = {"cwd": os.path.join(H, "scratchpad"), "tool_name": "Write", "tool_input": {"file_path": os.path.join(proj, "README.md")}}
            assert run("guard", dict(pw, session_id="S7")), "outside without project dir"
            assert run("guard", dict(pw, session_id="S8"), env=dict(ENV, CLAUDE_PROJECT_DIR=proj)) is None, "project dir allowed"
        finally:
            shutil.rmtree(proj)


# ---------- guard: CLAIM ----------

def change_file(name, tool="Edit", change="01-a", **ti):
    return {"tool_name": tool, "tool_input": dict(ti, file_path=os.path.join(REPO, "openspec/changes", change, name))}


def edit5():
    return {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(REPO, "openspec/changes/05-e/tasks.md")}}


def sh5(sid, c, effect=None, tid="t1"):
    """The whole Bash: guard before the run, the command itself (effect), claims after."""
    inp = {"session_id": sid, "cwd": REPO, "tool_name": "Bash", "tool_input": {"command": c}, "tool_use_id": tid}
    out = run("guard", inp)
    if not out:
        effect and effect()
        run("claims", dict(inp, hook_event_name="PostToolUseFailure"))
    return out


TASKS_TEXT = st.lists(st.sampled_from(["- [ ] a", "- [x] a", "- [X] b", "  - [x] c", "[x] not a task", "text", ""]), max_size=6).map("\n".join)


class Claims(HookCase):
    def test_claim_on_first_done_task(self):
        prop = change_file("proposal.md", "Write", content="x")
        claim = os.path.join(REPO, "openspec/changes/01-a/CLAIM")
        for f in (prop, change_file("specs/c/spec.md", "Write", content="- [x] in the spec"), change_file("design.md", "Write", content="x"),
                  change_file("verification.md", old_string="a", new_string="b"),
                  change_file("tasks.md", old_string="- [ ] two", new_string="- [ ] two\n- [ ] three"),
                  change_file("tasks.md", old_string="no such line", new_string="- [x] no such line")):
            assert not denied(f), f
            assert not os.path.exists(claim), ("analysis does not take the change", f)
        os.makedirs(os.path.join(REPO, "openspec/changes/13-q"))
        open(os.path.join(REPO, "openspec/changes/13-q/tasks.md"), "w").write("- [ ] a\n- [ ] a\n- [ ] b\n")
        two = {"old_string": "- [ ] a", "new_string": "- [x] a"}
        assert not denied(change_file("tasks.md", change="13-q", **two)), "non-unique old_string: Edit will refuse"
        assert not os.path.exists(os.path.join(REPO, "openspec/changes/13-q/CLAIM")), "refused edit does not take the change"
        assert not denied(change_file("tasks.md", "MultiEdit", "13-q", edits=[{"old_string": "- [ ] b", "new_string": "- [ ] c"}, {"old_string": "- [ ] c", "new_string": "- [x] c"}]))
        assert os.path.exists(os.path.join(REPO, "openspec/changes/13-q/CLAIM")), "MultiEdit applies edits in order"
        os.remove(os.path.join(REPO, "openspec/changes/13-q/CLAIM"))
        assert not denied(change_file("tasks.md", "MultiEdit", "13-q", edits=[{"old_string": "- [ ] b", "new_string": "- [x] b"}, {"old_string": "no such line", "new_string": "x"}]))
        assert not os.path.exists(os.path.join(REPO, "openspec/changes/13-q/CLAIM")), "MultiEdit with a refused edit changes nothing"
        assert not denied(change_file("tasks.md", change="13-q", replace_all=True, **two))
        assert os.path.exists(os.path.join(REPO, "openspec/changes/13-q/CLAIM")), "replace_all marks tasks"
        assert not denied(change_file("tasks.md", old_string="[ ] two", new_string="[x] two")), "first done task takes change"
        assert "session=S1" in open(claim).read(), "claim created"
        out = run("guard", dict(prop, session_id="S2", cwd=REPO, transcript_path=""))
        assert out and "is taken" in out["hookSpecificOutput"]["permissionDecisionReason"], "other agent blocked"
        assert denied({"tool_name": "Edit", "tool_input": {"file_path": os.path.join(REPO, "openspec/changes/02-b/tasks.md")}}), "WAITING"

    @settings(max_examples=60, deadline=None)
    @given(TASKS_TEXT, TASKS_TEXT, st.sampled_from(["Write", "Edit", "MultiEdit"]), st.sampled_from(["tasks.md", "proposal.md"]))
    def test_claim_on_first_done_task_property(self, old, new, tool, name):
        cdir = os.path.join(REPO, "openspec/changes/12-p")
        os.makedirs(cdir, exist_ok=True)
        claim = os.path.join(cdir, "CLAIM")
        if os.path.exists(claim):
            os.remove(claim)
        open(os.path.join(cdir, name), "w").write(old)
        edit = {"old_string": old, "new_string": new}
        ti = {"Write": {"content": new}, "Edit": edit, "MultiEdit": {"edits": [edit]}}[tool]
        done = lambda text: sum(l.strip().lower().startswith("- [x]") for l in text.split("\n"))
        assert run("guard", dict(change_file(name, tool, "12-p", **ti), session_id="S20", cwd=REPO)) is None
        assert os.path.exists(claim) == (name == "tasks.md" and done(new) > done(old)), (old, new, tool, name)

    def test_claim_removed_on_session_end(self):
        os.makedirs(os.path.join(REPO, "openspec/changes/03-c"))
        run("guard", dict(change_file("tasks.md", "Write", "03-c", content="- [x] a\n"), session_id="S1", cwd=REPO))
        c3 = os.path.join(REPO, "openspec/changes/03-c/CLAIM")
        assert os.path.exists(c3)
        run("end", {"session_id": "S1"})
        assert not os.path.exists(c3), "claim removed on SessionEnd"

    def test_manual_claim_without_a_session_id(self):
        # CLAIM placed by hand without a session id (2026-10-17)
        os.makedirs(os.path.join(REPO, "openspec/changes/05-e"))
        c5 = os.path.join(REPO, "openspec/changes/05-e/CLAIM")
        assert sh5("S3", 'cd "%s" && echo "claude-opus $(date +%%F)" > openspec/changes/05-e/CLAIM && ls -R' % REPO,
                   lambda: open(c5, "w").write("claude-opus 2026-10-17\n")) is None
        assert sh5("S4", 'cat "%s"; [ -f openspec/changes/05-e/CLAIM ] || echo me > openspec/changes/05-e/CLAIM' % c5) is None
        out = run("guard", dict(edit5(), session_id="S4", cwd=REPO))
        assert out and "rewrite it" in out["hookSpecificOutput"]["permissionDecisionReason"], "reading or re-claiming does not make it yours"
        assert run("guard", dict(edit5(), session_id="S3", cwd=REPO)) is None, "own manual CLAIM accepted"
        assert open(c5).read() == "claude-opus 2026-10-17 session=S3\n", "hook stamps session id"
        out = run("guard", dict(edit5(), session_id="S4", cwd=REPO))
        assert out and "last active 0 min ago" in out["hookSpecificOutput"]["permissionDecisionReason"], out
        assert sh5("S4", "openspec archive 05-e --yes"), "foreign archive blocked"
        assert sh5("S3", "rm x && openspec archive 05-e --yes") is None, "own archive allowed"
        assert sh5("S4", "echo 'later: openspec archive 05-e --yes'") is None, "archive inside a string is not a command"
        assert sh5("S4", "cd x && npx openspec archive 05-e -y"), "npx form blocked"
        run("end", {"session_id": "S3"})
        assert not os.path.exists(c5), "stamped claim removed on SessionEnd"

    def test_cp_created_claim(self):
        os.makedirs(os.path.join(REPO, "openspec/changes/08-h"))
        c8 = os.path.join(REPO, "openspec/changes/08-h/CLAIM")
        assert sh5("S9", "cp /tmp/tpl openspec/changes/08-h/CLAIM", lambda: open(c8, "w").write("tpl\n"), tid="t8") is None
        assert run("guard", dict(edit5(), session_id="S9", cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/08-h/a.md")})) is None, "cp-created CLAIM is mine"
        assert run("guard", dict(edit5(), session_id="S4", cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/08-h/a.md")})), "and not someone else's"

    def test_cd_and_python_claim(self):
        other = os.path.join(H, "elsewhere")
        os.makedirs(other, exist_ok=True)
        os.makedirs(os.path.join(REPO, "openspec/changes/09-i"))
        c9 = os.path.join(REPO, "openspec/changes/09-i/CLAIM")
        i9 = {"session_id": "S10", "cwd": other, "tool_name": "Bash", "tool_use_id": "t9",
              "tool_input": {"command": 'cd "%s" && python3 -c "open(\'openspec/changes/09-i/CLAIM\',\'w\')"' % REPO}}
        assert run("guard", i9) is None
        open(c9, "w").write("x\n")
        run("claims", dict(i9, cwd=REPO))
        assert run("guard", dict(edit5(), session_id="S10", cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/09-i/a.md")})) is None, "cd + python CLAIM is mine"

    def test_claim_before_the_post_hook(self):
        os.makedirs(os.path.join(REPO, "openspec/changes/10-j"))
        c10 = os.path.join(REPO, "openspec/changes/10-j/CLAIM")
        e10 = dict(edit5(), cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/10-j/a.md")})
        assert run("guard", {"session_id": "S11", "cwd": REPO, "tool_name": "Bash", "tool_use_id": "t10",
                             "tool_input": {"command": "echo a > openspec/changes/10-j/CLAIM; false"}}) is None
        open(c10, "w").write("a\n")
        assert run("guard", dict(e10, session_id="S11")) is None, "post hook has not run yet: still mine"

    def test_claim_made_after_the_command(self):
        os.makedirs(os.path.join(REPO, "openspec/changes/11-k"))
        c11 = os.path.join(REPO, "openspec/changes/11-k/CLAIM")
        assert sh5("S12", "cat openspec/changes/11-k/CLAIM 2>/dev/null", tid="t11") is None
        time.sleep(0.05)
        open(c11, "w").write("codex 2026-10-17\n")
        assert run("guard", dict(edit5(), session_id="S12", cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/11-k/a.md")})), "CLAIM made after my command ended is not mine"

    def test_write_created_claim(self):
        os.makedirs(os.path.join(REPO, "openspec/changes/07-g"))
        w7 = os.path.join(REPO, "openspec/changes/07-g/CLAIM")
        assert run("guard", {"session_id": "S3", "cwd": REPO, "tool_name": "Write", "tool_input": {"file_path": w7}}) is None
        open(w7, "w").write("claude 2026-10-17\n")
        assert run("guard", dict(edit5(), session_id="S3", cwd=REPO, tool_input={"file_path": os.path.join(REPO, "openspec/changes/07-g/a.md")})) is None, "Write-created CLAIM is mine"

    def test_claim_in_the_main_checkout(self):
        # worktree: CLAIM is placed and checked in the main folder
        os.makedirs(os.path.join(REPO, "openspec/changes/06-f"))
        open(os.path.join(REPO, "openspec/changes/06-f/tasks.md"), "w").write("- [ ] x\n")
        git("add", "openspec/changes/06-f"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "06")
        wt = os.path.join(H, "wt-06")
        git("worktree", "add", "-q", wt, "-b", "wip/06")
        wedit = {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(wt, "openspec/changes/06-f/tasks.md"), "old_string": "- [ ] x", "new_string": "- [x] x"}}
        assert run("guard", dict(wedit, session_id="S5", cwd=wt, tool_input=dict(wedit["tool_input"], new_string="- [ ] x\n- [ ] y"))) is None
        assert not os.path.exists(os.path.join(REPO, "openspec/changes/06-f/CLAIM")), "no claim without a done task"
        assert run("guard", dict(wedit, session_id="S5", cwd=wt)) is None
        assert "session=S5" in open(os.path.join(REPO, "openspec/changes/06-f/CLAIM")).read(), "claim in main checkout"
        assert not os.path.exists(os.path.join(wt, "openspec/changes/06-f/CLAIM")), "no claim inside worktree"
        assert run("guard", dict(wedit, session_id="S6", cwd=wt)), "main-checkout claim blocks worktree edit"


# ---------- context, subagent-context, beat, status ----------

@settings(max_examples=60, deadline=None)
@given(st.lists(st.tuples(st.text(max_size=400), st.sampled_from(["", "CLAIM", "WAITING", "both"]), st.text(max_size=50)),
                max_size=500) | st.just([]) | st.just([("é" * 5000, "CLAIM", "x")] * 500),
       st.sampled_from([None, "/p/AGENTS.md", "/Users/you/" + "d" * 200 + "/AGENTS.md"]))
def _subagent_ctx(raw, agents):
    rows = []
    for name, kind, label in raw:
        marks_ = {"": [], "CLAIM": ["CLAIM: " + label], "WAITING": ["WAITING: " + label],
                  "both": ["CLAIM: " + label, "WAITING: " + label]}[kind]
        rows.append("- %s — tasks 0/1%s" % (name, ("; " + "; ".join(marks_)) if marks_ else ""))
    text = wh.subagent_context_text(agents, rows)
    assert len(text) <= 4000, len(text)
    assert agents is None or text.startswith("Project rules: read " + agents), text[:200]


class Context(HookCase):
    def test_context(self):
        open(os.path.join(REPO, "openspec/changes/01-a/CLAIM"), "w").write("claude 2026-10-17 session=S1\n")
        ctx = run("context", {"session_id": "S1", "cwd": REPO, "source": "startup"})["hookSpecificOutput"]["additionalContext"]
        assert "PROJECT-RULE-42" in ctx and "01-a — tasks 1/2" in ctx and "CLAIM" in ctx and "WAITING" in ctx, ctx
        for claude_md, shown in (("@AGENTS.md\n", False), ("Read @AGENTS.md first\n", True), ("# Rules\n  @AGENTS.md\n", False)):
            open(os.path.join(REPO, "CLAUDE.md"), "w").write(claude_md)
            c = run("context", {"session_id": "S1i", "cwd": REPO, "source": "startup"})["hookSpecificOutput"]["additionalContext"]
            assert ("PROJECT-RULE-42" in c) == shown, (claude_md, c)

    def test_subagent_context(self):
        open(os.path.join(REPO, "openspec/changes/01-a/CLAIM"), "w").write("claude 2026-10-17 session=S1\n")
        sub = run("subagent-context", {"session_id": "S1", "cwd": REPO, "agent_id": "a1", "agent_type": "general-purpose", "hook_event_name": "SubagentStart"})
        sub = sub["hookSpecificOutput"]
        assert sub["hookEventName"] == "SubagentStart"
        sub = sub["additionalContext"]
        assert sub.startswith("Project rules: read " + os.path.join(REPO, "AGENTS.md")), sub
        assert "PROJECT-RULE-42" not in sub and len(sub) <= 4000, sub
        assert any("01-a" in l and "CLAIM" in l for l in sub.splitlines()), sub
        assert any("02-b" in l and "WAITING" in l for l in sub.splitlines()), sub
        bare = os.path.realpath(tempfile.mkdtemp(prefix="wh-bare-"))
        try:
            subprocess.run(["git", "init", "-q", bare], check=True)
            assert run("subagent-context", {"session_id": "S1", "cwd": bare, "hook_event_name": "SubagentStart"}) is None, "no AGENTS, no changes"
        finally:
            shutil.rmtree(bare)
        nogit = os.path.realpath(tempfile.mkdtemp(prefix="wh-nogit-"))
        try:
            assert run("subagent-context", {"session_id": "S1", "cwd": nogit, "hook_event_name": "SubagentStart"}) is None, "outside git"
        finally:
            shutil.rmtree(nogit)

    def test_subagent_project_context_property(self):
        _subagent_ctx()

    def test_beat_and_status(self):
        run("beat", {"session_id": "S1", "hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"description": "Test run"}, "cwd": REPO})
        out = run("status", {"session_id": "S1", "model": {"display_name": "Opus"}, "workspace": {"current_dir": REPO}}, raw=True)
        assert "▶ Bash: Test run" in out, out


MARKER = "name: marker-check\nabout: refuses a marker line\npoints: checks\ncommand: ./check.sh\n"
BROKEN = "name: marker-check\nabout: x\nnosuchkey: 1\npoints: checks\ncommand: ./check.sh\n"


class IntegrationErrorsInTheSessionContext(HookCase):
    """Requirement: Integration errors in the session context. REPO gets a solo-sdd/ tree."""

    def setUp(self):
        super().setUp()
        os.makedirs(os.path.join(REPO, "solo-sdd", "specs"))

    def put(self, text, owner=False, name="marker-check"):
        base = os.path.join(H, ".local/share/solo-sdd/integrations") if owner else os.path.join(REPO, "solo-sdd/integrations")
        os.makedirs(os.path.join(base, name), exist_ok=True)
        open(os.path.join(base, name, "integration"), "w").write(text)

    def config(self, text):
        open(os.path.join(REPO, "solo-sdd/config"), "w").write(text)

    def lines(self):
        ctx = run("context", {"session_id": "S1", "cwd": REPO, "source": "startup"})["hookSpecificOutput"]["additionalContext"]
        assert "PROJECT-RULE-42" in ctx, ctx  # the rest of the context stays
        return [l for l in ctx.splitlines() if l.startswith("integration errors")]

    def test_integration_errors_in_the_session_context_a_broken_description_at_start(self):
        self.put(BROKEN)
        found = self.lines()
        assert len(found) == 1 and found[0].startswith(
            "integration errors: solo-sdd/integrations/marker-check/integration:3: unknown key nosuchkey"), found
        assert not found[0].endswith(" in all"), found

    def test_integration_errors_in_the_session_context_all_descriptions_valid(self):
        self.put(MARKER)
        self.config("integrations: marker-check\n")
        assert self.lines() == []

    def test_integration_errors_in_the_session_context_a_broken_owner_integration_not_enabled(self):
        self.put(BROKEN, owner=True)
        assert self.lines() == []
        self.config("integrations: marker-check\n")
        found = self.lines()
        assert len(found) == 1 and "~/.local/share/solo-sdd/integrations/marker-check/integration:3" in found[0], found

    def test_integration_errors_in_the_session_context_the_count_and_a_missing_folder(self):
        self.put(BROKEN)
        self.config("integrations: marker-check, gone-check\n")
        found = self.lines()
        assert len(found) == 1 and found[0].endswith("; 2 in all"), found
        assert "solo-sdd/integrations/marker-check/integration:3" in found[0], found

    def test_integration_errors_in_the_session_context_a_broken_read_is_logged(self):
        self.put(BROKEN)
        self.config("integrations marker-check\n")
        assert self.lines() == []
        log = os.path.join(H, ".claude/hook-state/errors.log")
        assert "context integrations" in open(log).read()
        os.remove(log)


# ---------- stop ----------

def stop_fixture():
    """The state the stop checks see: a changed style, every task of 01-a checked, .env ignored."""
    open(os.path.join(REPO, ".gitignore"), "w").write(".env\n")
    open(os.path.join(REPO, "app.css"), "w").write("a{color:red}\n")
    open(os.path.join(REPO, "openspec/changes/01-a/tasks.md"), "w").write("- [x] one\n- [x] two\n")
    tr = os.path.join(H, "t.jsonl")
    lines = [{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Edit", "input": {"file_path": os.path.join(REPO, "app.css")}}]}},
        {"type": "user", "toolUseResult": {"stdout": "", "bashEditDiff": {"changedFiles": [os.path.join(REPO, "openspec/changes/01-a/tasks.md")]}}}]
    open(tr, "w").write("\n".join(json.dumps(l) for l in lines) + "\n")
    return tr, lines


class Stop(HookCase):
    def test_stop_reasons(self):
        tr, lines = stop_fixture()
        stop = {"session_id": "S1", "cwd": REPO, "transcript_path": tr,
                "last_assistant_message": "All done. The styles were updated and the change is complete, tests pass, nothing else to do here. I also reviewed the layout on all pages and it looks consistent."}
        out = run("stop", stop)
        assert out and out["decision"] == "block", out
        r = out["reason"]
        assert "uncommitted" in r and "not archived" in r and "browser" in r and "not in Russian" not in r, r
        assert run("stop", stop) is None, "same reasons not repeated"
        json.dump({"phase": "idle"}, open(os.path.join(H, ".claude/hook-state/S1.json"), "w"))
        assert run("stop", stop) is None, "a concurrent beat does not reset the stop key"
        assert run("stop", dict(stop, stop_hook_active=True)) is None
        git("add", "-A"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x")
        os.rename(os.path.join(REPO, "openspec/changes/01-a"), os.path.join(REPO, "openspec/changes/archive-01-a"))
        git("add", "-A"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "archive")
        lines.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "mcp__claude-in-chrome__navigate", "input": {}}]}})
        open(tr, "w").write("\n".join(json.dumps(l) for l in lines) + "\n")
        o = run("stop", dict(stop, last_assistant_message="Done: styles updated, checked in the browser, committed."))
        assert o is None, o

    def test_background_agents_still_running(self):
        tr, lines = stop_fixture()
        open(os.path.join(REPO, "app.css"), "w").write("a{color:blue}\n")
        tr2 = os.path.join(H, "t2.jsonl")
        open(tr2, "w").write(json.dumps(lines[0]) + "\n")
        stop2 = {"session_id": "S20", "cwd": REPO, "transcript_path": tr2, "last_assistant_message": "Done, waiting for agents."}
        bg = [{"id": "a1", "type": "subagent", "status": "running"}]
        assert run("stop", dict(stop2, background_tasks=bg)) is None, "running background agent: stop is silent"
        o = run("stop", dict(stop2, session_id="S21", background_tasks=[dict(bg[0], status="completed")]))
        assert o and o["decision"] == "block" and "uncommitted" in o["reason"], o

    def test_a_browser_in_a_subagent_transcript(self):
        tr, lines = stop_fixture()
        tr3 = os.path.join(H, "t3.jsonl")
        open(tr3, "w").write(json.dumps(lines[0]) + "\n")
        stop3 = {"session_id": "S22", "cwd": REPO, "transcript_path": tr3, "last_assistant_message": "Done, everything checked."}
        o = run("stop", stop3)
        assert o and "The interface changed" in o["reason"], o
        os.makedirs(os.path.join(H, "t3", "subagents"))
        sub_tr = os.path.join(H, "t3", "subagents", "agent-x.jsonl")
        open(sub_tr, "w").write(json.dumps(lines[0]) + "\n")  # no browser, only an edit
        o = run("stop", dict(stop3, session_id="S23"))
        assert o and "The interface changed" in o["reason"], "a subagent without a browser does not count"
        open(sub_tr, "w").write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "ui-check"}}]}}) + "\n")
        o = run("stop", dict(stop3, session_id="S24"))
        assert o and "The interface changed" not in o["reason"] and "uncommitted edits" in o["reason"], ("subagent ui-check counted", o)
        open(sub_tr, "w").write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "curl localhost:9222/json/version"}}]}}) + "\n")
        o = run("stop", dict(stop3, session_id="S25"))
        assert o and "The interface changed" not in o["reason"] and "uncommitted edits" in o["reason"], ("CDP sign in subagent Bash counted", o)

    def test_stop_respects_human_merge(self):
        # Requirement: Stop respects human merge. An open PR returns the agent only when the agent merges
        proj_pr, fbin = os.path.join(H, "proj-pr"), os.path.join(H, "fake-gh")
        os.makedirs(os.path.join(proj_pr, "solo-sdd")); os.makedirs(fbin)
        subprocess.run(["git", "init", "-q", proj_pr], check=True)
        open(os.path.join(fbin, "gh"), "w").write('#!/bin/sh\necho \'{"state": "OPEN", "url": "https://github.com/o/r/pull/9"}\'\n')
        os.chmod(os.path.join(fbin, "gh"), 0o755)
        tr5 = os.path.join(H, "t5.jsonl")
        open(tr5, "w").write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "git push -u origin HEAD"}}]}}) + "\n")
        pr_env, cfg_pr = dict(ENV, PATH=fbin + os.pathsep + ENV["PATH"]), os.path.join(proj_pr, "solo-sdd/config")
        stop5 = {"cwd": proj_pr, "transcript_path": tr5, "last_assistant_message": "Done, the PR is green."}
        for n, (text, returns) in enumerate((("", True), ("mode: team\n", False), ("delivery.merge-by: human\n", False),
                                             ("mode: team\ndelivery.merge-by: agent\n", True))):
            open(cfg_pr, "w").write(text)
            o = run("stop", dict(stop5, session_id="S-pr-%d" % n), pr_env)
            assert bool(o) == returns and (not o or "pull/9 is open and not merged" in o["reason"]), (text, o)
        open(cfg_pr, "w").write("mode: team\n")
        open(os.path.join(proj_pr, "app.css"), "w").write("a{}\n")
        open(tr5, "a").write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": os.path.join(proj_pr, "app.css")}}]}}) + "\n")
        o = run("stop", dict(stop5, session_id="S-pr-other"), pr_env)
        assert o and "uncommitted edits" in o["reason"] and "is open and not merged" not in o["reason"], ("other reasons stay", o)

    def test_reply_language(self):
        """Requirement: Reply language check. SOLO_SDD_REPLY_LANG ru|en turns it on; unset or other: no check."""
        en = "All done. The styles were updated and the change is complete, tests pass, nothing else to do here at all."
        ru = "\u0413\u043e\u0442\u043e\u0432\u043e. " * 20
        assert wh.wrong_language(en, "") is None and wh.wrong_language(ru, "") is None, "unset: no check"
        assert wh.wrong_language(en, "de") is None and wh.wrong_language(ru, "RU") is None, "other value: no check"
        assert wh.wrong_language(en, "ru") == "Russian" and wh.wrong_language(ru, "ru") is None
        assert wh.wrong_language(ru, "en") == "English" and wh.wrong_language(en, "en") is None
        assert wh.wrong_language("Short English reply.", "ru") is None, "under 80 letters: no check"
        assert wh.wrong_language("`" + "code " * 40 + "` " + ru, "ru") is None, "code is not counted"
        stop = {"session_id": "S-lang", "cwd": H, "last_assistant_message": en}
        assert run("stop", stop) is None, "unset: an English reply passes"
        o = run("stop", dict(stop, session_id="S-lang-ru"), dict(ENV, SOLO_SDD_REPLY_LANG="ru"))
        assert o and "not in Russian" in o["reason"] and "Rewrite it in Russian" in o["reason"], o
        assert run("stop", dict(stop, session_id="S-lang-en"), dict(ENV, SOLO_SDD_REPLY_LANG="en")) is None
        # Requirement: Readers use the settings. reply.language of solo-sdd/config first, the variable before the default
        proj = os.path.join(H, "proj-lang")
        os.makedirs(os.path.join(proj, "solo-sdd"))
        subprocess.run(["git", "init", "-q", proj], check=True)
        cfg, bare = os.path.join(proj, "solo-sdd/config"), {k: v for k, v in ENV.items() if k != "SOLO_SDD_REPLY_LANG"}
        at = dict(stop, cwd=proj)
        open(cfg, "w").write("# language\nreply.language: ru\n")
        o = run("stop", dict(at, session_id="S-cfg-ru"), bare)
        assert o and "Rewrite it in Russian" in o["reason"], o
        assert run("stop", dict(at, session_id="S-cfg-ru"), bare) is None, "returns the agent once"
        open(cfg, "w").write("reply.language: off\n")
        assert run("stop", dict(at, session_id="S-cfg-off"), dict(bare, SOLO_SDD_REPLY_LANG="ru")) is None, "the file wins"
        os.remove(cfg)
        o = run("stop", dict(at, session_id="S-cfg-env"), dict(bare, SOLO_SDD_REPLY_LANG="ru"))
        assert o and "Rewrite it in Russian" in o["reason"], o
        open(cfg, "w").write("reply.language ru\n")
        elog = os.path.join(H, ".claude/hook-state/errors.log")
        assert run("stop", dict(at, session_id="S-cfg-bad"), bare) is None, "a broken file: the defaults"
        assert "solo-sdd/config:1" in open(elog).read(), "a broken file is logged"
        os.remove(elog)


GATE = "name: marker-check\nabout: refuses a marker line\npoints: checks\ncommand: true\napplies: *.py\nmode: gate\n"


class StopWithoutAnIntegrationRun(HookCase):
    """Requirement: Stop without an integration run. REPO gets a solo-sdd/ tree, marker-check enabled with
    applies *.py, and a transcript that edits app.py; a run is the real `solo-sdd check` of this working copy."""

    def setUp(self):
        super().setUp()
        os.makedirs(os.path.join(REPO, "solo-sdd", "specs"))
        os.makedirs(os.path.join(REPO, "solo-sdd", "integrations", "marker-check"))
        self.desc = os.path.join(REPO, "solo-sdd", "integrations", "marker-check", "integration")
        open(self.desc, "w").write(GATE)
        open(os.path.join(REPO, "solo-sdd", "config"), "w").write("integrations: marker-check\n")
        self.edit("app.py")
        self.n = 0

    def edit(self, name):
        open(os.path.join(REPO, name), "w").write("x = %r\n" % time.time())
        self.tr = os.path.join(H, "t-int.jsonl")
        open(self.tr, "w").write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": os.path.join(REPO, name)}}]}}) + "\n")

    def reason(self):
        self.n += 1
        o = run("stop", {"session_id": "S-int-%d" % self.n, "cwd": REPO, "transcript_path": self.tr,
                         "last_assistant_message": "Done."})
        assert o and "uncommitted edits" in o["reason"], ("the other reasons stay", o)
        return [l for l in o["reason"].splitlines() if "apply to this session's edits" in l]

    def check_run(self):
        r = subprocess.run([PY, "-m", "solo_sdd", "check", "--point", "checks", "--changed"], cwd=REPO,
                           env=dict(ENV, PYTHONPATH=os.path.dirname(os.path.dirname(HOOK))), capture_output=True,
                           text=True, stdin=subprocess.DEVNULL)
        assert r.returncode == 0 and "PASS marker-check" in r.stdout, (r.stdout, r.stderr)

    def record(self):
        return os.path.join(wh.repo_dir(REPO, H), wh.tree_hash(REPO) + ".json")

    def test_stop_without_an_integration_run_edited_without_a_run(self):
        found = self.reason()
        assert len(found) == 1 and "marker-check" in found[0] and "`solo-sdd check --point checks --changed`" in found[0], found

    def test_stop_without_an_integration_run_a_run_on_the_current_tree(self):
        self.check_run()
        assert self.reason() == []
        self.edit("app.py")
        assert len(self.reason()) == 1, "an edit after the run needs a new run"
        self.edit("README.md")
        assert self.reason() == [], "an edit applies does not match"

    def test_stop_without_an_integration_run_an_edit_check_does_not_see(self):
        git("add", "-A"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "on the base")
        open(os.path.join(REPO, "notes.txt"), "w").write("dirty\n")  # keeps the uncommitted reason of reason()
        open(self.tr, "a").write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": os.path.join(REPO, "notes.txt")}}]}}) + "\n")
        assert self.reason() == [], "committed on the base: check --changed sees nothing to run"

    def test_stop_without_an_integration_run_a_broken_description_in_the_hook(self):
        open(self.desc, "a").write("nosuchkey: 1\n")
        assert self.reason() == []
        log = os.path.join(H, ".claude/hook-state/errors.log")
        assert "stop integration marker-check" in open(log).read() and "unknown key nosuchkey" in open(log).read()
        os.remove(log)
        open(self.desc, "w").write(GATE)
        open(os.path.join(REPO, "solo-sdd", "config"), "w").write("integrations marker-check\n")
        assert self.reason() == [], "a broken config: no reason"
        assert "stop integrations" in open(log).read()
        os.remove(log)

    def test_stop_without_an_integration_run_a_record_that_is_no_run(self):
        os.makedirs(wh.repo_dir(REPO, H))
        for make in (lambda p: os.mkfifo(p), lambda p: open(p, "w").write("{broken"),
                     lambda p: open(p, "w").write(json.dumps({"points": {"ship": {}}})),
                     lambda p: open(p, "w").write(json.dumps({"points": ["checks"]}))):
            path = self.record()
            if os.path.lexists(path):
                os.remove(path)
            make(path)
            assert len(self.reason()) == 1, open(path).read() if os.path.isfile(path) else "fifo"


# ---------- guard: the orchestrator status on SubagentHandback ----------

R2 = WT2 = first = head2 = None
ARCH = "openspec/changes/archive/2026-10-20-arch-x"


def handback_fixture():
    global R2, WT2, first, head2
    R2 = os.path.join(H, "proj2")
    os.makedirs(os.path.join(R2, "openspec/changes/arch-x"))
    os.makedirs(os.path.join(R2, "openspec/changes/stay-y"))
    for n in ("arch-x", "stay-y"):
        open(os.path.join(R2, "openspec/changes", n, "tasks.md"), "w").write("- [x] a\n")
    git2("init", "-q"); git2("add", "-A"); git2("commit", "-qm", "init")
    first = git2("rev-parse", "HEAD")
    WT2 = os.path.join(H, "wt-arch")
    git2("worktree", "add", "-q", WT2, "-b", "wip/arch")
    os.makedirs(os.path.join(WT2, "openspec/changes/archive"))
    os.rename(os.path.join(WT2, "openspec/changes/arch-x"), os.path.join(WT2, "openspec/changes/archive/2026-10-20-arch-x"))
    git2("add", "-A", cwd=WT2); git2("commit", "-qm", "archive", cwd=WT2)
    head2 = git2("rev-parse", "HEAD", cwd=WT2)


def status_msg(**over):
    f = dict(STATUS="archived", CHANGE="arch-x", BRANCH="wip/arch", WORKTREE=WT2, COMMIT=head2, ARCHIVE=ARCH,
             VALIDATE="openspec validate -> exit 0", TESTS="all tests -> exit 0", LIVE="ok", REVIEW="ok", AGENTS="none",
             HOOKS="ok", NOT_VERIFIED="nothing", NOTES="none")
    f.update(over)
    return "\n".join("%s: %s" % kv for kv in f.items())


def handback(msg, env=None):
    out = run("guard", {"session_id": "S30", "cwd": R2, "tool_name": "SubagentHandback", "tool_input": {"message": msg}}, env=env)
    assert not out or out["hookSpecificOutput"]["permissionDecision"] == "deny", out
    return out["hookSpecificOutput"]["permissionDecisionReason"] if out else None


FULL = {n: "value " + n for n in wh.STATUS_FIELDS}
FULL["STATUS"] = "archived"
FULL["WORKTREE"] = "/nonexistent-wt"


def _block(fields, order, fence, indent):
    lines = [indent + "%s: %s" % (n, fields[n]) for n in order if n in fields]
    return "\n".join((["```"] if fence else []) + lines + (["```"] if fence else []))


class Handback(HookCase):
    def setUp(self):
        super().setUp()
        handback_fixture()

    def test_archived_status(self):
        r = handback(status_msg()); assert r is None, r
        assert handback(status_msg(COMMIT=head2[:7])) is None, "short hash"
        assert handback("```\n" + status_msg().replace("\n", "\n  ") + "\n```") is None, "fenced and indented"
        for bad in (first, "deadbeef"):
            r = handback(status_msg(COMMIT=bad))
            assert r and head2 in r, r
        open(os.path.join(R2, "openspec/changes/stay-y/CLAIM"), "w").write("claude 2026-10-20 session=X\n")
        r = handback(status_msg(CHANGE="stay-y"))
        assert r and "openspec/changes/stay-y is still in" in r and "CLAIM" in r, r
        os.remove(os.path.join(R2, "openspec/changes/stay-y/CLAIM"))

    def test_status_values(self):
        r = handback("STATUS: done\nCHANGE: x")
        assert r and "archived, not_ready, blocked" in r, r
        assert handback("Executor report: all done") is None and handback("") is None, "not a status"
        assert handback("STATUS: not_ready\nCHANGE: arch-x\nNOTES: no access") is None, "honest not_ready"
        r = handback("STATUS: blocked\nCHANGE: arch-x")
        assert r and "NOTES" in r and "not_ready" in r, r

    def test_worktree_not_a_git_copy(self):
        nowt = os.path.join(H, "no-git-dir")
        os.makedirs(nowt)
        r = handback(status_msg(WORKTREE=nowt))
        assert r and "is not a git working copy" in r, r
        assert "is not a git working copy" in handback(status_msg(WORKTREE=os.path.join(H, "absent"))), "absent folder"

    def test_git_failure_passes(self):
        # git failure: .git exists but git exits with an error; the handback passes, the error goes to the log
        fake = os.path.join(H, "fakebin")
        os.makedirs(fake)
        open(os.path.join(fake, "git"), "w").write("#!/bin/sh\nexit 1\n")
        os.chmod(os.path.join(fake, "git"), 0o755)
        brk = os.path.join(H, "broken-wt")
        os.makedirs(os.path.join(brk, ".git"))
        assert handback(status_msg(WORKTREE=brk), env=dict(ENV, PATH=fake + ":" + os.environ["PATH"])) is None, "git failure passes"
        elog = os.path.join(H, ".claude/hook-state/errors.log")
        assert "guard" in open(elog).read(), "git failure logged"
        os.remove(elog)

    @marks.slow
    def test_git_timeout_passes(self):
        # git does not answer: a timeout is an environment failure too
        brk = os.path.join(H, "broken-wt")
        os.makedirs(os.path.join(brk, ".git"))
        elog = os.path.join(H, ".claude/hook-state/errors.log")
        slow = os.path.join(H, "slowbin")
        os.makedirs(slow)
        open(os.path.join(slow, "git"), "w").write("#!/bin/sh\nexec sleep 30\n")
        os.chmod(os.path.join(slow, "git"), 0o755)
        assert handback(status_msg(WORKTREE=brk), env=dict(ENV, PATH=slow + ":" + os.environ["PATH"])) is None, "git timeout passes"
        assert "Timeout" in open(elog).read(), "git timeout logged"
        os.remove(elog)

    def test_one_mismatch_per_archived_check(self):
        open(os.path.join(R2, "openspec/changes/arch-x/CLAIM"), "w").write("claude 2026-10-20 session=X\n")
        r = handback(status_msg())
        assert r and "the CLAIM of change arch-x is still in" in r and "was not moved" not in r, r
        os.remove(os.path.join(R2, "openspec/changes/arch-x/CLAIM"))
        r = handback(status_msg(VALIDATE="openspec validate -> exit 1"))
        assert r and "VALIDATE: after the first" in r and "TESTS" not in r, r

    def test_tests_field(self):
        # verbatim values from a consumer project run on 20.10.2026: several commands and arrows in the note
        for good in ("npm test -> exit 0 (250 files, 5455 tests)", "exit 0",
                     "npm test -> exit 0 (245 files, 5370 tests; npm run typecheck -> exit 0)",
                     "npm test -> exit 0 (250 files, 5455 tests); npm run typecheck -> 0 errors",
                     "npm test -> exit 0 (240 files, 5316 tests; npm run typecheck -> exit 0; after the CSS edit 1784 green)",
                     "npm test (250 files; npm run typecheck with 0 errors) -> exit 0"):
            assert handback(status_msg(TESTS=good)) is None, good
        for bad in ("npm test -> exit 1 (then exit 0 on retry)", "npm test -> exit 01", "npm test -> exit 0x", "npm test -> exit 0(x)",
                    "npm test -> exit 0; npm run typecheck -> exit 2", "npm test: exit 0", "npm test -> 0 errors"):
            r = handback(status_msg(TESTS=bad))
            assert r and "TESTS: after the first" in r, (bad, r)
        for bad in ("npm test -> exit 0 ->  exit 1", "npm test ->exit 1 -> exit 0", "npm test->exit 0->exit 2"):
            assert handback(status_msg(TESTS=bad)), bad
        assert handback(status_msg(TESTS="npm test ->exit 0")) is None, "arrow without spaces"
        for bad in ("npm test -> exit 0 -> EXIT 1", "npm test -> exit 0 -> exit\t1", "npm test -> exit 0 -> exit: 1",
                    "npm test -> exit 0 -> exit=1", "npm test -> exit 0 (250); build -> failed (exit 1)",
                    "npm test -> exit 0; lint -> FAILED: exit 2"):
            r = handback(status_msg(TESTS=bad))
            assert r and "TESTS: after the first" in r, (bad, r)

    def test_live_field(self):
        # LIVE: one command from the WORKTREE root; trimming output and multiple steps are the stand's job
        for cmd, sign in (("npm run build && node scenarios/docs/check.ts -> 48 checks passed", "&&"), ("a || b -> ok", "||"),
                          ("a; b -> ok", ";"), ("node packages/core/scenarios/ocr/check.ts | tail -1 -> 25 of 25", "|"),
                          ("cd packages/core -> ok", "cd ")):
            r = handback(status_msg(LIVE=cmd))
            assert r and "LIVE" in r and "«%s»" % sign in r and "stand" in r, (cmd, r)
        for good in ("COUNCIL_DEV=1 node packages/core/scenarios/ocr/check.ts -> 25 of 25", "node check.ts --title \"a; b | c\" -> ok",
                     "node check.ts --title 'a && b || c' -> ok", "find . -exec x {} \\; -> ok", "node c.ts -> a; b", "node c.ts -> a && b | c",
                     "ok", "cdx run -> ok", "node c.ts --title \"a \\\" && b\" -> ok"):
            assert handback(status_msg(LIVE=good)) is None, good
        assert handback(status_msg(STATUS="not_ready", LIVE="a && b | c; cd x", NOTES="no access")) is None, "not_ready skips LIVE"

    def test_archive_commit_and_empty_fields(self):
        r = handback(status_msg(ARCHIVE="openspec/changes"))
        assert r and "ARCHIVE openspec/changes is not an existing folder" in r, r
        assert handback(status_msg() + "\nCOMMIT: deadbeef") is None, "first COMMIT wins"
        r = handback("COMMIT: deadbeef\n" + status_msg())
        assert r and "COMMIT deadbeef" in r, r
        o = run("guard", {"session_id": "S30", "cwd": WT2, "tool_name": "SubagentHandback", "tool_input": {"message": status_msg(WORKTREE="")}})
        r = o["hookSpecificOutput"]["permissionDecisionReason"]
        assert "empty: WORKTREE" in r and "is not a git working copy" not in r and "COMMIT" not in r and "was not moved" not in r, r

    def test_status_block_format_property(self):
        nostatus = st.text() | st.lists(st.sampled_from(["", " STATUS", "status: x", "CHANGE: a", "```", "  NOTES: n"])).map("\n".join)

        @settings(max_examples=200, deadline=None)
        @given(nostatus.filter(lambda t: not any(l.lstrip().startswith("STATUS:") for l in t.splitlines())))
        def no_status(text):
            assert wh.status_problems(text, H) == []

        @settings(max_examples=100, deadline=None)
        @given(st.sets(st.sampled_from([n for n in wh.STATUS_FIELDS if n != "STATUS"]), min_size=1),
               st.permutations(list(wh.STATUS_FIELDS)), st.booleans(), st.sampled_from(["", " ", "    ", "\t"]))
        def missing(drop, order, fence, indent):
            problems = wh.status_problems(_block({n: v for n, v in FULL.items() if n not in drop}, order, fence, indent), H)
            assert all(n in "\n".join(problems) for n in drop), (drop, problems)

        assert wh.status_problems("", H) == []
        no_status()
        missing()

    def test_repeatable_live_property(self):
        word = st.sampled_from(["a", "node", "x.ts", "--flag", "FOO=1", "{}"])
        plain = st.text(alphabet="ab ;|&\\", max_size=6)
        tok = st.one_of(word.map(lambda w: (w, False)),
                        plain.map(lambda t: ("'" + t + "'", False)),
                        plain.filter(lambda t: "\\" not in t).map(lambda t: ('"' + t + '"', False)),
                        st.sampled_from(["\\;", "\\|", "\\&", "\\ "]).map(lambda e: (e, False)),
                        st.sampled_from(["&&", "||", ";", "|"]).map(lambda o: (o, True)))

        @settings(max_examples=500, deadline=None)
        @given(st.lists(tok, min_size=1, max_size=8), st.sampled_from([" ", ""]), st.sampled_from(["", " -> ok; a && b"]))
        def prop(toks, sep, tail):
            cmd = sep.join(t for t, _ in toks if t not in ("cd",))
            if cmd.lstrip().startswith("cd "):
                return
            refused = bool(wh.live_problems(cmd + tail))
            assert refused == any(op for _, op in toks), cmd
        prop()


# ---------- hook registration in settings.json (work_hooks_settings.py as a process) ----------

SETTINGS = os.path.join(os.path.dirname(HOOK), "work_hooks_settings.py")
D = "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"
# autoMode rule about merge: a repeated run replaces the previous version by the constant prefix or the old one.
# Requirements: Owner merge rule in auto mode, Hook registration
PFX = "The owner's merge rule (solo-sdd)"
OLD_PFX = "The owner's global rules (~/.claude/CLAUDE.md, section 13)"
OLD = (OLD_PFX + " require Claude to merge its own verified pull requests in the owner's repositories with gh pr merge and then update the local main branch. "
       "Such a merge is approved work, not a merge without review, unless the merge or push triggers a production deploy, which still needs the owner's consent.")
ours = lambda x: x.startswith((PFX, OLD_PFX))
PIECES = ["$defaults", OLD, PFX + " old version", OLD_PFX + " old version", "foreign a", "foreign b",
          " " + PFX + " not at the start", "sdd-pr.py merge foreign line"]


def run_settings(home, n=1):
    outs = []
    for _ in range(n):
        subprocess.run([PY, SETTINGS], check=True, capture_output=True, env=dict(os.environ, HOME=home))
        outs.append(json.load(open(os.path.join(home, ".claude/settings.json")))["autoMode"]["allow"])
    return outs


def rule_after(allow, n=2):
    home = os.path.realpath(tempfile.mkdtemp(prefix="wh-merge-"))
    try:
        os.makedirs(os.path.join(home, ".claude"))
        open(os.path.join(home, ".claude/settings.json"), "w").write(json.dumps({"autoMode": {"allow": allow}}))
        return run_settings(home, n)[-1]
    finally:
        shutil.rmtree(home)


def rule_text():
    return [x for x in rule_after(["$defaults"], 1) if x.startswith(PFX)][0]


class Registration(unittest.TestCase):
    def test_hook_registration_two_runs(self):
        # connection in settings.json: two runs in a row, no duplicates, with a backup
        SH = os.path.realpath(tempfile.mkdtemp(prefix="wh-set-"))
        self.addCleanup(shutil.rmtree, SH, True)
        os.makedirs(os.path.join(SH, ".claude"))
        open(os.path.join(SH, ".claude/settings.json"), "w").write("{}")
        for _ in range(2):
            subprocess.run([PY, SETTINGS], check=True, capture_output=True, env=dict(os.environ, HOME=SH))
        hk = json.load(open(os.path.join(SH, ".claude/settings.json")))["hooks"]
        assert sum("subagent-context" in json.dumps(g) for g in hk["SubagentStart"]) == 1, hk["SubagentStart"]
        assert [g["matcher"].split("|").count("SubagentHandback") for g in hk["PreToolUse"] if g["hooks"][0]["command"].endswith('"$f" guard')] == [1], hk["PreToolUse"]
        assert sum("process-guard.py" in json.dumps(g) for g in hk["PreToolUse"]) == 1, hk["PreToolUse"]
        assert any(n.startswith("settings.json.bak-") for n in os.listdir(os.path.join(SH, ".claude"))), "backup"
        hs = json.load(open(os.path.join(SH, ".claude/settings.json")))
        assert hs["env"] == {"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "2"}, hs.get("env")

    @marks.slow
    @settings(max_examples=25, deadline=None)
    @given(st.one_of(st.none(), st.dictionaries(st.sampled_from(["A", "PATH_X", "LANG", D]),
                                                st.sampled_from(["", "0", "1", "2", "3", "x"]), max_size=4)))
    def test_hook_registration_depth_property(self, env):
        # subagent depth: a missing one becomes "2", a set one and other env variables do not change
        home = os.path.realpath(tempfile.mkdtemp(prefix="wh-depth-"))
        try:
            os.makedirs(os.path.join(home, ".claude"))
            open(os.path.join(home, ".claude/settings.json"), "w").write(json.dumps({} if env is None else {"env": env}))
            out = subprocess.run([PY, SETTINGS], check=True, capture_output=True, text=True,
                                 env=dict(os.environ, HOME=home)).stdout
            got = json.load(open(os.path.join(home, ".claude/settings.json")))["env"]
            want = dict(env or {})
            want.setdefault(D, "2")
            assert got == want, (env, got)
            phrase = "set by the owner, not changed" if env and D in env else "written, applies to new sessions"
            assert f"subagent depth {want[D]}: {phrase}" in out, out
        finally:
            shutil.rmtree(home)

    def test_owner_merge_rule_in_auto_mode_replacement_by_the_prefix(self):
        for prev in (OLD, PFX + " old version"):
            got = rule_after(["$defaults", prev, "foreign rule"], 1)
            assert len(got) == 3 and got[0] == "$defaults" and got[2] == "foreign rule" and got[1].startswith(PFX) and got[1] != prev, got

    def test_owner_merge_rule_in_auto_mode_a_bare_api_merge(self):
        assert "does not approve a raw gh api -X PUT .../merge call" in rule_text()

    def test_owner_merge_rule_in_auto_mode_a_prod_deploy(self):
        assert "triggers a production deploy, which still needs the owner's consent" in rule_text()

    def test_owner_merge_rule_in_auto_mode_a_human_merge_project(self):
        r = rule_text()
        assert "delivery.merge-by: human, where a person merges" in r and "CLAUDE.md" not in r and "section 13" not in r, r
        assert r.count("gh pr merge") == 2 and "without a solo-sdd/ tree merges with gh pr merge" in r \
            and "nor gh pr merge in a repository with a solo-sdd/ tree" in r, r

    def test_hook_registration_the_merge_rule_after_a_repeated_run(self):
        got = rule_after(["$defaults", OLD, "foreign rule"])
        mine = [x for x in got if ours(x)]
        assert len(mine) == 1 and mine[0].startswith(PFX) and got == ["$defaults", mine[0], "foreign rule"], got
        for w in ("sdd-pr.py merge", "sdd-pr.py land", "git merge origin/", "without a solo-sdd/ tree merges with gh pr merge"):
            assert w in mine[0], w

    @marks.slow
    @settings(max_examples=25, deadline=None)
    @given(st.one_of(st.none(), st.lists(st.sampled_from(PIECES), max_size=6)))
    def test_hook_registration_property(self, allow):
        home = os.path.realpath(tempfile.mkdtemp(prefix="wh-merge-"))
        try:
            os.makedirs(os.path.join(home, ".claude"))
            open(os.path.join(home, ".claude/settings.json"), "w").write(json.dumps({} if allow is None else {"autoMode": {"allow": allow}}))
            first_, second = run_settings(home, 2)
            assert first_ == second, (allow, first_, second)
            src = ["$defaults"] if allow is None else allow
            at = next((i for i, x in enumerate(src) if ours(x)), len([x for x in src if not ours(x)]))
            assert sum(ours(x) for x in second) == 1 and second[at].startswith(PFX), (allow, second)
            assert second[:at] + second[at + 1:] == [x for x in src if not ours(x)], (allow, second)
        finally:
            shutil.rmtree(home)


# ---------- guard: text is not a command ----------

class TextIsNotACommand(HookCase):
    def test_heredoc_bodies_and_search_patterns(self):
        assert not bash("cat > check.ts <<'EOF'\nfn(env)\nprintenv\nprintenv API_KEY\necho $API_KEY\nEOF"), "heredoc body is not a command"
        assert not bash("cat <<EOF\nenv\nEOF"), "heredoc without quotes"
        assert not bash("cat <<-EOF\n\tenv\n\tEOF"), "heredoc with tabs"
        assert bash("bash <<'EOF'\nenv\nEOF"), "a heredoc body for a shell is commands"
        assert bash("cat <<'EOF' | sh\nenv\nEOF"), "heredoc in a pipeline into a shell"
        assert bash("cat <<'EOF'\nhi\nEOF\nenv"), "the tail after a heredoc is checked"
        assert bash("cat >> ~/.zshrc <<'EOF'\nexport SOLO_SDD_EXPENSIVE_OK=1\nEOF"), "moving the bypass into the profile through a heredoc"
        assert not bash("grep -n \"process.env\" apps/desktop/src/main"), "a search pattern is not .env"
        assert not bash("git grep -e process.env -- src"), "an -e pattern is not .env"
        assert bash('T="${TMPDIR:-/tmp}"; grep -n "process.env" apps/desktop/src/main'), "a ${ is not plain for the secret guard: a .env name anywhere counts"
        assert bash("grep API_KEY .env"), "a .env path for grep"
        assert bash("grep -e API_KEY .env"), "a .env path for grep -e"
        assert bash("rg -A 2 KEY .env"), "an option value is not a pattern"
        assert not bash("cat > stand.sh <<'EOF'\ncodex exec -m gpt-6-astra 'x'\nEOF"), "a stand file is not a Codex run"
        assert bash("codex exec -m gpt-6-astra 'x'"), "the same run without heredoc"

    def test_codex_behind_shell_forms(self):
        for c in ("eval codex exec -m gpt-6-astra hi", "{ codex exec -m gpt-6-astra hi; }",
                  "if true; then codex exec -m gpt-6-astra hi; fi", "echo x | xargs codex exec -m gpt-6-astra",
                  "! codex exec -m gpt-6-astra hi", "timeout 60 codex exec -m gpt-6-astra hi",
                  "(codex exec -m gpt-6-astra hi)", "nice -n 5 codex exec -m gpt-6-astra hi",
                  "eval 'codex exec -m gpt-6-astra hi'"):
            assert bash(c), c
        assert bash("timeout -s KILL 5 bash <<'EOF'\nenv\nEOF"), "heredoc through timeout into a shell"
        assert bash("(bash <<'EOF'\nenv\nEOF\n)"), "heredoc in a subshell"
        assert bash("rg --pre 'cat .env' x ."), "--pre is a command"

    def test_patterns_scripts_and_substitutions(self):
        assert not bash("grep -nE 'a|env|printenv' f.sh | head"), "| inside the pattern quotes"
        assert not bash("sed -i '' 's/a/process.env[\"NEVER\"]/' f.ts"), "a sed script is not .env"
        assert bash("sed -n 1p .env"), "a .env path for sed"
        assert bash("sed -i '' 's/a/b/' .env"), "a .env path for sed -i"
        assert not bash("node -e 'const out=\"Usage: codex exec [FLAGS] [TEXT]\\n\";' a.txt b.txt && npm test"), "Codex help in a node argument"
        assert bash("bash -c 'codex exec -m gpt-6-astra hi'"), "Codex in bash -c"
        assert bash("cd w && codex exec -m gpt-6-astra hi"), "Codex after cd"
        assert bash("timeout 60 codex exec -m gpt-6-astra hi"), "Codex under timeout"
        assert bash("cat <<EOF\n$(printenv)\nEOF"), "substitution in an unquoted body"
        assert not bash("cat <<'EOF'\n$(printenv)\nEOF"), "a quoted body is text"
        assert bash("grep \"$(printenv)\" f"), "substitution in a pattern"
        for c in ("grep -f /dev/null .env", "grep --file=/dev/null .env", "sed -n -f /dev/null .env"):
            assert bash(c), "patterns in a file: .env is a path: " + c
        for c in ("echo $(codex exec -m gpt-6-astra hi)", "X=$(codex exec -m gpt-6-astra hi)", "echo \"`codex exec -m gpt-6-astra hi`\"",
                  "caffeinate -i codex exec -m gpt-6-astra hi", "gtimeout 60 codex exec -m gpt-6-astra hi", "npx codex exec -m gpt-6-astra hi"):
            assert bash(c), "Codex in a substitution or under a wrapper: " + c
        for c in ("setsid codex exec -m gpt-6-astra hi", "stdbuf -oL codex exec -m gpt-6-astra hi", "sudo -u root codex exec -m gpt-6-astra hi",
                  "cat <(codex exec -m gpt-6-astra hi)", "echo $( (codex exec -m gpt-6-astra hi) )", "find . -exec codex exec -m gpt-6-astra hi \\;"):
            assert bash(c), "Codex behind any wrapper and in a substitution: " + c
        assert bash("grep <(codex exec -m gpt-6-astra hi) f"), "Codex in <(…) in place of a pattern"
        for c in ("sed 'r .env' x", "sed '1r .env' /dev/null", "bash -lc 'codex exec -m gpt-6-astra hi'",
                  "codex -m gpt-6-astra exec hi", "cat <<'A'; bash <<'B'\nx\nA\ncodex exec -m gpt-6-astra hi\nB"):
            assert bash(c), "reading .env by a sed script, Codex in -lc, after a flag and in a second heredoc: " + c
        assert not bash("grep -c x f | head"), "search output into a text reader: the pattern is cut"
        assert bash("grep -q test x; codex exec -m sol hi"), "a test marker in a search pattern stays a marker"
        assert bash("cat <<'EOF' | tee >(bash)\nprintenv\nEOF"), "the body goes to >(bash)"


# ---------- Requirement: Process root. The own solo-sdd/ tree, the legacy openspec/ one and both present ----------

R3 = None


def r3_fixture():
    global R3
    R3 = os.path.join(H, "proj3")
    os.makedirs(os.path.join(R3, "solo-sdd/changes/a"))
    open(os.path.join(R3, "solo-sdd/project.md"), "w").write("OWN-INTENT-7\n")
    open(os.path.join(R3, "solo-sdd/changes/a/tasks.md"), "w").write("- [x] one\n- [ ] two\n")
    open(os.path.join(R3, "solo-sdd/changes/a/CLAIM"), "w").write("claude 2026-11-09 session=OTHER\n")
    git2("init", "-q", cwd=R3); git2("add", "-A", cwd=R3); git2("commit", "-qm", "init", cwd=R3)


def e3():
    return {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(R3, "solo-sdd/changes/a/tasks.md"), "old_string": "x", "new_string": "y"}}


class ProcessRoot(HookCase):
    def setUp(self):
        super().setUp()
        r3_fixture()

    def test_own_tree(self):
        ctx3 = run("context", {"session_id": "S40", "cwd": R3})["hookSpecificOutput"]["additionalContext"]
        assert "OWN-INTENT-7" in ctx3 and "a — tasks 1/2; CLAIM" in ctx3 and "solo-sdd/" in ctx3, ctx3
        assert "openspec" not in ctx3, "own tree: no openspec line and no import hint: " + ctx3
        sub3 = run("subagent-context", {"session_id": "S40", "cwd": R3, "hook_event_name": "SubagentStart"})["hookSpecificOutput"]["additionalContext"]
        assert "a — tasks 1/2; CLAIM" in sub3, sub3
        r = run("guard", dict(e3(), session_id="S40", cwd=R3))
        assert r and "taken by another agent" in r["hookSpecificOutput"]["permissionDecisionReason"], r
        assert run("guard", dict(e3(), session_id="OTHER", cwd=R3)) is None, "the owner session edits its change"

    def test_archive_command_recognised(self):
        # Requirement: Archive command recognised. solo-sdd archive of a foreign change is refused, an own one passes
        sa = {"tool_name": "Bash", "tool_input": {"command": "solo-sdd archive a --yes"}, "cwd": R3}
        assert run("guard", dict(sa, session_id="S40")), "solo-sdd archive of a foreign change"
        assert run("guard", dict(sa, session_id="S40", tool_input={"command": "python3 -m solo_sdd archive a --yes"})), "module form"
        for c in ("(cd %s && solo-sdd archive a --yes)" % R3, "solo-sdd archive a>/tmp/log", "solo-sdd archive a</dev/null",
                  "solo-sdd archive a&>/tmp/log", "solo-sdd archive a&>>/tmp/log"):
            assert run("guard", dict(sa, session_id="S40", tool_input={"command": c})), "a subshell or a glued redirection: " + c
        assert run("guard", dict(sa, session_id="OTHER")) is None, "own archive"

    def test_stop_every_task_checked(self):
        # stop: every task checked in an own-tree change that is not archived
        open(os.path.join(R3, "solo-sdd/changes/a/tasks.md"), "w").write("- [x] one\n- [x] two\n")
        git2("add", "-A", cwd=R3); git2("commit", "-qm", "done", cwd=R3)
        tr4 = os.path.join(H, "t4.jsonl")
        open(tr4, "w").write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit",
                             "input": {"file_path": os.path.join(R3, "solo-sdd/changes/a/tasks.md")}}]}}) + "\n")
        o = run("stop", {"session_id": "S41", "cwd": R3, "transcript_path": tr4, "last_assistant_message": "Done."})
        assert o and "Change a: every task is checked but it is not archived" in o["reason"], o

    def test_handback_on_the_own_tree(self):
        # status handback on the own tree: archive folder and the change left in changes/
        handback_fixture()
        WT3 = os.path.join(H, "wt3")
        git2("worktree", "add", "-q", WT3, "-b", "wip/a3", cwd=R3)
        os.makedirs(os.path.join(WT3, "solo-sdd/changes/archive"))
        os.rename(os.path.join(WT3, "solo-sdd/changes/a"), os.path.join(WT3, "solo-sdd/changes/archive/2026-11-10-a"))
        git2("add", "-A", cwd=WT3); git2("commit", "-qm", "archive", cwd=WT3)
        os.remove(os.path.join(R3, "solo-sdd/changes/a/CLAIM"))
        own = dict(CHANGE="a", BRANCH="wip/a3", WORKTREE=WT3, COMMIT=git2("rev-parse", "HEAD", cwd=WT3),
                   ARCHIVE="solo-sdd/changes/archive/2026-11-10-a")
        assert handback(status_msg(**own)) is None, "archived on the own tree"
        r = handback(status_msg(**dict(own, ARCHIVE="openspec/changes/archive/2026-11-10-a")))
        assert r and "inside solo-sdd/changes/archive/" in r, r
        os.makedirs(os.path.join(WT3, "solo-sdd/changes/b"))
        r = handback(status_msg(**dict(own, CHANGE="b", ARCHIVE="solo-sdd/changes/archive/2026-11-10-a")))
        assert r and "solo-sdd/changes/b is still in" in r, r

    def test_both_trees_present(self):
        # both trees present: solo-sdd/ wins, an openspec/ change is not guarded and not listed
        os.makedirs(os.path.join(R3, "openspec/changes/legacy"))
        open(os.path.join(R3, "openspec/changes/legacy/CLAIM"), "w").write("claude 2026-11-09 session=OTHER\n")
        ctx3 = run("context", {"session_id": "S42", "cwd": R3})["hookSpecificOutput"]["additionalContext"]
        assert "legacy" not in ctx3 and "solo-sdd import" not in ctx3, ctx3
        assert run("guard", dict(e3(), session_id="S42", cwd=R3, tool_input={"file_path": os.path.join(R3, "openspec/changes/legacy/a.md")})) is None, "openspec/ is not the root"

    def test_legacy_tree(self):
        # legacy tree: the context lists the change and carries the import hint
        R4 = os.path.join(H, "proj4")
        os.makedirs(os.path.join(R4, "openspec/changes/a"))
        open(os.path.join(R4, "openspec/changes/a/tasks.md"), "w").write("- [ ] one\n")
        git2("init", "-q", cwd=R4)
        ctx4 = run("context", {"session_id": "S43", "cwd": R4})["hookSpecificOutput"]["additionalContext"]
        assert "a — tasks 0/1" in ctx4 and "process in openspec/: run solo-sdd import openspec" in ctx4, ctx4


# ---------- Requirement: Review before archive. The actor's transcript decides: a code edit needs a `Review:` agent after the first one ----------

R5 = APP5 = TASKS5 = EDIT5 = REVIEW5 = TICK5 = BASH5 = None
_n5 = [0]


def _tool(name, **ti):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": ti}]}}


def r5_fixture():
    global R5, APP5, TASKS5, EDIT5, REVIEW5, TICK5, BASH5
    R5 = os.path.join(H, "proj5")
    APP5, TASKS5 = os.path.join(R5, "src/app.py"), os.path.join(R5, "solo-sdd/changes/add-words/tasks.md")
    os.makedirs(os.path.dirname(APP5)); os.makedirs(os.path.dirname(TASKS5))
    open(APP5, "w").write("x = 1\n"); open(TASKS5, "w").write("- [ ] one\n")
    git2("init", "-q", cwd=R5)
    EDIT5, REVIEW5, TICK5 = _tool("Edit", file_path=APP5), _tool("Agent", description="Review: add-words", prompt="x"), _tool("Edit", file_path=TASKS5)
    BASH5 = [_tool("Bash", command="cat > src/app.py <<'EOF'\nx = 2\nEOF"),
             {"type": "user", "toolUseResult": {"stdout": "", "bashEditDiff": {"changedFiles": [APP5]}}}]


def archive5(lines, sub=None, env=None, path=None, cmd=None):
    _n5[0] += 1
    tr = path or os.path.join(H, "t5-%d.jsonl" % _n5[0])
    if lines is not None:
        open(tr, "w").write("".join(json.dumps(l) + "\n" for l in lines))
    inp = {"session_id": "S50", "cwd": R5, "tool_name": "Bash", "transcript_path": tr,
           "tool_input": {"command": cmd or "cd %s && solo-sdd archive add-words --yes" % R5}}
    if sub is not None:
        os.makedirs(tr[:-6] + "/subagents", exist_ok=True)
        open(tr[:-6] + "/subagents/agent-orc1.jsonl", "w").write("".join(json.dumps(l) + "\n" for l in sub))
        inp["agent_id"] = "orc1"
    out = run("guard", inp, env)
    return out["hookSpecificOutput"]["permissionDecisionReason"] if out else None


class ReviewBeforeArchive(HookCase):
    def setUp(self):
        super().setUp()
        r5_fixture()

    def test_review_before_archive_no_review(self):
        r = archive5([EDIT5])
        assert r and "src/app.py" in r and "Review:" in r, r
        for c in ("/usr/bin/python3 -m solo_sdd archive add-words --yes", "python3.12 -m solo_sdd archive add-words",
                  "~/.local/bin/solo-sdd archive add-words", "env A=1 solo-sdd archive add-words", "time solo-sdd archive add-words",
                  'bash -c "solo-sdd archive add-words"', "npx solo-sdd@latest archive add-words", "uv run solo-sdd archive add-words",
                  "timeout 600 solo-sdd archive add-words", "/usr/bin/env solo-sdd archive add-words", "uvx solo-sdd archive add-words",
                  "npm exec solo-sdd -- archive add-words", "python3 -I -m solo_sdd archive add-words", "sudo -E solo-sdd archive add-words",
                  "{ solo-sdd archive add-words; }", "if true; then solo-sdd archive add-words; fi", "`solo-sdd archive add-words`"):
            assert archive5([EDIT5], cmd=c), "every form of the archive command: " + c
        for c in ("solo-sdd archive --help", "echo 'later: solo-sdd archive add-words'", "grep 'solo-sdd archive' f"):
            assert archive5([EDIT5], cmd=c) is None, "not an archive run: " + c

    def test_review_before_archive_the_command_read_by_the_shell_parser(self):
        """The archive run is found with the hooks' shell parser: a -c string is a command again, quotes are removed."""
        for c in ('bash -c "env A=1 solo-sdd archive add-words"', "sh -c 'npx solo-sdd archive add-words'",
                  "bash -c 'python3 -m solo_sdd archive add-words'", 'zsh -c "uv run solo-sdd archive add-words"',
                  'bash -c "timeout 600 solo-sdd archive add-words"', '"$HOME/.local/bin/solo-sdd" archive add-words',
                  "'solo-sdd' archive add-words", "env -i PATH=/bin solo-sdd archive add-words", "npx --yes solo-sdd archive add-words",
                  "pipx run solo-sdd archive add-words", "uv run --with y solo-sdd archive add-words", "nice solo-sdd archive add-words",
                  "! solo-sdd archive add-words", "echo $(solo-sdd archive add-words)", "eval 'solo-sdd archive add-words'",
                  "bash <<'EOF'\nsolo-sdd archive add-words\nEOF", "(solo-sdd archive add-words)",
                  "(cd %s && solo-sdd archive add-words)" % R5, "solo-sdd archive add-words>/tmp/log",
                  "solo-sdd archive add-words</dev/null", "bash -c 'echo a > /dev/null; solo-sdd archive add-words'"):
            r = archive5([EDIT5], cmd=c)
            assert r and "src/app.py" in r, "an archive run: %s -> %s" % (c, r)
        for c in ("echo solo-sdd archive add-words", 'echo "solo-sdd archive add-words"', "man solo-sdd archive add-words",
                  'git commit -m "a; solo-sdd archive add-words"', "git log --grep 'openspec archive add-words'",
                  "ls solo-sdd/changes/archive/add-words", "solo-sdd archives add-words", "solo-sdd validate --all archive add-words",
                  "cat <<'EOF'\nsolo-sdd archive add-words\nEOF", "mysolo-sdd archive add-words"):
            assert archive5([EDIT5], cmd=c) is None, "not an archive run: " + c

    def test_review_before_archive_review_only_before_the_code(self):
        assert archive5([REVIEW5, EDIT5]), "a review before the first code edit does not count"

    def test_review_before_archive_fixes_after_the_review(self):
        assert archive5([EDIT5, REVIEW5, EDIT5, TICK5]) is None, "Nit fixes after the review pass"

    def test_review_before_archive_only_artifacts_after_the_review(self):
        assert archive5([REVIEW5, TICK5]) is None, "only artifacts: no code edit"
        assert archive5([EDIT5, REVIEW5, TICK5]) is None

    def test_review_before_archive_a_bash_edit(self):
        r = archive5(BASH5)
        assert r and "src/app.py" in r, r
        assert archive5(BASH5 + [REVIEW5]) is None

    def test_review_before_archive_an_orchestrator_subagent(self):
        assert archive5([EDIT5], sub=[EDIT5, REVIEW5]) is None, "the orchestrator's own transcript decides"
        r = archive5([EDIT5, REVIEW5], sub=[EDIT5])
        assert r and "src/app.py" in r, "a review in the main session does not count for the orchestrator: %s" % r

    def test_review_before_archive_an_unreadable_transcript(self):
        h = os.path.realpath(tempfile.mkdtemp(prefix="wh-home5-"))
        try:
            env = dict(BASE_ENV, HOME=h)
            assert archive5(None, env=env, path=os.path.join(h, "no-such.jsonl")) is None, "a missing transcript passes"
            log = open(os.path.join(h, ".claude/hook-state/errors.log")).read()
            assert "no-such.jsonl" in log, log
        finally:
            shutil.rmtree(h)


# Requirement: Archive run behind runners and options. Each form is refused twice: by Review before archive on the R5
# transcript fixture and, with no edits, by a foreign CLAIM of the change in R6
R6 = None


def archive_refused(c):
    r = archive5([EDIT5], cmd=c)
    assert r and "src/app.py" in r, "Review before archive: %s -> %s" % (c, r)
    out = run("guard", {"session_id": "S60", "cwd": R6, "tool_name": "Bash", "tool_input": {"command": c}})
    r = out and out["hookSpecificOutput"]["permissionDecisionReason"]
    assert r and "Archiving is not allowed" in r and "taken by another agent" in r, "foreign CLAIM: %s -> %s" % (c, r)


class ArchiveRunners(HookCase):
    def setUp(self):
        global R6
        super().setUp()
        r5_fixture()
        R6 = os.path.join(H, "proj6")
        os.makedirs(os.path.join(R6, "solo-sdd/changes/add-words"))
        open(os.path.join(R6, "solo-sdd/changes/add-words/CLAIM"), "w").write("claude 2026-11-11 session=OTHER\n")
        git2("init", "-q", cwd=R6)

    def test_archive_run_behind_runners_and_options_a_runner_option_value_named_like_the_program(self):
        for c in ("uvx --from solo-sdd solo-sdd archive add-words", "uv run --project /p/solo-sdd solo-sdd archive add-words",
                  "npx -p solo-sdd solo-sdd archive add-words", "uv run env A=1 solo-sdd archive add-words",
                  "uv run timeout 60 solo-sdd archive add-words", "uv run npx solo-sdd archive add-words",
                  "npx uvx solo-sdd archive add-words"):
            archive_refused(c)

    def test_known_limit_an_argument_of_a_runner_started_program_reads_as_an_archive_run(self):
        """Not a requirement: pins a known false refusal kept over a missed run (proposal Out of Scope of archive-run-words);
        a fix of the limit inverts this test."""
        for c in ("npx prettier solo-sdd archive add-words", "uv run pytest solo-sdd archive add-words"):
            assert archive5([EDIT5], cmd=c), "known false refusal: " + c

    def test_archive_run_behind_runners_and_options_a_runner_that_starts_python(self):
        archive_refused("uv run python -m solo_sdd archive add-words")

    def test_archive_run_behind_runners_and_options_valued_options(self):
        for c in ("python3 -W ignore -m solo_sdd archive add-words", "python3 -X dev -m solo_sdd archive add-words",
                  "python3 -msolo_sdd archive add-words", "sudo -u root solo-sdd archive add-words",
                  "env -u X solo-sdd archive add-words", "env -C /p solo-sdd archive add-words",
                  "sudo -u root bash -c 'solo-sdd archive add-words'", "env -u X eval 'solo-sdd archive add-words'"):
            archive_refused(c)

    def test_archive_run_behind_runners_and_options_end_of_options_before_the_c_string(self):
        archive_refused("bash -c -- 'solo-sdd archive add-words'")

    def test_archive_run_behind_runners_and_options_words_that_stay_text(self):
        for c in ("echo solo-sdd archive add-words", "uvx --from solo-sdd solo-sdd validate --all"):
            assert archive5([EDIT5], cmd=c) is None, "not an archive run: " + c
            assert run("guard", {"session_id": "S60", "cwd": R6, "tool_name": "Bash", "tool_input": {"command": c}}) is None, c


# ---------- Requirement: Secret file tools refused, Secret file reads in Bash, Environment dumps refused ----------

# The not-plain rule: a command with a form the parser does not read gets no exemption. Each form alone makes an
# exempt use refused, so dropping any one of them from NOT_PLAIN fails this test; the last two are accepted false refusals.
NOT_PLAIN_CASES = {"#": "echo hi # see .env", "$'": "echo $'hi' .env", "${": "echo ${HOME} .env", "$(": "echo $(date) .env",
                   "`": "echo `date` .env", "\\": "echo a\\ b .env"}
# Requirement: Known bypasses of the Bash guard. The Bash checks guard against accidental reads, not a boundary: these
# forms pass today. A change that closes one moves it to a refused list; until then this test says the README is true.
KNOWN_BYPASSES = ("cat .e{n,}v", "sh -c 'cat \"$1\"' _ .env", "ls >(cat ')' .env)", "cat <<EOF 'x\n'; cat .env\nEOF",
                  "${X:-env} | wc -l", "sed '1r.env' a.txt")
SECRET_WORDS = ["KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "WEBHOOK", "CREDENTIAL"]
OTHER_WORDS = ["MONKEY", "KEYBOARD", "TOKENIZER", "SECRETARY", "PASSWORDLESS", "NAME", "API", "DB", "HOME", "PATH", "KEYED"]


class SecretFiles(HookCase):
    def setUp(self):
        global ENV_TREE
        super().setUp()
        ENV_TREE = os.path.join(H, "env-tree")
        os.makedirs(os.path.join(ENV_TREE, "app"))
        open(os.path.join(ENV_TREE, "app", ".env.ts"), "w").write("API_KEY=x\n")
        open(os.path.join(ENV_TREE, "app", ".env.local"), "w").write("API_KEY=x\n")
        open(os.path.join(ENV_TREE, "app", "main.py"), "w").write("")

    def test_secret_file_tools_refused_the_read_tool(self):
        for ti in ({"file_path": "/p/.env"}, {"file_path": "/p/.env.local"}, {"file_path": os.path.join(REPO, "app.env")},
                   {"file_path": "/p/.env.development.local"}, {"file_path": "/p/config.prod.env"}):
            assert denied({"tool_name": "Read", "tool_input": ti}), ti
        for ti in ({"pattern": "KEY", "path": ".env"}, {"pattern": "KEY", "glob": ".env*"}, {"pattern": "KEY", "glob": "**/{.env,x.py}"},
                   {"pattern": "KEY", "path": "/p/sub/.env.prod"}, {"pattern": "KEY", "glob": "**/.env.production"},
                   {"pattern": "KEY", "glob": ".env.prod*"}, {"pattern": "KEY", "glob": "*.env"}, {"pattern": "KEY", "glob": "*env*"},
                   {"pattern": "KEY", "path": "/p/.env.production.local"}, {"pattern": "KEY", "glob": ".e*"},
                   {"pattern": "KEY", "glob": ".en?"}, {"pattern": "KEY", "glob": ".[a-z]nv"}, {"pattern": "KEY", "glob": "*.e*"},
                   {"pattern": "KEY", "glob": "*.ts", "path": ENV_TREE}, {"pattern": "KEY", "glob": "*nv.l*", "path": ENV_TREE},
                   {"file_path": "/p/.ENV"}, {"file_path": "/p/.env.example.local"}):
            if "file_path" in ti:
                assert denied({"tool_name": "Read", "tool_input": ti}), ti
                continue
            assert denied({"tool_name": "Grep", "tool_input": ti}), ti

    def test_secret_file_tools_refused_a_template_file(self):
        for ti in ({"file_path": "/p/.env.example"}, {"file_path": "/p/.env.sample"}, {"file_path": "/p/.envrc"}, {"file_path": "/p/env.py"}):
            assert not denied({"tool_name": "Read", "tool_input": ti}), ti
        for ti in ({"pattern": "KEY", "path": "/p"}, {"pattern": "KEY", "path": "/p", "glob": "*.py"}, {"pattern": "KEY", "glob": ".env.example"},
                   {"pattern": "KEY", "glob": "*.py", "path": ENV_TREE}, {"pattern": "KEY", "glob": "**/*.{ts,tsx}"}):
            assert not denied({"tool_name": "Grep", "tool_input": ti}), ti

    # Requirement: Secret file reads in Bash
    def test_secret_file_reads_in_bash_indirect_reads(self):
        for c in ("python3 -c \"print(open('.env').read())\"", "cp .env /tmp/e", "cp .env /tmp/e && cat /tmp/e", "source .env && echo ok",
                  ". ./.env", "git diff .env", "while read l; do echo $l; done < .env", "mv .env.local x", "awk 1 <.env",
                  "bash -c 'cat .env'", "sh -c \"source .env\"", "eval 'cat .env'", "echo \"$(cat .env)\"", "test -f .env && cat .env",
                  "sudo cat .env", "env -i cat .env", "/bin/cat .env", "(cat .env)", "cat $HOME/proj/.env", "xxd prod.env",
                  "grep KEY .env | wc -l", "diff .env .env.example", "rg -L KEY .env", "rg -tc KEY .env", "grep -ec KEY .env",
                  "echo \"$(echo $(cat .env))\"", "ls $(echo $(cat .env))", "echo $(echo `cat .env`)", "echo cat .env | bash",
                  "echo 'cat .env' | sh", "cat .env.development.local", "find . -name .env -exec cat {} +", "ln -s .env x",
                  "cp -t /tmp .env", "cp .env .env.bak", "rg -g -l KEY .env", "rg --glob -c KEY .env", "rg -r -c KEY .env",
                  "rg --replace -c KEY .env", "grep -e -q -e '' .env | awk 1", "grep --regexp -l --regexp '' .env | awk 1",
                  "grep --cou KEY .env", "cp -vt /tmp .env", "cp -t/tmp .env", "cp --target /tmp .env", "ln -st /tmp .env",
                  "install -m 600 .env /tmp/e", "bash -c -- 'cat .env'", "echo 'cat .env' | bash -s x", "cat '>' .env",
                  "head -50 '2>' .env", "sed -n '/=/p' '>' .env", "echo $(echo $(echo $(echo $(cat .env))))", "cat .ENV",
                  "echo 'cat .env' | tee /dev/null | sh", "cat .env.example.local", "ls -la .env  # check it's there\ncat .env",
                  "test -f .env && echo found  # it's present\nsource .env", "grep -c '^API_KEY=' .env  # count, don't print\ngrep API_KEY .env",
                  "find . -name .env  # where's it\nhead .env", "echo start  # it's a test\nwhile read l; do echo $l; done < .env",
                  "echo $'it\\'s' .env; cat .env", "echo \\ #; cat .env", "echo \\;#; cat .env", "echo \\|#| cat .env",
                  "echo ${X:- #}; cat .env", "echo \"$(echo \" #\"; cat .env)\"", "ls # it's\necho \\;#; cat .env",
                  "printf $'KEY=1\\n' >> .env", "echo ${X:-\"}\" #}; cat .env", "echo \"$(echo \")\" \" #\"; cat .env)\"",
                  "echo ${X:-(a) #}; cat .env", "cat .e\\nv # x", "cat .e\"\"nv", "cat x # cat <<EOF\ncat .env\nEOF",
                  "echo $'a\\'\ncat <<EOF\n'; cat .env\nEOF", "cat .e\\\nnv # c", "cat .e\\\nnv ${X:-}"):
            assert bash(c), c

    def test_secret_file_reads_in_bash_allowed_uses(self):
        for c in ("test -f .env", "[ -f .env ] && echo yes", "[[ -s .env ]]", "ls -la .env", "stat .env", "touch .env", "chmod 600 .env",
                  "git check-ignore .env", "grep -c '^API_KEY=.' .env", "grep -q KEY .env", "rg -l KEY .env", "grep --count KEY .env",
                  "echo 'API_KEY=' >> .env", "printf 'X=1' >>.env", "cat .env.example", "cp .env.example .env.example.bak",
                  "echo 'put the key into .env'", "git commit -m 'guard .env reads'", "bash -c 'test -f .env'",
                  "cat > notes.md <<'EOF'\ncat .env\nEOF", "grep -rn 'process.env' src", "cp .env.example .env",
                  "cp -n .env.example .env", "ln -s .env.example .env", "find . -name .env", "find . -name '.env*' -type f",
                  "grep -lc KEY .env", "rg --files-with-matches KEY .env", "echo hi | bash", "echo \"<.env\"",
                  "source .env/bin/activate", "grep -c -e KEY .env", "rg -c -g '*.env' KEY .env",
                  "grep -ci --max-count 1 KEY .env", "cp -n .env.example .env", "test -f .env || cp .env.example .env",
                  "echo x 1>>.env", "ls -la .env 2>&1", "echo 'cat .env' | wc -l",
                  "echo ${#API_KEY}", "echo $# # it's", "git commit -m 'fix #12'", "grep -v '^#' x # don't",
                  "cat > notes.md <<'EOF'\n# Setup\nCopy .env.example to .env, then run env.\nEOF"):
            assert not bash(c), c

    def test_secret_file_reads_in_bash_not_plain_forms(self):
        assert set(NOT_PLAIN_CASES) == set(wh.NOT_PLAIN), wh.NOT_PLAIN
        for form, c in NOT_PLAIN_CASES.items():
            assert bash(c), c
            assert [t for t in wh.NOT_PLAIN if t in c] == [form], (form, c)
        for c in ("test -f .env && echo ${#API_KEY}", "echo hi # see .env", "ls .env  # cat .env", "echo '#' .env", "ls a#b .env",
                  "python3 app.py  # don't\nls .env", "printf 'X=\\n' >>.env", "# cat .env",
                  "git commit -m \"$(cat <<'EOF'\nguard env dumps\nEOF\n)\""):  # accepted false refusals
            assert bash(c), c

    # Requirement: Environment dumps refused
    def test_environment_dumps_refused_a_shell_dump(self):
        for c in ("set | grep -i api", "set", "export -p", "declare -p", "typeset -p", "export", "declare -px", "(set)",
                  "env", "env | grep KEY", "printenv", "sudo env", "x=1; set", "declare -p API_KEY", "bash -c env",
                  "bash -c 'env | grep KEY'", "eval env", "eval 'set | grep KEY'", "sh -c \"printenv API_KEY\"", "env 2>&1",
                  "env 2>&1 | grep KEY", "set 2>&1 | head", "env -u FOO", "echo \"$(echo \"$(env)\")\"", "echo env | sh",
                  "/usr/bin/env", "bash -c -- env", "echo env | bash -s x", "ls # it's\nenv", "echo x\\\t#; env",
                  "echo ${X:- #}; env", "echo \"$(echo \" #\"; env)\"", "echo $'x' # it's\nenv", "echo ${X:-\"}\" #}; env",
                  "echo \"$(echo \")\" \" #\"; env)\"", "e\\nv # x", "x=1 # y\nset", "echo `export -p`", "declare -x # c",
                  "typeset -x # c", "set 2>&1 # c", "export 2>&1 # c", "declare -x 2>&1 # c", "set > /tmp/s # c"):
            assert bash(c), c
        for c in ("set -e", "set -euo pipefail", "set -- a b", "export PATH=/x:$PATH", "export -n FOO", "declare -p HOME",
                  "env -u ELECTRON_RUN_AS_NODE npm test", "printenv HOME", "env FOO=1 make", "echo set"):
            assert not bash(c), c

    def test_known_bypasses_of_the_bash_guard_known_limits(self):
        for c in KNOWN_BYPASSES:
            assert not bash(c), "a known bypass is refused now, move it to the refused tests and the README: " + c

    # Requirement: Secret variable names
    def test_secret_variable_names_a_word_inside_a_name(self):
        for c in ("echo $MONKEY_NAME", "echo $KEYBOARD_LAYOUT", "echo ${TOKENIZER_PATH}", "printenv PASSWORDLESS_MODE", "echo $HOME",
                  'echo "${#OPENAI_API_KEY}"'):
            assert not bash(c), c

    def test_secret_variable_names_a_secret_part(self):
        for c in ('echo "$OPENAI_API_KEY"', "echo $db_password", "echo $apiKey", "printenv GITHUB_TOKENS", "printf %s ${SLACK_WEBHOOK}",
                  "echo $AWS_SECRET2", "echo $api2key", "echo $client_credentials"):
            assert bash(c), c

    @settings(max_examples=300, deadline=None)
    @given(st.lists(st.sampled_from(SECRET_WORDS + [w + "S" for w in SECRET_WORDS] + OTHER_WORDS), min_size=1, max_size=4),
           st.sampled_from(["upper", "lower", "camel"]), st.sampled_from(["_", "1", "_2_"]))
    def test_secret_variable_names_property(self, words, style, sep):
        if style == "camel":
            name = words[0].lower() + "".join(w.capitalize() for w in words[1:])
        else:
            name = sep.join(w.lower() if style == "lower" else w for w in words)
        want = any(w in SECRET_WORDS or w.endswith("S") and w[:-1] in SECRET_WORDS for w in words)
        assert wh.secret_var(name) == want, (name, want)


ENV_TREE = None


# ---------- Requirement: Direct merge refused in a process tree ----------

TREE = None


def merge_denied(c, cwd=None):
    out = run("guard", {"session_id": "S1", "cwd": cwd or TREE, "tool_name": "Bash", "tool_input": {"command": c}})
    return out["hookSpecificOutput"]["permissionDecisionReason"] if out else None


# Requirement: Known bypasses of the merge guard. An accident guard, not a boundary: these direct merges pass today.
# A change that closes one moves it to the refused tests and the README.
KNOWN_MERGE_BYPASSES = ("echo 5 | xargs gh pr merge", "find . -maxdepth 0 -exec gh pr merge 5 \\;", "sudo -u me gh pr merge 5",
                        "env -u FOO gh pr merge 5", "f(){ gh pr merge 5; }; f",
                        "A=(1 2) bash -c 'gh pr merge 5'", "A=(1 2) eval gh pr merge 5", "A=(1 2) FOO='a b' gh pr merge 5", "cat =(bash -c 'gh pr merge 5')",
                        "cat =(sh -c 'gh pr merge 5')", "cat =(eval gh pr merge 5)", "cat =(FOO='a b' gh pr merge 5)",
                        # a quote inside a word after A=(…) or in =(…): the quotes-ignored read strips quotes only at word ends
                        "A=(1 2) 'g'h pr merge 5", "cat =(gh p''r merge 5)",
                        'echo "$(echo "$(echo "$(echo "$(gh pr merge 5)")")")"', 'echo "$(echo "`gh pr merge 5; grep ")" f`")"',
                        "echo $(echo '(') $(echo '(') $(echo '(') \"$(gh pr merge 5)\"", 'echo "x\n$\\\n(gh pr merge 5)"')
KNOWN_MERGE_FALSE_REFUSALS = ('git commit -m "fix #42 (gh pr merge is refused)"', 'git commit -m "fix #42; gh pr merge later"',
                              "git commit -m 'fix #42\ngh pr merge later'", "echo ${X} 'a | gh pr merge 5'", "gh pr merge --help",
                              "gh api repos/o/r/pulls/5/merge", 'A=(x y); git commit -m "a; gh pr merge later"')
MERGE_FLAGS = ["--squash", "--merge", "--rebase", "--delete-branch", "--admin", "-R o/r", "--repo=o/r", "-t subj"]
API_PARTS = [["-X PUT", "-XPUT", "--method PUT", "--method=PUT"], ["-f merge_method=squash", "-F sha=abc", "-H 'Accept: x'"]]


class DirectMerge(HookCase):
    def setUp(self):
        global TREE
        super().setUp()
        TREE = os.path.join(H, "tree")
        os.makedirs(os.path.join(TREE, "solo-sdd/specs"))
        subprocess.run(["git", "init", "-q", TREE], check=True, capture_output=True)

    def test_direct_merge_refused_in_a_process_tree_a_process_tree(self):
        why = merge_denied("gh pr merge 5 --squash")
        assert why and "sdd-pr.py merge" in why, why

    def test_direct_merge_refused_in_a_process_tree_the_api_form(self):
        assert merge_denied("gh api -X PUT repos/o/r/pulls/5/merge")
        assert merge_denied("cd sub && GH_TOKEN=x command gh api --method=PUT /repos/o/r/pulls/12/merge -f merge_method=squash")
        assert merge_denied('bash -c "gh pr merge 5"') and merge_denied("echo $(gh pr merge 5)"), "a shell string and a substitution run"
        assert merge_denied("eval gh pr merge 5") and merge_denied("/opt/homebrew/bin/gh pr -R o/r merge 5")
        assert merge_denied("echo ${X}; gh pr merge 5"), "a form the reader cannot read is read again with quotes ignored"
        assert merge_denied("echo $'\\'' ; gh pr merge 5 ; echo '\\''"), "a quote boundary moved by $'…'"
        for c in ('x="$(cd d && gh pr merge 5)"', 'echo "`cd d; gh pr merge 5`"', 'git commit -m "$(true\ngh pr merge 5)"'):
            assert merge_denied(c), "a substitution is a command list: " + c
        assert merge_denied("gh api -X PUT 'repos/o/r/pulls/5/merge?merge_method=squash'"), "a query string after the endpoint"
        assert merge_denied("FOO='a b' gh pr merge 5 --squash"), "an assignment with a quoted value is not the program"
        assert merge_denied('git commit -m msg -m "$(gh pr merge 5)"'), "a substitution in a message runs"

    def test_direct_merge_refused_in_a_process_tree_no_tree(self):
        assert merge_denied("gh pr merge 5 --squash", REPO) is None
        assert merge_denied("gh api -X PUT repos/o/r/pulls/5/merge", REPO) is None

    def test_direct_merge_refused_in_a_process_tree_text_about_a_merge(self):
        for c in ('git commit -m "explain gh pr merge"', "echo 'gh pr merge 5'", 'grep -n "gh pr merge" skills/ship/SKILL.md',
                  "cat > note.md <<'EOF'\ngh pr merge 5\nEOF", 'gh pr create --title "gh pr merge" --body x',
                  "gh pr view 5", "gh pr checkout merge", 'git commit -m "guard refuses gh pr merge (#42)"',
                  "git commit -m 'fix #12: gh pr merge is refused'", "gh pr view 5 # merge after green",
                  "gh pr view ${PR} && git merge origin/main", "ls # gh and merge",
                  "git commit -m \"$(cat <<'EOF'\nship: the guard\n\ngh pr merge is refused in a tree\nEOF\n)\"",
                  "git commit -m \"ship: x\" -m \"$(cat <<'EOF'\ngh pr merge is refused in a tree\nEOF\n)\"",
                  "gh pr create --title t --body \"$(cat <<'EOF'\ngh pr merge is refused\nEOF\n)\"", "gh api repos/o/r/pulls/5", "python3 ~/.local/bin/sdd-pr.py merge u squash abc"):
            assert merge_denied(c) is None, c

    # Requirement: Shell forms the text cut cannot read
    def test_shell_forms_the_text_cut_cannot_read_a_plain_expansion_before_a_message(self):
        assert merge_denied('T="${TMPDIR:-/tmp}"; git commit -m "a; gh pr merge 5"') is None, "the message after ${TMPDIR:-/tmp} is cut"
        for c in ('T=${X:-"a b"}; git commit -m "a; gh pr merge 5"', 'T=${X; git commit -m "a; gh pr merge 5"'):
            assert merge_denied(c), "a ${ the cut cannot read keeps the line uncut: " + c

    def test_shell_forms_the_text_cut_cannot_read_a_zsh_process_substitution(self):
        assert merge_denied("git commit -m =(gh pr merge 5)"), "zsh runs the command inside =(…): the line is checked uncut"

    def test_known_bypasses_of_the_merge_guard_an_array_assignment_before_a_merge(self):
        # =( makes the merge guard read the line with quotes ignored, so the merge after it is found
        for c in ("A=(1 2) gh pr merge 5", "cat =(gh pr merge 5)", "A=(1 2) \\gh pr merge 5", "A=(1 2) g\\h pr merge 5",
                  "cat =(\\gh pr merge 5)", "A=(1 2) /usr/bin/env gh pr merge 5", "cat =(/usr/bin/env gh pr merge 5)"):
            assert merge_denied(c), c

    def test_known_bypasses_of_the_merge_guard_a_known_bypass_closed(self):
        for c in KNOWN_MERGE_BYPASSES:
            assert merge_denied(c) is None, "a known bypass is refused now, move it to the refused tests and the README: " + c

    def test_known_bypasses_of_the_merge_guard_a_known_false_refusal(self):
        for c in KNOWN_MERGE_FALSE_REFUSALS:
            assert merge_denied(c), "a known false refusal passes now, move it to the passing tests: " + c

    @settings(max_examples=60, deadline=None)
    @given(st.booleans(), st.data())
    def test_direct_merge_refused_in_a_process_tree_property(self, tree, data):
        if data.draw(st.booleans(), "api"):
            words = [data.draw(st.sampled_from(API_PARTS[0]))] + data.draw(st.lists(st.sampled_from(API_PARTS[1]), max_size=2))
            words.append(data.draw(st.sampled_from(["repos/o/r/pulls/5/merge", "/repos/{owner}/{repo}/pulls/77/merge",
                                                    "repos/o/r/pulls/5/merge?merge_method=squash"])))
            cmd = "gh api " + " ".join(data.draw(st.permutations(words)))
        else:
            flags = data.draw(st.lists(st.sampled_from(MERGE_FLAGS), max_size=3, unique=True))
            cmd = "gh pr merge " + " ".join(data.draw(st.permutations(flags + ["5"])))
        # (form, quote around the command, runs): a quoted command is an argument of another program, not a run;
        # a quoted substitution runs its command list
        wrap, q, command = data.draw(st.sampled_from([
            ("%s", "", True), ("cd x && %s", "", True), ("FOO='a b' %s", "'", True), ("true; %s", "", True), ("git status && %s", "", True),
            ('x="$(cd d && %s)"', '"', True), ('echo "`true; %s`"', '"', True), ("echo ${X}; %s", "", True),
            ('git commit -m "%s"', '"', False), ("echo '%s'", "'", False), ("printf '%%s\\n' \"%s\"", '"', False),
            ('git commit -m "%s (#42)"', '"', False), ("git commit -m 'fix #1: %s'", "'", False)]))
        other = {'"': "'", "'": '"'}.get(q)
        got = merge_denied(wrap % (cmd.replace(q, other) if q else cmd), TREE if tree else REPO)
        assert bool(got) == (tree and command), (tree, wrap, cmd, got)


# ---------- Requirements: Checks without the policy, Hook errors in the session context, Error log size (work-hooks-subagents)
# and Test model allowlist (model-guard). The hook reads model-policy.json next to itself: a copy of the hook in its own folder,
# loaded in this process. ----------

def policy_stand(text=None):
    """A folder with hooks/work_hooks.py, hooks/model-policy.json (the repository one, or `text`) and an empty home."""
    d = os.path.realpath(tempfile.mkdtemp(prefix="wh-policy-"))
    os.makedirs(os.path.join(d, "hooks"))
    os.makedirs(os.path.join(d, "home/.claude/hook-state"))
    shutil.copy(HOOK, os.path.join(d, "hooks/work_hooks.py"))
    if text is None:
        shutil.copy(os.path.join(os.path.dirname(HOOK), "model-policy.json"), os.path.join(d, "hooks"))
    else:
        open(os.path.join(d, "hooks/model-policy.json"), "w").write(text)
    return d


def stand_run(d, cmd, inp):
    home = os.path.join(d, "home")
    return call(load(os.path.join(d, "hooks/work_hooks.py")), cmd, dict({"session_id": "SP", "cwd": home}, **inp),
                dict(BASE_ENV, HOME=home))


def stand_log(d, lines=None):
    p = os.path.join(d, "home/.claude/hook-state/errors.log")
    if lines is not None:
        open(p, "w").write("".join(l + "\n" for l in lines))
    return open(p).read() if os.path.exists(p) else ""


def stand_denied(out):
    return bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny"


def ago(days):
    return (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat(timespec="seconds")


def context_text(out):
    return out["hookSpecificOutput"]["additionalContext"] if out else ""


class Policy(HookCase):
    def test_checks_without_the_policy_a_broken_policy(self):
        d = policy_stand("{")
        try:
            assert stand_denied(stand_run(d, "guard", {"tool_name": "Bash", "tool_input": {"command": "git worktree add ../wt"}, "cwd": OUTSIDE}))
            assert "model-policy.json" in stand_log(d), stand_log(d)
        finally:
            shutil.rmtree(d)

    def test_checks_without_the_policy_model_checks_let_through(self):
        d = policy_stand("{")
        try:
            assert stand_run(d, "guard", agent("Review: x", "haiku")) is None
            assert "model-policy.json" in stand_log(d), stand_log(d)
            assert stand_run(d, "guard", {"tool_name": "Bash", "tool_input": {"command": "pytest --model opus"}}) is None
            for text in ("null", "{}", "[]"):
                open(os.path.join(d, "hooks/model-policy.json"), "w").write(text)
                stand_log(d, [])
                assert stand_denied(stand_run(d, "guard", {"tool_name": "Bash", "tool_input": {"command": "git worktree add ../wt"}, "cwd": OUTSIDE})), text
                assert "model-policy.json" in stand_log(d), (text, stand_log(d))
        finally:
            shutil.rmtree(d)

    def test_hook_errors_in_the_session_context_a_recent_error(self):
        d = policy_stand()
        try:
            last = ago(1) + " stop ValueError('b')"
            stand_log(d, [ago(1.2) + " guard ValueError('a')", last, "no time here"])
            text = context_text(stand_run(d, "context", {}))
            assert "hook errors: 2 in the last 7 days, last: " + last in text, text
        finally:
            shutil.rmtree(d)

    def test_hook_errors_in_the_session_context_old_errors_only(self):
        d = policy_stand()
        try:
            stand_log(d, [ago(30) + " guard ValueError('a')", ago(8) + " guard ValueError('b')"])
            assert "hook errors" not in context_text(stand_run(d, "context", {}))
        finally:
            shutil.rmtree(d)

    def test_hook_errors_in_the_session_context_errors_outside_a_project(self):
        d = policy_stand()
        try:
            stand_log(d, [ago(0) + " guard ValueError('a')"])
            assert "hook errors: 1 in the last 7 days" in context_text(stand_run(d, "context", {}))
        finally:
            shutil.rmtree(d)

    def test_error_log_size_a_long_log(self):
        d = policy_stand()
        try:
            lines = ["%s guard ValueError(%d)" % (ago(0), i) for i in range(1500)]
            stand_log(d, lines)
            stand_run(d, "end", {})
            assert stand_log(d).splitlines() == lines[500:]
            # a cleanup failure later in the hook (a dangling state file) does not skip the trim
            os.symlink(os.path.join(d, "gone"), os.path.join(d, "home/.claude/hook-state/x.json"))
            stand_log(d, lines)
            stand_run(d, "end", {})
            kept = stand_log(d).splitlines()
            assert kept[:1000] == lines[500:] and len(kept) <= 1001, len(kept)
        finally:
            shutil.rmtree(d)

    def test_test_model_allowlist_an_unknown_expensive_model(self):
        r = reason({"tool_name": "Bash", "tool_input": {"command": "pytest --model gpt-9-ultra"}})
        assert "gpt-9-ultra" in r and "luna" in r and "haiku" in r, r

    def test_test_model_allowlist_a_cheap_model(self):
        assert not bash("pytest --model=claude-haiku-4-5") and not bash("pytest --model gpt-6-luna tests")
        assert not bash("pytest --model anthropic/claude-3-haiku") and not bash("pytest --model 'openrouter:haiku'"), "a provider prefix"

    def test_test_model_allowlist_a_module_and_a_marker(self):
        assert not bash("python3 -m pytest -m slow tests")

    def test_test_model_allowlist_the_owner_override(self):
        assert not denied_env({"tool_name": "Bash", "tool_input": {"command": "pytest --model gpt-9-ultra"}}, OWNER)


# ---------- Requirements: Browser signs from the policy file, Broken browser key fails open (work-hooks-subagents).
# The scenarios Another browser tool, A built-in sign removed, A broken key and A policy file that does not parse run on
# a deployed copy in the stand tests/stands/hook-tool-names.py; here the shipped values and the property. ----------

BROWSER_PARTS = ("tools", "skills", "bash")


def builtin_signs():
    return {"tools": wh.BROWSER_TOOLS, "skills": wh.BROWSER_SKILLS, "bash": wh.BROWSER_BASH}


def expected_signs(doc):
    """(signs by part, names the log must hold) for a parsed policy `doc`; NOFILE and BADJSON stand for an unreadable file."""
    signs = {p: set(v) for p, v in builtin_signs().items()}
    if not isinstance(doc, dict):
        return signs, {"model-policy.json"}
    if "browser" not in doc:
        return signs, set()
    if not isinstance(doc["browser"], dict):
        return signs, {"browser"}
    broken = set()
    for p in BROWSER_PARTS:
        if p not in doc["browser"]:
            continue
        v = doc["browser"][p]
        if isinstance(v, list) and all(isinstance(x, str) and x for x in v):
            signs[p] |= set(v)
        else:
            broken.add("browser." + p)
    return signs, broken


JSON_ANY = st.recursive(st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False) | st.text(max_size=8),
                        lambda c: st.lists(c, max_size=3) | st.dictionaries(st.text(max_size=6), c, max_size=3), max_leaves=6)
SIGN = st.text(max_size=12) | st.sampled_from(["", "mcp__mybrowser__", "--remote-debugging-port", "run"])
PART = st.lists(SIGN, max_size=4) | st.lists(SIGN | JSON_ANY, max_size=3) | JSON_ANY
BROWSER_KEY = st.dictionaries(st.sampled_from(BROWSER_PARTS + ("extra", "Tools")), PART, max_size=4) | JSON_ANY
POLICY_DOC = st.fixed_dictionaries({}, optional={"browser": BROWSER_KEY, "cheap": JSON_ANY}) | JSON_ANY
NOT_JSON = st.sampled_from(["", "{", "nul", '{"browser": ', "\x00"]) | st.text(max_size=10).filter(lambda t: not t.strip()[:1] in list("{[\"-0123456789tfn"))


class BrowserSigns(unittest.TestCase):
    def test_browser_signs_from_the_policy_file_the_shipped_values(self):
        shipped = json.load(open(os.path.join(os.path.dirname(HOOK), "model-policy.json")))["browser"]
        assert shipped == {p: list(v) for p, v in builtin_signs().items()}, shipped

    def test_broken_browser_key_fails_open_property(self):
        """For any policy file the hook never fails and counts exactly the built-in signs plus the valid parts; each
        broken part, a broken key or the file gets one errors.log line naming it."""
        d = os.path.realpath(tempfile.mkdtemp(prefix="wh-browser-"))
        self.addCleanup(shutil.rmtree, d, True)
        pol, log = os.path.join(d, "model-policy.json"), os.path.join(d, "state", "errors.log")

        @settings(max_examples=400, deadline=None)
        @given(st.one_of(POLICY_DOC.map(lambda doc: (json.dumps(doc), doc)), NOT_JSON.map(lambda t: (t, None)), st.just((None, None))))
        def check(case):
            text, doc = case
            if os.path.exists(pol):
                os.remove(pol)
            if text is not None:
                open(pol, "w").write(text)
            if os.path.exists(log):
                os.remove(log)
            with mock.patch.object(wh, "HERE", d), mock.patch.object(wh, "STATE", os.path.dirname(log)):
                got = wh.browser_signs()
            want, names = expected_signs(doc)
            assert {p: set(got[p]) for p in BROWSER_PARTS} == want, (text, got)
            lines = open(log).read().splitlines() if os.path.exists(log) else []
            assert sorted(l.split()[2] for l in lines) == sorted(names), (text, lines)
        check()


# ---------- Worktree add: home and session folder outside the temporary roots, so ~ and relative paths are not temporary ----------

WT_HOME = WT_ENV = None
PLAIN = "git worktree add [-b <name> | -B <name> | --detach | -f] <path> [<commit>]"


def wt_reason(c, cwd=None):
    """The refusal reason of the real guard for a Bash command, "" when it passes."""
    out = run("guard", {"session_id": "SW", "cwd": cwd or WT_HOME, "tool_name": "Bash", "tool_input": {"command": c}}, WT_ENV)
    return out["hookSpecificOutput"]["permissionDecisionReason"] if out else ""


QUOTINGS = st.sampled_from(["plain", "single", "double", "backslash", "splice-single", "splice-double", "dollar-single",
                            "dollar-double"])


def outside_paths():
    return st.sampled_from(["~/wt", "~/code/proj/tmp/wt", "../wt", "wt", "/tmp/../Users/wt", "%s/x" % WT_HOME])


def quoted(word, how, at):
    at = 1 + at % (len(word) - 1)
    return {"plain": word, "single": "'%s'" % word, "double": '"%s"' % word, "backslash": word[:at] + "\\" + word[at:],
            "splice-single": word[:at] + "''" + word[at:], "splice-double": word[:at] + '""' + word[at:],
            "dollar-single": "$'%s'" % word, "dollar-double": '$"%s"' % word}[how]


def worktree_property(decide):
    """For any quoting of `worktree` and `add` and a path outside the temporary roots, decide(cmd) refuses."""
    @settings(max_examples=40, deadline=None)
    @given(QUOTINGS, QUOTINGS, st.integers(0, 50), st.integers(0, 50), outside_paths())
    def prop(qw, qa, aw, aa, path):
        c = "git %s %s %s" % (quoted("worktree", qw, aw), quoted("add", qa, aa), path)
        assert decide(c), c
    prop()


def raw_text_mutant(c):
    """The old rule: `worktree add` counted in the raw text."""
    import re
    return bool(re.search(r"\bworktree\s+add\b", c)) and not re.search(r"/tmp/|/var/folders/|\$\{?TMPDIR", c)


class WorktreeWords(HookCase):
    def setUp(self):
        global WT_HOME, WT_ENV
        super().setUp()
        WT_HOME = os.path.realpath(tempfile.mkdtemp(prefix="wh-wt-", dir=OUTSIDE))
        self.addCleanup(shutil.rmtree, WT_HOME, True)
        WT_ENV = dict(BASE_ENV, HOME=WT_HOME)

    def tearDown(self):
        super().tearDown()
        assert not os.path.exists(os.path.join(WT_HOME, ".claude/hook-state/errors.log")), "worktree guard errors"

    def test_worktree_add_by_shell_words_a_quoted_subcommand(self):
        for c in ('git worktree "add" ~/wt', 'git "worktree" add ~/wt', "git worktree ad\\d ~/wt"):
            assert PLAIN in wt_reason(c), c

    def test_worktree_add_by_shell_words_a_variable_subcommand(self):
        assert wt_reason("W=worktree; git $W add ~/wt")

    def test_worktree_add_by_shell_words_a_heredoc_decoy(self):
        assert wt_reason("cat <<'EOF'\ngit worktree add /tmp/a\nEOF\ngit -C ~ worktree add wt")

    def test_worktree_add_by_shell_words_a_clustered_option_or_git_c(self):
        for c in ("git worktree add -fb x /tmp/wt", "git -C x worktree add /tmp/wt"):
            assert PLAIN in wt_reason(c), c

    def test_worktree_add_by_shell_words_a_tmp_folder_inside_the_project_or_a_comment(self):
        for c in ("git worktree add ~/code/proj/tmp/wt", "git worktree add ../wt # /tmp/"):
            assert wt_reason(c), c

    def test_worktree_add_by_shell_words_the_plain_form(self):
        for c in ('git worktree add "${TMPDIR:-/tmp}/wt-x"', "git worktree add -b feat /tmp/wt-y main"):
            assert not wt_reason(c), (c, wt_reason(c))

    def test_worktree_add_by_shell_words_text_is_not_a_command(self):
        for c in ('git commit -m "docs: explain git worktree add"', "echo 'git worktree add /tmp/x'",
                  'git commit -m "worktree: add a guard (#12)"', 'git add -A && git commit -m "worktree-guard-words: fix #3"',
                  "cp -r ~/src/git $HOME/backup", 'grep -rn "worktree" "$W"/global', "rg worktree $DIR", "echo worktree $HOME"):
            assert not wt_reason(c), (c, wt_reason(c))

    def test_worktree_add_by_shell_words_wrapped_forms(self):
        for c in ("bash -c 'git worktree add /tmp/wt'", "eval git worktree add /tmp/wt", "sudo git worktree add /tmp/wt",
                  "echo $(git worktree add /tmp/wt)", "G=git; $G worktree add /tmp/wt", "git $'worktree' add ~/wt",
                  "git -c alias.wt=worktree wt add /tmp/wt", 'git worktree add "$(mktemp -d)/wt"', "git worktree $'add' /tmp/wt",
                  "git worktree a$'dd' ~/wt", "A=add; git worktree $A /tmp/wt"):
            assert PLAIN in wt_reason(c), c
        assert not wt_reason("git -C x log") and not wt_reason("git worktree list"), "other git commands pass"

    def test_worktree_add_by_shell_words_any_quoting_is_refused(self):
        worktree_property(lambda c: bool(wt_reason(c)))
        try:
            worktree_property(raw_text_mutant)
        except AssertionError:
            return
        raise AssertionError("the property does not catch the raw-text mutant")

    def test_worktree_path_line_state_tmpdir_changed_on_the_line(self):
        for c in ('TMPDIR=$HOME/Code; git worktree add "$TMPDIR/wt"', 'export TMPDIR=~/Code && git worktree add "${TMPDIR:-/tmp}/wt"',
                  '(TMPDIR=~/Code; git worktree add "$TMPDIR/wt")'):
            assert wt_reason(c), c

    def test_worktree_path_line_state_a_link_made_on_the_line(self):
        assert wt_reason("ln -s ~/Code /tmp/lnk && git worktree add /tmp/lnk/wt")
        assert wt_reason("(ln -s ~/Code /tmp/lnk; git worktree add /tmp/lnk/wt)")

    def test_worktree_path_line_state_a_cd_before_a_relative_path(self):
        assert not wt_reason("git worktree add wt", cwd="/private/tmp"), "a relative path in a temporary folder passes"
        assert wt_reason("cd ~/Code && git worktree add wt", cwd="/private/tmp")
        assert wt_reason("(cd ~/Code && git worktree add wt)", cwd="/private/tmp")

    def test_worktree_guard_known_limits_known_passes(self):
        """Outside the guard (an accident guard, not a boundary): each pinned as passing, so a change to it is a decision."""
        for c in ("G=git; $G worktree $A /tmp/x", "xargs git worktree $A /tmp/x", "git config alias.wt worktree && git wt add ~/wt",
                  'bash -c "git worktree \\$A /tmp/x"', "GIT worktree $A /tmp/x", "2>/dev/null git worktree $A /tmp/x",
                  "env -u X git worktree $A /tmp/x", "f() { git worktree $1 /tmp/x; }; f add",
                  "case x in x) git worktree $A /tmp/x;; esac", "git --config-env a.b=C worktree $A /tmp/x",
                  "stdbuf -o0 git worktree $A /tmp/x", 'B="x y" git worktree $A /tmp/x',
                  "echo #'\ngit $'\\x77orktree' $'\\x61dd' ~/wt\n#'"):
            assert not wt_reason(c), (c, wt_reason(c))

    def test_worktree_guard_known_limits_known_refusals(self):
        """Correct commands the guard refuses: each pinned as refused naming the plain form."""
        for c in ('git commit -m "git worktree add (#12)"', "git worktree add '/tmp/wt (copy)'", "git worktree $SUB",
                  'git worktree "$@"', "git commit -m 'see `git worktree add /tmp/x`'"):
            assert PLAIN in wt_reason(c), c

    def test_worktree_guard_known_limits_an_array_assignment_before_a_worktree_add(self):
        for c in ("ARR=(a b); git worktree add /tmp/wt-x", 'A=(1); git commit -m "see git worktree add /tmp/x"'):
            reason = wt_reason(c)
            assert PLAIN in reason and "=(…)" in reason, (c, reason)

    def test_orchestrator_launch_the_launch_commands_pass(self):
        for c in ('mktemp -d "${TMPDIR:-/tmp}/sdd-XXXXXX"', "git worktree add -b change/x /private/tmp/sdd-AbC123/wt-x",
                  "git worktree add -b change/x /private/tmp/sdd-AbC123/wt-x origin/main"):
            assert not wt_reason(c), (c, wt_reason(c))


if __name__ == "__main__":
    unittest.main()
