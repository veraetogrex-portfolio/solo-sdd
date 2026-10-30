#!/usr/bin/env python3
"""solo-sdd: точка входа, колесо, install и блок правил — на временной домашней папке."""
import contextlib, hashlib, io, json, os, shutil, subprocess, sys, tempfile, unittest, zipfile
from unittest import mock

from hypothesis import assume, given, settings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import __version__, cli, layout, rules_block  # noqa: E402

RULES = "global/AGENTS.md"
NET = ("Could not find a version", "No matching distribution", "Temporary failure", "ConnectionError", "Max retries")
DATA_DIRS = ("solo_sdd", "global", "skills", "schema", "templates")


def run(args, home, cwd=REPO, path=None, extra=None):
    env = dict(os.environ, HOME=home)
    if path is not None:
        env["PATH"] = path
    env.update(extra or {})
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def copy_repo(dest):
    """Копия данных репозитория: pull пишет в неё, а не в настоящий global/AGENTS.md."""
    ignore = shutil.ignore_patterns("__pycache__")
    for d in DATA_DIRS:
        shutil.copytree(os.path.join(REPO, d), os.path.join(dest, d), ignore=ignore)
    for f in ("targets.json", "sync.py", "ALGORITHM.md"):
        shutil.copy(os.path.join(REPO, f), dest)


class EntryPoint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)

    def test_version(self):
        code, out, _ = run([sys.executable, "-m", "solo_sdd", "--version"], self.home)
        self.assertEqual((code, out.strip()), (0, __version__))

    def test_no_command_and_unknown(self):
        for args in ([], ["bogus"], ["--bogus"], ["status", "--bogus"], ["sync"], ["sync", "push"]):
            code, out, _ = run([sys.executable, "-m", "solo_sdd", *args], self.home)
            self.assertEqual(code, 2, args)
            self.assertIn("команды solo-sdd", out)

    def test_status_matches_sync_py(self):
        code, out, _ = run([sys.executable, "-m", "solo_sdd", "status"], self.home)
        self.assertEqual(code, 0)
        first, _, rest = out.partition("\n")
        self.assertTrue(first.startswith("источник: "), first)
        self.assertEqual(rest, run([sys.executable, "sync.py", "status"], self.home)[1])

    def test_status_first_line_clean_home(self):
        code, out, _ = run([sys.executable, "-m", "solo_sdd", "status"], self.home)
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0], f"источник: {layout.REPO} {__version__}")

    def test_status_first_line_from_state(self):
        data = os.path.join(self.home, ".local", "share", "solo-sdd")
        os.makedirs(data)
        with open(os.path.join(data, "state.json"), "w") as f:
            json.dump({"_source": "/где/то/ещё", "_version": "9.9.9"}, f)
        code, out, _ = run([sys.executable, "-m", "solo_sdd", "status"], self.home)
        self.assertEqual((code, out.splitlines()[0]), (0, "источник: /где/то/ещё 9.9.9"))

    def pull_from_copy(self, with_git):
        repo = os.path.join(self.tmp, "repo-git" if with_git else "repo-pkg")
        os.makedirs(repo)
        copy_repo(repo)
        if with_git:
            os.makedirs(os.path.join(repo, ".git"))
        env = {"PYTHONPATH": repo}
        self.assertEqual(run([sys.executable, os.path.join(repo, "sync.py"), "push"], self.home, cwd=repo)[0], 0)
        edited = os.path.join(self.home, ".claude/skills/spec-next/SKILL.md")
        with open(edited, "a", encoding="utf-8") as f:
            f.write("\nправка на месте\n")
        code, out, err = run([sys.executable, "-m", "solo_sdd", "sync", "pull", "spec-next"], self.home,
                             cwd=repo, extra=env)
        self.assertEqual(code, 0, err)
        with open(os.path.join(repo, "skills/spec-next/SKILL.md"), encoding="utf-8") as f:
            self.assertIn("правка на месте", f.read())
        return out

    HINT = "источник — установленный пакет: правка пропадёт при обновлении, перенесите её в клон"

    def test_pull_without_git_warns(self):
        self.assertIn(self.HINT, self.pull_from_copy(False).splitlines())

    def test_pull_with_git_silent(self):
        self.assertNotIn(self.HINT, self.pull_from_copy(True))

    def test_upgrade_hint(self):
        git = os.path.join(self.tmp, "clone")
        os.makedirs(os.path.join(git, ".git"))
        plain = os.path.join(self.tmp, "plain")
        os.makedirs(plain)
        self.assertEqual(cli.upgrade_hint("/x/uv/tools/solo-sdd", git), "uv tool upgrade solo-sdd")
        self.assertEqual(cli.upgrade_hint("/x/pipx/venvs/solo-sdd", git), "pipx upgrade solo-sdd")
        self.assertEqual(cli.upgrade_hint("/usr", "/x/node_modules/solo-sdd"), "npm update -g solo-sdd")
        self.assertEqual(cli.upgrade_hint("/usr", git), f"git pull в {git}")
        self.assertEqual(cli.upgrade_hint("/usr", plain),
                         "python3 -m pip install --upgrade git+https://github.com/veraetogrex-portfolio/solo-sdd")

    def test_wheel(self):
        wheels = os.path.join(self.tmp, "wheels")
        code, _, err = run([sys.executable, "-m", "pip", "wheel", ".", "-w", wheels, "--no-deps"], self.home)
        if code != 0 and any(mark in err for mark in NET):
            self.skipTest("сборщик недоступен из-за сети")
        self.assertEqual(code, 0, err[-2000:])
        wheel = os.path.join(wheels, os.listdir(wheels)[0])
        folder = os.path.join(self.tmp, "unpacked")
        with zipfile.ZipFile(wheel) as z:
            names = z.namelist()
            for need in ("solo_sdd/data/skills/spec-next/SKILL.md", "solo_sdd/data/targets.json", "solo_sdd/data/sync.py"):
                self.assertIn(need, names)
            z.extractall(folder)
        expected = len(list(layout.pairs()))
        code, out, err = run([sys.executable, os.path.join(folder, "solo_sdd", "data", "sync.py"), "status"],
                             self.home, cwd=self.tmp)
        self.assertEqual((code, len(out.splitlines())), (0, expected), err)
        code, out, err = run([sys.executable, "-m", "solo_sdd", "status"], self.home, cwd=self.tmp,
                             extra={"PYTHONPATH": folder})
        self.assertEqual(code, 0, err)
        self.assertTrue(out.startswith("источник: " + os.path.join(folder, "solo_sdd", "data") + " "), out)


