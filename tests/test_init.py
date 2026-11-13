#!/usr/bin/env python3
"""solo-sdd init: the solo-sdd/ tree from the package templates, the settings with questions and flags; temporary repositories."""
import contextlib, io, os, select, subprocess, sys, tempfile, time, unittest
import marks
from unittest import mock

from hypothesis import given, settings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import cli, init, rules_block  # noqa: E402

FILES = ("solo-sdd/project.md", "solo-sdd/analyze.md", "docs/waiting.md")
TREE = FILES + ("solo-sdd/specs", "solo-sdd/changes")
CONFIG = "solo-sdd/config"


def snapshot(root):
    """Every file and folder under root (no .git): {path: bytes, folder: None}."""
    out = {}
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if x != ".git"]
        for x in dirs:
            out[os.path.relpath(os.path.join(d, x), root)] = None
        for n in names:
            p = os.path.join(d, n)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root)] = f.read()
    return out


class Env:
    """A temporary project with its own HOME; PATH holds only /usr/bin:/bin, so no openspec or gh is reachable."""

    def __init__(self, git=True):
        self.tmp = tempfile.TemporaryDirectory()
        self.proj = os.path.join(self.tmp.name, "proj")
        os.makedirs(self.proj)
        if git:
            os.mkdir(os.path.join(self.proj, ".git"))
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home)
        self.patch = mock.patch.dict(os.environ, {"PATH": "/usr/bin:/bin", "HOME": self.home})
        self.calls = []

    def __enter__(self):
        self.patch.start()
        return self

    def __exit__(self, *a):
        self.patch.stop()
        self.tmp.cleanup()

    def write(self, rel, text):
        p = os.path.join(self.proj, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(text)

    def init(self, *flags, answers=None):
        """init.main on the project with stdin not a terminal; answers: lines for the questions (then asked)."""
        buf, lines = io.StringIO(), list(answers or [])

        def read(prompt):
            print(prompt)
            if not lines:
                raise EOFError
            return lines.pop(0)
        argv = [self.proj, *flags]
        real = subprocess.Popen

        def only_git_gh(args, *a, **k):
            self.calls.append(list(args))
            assert os.path.basename(args[0]) in ("git", "gh"), "external program %s" % args[0]
            return real(args, *a, **k)
        with contextlib.redirect_stdout(buf), mock.patch.object(sys, "stdin", io.StringIO()), \
                mock.patch.object(subprocess, "Popen", only_git_gh):
            if answers is None:
                code = init.main(argv)
            else:
                with mock.patch.object(sys.stdin, "isatty", return_value=True), mock.patch.object(init, "input", read, create=True):
                    code = init.main(argv)
        return code, buf.getvalue()

    def config(self):
        with open(os.path.join(self.proj, CONFIG), encoding="utf-8") as f:
            return f.read()


class InitTest(unittest.TestCase):
    def test_new_project(self):
        with Env() as e:
            code, out = e.init()
            self.assertEqual(code, 0, out)
            files = snapshot(e.proj)
            for rel in TREE:
                self.assertIn(rel, files)
            with open(os.path.join(REPO, "templates/solo-sdd/project.md"), "rb") as f:
                self.assertEqual(files["solo-sdd/project.md"], f.read())
            lines = out.splitlines()
            self.assertEqual(lines[-1], "next: /project-init")
            self.assertEqual(sorted(l for l in lines if l.startswith("created ")),
                             sorted(["created " + r + ("/" if r in TREE[3:] else "") for r in TREE] + ["created " + CONFIG]
                                    + ["created the solo-sdd rules block in AGENTS.md", "created CLAUDE.md"]))
            self.assertNotIn("openspec", out)
            p = subprocess.run([sys.executable, "-m", "solo_sdd", "validate", "--all"], cwd=e.proj, capture_output=True,
                               text=True, stdin=subprocess.DEVNULL, env=dict(os.environ, PYTHONPATH=REPO))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_repeat(self):
        with Env() as e:
            e.init()
            before = snapshot(e.proj)
            code, out = e.init()
            self.assertEqual(code, 0)
            self.assertEqual(snapshot(e.proj), before)
            self.assertNotIn("created", out)
            self.assertEqual(out.splitlines()[-1], "next: /project-init")

    def test_not_repo(self):
        with Env(git=False) as e:
            code, out = e.init()
            self.assertEqual(code, 1)
            self.assertIn("not a git repository: git init", out.splitlines())
            self.assertEqual(snapshot(e.proj), {})

    def test_openspec_project(self):
        with Env() as e:
            e.write("openspec/config.yaml", "schema: solo\n")
            before = snapshot(e.proj)
            code, out = e.init()
            self.assertEqual(code, 0)
            self.assertEqual(snapshot(e.proj), before)
            self.assertIn("solo-sdd import openspec", out)
            self.assertFalse([l for l in out.splitlines() if l.startswith("created ")], out)

    def test_openspec_next_to_solo_sdd(self):
        with Env() as e:
            e.write("openspec/config.yaml", "schema: solo\n")
            e.write("solo-sdd/project.md", "# Own\n")
            code, out = e.init()
            self.assertEqual(code, 0)
            self.assertEqual(snapshot(e.proj)["solo-sdd/project.md"], b"# Own\n")
            self.assertIn("created solo-sdd/specs/", out.splitlines())

    def test_cli_arguments(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["init", "a", "b"]), 2)

    @marks.slow
    @settings(max_examples=marks.examples(40), deadline=None)
    @given(st.dictionaries(st.sampled_from(FILES), st.text()))
    def test_project_init_tree_property(self, existing):
        """Project init tree: an existing file keeps every byte, a second run creates and changes nothing."""
        with Env() as e:
            for rel, text in existing.items():
                e.write(rel, text)
            before = snapshot(e.proj)
            self.assertEqual(e.init()[0], 0)
            first = snapshot(e.proj)
            for rel, data in before.items():
                self.assertEqual(first[rel], data, rel)
            code, out = e.init()
            self.assertEqual(code, 0)
            self.assertNotIn("created", out)
            self.assertEqual(snapshot(e.proj), first)