class Install(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)

    def snapshot(self):
        files, dirs = {}, set()
        for d, subdirs, names in os.walk(self.home):
            dirs.update(os.path.join(d, s) for s in subdirs)
            for n in names:
                p = os.path.join(d, n)
                with open(p, "rb") as f:
                    files[p] = (f.read(), os.stat(p).st_mtime_ns)
        return files, dirs

    def test_install_without_openspec(self):
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty)
        code, out, _ = run([sys.executable, "-m", "solo_sdd", "install"], self.home, path=empty)
        self.assertEqual(code, 1)
        self.assertIn("fail openspec:", out)
        self.assertIn("npm i -g @fission-ai/openspec", out)
        self.assertTrue(os.path.exists(os.path.join(self.home, ".claude/skills/spec-next/SKILL.md")))
        with open(os.path.join(self.home, ".claude/CLAUDE.md"), encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), rules_block.block(layout.read(os.path.join(REPO, RULES))))
        self.assertFalse(os.path.exists(os.path.join(self.home, ".local/share/openspec/schemas/solo")))

    def fake_openspec(self):
        bin_dir = os.path.join(self.tmp, "bin")
        os.makedirs(bin_dir)
        with open(os.path.join(bin_dir, "openspec"), "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(os.path.join(bin_dir, "openspec"), 0o755)
        return bin_dir

    def test_schema_build_failure(self):
        bin_dir = self.fake_openspec()
        data = os.path.join(self.home, ".local", "share", "solo-sdd")
        failed = subprocess.CompletedProcess([], 1, "ОШИБКА схема: нет якоря\n", "")
        out = io.StringIO()
        with mock.patch.multiple(layout, HOME=self.home, DATA=data, STATE=os.path.join(data, "state.json")), \
                mock.patch.dict(os.environ, {"PATH": bin_dir}), \
                mock.patch.object(cli.subprocess, "run", return_value=failed), \
                contextlib.redirect_stdout(out):
            code = cli.main(["install"])
        self.assertEqual(code, 1)
        self.assertIn("fail openspec: схема solo не собрана: ОШИБКА схема: нет якоря", out.getvalue().splitlines())

    @unittest.skipUnless(shutil.which("openspec"), "openspec не установлен")
    def test_real_schema_build_on_clean_home(self):
        code, out, err = run([sys.executable, "-m", "solo_sdd", "install"], self.home)
        self.assertEqual(code, 0, out + err)
        for _, _, target, _ in layout.pairs():
            self.assertTrue(os.path.exists(target.replace(layout.HOME, self.home, 1)), target)
        code, out, err = run(["openspec", "schemas"], self.home)
        self.assertRegex(out, r"(?m)^\s*solo\b")

    def test_update_prints_upgrade_hint_last(self):
        for schema in (1, 0):
            code, out = inproc(self.home, "update", schema=schema, prefix="/x/uv/tools/solo-sdd")
            self.assertEqual(code, schema)
            self.assertEqual(out.splitlines()[-1], "uv tool upgrade solo-sdd")

    def test_repeat_changes_nothing(self):
        bin_dir = os.path.join(self.tmp, "bin")
        os.makedirs(bin_dir)
        fake = os.path.join(bin_dir, "openspec")
        with open(fake, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(fake, 0o755)
        schema = os.path.join(self.home, ".local/share/openspec/schemas/solo/schema.yaml")
        built = []

        def fake_build(*a, **k):
            built.append(a)
            os.makedirs(os.path.dirname(schema), exist_ok=True)
            with open(schema, "w") as f:
                f.write("name: solo\n")
            return subprocess.CompletedProcess(a, 0, "", "")

        data = os.path.join(self.home, ".local", "share", "solo-sdd")
        patches = [mock.patch.object(layout, "HOME", self.home), mock.patch.object(layout, "DATA", data),
                   mock.patch.object(layout, "STATE", os.path.join(data, "state.json")),
                   mock.patch.dict(os.environ, {"PATH": bin_dir}), mock.patch.object(cli.subprocess, "run", fake_build)]
        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["install"]), 0)
            self.assertEqual(len(built), 1)
            before = self.snapshot()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(cli.main(["install"]), 0)
        self.assertEqual(len(built), 1, "сборка схемы запускалась повторно")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("всё разложено", out.getvalue())
        self.assertFalse(os.path.isdir(os.path.join(data, "backup")))


class ManagedBlock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = layout.read(os.path.join(REPO, RULES))
        cls.body = rules_block.norm(cls.source)

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, ".claude"))
        self.claude = os.path.join(self.home, ".claude", "CLAUDE.md")
        self.state_file = os.path.join(self.home, ".local/share/solo-sdd/state.json")

    def sync(self, *args, repo=REPO):
        return run([sys.executable, os.path.join(repo, "sync.py"), *args], self.home, cwd=self.tmp)[:2]

    def put(self, data):
        with open(self.claude, "wb") as f:
            f.write(data)

    def get(self):
        with open(self.claude, "rb") as f:
            return f.read()

    def state(self):
        with open(self.state_file) as f:
            return json.load(f)

    def set_state(self, **entries):
        os.makedirs(os.path.dirname(self.state_file))
        with open(self.state_file, "w") as f:
            json.dump(entries, f)

    def kind(self, repo=REPO):
        for line in self.sync("status", repo=repo)[1].splitlines():
            if line.endswith("CLAUDE.md"):
                return line.split()[0]

    def backups(self):
        root = os.path.join(self.home, ".local/share/solo-sdd/backup")
        found = []
        for d, _, names in os.walk(root):
            for n in names:
                with open(os.path.join(d, n), "rb") as f:
                    found.append(f.read())
        return found

    def test_own_rules_kept_block_appended(self):
        mine = "мои правила\nбез перевода строки в конце".encode()
        self.put(mine)
        self.assertEqual(self.sync("push")[0], 0)
        self.assertEqual(self.get(), mine + b"\n\n" + rules_block.block(self.body).encode())
        self.assertEqual(self.backups(), [mine])
        self.assertEqual(self.state()["_blocks"]["~/.claude/CLAUDE.md"], "\n\n")
        self.assertEqual(self.kind(), "ok")

    def test_migration_of_owner_layout(self):
        self.put(self.source.encode())
        self.set_state(**{"~/.claude/CLAUDE.md": digest(self.source)})
        self.assertEqual(self.kind(), "outdated")
        self.assertEqual(self.sync("push")[0], 0)
        self.assertEqual(self.kind(), "ok")
        self.assertEqual(self.backups(), [])
        self.assertIsNone(self.state()["_blocks"]["~/.claude/CLAUDE.md"])
        lines = [l for l in self.get().decode().splitlines(True) if "solo-sdd:" not in l]
        self.assertEqual("".join(lines), self.source)

    def test_migration_with_new_source(self):
        old = "старый текст\n"
        self.put(old.encode())
        self.set_state(**{"~/.claude/CLAUDE.md": digest(old)})
        self.assertEqual(self.sync("push")[0], 0)
        self.assertEqual(self.get(), rules_block.block(self.body).encode())
        self.assertEqual(self.backups(), [old.encode()])

    def test_edit_inside_block_is_drift_and_pull_takes_body(self):
        self.assertEqual(self.sync("push")[0], 0)
        edited = self.get().decode().replace(self.body.splitlines()[0], "ПРАВКА НА МЕСТЕ", 1)
        self.put(edited.encode())
        self.assertEqual(self.kind(), "drift")
        self.assertEqual(self.sync("push")[0], 1)
        self.assertEqual(self.get().decode(), edited)
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(repo)
        copy_repo(repo)
        code, out = self.sync("pull", RULES, repo=repo)
        self.assertEqual(code, 0, out)
        with open(os.path.join(repo, RULES), encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), rules_block.parse(edited)[1])
        self.assertEqual(self.kind(repo), "ok")

    def test_first_without_marks_is_not_pulled(self):
        self.put("чужие правила\n".encode())
        self.assertEqual(self.kind(), "first")
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(repo)
        copy_repo(repo)
        code, out = self.sync("pull", RULES, repo=repo)
        self.assertEqual(code, 0)
        with open(os.path.join(repo, RULES), encoding="utf-8") as f:
            self.assertEqual(f.read(), self.source)

    def test_broken_marks_are_never_written(self):
        b, e = rules_block.BEGIN, rules_block.END
        for bad in (f"a\n{b}\nx\n", f"{e}\nx\n{b}\n", f"{b}\n1\n{e}\n{b}\n2\n{e}\n", f"{e}\n"):
            self.put(bad.encode())
            self.assertEqual(self.kind(), "drift", bad)
            for args in (("push",), ("push", "--force")):
                code, out = self.sync(*args)
                self.assertEqual(code, 1)
                self.assertIn("битые метки", out)
                self.assertEqual(self.get(), bad.encode())

    def erased(self):
        """Блок стоял, метки стёрты, человек дописал текст."""
        self.assertEqual(self.sync("push")[0], 0)
        text = self.get().decode().replace(rules_block.BEGIN + "\n", "").replace(rules_block.END + "\n", "")
        text += "личная дописка\n"
        self.put(text.encode())
        return text.encode()

    def test_erased_marks_are_never_written_or_pulled(self):
        mine = self.erased()
        self.assertEqual(self.kind(), "drift")
        for args in (("push",), ("push", "--force")):
            code, out = self.sync(*args)
            self.assertEqual(code, 1)
            self.assertIn("битые метки", out)
            self.assertEqual(self.get(), mine)
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(repo)
        copy_repo(repo)
        code, out = self.sync("pull", RULES, repo=repo)
        self.assertEqual(code, 1)
        self.assertIn("CLAUDE.md", out)
        with open(os.path.join(repo, RULES), encoding="utf-8") as f:
            self.assertEqual(f.read(), self.source)

    def test_pull_with_broken_marks_names_file(self):
        self.put(f"a\n{rules_block.BEGIN}\nx\n".encode())
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(repo)
        copy_repo(repo)
        code, out = self.sync("pull", RULES, repo=repo)
        self.assertEqual(code, 1)
        self.assertIn("~/.claude/CLAUDE.md", out)
        self.assertNotIn("копий, отличных от репозитория, нет", out)
        with open(os.path.join(repo, RULES), encoding="utf-8") as f:
            self.assertEqual(f.read(), self.source)

    def test_old_layout_edited_in_place_force_appends_block(self):
        mine = ("старая раскладка\n" + self.source + "правка\n").encode()
        self.put(mine)
        self.set_state(**{"~/.claude/CLAUDE.md": digest(self.source)})
        self.assertEqual(self.kind(), "drift")
        self.assertEqual(self.sync("push", "--force")[0], 0)
        self.assertTrue(self.get().startswith(mine))
        self.assertIn(rules_block.block(self.body).encode(), self.get())
        self.assertEqual(self.backups(), [mine])

    def test_no_rules_file_equals_block(self):
        self.assertFalse(os.path.exists(self.claude))
        self.assertEqual(self.sync("push")[0], 0)
        self.assertEqual(self.get().decode(), rules_block.block(self.source))
        self.assertEqual(self.kind(), "ok")

    def test_mark_substring_inside_line_is_text(self):
        human = f"см. {rules_block.BEGIN} в середине строки\n".encode()
        self.put(human)
        self.assertEqual(self.sync("push")[0], 0)
        self.assertEqual(self.get(), human + b"\n" + rules_block.block(self.body).encode())

    def test_not_utf8_is_unreachable_and_untouched(self):
        raw = b"\xff\xfe\x00 rules\n"
        self.put(raw)
        self.assertEqual(self.kind(), "unreachable")
        for args in (("push",), ("push", "--force")):
            self.assertEqual(self.sync(*args)[0], 1)
            self.assertEqual(self.get(), raw)

    def test_crlf_of_human_is_kept(self):
        human = b"a\r\nb\r\n"
        self.put(human)
        self.assertEqual(self.sync("push")[0], 0)
        self.assertTrue(self.get().startswith(human))
        self.assertEqual(self.get(), human + b"\n" + rules_block.block(self.body).encode())
        self.assertEqual(self.backups(), [human])