def config_values(text):
    from solo_sdd import settings as conf
    return conf.parse_settings(text)


class QuestionsAndFlags(unittest.TestCase):
    """Requirement: Questions and flags; Requirement: Proposed settings (the written comments)."""

    def test_non_interactive(self):
        with Env() as e:
            code, out = e.init("--team", "--agents", "claude", "--set", "dispatch.limit=3")
            self.assertEqual(code, 0, out)
            self.assertNotIn("[", out)
            v = config_values(e.config())
            self.assertEqual((v["mode"], v["agents"], v["dispatch.limit"]), ("team", "claude, other", "3"))

    def test_closed_stdin_cli(self):
        """stdin closed (sys.stdin is None) and, below, stdin from /dev/null: no question, no crash."""
        with Env() as e:
            p = subprocess.run(["/bin/sh", "-c", 'exec "$0" -m solo_sdd init --solo <&-', sys.executable], cwd=e.proj,
                               capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=REPO), timeout=60)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertNotIn("[", p.stdout)
            self.assertIn("mode: solo\n", e.config())
        with Env() as e:
            p = subprocess.run([sys.executable, "-m", "solo_sdd", "init"], cwd=e.proj, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, env=dict(os.environ, PYTHONPATH=REPO), timeout=60)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertNotIn("[", p.stdout)

    def test_only_git_and_gh(self):
        """Project detection calls no program besides git and gh: the Env guard records them and refuses any other."""
        with Env() as e:
            os.rmdir(os.path.join(e.proj, ".git"))
            for args in (["init", "-q"], ["remote", "add", "origin", "https://example.com/x.git"]):
                subprocess.run(["git", *args], cwd=e.proj, check=True, stdin=subprocess.DEVNULL)
            self.assertEqual(e.init()[0], 0)
            self.assertEqual(sorted({c[0] for c in e.calls}), ["gh", "git"])
            self.assertIn("branch protection unknown", e.config())
        with Env() as e, mock.patch.object(init.setup_detect, "_out", lambda cmd, cwd: subprocess.run(["ls"])):
            self.assertRaises(AssertionError, e.init)

    def test_proposals_with_reasons(self):
        with Env() as e:
            self.assertEqual(e.init()[0], 0)
            text = e.config()
            self.assertIn("# mode: authors unknown, no CODEOWNERS, no remote\nmode: solo\n", text)
            self.assertIn("# agents: other: always\nagents: other\n", text)
            self.assertIn("# delivery.mode: no remote\ndelivery.mode: local\n", text)

    def ci_project(self, e, workflow):
        os.rmdir(os.path.join(e.proj, ".git"))
        for args in (["init", "-q"], ["remote", "add", "origin", "https://example.com/x.git"]):
            subprocess.run(["git", *args], cwd=e.proj, check=True, stdin=subprocess.DEVNULL)
        if workflow:
            e.write(".github/workflows/test.yml", "on: push\n")

    def test_a_remote_with_ci(self):
        with Env() as e:
            self.ci_project(e, True)
            code, out = e.init("--yes")
            self.assertEqual(code, 0, out)
            self.assertIn("# delivery.mode: remote origin, CI .github/workflows/test.yml\ndelivery.mode: pr\n", e.config())
            self.assertNotIn("CI workflow", out)

    def test_a_remote_without_ci(self):
        with Env() as e:
            self.ci_project(e, False)
            code, out = e.init("--yes")
            self.assertEqual(code, 0, out)
            self.assertIn("# delivery.mode: remote origin, no CI workflow in .github/workflows\ndelivery.mode: local\n",
                          e.config())
            self.assertIn(init.NO_CI, out)

    def test_pr_chosen_without_ci(self):
        with Env() as e:
            self.ci_project(e, False)
            code, out = e.init("--yes", "--delivery", "pr")
            self.assertEqual(code, 0, out)
            self.assertIn("# delivery.mode: chosen; proposed local: remote origin, no CI workflow in .github/workflows\n"
                          "delivery.mode: pr\n", e.config())
            self.assertIn(init.NO_CI, out)

    def test_yes_on_terminal(self):
        with Env() as e:
            code, out = e.init("--yes", answers=["team"])
            self.assertEqual(code, 0)
            self.assertNotIn("[", out)
            self.assertIn("mode: solo\n", e.config())

    def test_questions(self):
        with Env() as e:
            code, out = e.init(answers=["cloud", "team", "", "pr"])
            self.assertEqual(code, 0, out)
            for prompt in ("mode (solo, team) [solo]: ", "agents (claude, codex, cursor, other) [other]: ",
                           "delivery.mode (local, pr) [local]: "):
                self.assertIn(prompt, out)
            self.assertIn("mode takes solo, team, not 'cloud'", out)
            self.assertIn("mode: proposed solo (authors unknown, no CODEOWNERS, no remote)", out)
            text = e.config()
            self.assertIn("# mode: chosen; proposed solo: authors unknown, no CODEOWNERS, no remote\nmode: team\n", text)
            self.assertIn("delivery.mode: pr\n", text)

    def test_flag_answers_its_question(self):
        with Env() as e:
            code, out = e.init("--delivery", "pr", answers=[])
            self.assertEqual(code, 0)
            self.assertNotIn("delivery.mode (local, pr)", out)
            self.assertIn("mode (solo, team) [solo]: ", out)

    def test_wrong_values(self):
        cases = ((["--set", "delivery.mode=cloud"], "local, pr"), (["--set", "colour=red"], "unknown key colour"),
                 (["--solo", "--team"], "mode given twice"), (["--agents", "vim"], "unknown agent vim"),
                 (["--set", "dispatch.limit"], "--set takes key=value"), (["--set", "dispatch.limit=0"], "whole number"))
        for flags, words in cases:
            with Env() as e:
                code, out = e.init(*flags)
                self.assertEqual(code, 1, flags)
                self.assertIn(words, out)
                self.assertEqual(snapshot(e.proj), {}, flags)

    def test_openspec_no_questions(self):
        with Env() as e:
            e.write("openspec/config.yaml", "schema: solo\n")
            code, out = e.init(answers=[])
            self.assertEqual(code, 0)
            self.assertNotIn("[", out)
            self.assertIn("solo-sdd import openspec", out)

    def test_bad_arguments(self):
        with contextlib.redirect_stdout(io.StringIO()):
            for argv in (["init", "--agents"], ["init", "--colour"], ["init", "a", "b"]):
                self.assertEqual(cli.main(argv), 2, argv)

    def test_terminal_pty(self):
        """The terminal case through a pseudo-terminal: three questions, Enter, Enter, pr."""
        import pty
        with Env() as e:
            master, slave = pty.openpty()
            p = subprocess.Popen([sys.executable, "-m", "solo_sdd", "init"],
                                 cwd=e.proj, stdin=slave, stdout=slave, stderr=slave, env=dict(os.environ, PYTHONPATH=REPO))
            os.close(slave)
            out, sent, end = b"", False, time.time() + 60
            while time.time() < end:
                if not sent and out.count(b"]: ") >= 1:
                    os.write(master, b"\n\npr\n")
                    sent = True
                r, _, _ = select.select([master], [], [], 0.2)
                if r:
                    try:
                        chunk = os.read(master, 4096)
                    except OSError:
                        break
                    if not chunk:
                        break
                    out += chunk
                elif p.poll() is not None:
                    break
            p.wait(10)
            os.close(master)
            self.assertEqual(p.returncode, 0, out)
            for prompt in (b"mode (solo, team) [solo]: ", b"agents (", b"delivery.mode (local, pr) [local]: "):
                self.assertIn(prompt, out)
            self.assertIn("delivery.mode: pr\n", e.config())


class RepeatAndReconfigure(unittest.TestCase):
    """Requirement: Repeat and reconfigure."""

    TEXT = "# own comment\nmode: solo\r\nagents: claude, other\n# tail\n"

    def test_repeat_with_flags(self):
        with Env() as e:
            e.write(CONFIG, self.TEXT)
            code, out = e.init("--team", answers=["team"])
            self.assertEqual(code, 0)
            self.assertIn("solo-sdd/config kept, the flags are not applied: solo-sdd init --reconfigure", out)
            self.assertNotIn("[", out)
            with open(os.path.join(e.proj, CONFIG), "rb") as f:
                self.assertEqual(f.read(), self.TEXT.encode())

    def test_reconfigure_mode_only(self):
        with Env() as e:
            e.write(CONFIG, self.TEXT)
            code, out = e.init("--reconfigure", answers=["team", "", ""])
            self.assertEqual(code, 0, out)
            self.assertIn("mode (solo, team) [solo]: ", out)
            self.assertIn("dispatch.limit (a whole number from 1) [2]: ", out)
            self.assertIn("changed solo-sdd/config", out)
            with open(os.path.join(e.proj, CONFIG), "rb") as f:
                self.assertEqual(f.read(), self.TEXT.replace("mode: solo", "mode: team").encode())

    def test_reconfigure_enter_keeps(self):
        with Env() as e:
            e.write(CONFIG, self.TEXT)
            code, out = e.init("--reconfigure", answers=[""] * 7)
            self.assertEqual(code, 0)
            self.assertNotIn("changed", out)
            with open(os.path.join(e.proj, CONFIG), "rb") as f:
                self.assertEqual(f.read(), self.TEXT.encode())

    def test_reconfigure_flags(self):
        with Env() as e:
            e.write(CONFIG, self.TEXT)
            self.assertEqual(e.init("--reconfigure", "--yes", "--set", "dispatch.limit=4", "--solo")[0], 0)
            with open(os.path.join(e.proj, CONFIG), "rb") as f:
                self.assertEqual(f.read(), (self.TEXT + "dispatch.limit: 4\r\n").encode())

    def test_reconfigure_agents_same_names(self):
        for text in ("agents: codex\n", "agents: other, codex\n", "agents:codex\n", "agents: other,codex\n"):
            with Env() as e:
                e.write(CONFIG, text)
                code, out = e.init("--reconfigure", "--yes", "--agents", "codex")
                self.assertEqual(code, 0)
                self.assertNotIn("changed", out)
                self.assertEqual(e.config(), text)
                for answers in (["", "other,codex"], [""] * 7):
                    code, out = e.init("--reconfigure", answers=answers)
                    self.assertNotIn("changed", out)
                    self.assertEqual(e.config(), text)

    def test_reconfigure_against_the_delivery_section(self):
        """The value in effect includes the AGENTS.md «Delivery» item: an answer that differs from it is written."""
        with Env() as e:
            e.write(CONFIG, self.TEXT)
            e.write("AGENTS.md", "## Delivery\n\n- Mode: pr\n")
            self.assertEqual(e.init("--reconfigure", "--yes", "--delivery", "local")[0], 0)
            self.assertIn("delivery.mode: local", e.config())

    def test_reconfigure_broken(self):
        with Env() as e:
            e.write(CONFIG, "mode solo\n")
            code, out = e.init("--reconfigure", "--yes")
            self.assertEqual(code, 1)
            self.assertIn("solo-sdd/config:1", out)
            self.assertNotIn("created", out)

    FLAGS = (["--solo"], ["--team"], ["--yes"], ["--agents", "claude"], ["--delivery", "pr"],
             ["--set", "dispatch.limit=5"], ["--set", "delivery.mode=cloud"], ["--set", "reply.language=en"])
    LINE = st.one_of(st.sampled_from(["mode: solo", "mode: team", "delivery.mode: pr", "dispatch.limit: 7",
                                      "agents: codex", "# note", "", "broken line", "colour: red"]), st.text(max_size=20))

    @settings(max_examples=60, deadline=None)
    @given(st.lists(LINE, max_size=6), st.sampled_from(["\n", "\r\n", ""]),
           st.lists(st.sampled_from(range(8)), max_size=5), st.lists(st.sampled_from(["", "team", "pr", "x"]), max_size=4))
    def test_repeat_and_reconfigure_property(self, lines, end, picks, answers):
        """Repeat and reconfigure: with any flags or answers and no --reconfigure, an existing config keeps every byte."""
        text = end.join(lines)
        with Env() as e:
            e.write(CONFIG, text)
            flags = [f for i in picks for f in self.FLAGS[i]]
            e.init(*flags, answers=answers)
            with open(os.path.join(e.proj, CONFIG), "rb") as f:
                self.assertEqual(f.read(), text.encode())