class BlockProperty(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(os.path.join(self.repo, "global"))
        with open(os.path.join(self.repo, "targets.json"), "w") as f:
            json.dump({"roots": {}, "skills": {},
                       "files": {RULES: {"mode": "block", "copies": ["~/AGENTS.md"]}}}, f)

    def source(self, text):
        with open(os.path.join(self.repo, RULES), "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return rules_block.norm(layout.read(os.path.join(self.repo, RULES)))

    human = st.one_of(
        st.just(""), st.text(alphabet=" \t\n\r", max_size=6),
        st.text(max_size=20).filter(lambda t: not t.endswith("\n")),
        st.just("x\n<!-- не метка\n"), st.just("<!--"), st.just("a\r\nb\r\n"), st.just("a\x0bb\x85c\n"),
        st.text(max_size=40))
    bodies = st.one_of(st.just(""), st.just("x"), st.just("\n"), st.text(max_size=40))

    @settings(max_examples=100, deadline=None)
    @given(human, bodies, bodies)
    def test_managed_rules_block_property(self, human, first, second):
        assume(rules_block.parse(human) is None)
        home = tempfile.mkdtemp(dir=self.tmp)
        data = os.path.join(home, ".local", "share", "solo-sdd")
        copy = os.path.join(home, "AGENTS.md")
        key = "~/AGENTS.md"
        with open(copy, "wb") as f:
            f.write(human.encode())

        def disk():
            with open(copy, "rb") as f:
                return f.read()

        def push():
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(layout.push(), 0)

        with mock.patch.multiple(layout, REPO=self.repo, HOME=home, DATA=data, STATE=os.path.join(data, "state.json")):
            body = self.source(first)
            assume(isinstance(rules_block.parse(rules_block.block(body)), tuple))
            push()
            sep = layout.load_state()["_blocks"][key]
            self.assertTrue(disk().startswith(human.encode()))
            self.assertEqual(disk(), human.encode() + sep.encode() + rules_block.block(body).encode())
            snapshot = (disk(), layout.load_state())
            push()
            self.assertEqual((disk(), layout.load_state()), snapshot, "повтор раскладки что-то изменил")
            body = self.source(second)
            assume(isinstance(rules_block.parse(rules_block.block(body)), tuple))
            push()
            self.assertEqual(disk(), human.encode() + sep.encode() + rules_block.block(body).encode())
            self.assertEqual(rules_block.remove(disk().decode(), sep), human)


class RulesBlockUnit(unittest.TestCase):
    @given(st.text(max_size=40))
    def test_append_remove_roundtrip(self, text):
        assume(rules_block.parse(text) is None)
        new, sep = rules_block.append(text, "body")
        self.assertEqual(rules_block.remove(new, sep), text)


D = "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"
MINE = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}}


def inproc(home, *args, repo=None, schema=0, prefix=None):
    """cli.main в этом процессе на временной домашней папке; схема solo не собирается."""
    data = os.path.join(home, ".local", "share", "solo-sdd")
    out = io.StringIO()
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.multiple(layout, HOME=home, DATA=data, STATE=os.path.join(data, "state.json")))
        stack.enter_context(mock.patch.dict(os.environ, {"HOME": home}))
        stack.enter_context(mock.patch.object(cli, "build_schema", lambda force: schema))
        if prefix:
            stack.enter_context(mock.patch.object(cli.sys, "prefix", prefix))
        if repo:
            stack.enter_context(mock.patch.object(layout, "REPO", repo))
        stack.enter_context(contextlib.redirect_stdout(out))
        code = cli.main(list(args))
    return code, out.getvalue()


class Hooks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.settings = os.path.join(self.home, ".claude", "settings.json")
        self.state_file = os.path.join(self.home, ".local/share/solo-sdd/state.json")
        os.makedirs(os.path.dirname(self.settings))

    def put(self, text, path=None):
        with open(path or self.settings, "wb") as f:
            f.write(text if isinstance(text, bytes) else text.encode())

    def get(self, path=None):
        with open(path or self.settings, "rb") as f:
            return f.read()

    def state(self):
        with open(self.state_file) as f:
            return json.load(f)

    def baks(self):
        return sorted(n for n in os.listdir(os.path.dirname(self.settings)) if ".bak-" in n)

    def tree(self):
        found = {}
        for d, _, names in os.walk(self.home):
            for n in names:
                with open(os.path.join(d, n), "rb") as f:
                    found[os.path.join(d, n)] = f.read()
        return found

    def test_without_flag_settings_untouched(self):
        self.put(json.dumps(MINE, indent=4))
        before = (self.get(), os.stat(self.settings).st_mtime_ns)
        self.assertEqual(inproc(self.home, "install")[0], 0)
        self.assertEqual((self.get(), os.stat(self.settings).st_mtime_ns), before)
        self.assertEqual(self.baks(), [])
        self.assertNotIn("_hooks", self.state())

    def test_install_hooks_keeps_mine_and_records(self):
        raw = json.dumps(MINE, indent=4)
        self.put(raw)
        code, out = inproc(self.home, "install", "--hooks")
        self.assertEqual(code, 0, out)
        text = self.get().decode()
        self.assertIn("echo mine", text)
        self.assertIn("work_hooks.py", text)
        self.assertIn("глубина субагентов 2: записана", out)
        baks = self.baks()
        self.assertEqual(len(baks), 1)
        self.assertEqual(self.get(os.path.join(os.path.dirname(self.settings), baks[0])), raw.encode())
        steps = self.state()["_hooks"]
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["env"], {D: "2"})
        self.assertEqual(steps[0]["backup"], "~/.claude/" + baks[0])

    def test_depth_of_owner_kept(self):
        self.put(json.dumps({"env": {D: "3"}}))
        code, out = inproc(self.home, "install", "--hooks")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.get())["env"], {D: "3"})
        self.assertNotIn("env", self.state()["_hooks"][0])
        self.assertIn("глубина субагентов 3: задана владельцем, не меняю", out)

    def test_repeat_changes_nothing(self):
        self.put(json.dumps(MINE, indent=4))
        inproc(self.home, "install", "--hooks")
        before = self.tree()
        code, out = inproc(self.home, "install", "--hooks")
        self.assertEqual(code, 0)
        self.assertEqual(self.tree(), before)
        self.assertEqual(len(self.state()["_hooks"]), 1)
        self.assertIn("глубина субагентов 2: записана", out)

    def test_missing_settings_created_and_removed(self):
        os.rmdir(os.path.dirname(self.settings))
        self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        self.assertTrue(os.path.isfile(self.settings))
        self.assertIsNone(self.state()["_hooks"][0]["backup"])
        self.assertEqual(inproc(self.home, "uninstall")[0], 0)
        self.assertFalse(os.path.exists(self.settings))
        self.assertNotIn("_hooks", self.state())

    def test_hostile_input(self):
        for bad in ('{"hooks": {"Stop": [', "[]", '{"hooks": []}', '{"env": 1}', '{"autoMode": []}',
                    '{"hooks": {"Stop": {}}}', b"\xff\xfe{}"):
            self.put(bad)
            code, out = inproc(self.home, "install", "--hooks")
            self.assertEqual(code, 1, bad)
            self.assertIn("fail settings:", out)
            self.assertEqual(self.get(), bad if isinstance(bad, bytes) else bad.encode())
            self.assertEqual(self.baks(), [])
            self.assertTrue(os.path.exists(os.path.join(self.home, ".claude/skills/spec-next/SKILL.md")))
            self.assertNotIn("_hooks", self.state())

    def test_script_matches_install_hooks(self):
        other = os.path.join(self.tmp, "other")
        os.makedirs(os.path.join(other, ".claude"))
        raw = json.dumps(MINE, indent=4)
        self.put(raw)
        self.put(raw, os.path.join(other, ".claude", "settings.json"))
        inproc(self.home, "install", "--hooks")
        code, out, err = run(["/usr/bin/python3", os.path.join(REPO, "global", "work_hooks_settings.py")], other)
        self.assertEqual(code, 0, err)
        self.assertIn("ok: хуки подключены", out)
        self.assertEqual(self.get(), self.get(os.path.join(other, ".claude", "settings.json")))
        with open(os.path.join(other, ".local/share/solo-sdd/state.json")) as f:
            self.assertEqual(len(json.load(f)["_hooks"]), 1)

    def test_uninstall_returns_as_it_was(self):
        rules = os.path.join(self.home, ".claude", "CLAUDE.md")
        mine = "мои правила\r\nбез конца".encode()
        settings_raw = b'{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo mine"}]}]}}\n'
        self.put(mine, rules)
        self.put(settings_raw)
        self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        self.assertNotEqual(self.get(), settings_raw)
        code, out = inproc(self.home, "uninstall")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.get(rules), mine)
        self.assertEqual(self.get(), settings_raw)
        self.assertFalse(os.path.exists(os.path.join(self.home, ".claude/skills/spec-next")))

    def test_edited_skill_stays(self):
        inproc(self.home, "install")
        edited = os.path.join(self.home, ".codex/skills/spec-next/SKILL.md")
        with open(edited, "a") as f:
            f.write("правка\n")
        code, out = inproc(self.home, "uninstall")
        self.assertEqual(code, 0)
        self.assertIn("оставлено", out)
        self.assertIn("~/.codex/skills/spec-next/SKILL.md", out)
        left = [p for p in self.tree() if "/skills/" in p]
        self.assertEqual(left, [edited])
        for root in (".agents/skills", ".claude/skills"):
            self.assertEqual(os.listdir(os.path.join(self.home, root)), [])
        self.assertEqual(os.listdir(os.path.join(self.home, ".codex/skills/spec-next")), ["SKILL.md"])

    def test_source_updated_before_uninstall(self):
        rules = os.path.join(self.home, ".claude", "CLAUDE.md")
        mine = b"human\nno newline"
        self.put(mine, rules)
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(repo)
        copy_repo(repo)
        self.assertEqual(inproc(self.home, "install", repo=repo)[0], 0)
        with open(os.path.join(repo, RULES), "a", encoding="utf-8") as f:
            f.write("\nновая строка\n")
        self.assertEqual(inproc(self.home, "install", repo=repo)[0], 0)
        self.assertIn("новая строка", self.get(rules).decode())
        self.assertEqual(inproc(self.home, "uninstall", repo=repo)[0], 0)
        self.assertEqual(self.get(rules), mine)

    def test_human_edits_after_install_survive(self):
        rules = os.path.join(self.home, ".claude", "CLAUDE.md")
        self.put(b"human\n", rules)
        self.put(json.dumps({"model": "x"}))
        inproc(self.home, "install", "--hooks")
        s = json.loads(self.get())
        s["added"] = [1]
        self.put(json.dumps(s))
        with open(rules, "a") as f:
            f.write("после\n")
        code, out = inproc(self.home, "uninstall")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(self.get()), {"model": "x", "added": [1]})
        self.assertEqual(self.get(rules), "human\nпосле\n".encode())

    def test_uninstall_broken_settings(self):
        inproc(self.home, "install", "--hooks")
        broken = b'{"hooks": ['
        self.put(broken)
        code, out = inproc(self.home, "uninstall")
        self.assertEqual(code, 1)
        self.assertIn("fail settings:", out)
        self.assertEqual(self.get(), broken)
        self.assertEqual(len(self.state()["_hooks"]), 1)

    def test_uninstall_broken_marks(self):
        inproc(self.home, "install")
        rules = os.path.join(self.home, ".claude", "CLAUDE.md")
        bad = (self.get(rules).decode() + rules_block.BEGIN + "\n").encode()
        self.put(bad, rules)
        code, out = inproc(self.home, "uninstall")
        self.assertEqual(code, 0)
        self.assertIn("битые метки", out)
        self.assertIn("~/.claude/CLAUDE.md", out)
        self.assertEqual(self.get(rules), bad)

    def test_purge(self):
        schema = os.path.join(self.home, ".local/share/openspec/schemas/solo")
        os.makedirs(schema)
        inproc(self.home, "install")
        inproc(self.home, "uninstall")
        self.assertTrue(os.path.isdir(schema))
        self.assertEqual(inproc(self.home, "uninstall", "--purge")[0], 0)
        self.assertFalse(os.path.exists(schema))
        self.assertFalse(os.path.exists(os.path.join(self.home, ".local/share/solo-sdd")))

    def test_purge_with_broken_settings_keeps_schema(self):
        schema = os.path.join(self.home, ".local/share/openspec/schemas/solo")
        os.makedirs(schema)
        inproc(self.home, "install", "--hooks")
        self.put(b'{"hooks": [')
        code, out = inproc(self.home, "uninstall", "--purge")
        self.assertEqual(code, 1)
        self.assertIn("fail purge:", out)
        self.assertTrue(os.path.isdir(schema))

    def test_unknown_flags(self):
        self.assertEqual(inproc(self.home, "install", "--bogus")[0], 2)
        self.assertEqual(inproc(self.home, "uninstall", "--hooks")[0], 2)
        self.assertEqual(inproc(self.home, "install", "--purge")[0], 2)