def body():
    with open(os.path.join(REPO, "global/AGENTS.md"), encoding="utf-8", newline="") as f:
        return rules_block.norm(f.read())


class ProjectRules(unittest.TestCase):
    """Requirement: Project rules block; Requirement: Rules scope setting."""

    def read(self, e, rel):
        with open(os.path.join(e.proj, rel), "rb") as f:
            return f.read().decode()

    def test_no_file(self):
        with Env() as e:
            code, out = e.init()
            self.assertEqual(code, 0, out)
            self.assertEqual(self.read(e, "AGENTS.md"), rules_block.block(body()))
            self.assertEqual(self.read(e, "CLAUDE.md"), "@AGENTS.md\n")

    def test_own_text_kept_block_at_end(self):
        with Env() as e:
            e.write("AGENTS.md", "# Team rules\r\nown line")
            e.write("CLAUDE.md", "# own claude file\n")
            self.assertEqual(e.init()[0], 0)
            text = self.read(e, "AGENTS.md")
            self.assertTrue(text.startswith("# Team rules\r\nown line\n\n"))
            self.assertEqual(rules_block.parse(text), ("# Team rules\r\nown line\n\n", body(), ""))
            self.assertEqual(self.read(e, "CLAUDE.md"), "# own claude file\n")

    def test_edited_block_is_drift(self):
        with Env() as e:
            e.write("AGENTS.md", "own\n")
            e.init()
            edited = self.read(e, "AGENTS.md").replace("\n", "\nedited line\n", 4)
            e.write("AGENTS.md", edited)
            code, out = e.init("--reconfigure", "--yes")
            self.assertEqual(code, 0)
            self.assertIn("drift   AGENTS.md — the solo-sdd block was edited in place, kept as is", out)
            self.assertEqual(self.read(e, "AGENTS.md"), edited)

    def test_older_block_is_updated(self):
        with Env() as e:
            old = "own\n\n" + rules_block.block("old rules\n")
            e.write("AGENTS.md", old)
            e.write(init.RECORD, init._digest("old rules\n") + "\n")
            code, out = e.init()
            self.assertEqual(code, 0)
            self.assertIn("updated the solo-sdd rules block in AGENTS.md", out)
            self.assertEqual(self.read(e, "AGENTS.md"), "own\n\n" + rules_block.block(body()))
            self.assertEqual(self.read(e, init.RECORD), init._digest(body()) + "\n")

    def test_crlf_checkout_is_not_drift(self):
        """A Windows checkout turns the whole file into CRLF: the same block is ok, an older one is updated with CRLF."""
        with Env() as e:
            e.write("AGENTS.md", "own\n")
            e.init()
            crlf = self.read(e, "AGENTS.md").replace("\n", "\r\n")
            e.write("AGENTS.md", crlf)
            code, out = e.init()
            self.assertEqual(code, 0)
            self.assertNotIn("drift", out)
            self.assertEqual(self.read(e, "AGENTS.md"), crlf)
        with Env() as e:
            e.write("AGENTS.md", ("own\n\n" + rules_block.block("old rules\n")).replace("\n", "\r\n"))
            e.write(init.RECORD, init._digest("old rules\n") + "\n")
            code, out = e.init()
            self.assertIn("updated the solo-sdd rules block in AGENTS.md", out)
            self.assertEqual(self.read(e, "AGENTS.md"), ("own\n\n" + rules_block.block(body())).replace("\n", "\r\n"))

    def test_crlf_rules_source(self):
        """A CRLF clone of the package gives the same LF block and no drift on a repeat."""
        with Env() as e:
            root = os.path.join(e.tmp.name, "pkg")
            os.makedirs(os.path.join(root, "global"))
            with open(os.path.join(root, "global/AGENTS.md"), "w", encoding="utf-8", newline="") as f:
                f.write(body().replace("\n", "\r\n"))
            with mock.patch.object(init.resources, "ROOT", root), mock.patch.object(init.shutil, "copyfile",
                                                                                     lambda a, b: open(b, "w").close()):
                e.init()
                code, out = e.init()
            self.assertEqual(code, 0)
            self.assertNotIn("drift", out)
            self.assertEqual(self.read(e, "AGENTS.md"), rules_block.block(body()))

    def test_unrecorded_other_block_and_broken_or_erased_markers(self):
        b, end = rules_block.BEGIN, rules_block.END
        for text, note in (("x\n" + rules_block.block("someone's rules\n"), "edited in place"),
                           ("x\n%s\n" % b, "broken solo-sdd markers"), ("%s\n%s\n" % (end, b), "broken solo-sdd markers")):
            with Env() as e:
                e.write("AGENTS.md", text)
                code, out = e.init()
                self.assertEqual(code, 0)
                self.assertIn(note, out)
                self.assertEqual(self.read(e, "AGENTS.md"), text)
                self.assertFalse(os.path.exists(os.path.join(e.proj, init.RECORD)))
        with Env() as e:
            e.init()
            e.write("AGENTS.md", "markers gone\n")
            code, out = e.init()
            self.assertIn("the solo-sdd markers were erased", out)
            self.assertEqual(self.read(e, "AGENTS.md"), "markers gone\n")

    def test_scope_global(self):
        with Env() as e:
            code, out = e.init("--set", "rules.scope=global")
            self.assertEqual(code, 0, out)
            self.assertFalse(os.path.exists(os.path.join(e.proj, "AGENTS.md")))
            self.assertIn("rules.scope: global, AGENTS.md gets no block; the rules come from the global block", out)
            self.assertIn("rules.scope: global\n", e.config())
        with Env() as e:
            e.init()
            before = self.read(e, "AGENTS.md")
            code, out = e.init("--reconfigure", "--yes", "--set", "rules.scope=global")
            self.assertIn("AGENTS.md gets no block (an existing one is kept)", out)
            self.assertEqual(self.read(e, "AGENTS.md"), before)
        with Env() as e:
            e.write("AGENTS.md", "own\n")
            code, out = e.init("--set", "rules.scope=global")
            self.assertIn("AGENTS.md gets no block; the rules", out)
            self.assertEqual(self.read(e, "AGENTS.md"), "own\n")

    def test_scope_project(self):
        with Env() as e:
            e.write("AGENTS.md", "own\n")
            self.assertEqual(e.init("--set", "rules.scope=project")[0], 0)
            self.assertEqual(rules_block.parse(self.read(e, "AGENTS.md"))[1], body())
        with Env() as e:
            code, out = e.init("--set", "rules.scope=team")
            self.assertEqual(code, 1)
            self.assertIn("rules.scope takes project, global", out)

    def check_block_property(self, text):
        with Env() as e:
            e.write("AGENTS.md", text)
            self.assertEqual(e.init()[0], 0)
            first = snapshot(e.proj)
            new = first["AGENTS.md"].decode()
            self.assertTrue(new.startswith(text))
            before, got, after = rules_block.parse(new)
            self.assertEqual((before.rstrip("\n") == text.rstrip("\n"), got, after), (True, body(), ""))
            code, out = e.init()
            self.assertEqual((code, snapshot(e.proj)), (0, first), out)

    TEXT = st.one_of(st.text(st.characters(blacklist_categories=("Cs",))),
                     st.lists(st.sampled_from(["# Rules", "line", "", "\r", "  "]), max_size=6).map("\n".join),
                     st.text("ab\n\r", max_size=12))

    @marks.slow
    @settings(max_examples=marks.examples(50), deadline=None)
    @given(TEXT)
    def test_project_rules_block_property(self, text):
        """Project rules block: for an AGENTS.md without markers, init keeps every byte outside the block, a repeat changes nothing."""
        if rules_block.parse(text) is not None:
            return
        self.check_block_property(text)

    def test_property_catches_trimmed_newlines(self):
        real = rules_block.append

        def trimmed(text, b):
            return real(text.rstrip("\n"), b)
        with mock.patch.object(init.rules_block, "append", trimmed):
            self.assertRaises(AssertionError, self.check_block_property, "own\n\n\n")


if __name__ == "__main__":
    unittest.main()