class Doctor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.home)
        os.makedirs(self.bin)
        self.schema = os.path.join(self.home, ".local/share/openspec/schemas/solo/schema.yaml")
        self.state_file = os.path.join(self.home, ".local/share/solo-sdd/state.json")

    def fake(self, version, schemas="  solo (user override)"):
        path = os.path.join(self.bin, "openspec")
        with open(path, "w") as f:
            f.write('#!/bin/sh\ncase "$1" in --version) echo %s;; schemas) echo "%s";; esac\n' % (version, schemas))
        os.chmod(path, 0o755)

    def installed(self, version="1.14.0"):
        self.fake(version)
        os.makedirs(os.path.dirname(self.schema))
        with open(self.schema, "w") as f:
            f.write("name: solo\n")
        self.assertEqual(self.go("install")[0], 0)

    def go(self, *args, extra=None):
        env = {"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": ""}
        env.update(extra or {})
        return run([sys.executable, "-m", "solo_sdd", *args], self.home, path=self.bin, extra=env)

    def state(self):
        with open(self.state_file) as f:
            return json.load(f)

    def save(self, state):
        with open(self.state_file, "w") as f:
            json.dump(state, f)

    def test_no_openspec(self):
        code, out, _ = self.go("doctor")
        self.assertEqual(code, 1)
        self.assertRegex(out, r"(?m)^fail openspec: .*npm i -g @fission-ai/openspec")

    def test_old_openspec(self):
        self.fake("1.13.0")
        code, out, _ = self.go("doctor")
        self.assertEqual(code, 1)
        self.assertIn("fail openspec: версия 1.13.0", out)

    def test_all_good(self):
        self.installed()
        code, out, _ = self.go("doctor", extra={"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "2"})
        self.assertEqual(code, 0, out)
        for name in ("python", "openspec", "schema", "layout", "hooks", "depth"):
            self.assertRegex(out, r"(?m)^(ok|warn) %s: " % name)
        self.assertNotIn("fail", out)

    def test_schema_missing(self):
        self.fake("1.14.0", schemas="  spec-driven")
        code, out, _ = self.go("doctor")
        self.assertEqual(code, 1)
        self.assertRegex(out, r"(?m)^fail schema: ")

    def test_no_gh_is_warning(self):
        self.installed()
        code, out, _ = self.go("doctor", extra={"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "2"})
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"(?m)^warn gh: ")

    def test_empty_depth_falls_back_to_settings(self):
        self.installed()
        os.makedirs(os.path.join(self.home, ".claude"), exist_ok=True)
        with open(os.path.join(self.home, ".claude/settings.json"), "w") as f:
            json.dump({"env": {D: "2"}}, f)
        code, out, _ = self.go("doctor")
        self.assertIn("ok depth: 2", out.splitlines())

    @unittest.skipUnless(os.path.exists("/usr/bin/python3"), "нет /usr/bin/python3")
    def test_python_hooks_ok(self):
        self.fake("1.14.0")
        self.assertRegex(self.go("doctor")[1], r"(?m)^ok python-hooks: ")

    def test_drift(self):
        self.installed()
        self.go("install")
        target = os.path.join(self.home, ".claude/skills/spec-next/SKILL.md")
        with open(target, "a") as f:
            f.write("\nправка\n")
        code, out, _ = self.go("doctor")
        self.assertEqual(code, 1)
        self.assertRegex(out, r"(?m)^fail layout: .*drift 1")

    def test_hooks_removed(self):
        self.installed()
        self.assertEqual(self.go("install", "--hooks")[0], 0)
        self.assertIn("ok hooks: на месте", self.go("doctor")[1])
        os.remove(os.path.join(self.home, ".claude/settings.json"))
        code, out, _ = self.go("doctor")
        self.assertEqual(code, 1)
        self.assertIn("fail hooks:", out)

    def test_depth_one(self):
        self.installed()
        code, out, _ = self.go("doctor", extra={"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1"})
        self.assertEqual(code, 0, out)
        self.assertIn("warn depth:", out)
        self.assertIn("solo-sdd install --hooks", out)

    def test_other_source(self):
        self.installed()
        state = self.state()
        state["_source"] = os.path.join(self.tmp, "elsewhere")
        self.save(state)
        code, out, _ = self.go("doctor")
        self.assertIn("warn source: разложено из", out)


class UninstallProperty(unittest.TestCase):
    @staticmethod
    def settings_strategy():
        from solo_sdd import hooks
        need = hooks._need()
        group = st.fixed_dictionaries({"hooks": st.just([{"type": "command", "command": "echo mine"}])})
        old_ours = {"hooks": [{"type": "command", "command": "old work_hooks.py beat"}]}
        ev = st.sampled_from(["Stop", "PreToolUse", "SessionStart", "PostToolUse", "Custom"])

        def events(e):
            exact = need.get(e, [])
            return st.one_of(
                st.just([]), st.lists(group, max_size=2), st.lists(st.just(old_ours), min_size=1, max_size=2),
                st.builds(lambda a, b, c: a + b + c, st.lists(group, max_size=1), st.just(list(exact)), st.lists(group, max_size=1)),
                st.builds(lambda a, b: a + [old_ours] + b, st.lists(group, max_size=1), st.lists(group, max_size=1)))

        hook = st.dictionaries(ev, st.none(), max_size=3).flatmap(
            lambda d: st.fixed_dictionaries({e: events(e) for e in d}))
        prefixed = hooks.P + " старая версия"
        auto = st.one_of(
            st.just({}), st.just({"allow": []}), st.just({"allow": ["$defaults"]}),
            st.just({"allow": ["$defaults", prefixed, "чужое"]}), st.just({"allow": ["чужое", prefixed, "ещё", prefixed + "2"]}),
            st.just({"allow": [hooks.RULE]}), st.just({"allow": ["a", hooks.RULE, "b"]}))
        env = st.sampled_from([{}, {"A": "1"}, {hooks.D: "3"}, {hooks.D: "2"}, {"A": "1", hooks.D: "2"}])
        leaf = st.recursive(st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=5)),
                            lambda c: st.one_of(st.lists(c, max_size=3), st.dictionaries(st.text(max_size=3), c, max_size=3)),
                            max_leaves=6)
        return st.fixed_dictionaries({}, optional={
            "hooks": hook, "env": env, "autoMode": auto,
            "statusLine": st.just({"type": "command", "command": "mine"}), "model": st.text(max_size=5),
            "extra": leaf, "permissions": st.fixed_dictionaries({"allow": st.lists(st.text(max_size=4), max_size=2)})})

    dumps = st.sampled_from([
        lambda x: json.dumps(x), lambda x: json.dumps(x, indent=4), lambda x: json.dumps(x, separators=(",", ":")),
        lambda x: json.dumps(x, ensure_ascii=False), lambda x: json.dumps(x, indent=2, ensure_ascii=False)])

    @settings(max_examples=60, deadline=None)
    @given(st.data())
    def test_uninstall_restores_property(self, data):
        human = data.draw(BlockProperty.human)
        assume(rules_block.parse(human) is None)
        present = data.draw(st.booleans())
        value = data.draw(self.settings_strategy())
        text = data.draw(self.dumps)(value) + data.draw(st.sampled_from(["", "\n"]))
        home = tempfile.mkdtemp()
        try:
            claude = os.path.join(home, ".claude")
            os.makedirs(claude)
            rules = os.path.join(claude, "CLAUDE.md")
            path = os.path.join(claude, "settings.json")
            with open(rules, "wb") as f:
                f.write(human.encode())
            if present:
                with open(path, "wb") as f:
                    f.write(text.encode())
            self.assertEqual(inproc(home, "install", "--hooks")[0], 0)
            self.assertEqual(inproc(home, "uninstall")[0], 0)
            with open(rules, "rb") as f:
                self.assertEqual(f.read(), human.encode())
            if present:
                with open(path, "rb") as f:
                    self.assertEqual(f.read(), text.encode())
            else:
                self.assertFalse(os.path.exists(path))
        finally:
            shutil.rmtree(home, True)


if __name__ == "__main__":
    unittest.main()
