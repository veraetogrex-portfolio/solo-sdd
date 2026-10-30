#!/usr/bin/env python3
"""sync.py на временной домашней папке и временной копии репозитория: живые места не трогаются."""
import contextlib, importlib.util, io, json, os, re, shutil, subprocess, sys, tempfile, unittest
from unittest import mock

from hypothesis import given, settings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECOND = "20261021-145202"
# Запуск sync.py, в котором время и pid не меняются: все запуски попадают в одну секунду с одним pid.
FROZEN = ("import os, runpy, sys, time; time.strftime = lambda *a: %r; os.getpid = lambda: 1; "
          "sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')" % SECOND)


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, "home")
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.home)
        os.makedirs(os.path.join(self.repo, "skills", "alpha"))
        os.makedirs(os.path.join(self.repo, "global"))
        shutil.copy(os.path.join(REPO, "sync.py"), self.repo)
        self.put("skills/alpha/SKILL.md", "alpha v1\n")
        self.put("global/AGENTS.md", "rules v1\n")
        self.put("targets.json", json.dumps({
            "roots": {"agents": "~/.agents/skills", "codex": "~/.codex/skills"},
            "skills": {"alpha": ["agents", "codex"]},
            "files": {"global/AGENTS.md": ["~/AGENTS.md"]},
        }))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def put(self, rel, text):
        with open(os.path.join(self.repo, rel), "w") as f:
            f.write(text)

    def home_path(self, rel):
        return os.path.join(self.home, rel)

    def text(self, path):
        with open(path) as f:
            return f.read()

    def run_sync(self, *args):
        result = subprocess.run([sys.executable, os.path.join(self.repo, "sync.py"), *args],
                                env=dict(os.environ, HOME=self.home), capture_output=True, text=True)
        return result.returncode, result.stdout

    def run_frozen(self, *args):
        result = subprocess.run([sys.executable, "-c", FROZEN, os.path.join(self.repo, "sync.py"), *args],
                                env=dict(os.environ, HOME=self.home), capture_output=True, text=True)
        return result.returncode, result.stdout

    def backups(self):
        """{имя папки запуска: [тексты резервных копий]}."""
        root = self.home_path(".local/share/solo-sdd/backup")
        return {name: [self.text(os.path.join(d, f)) for d, _, files in os.walk(os.path.join(root, name)) for f in files]
                for name in sorted(os.listdir(root))} if os.path.isdir(root) else {}

    def kinds(self):
        _, out = self.run_sync("status")
        return [line.split()[0] for line in out.splitlines()]

    def test_push_creates_then_updates_outdated(self):
        self.assertEqual(self.kinds(), ["missing", "missing", "missing"])
        self.assertEqual(self.run_sync("push")[0], 0)
        self.assertEqual(self.text(self.home_path(".codex/skills/alpha/SKILL.md")), "alpha v1\n")
        self.assertEqual(self.kinds(), ["ok", "ok", "ok"])
        self.put("skills/alpha/SKILL.md", "alpha v2\n")
        self.assertEqual(self.kinds(), ["outdated", "outdated", "ok"])
        self.assertEqual(self.run_sync("push")[0], 0)
        self.assertEqual(self.text(self.home_path(".agents/skills/alpha/SKILL.md")), "alpha v2\n")

    def test_edit_on_site_is_kept_and_pulled(self):
        self.run_sync("push")
        edited = self.home_path(".codex/skills/alpha/SKILL.md")
        with open(edited, "w") as f:
            f.write("alpha improved by codex\n")
        self.assertEqual(self.kinds(), ["ok", "drift", "ok"])
        code, out = self.run_sync("push")
        self.assertEqual(code, 1)
        self.assertIn("pull alpha", out)
        self.assertEqual(self.text(edited), "alpha improved by codex\n", "правку на месте затёрли")
        self.assertEqual(self.run_sync("pull", "alpha")[0], 0)
        self.assertEqual(self.text(os.path.join(self.repo, "skills/alpha/SKILL.md")), "alpha improved by codex\n")
        self.assertEqual(self.run_sync("push")[0], 0)
        self.assertEqual(self.text(self.home_path(".agents/skills/alpha/SKILL.md")), "alpha improved by codex\n")
        self.assertEqual(self.kinds(), ["ok", "ok", "ok"])

    def test_first_adoption_keeps_backup(self):
        os.makedirs(self.home_path(".agents/skills/alpha"))
        with open(self.home_path(".agents/skills/alpha/SKILL.md"), "w") as f:
            f.write("old local alpha\n")
        self.assertEqual(self.kinds()[0], "first")
        code, out = self.run_sync("push")
        self.assertEqual(code, 0)
        self.assertEqual(self.text(self.home_path(".agents/skills/alpha/SKILL.md")), "alpha v1\n")
        backups = [os.path.join(d, f) for d, _, files in os.walk(self.home_path(".local/share/solo-sdd/backup"))
                   for f in files]
        self.assertEqual([self.text(b) for b in backups], ["old local alpha\n"])

    def test_force_overrides_drift_with_backup(self):
        self.run_sync("push")
        with open(self.home_path("AGENTS.md"), "w") as f:
            f.write("rules edited\n")
        self.assertEqual(self.run_sync("push", "--force")[0], 0)
        self.assertEqual(self.text(self.home_path("AGENTS.md")), "rules v1\n")
        self.assertIn("rules edited\n", [self.text(os.path.join(d, f)) for d, _, files in
                                         os.walk(self.home_path(".local/share/solo-sdd/backup")) for f in files])

    def test_two_pushes_in_one_second_keep_both_versions(self):
        with open(self.home_path("AGENTS.md"), "w") as f:
            f.write("ORIGINAL\n")
        self.assertEqual(self.run_frozen("push")[0], 0)
        with open(self.home_path("AGENTS.md"), "w") as f:
            f.write("EDIT2\n")
        code, out = self.run_frozen("push", "--force")
        self.assertEqual(code, 0)
        self.assertIn(f"было сохранено: ~/.local/share/solo-sdd/backup/{SECOND}-1-2/AGENTS.md", out)
        self.assertEqual(self.backups(), {f"{SECOND}-1-1": ["ORIGINAL\n"], f"{SECOND}-1-2": ["EDIT2\n"]})

    def test_real_run_folder_has_time_pid_and_number(self):
        with open(self.home_path("AGENTS.md"), "w") as f:
            f.write("ORIGINAL\n")
        self.run_sync("push")
        name, = self.backups()
        self.assertRegex(name, r"^\d{8}-\d{6}-\d+-1$")

    def test_occupied_backup_path_keeps_both_files(self):
        outside = os.path.join(self.tmp, "outside", "rules.md")
        inside = self.home_path(outside.lstrip("/"))
        for path, text in ((outside, "mine\n"), (inside, "theirs\n")):
            os.makedirs(os.path.dirname(path))
            with open(path, "w") as f:
                f.write(text)
        self.put("targets.json", json.dumps({"roots": {}, "skills": {},
                                             "files": {"global/AGENTS.md": [outside, "~/" + outside.lstrip("/")]}}))
        code, out = self.run_sync("push")
        self.assertEqual(code, 1)
        self.assertEqual(self.text(outside), "rules v1\n")
        self.assertEqual(self.text(inside), "theirs\n", "копию заменили без резервной копии")
        self.assertRegex(out, r"(?m)^нет доступа .*" + re.escape(outside.lstrip("/")) + ": резервная копия уже есть$")
        self.assertEqual(list(self.backups().values()), [["mine\n"]], "резервную копию заменили")

    def test_push_without_overwrite_makes_no_backup_folder(self):
        self.assertEqual(self.run_sync("push")[0], 0)
        self.assertEqual(self.run_sync("push")[0], 0)
        self.assertEqual(self.backups(), {})

    def load_sync(self, home):
        """Свой экземпляр sync.py на домашнюю папку home, без запуска процесса: так быстрее в property-тесте."""
        spec = importlib.util.spec_from_file_location("sync_under_test", os.path.join(self.repo, "sync.py"))
        sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sync)
        sync.HOME, sync.DATA = home, os.path.join(home, ".local", "share", "solo-sdd")
        sync.STATE = os.path.join(sync.DATA, "state.json")
        return sync

    @settings(max_examples=60, deadline=None)
    @given(st.lists(st.one_of(st.sampled_from(["push", "force"]),
                              st.sampled_from(["", "rules v1\n", "a\n", "a\r\nb\n", "c\rd"]).map(str.encode),
                              st.text(max_size=8).map(str.encode)), max_size=30))
    def test_backup_never_overwritten_property(self, steps):
        """Requirement: Backup never overwritten. Время и pid не меняются на всей последовательности."""
        home = tempfile.mkdtemp(dir=self.tmp)
        sync = self.load_sync(home)
        copy, root = os.path.join(home, "AGENTS.md"), os.path.join(sync.DATA, "backup")
        replaced = set()

        def content():
            if not os.path.exists(copy):
                return None
            with open(copy, "rb") as f:
                return f.read()

        def saved():
            found = []
            for d, _, files in os.walk(root):
                for name in files:
                    with open(os.path.join(d, name), "rb") as f:
                        found.append(f.read())
            return found

        with mock.patch("time.strftime", return_value=SECOND), contextlib.redirect_stdout(io.StringIO()):
            for step in steps:
                if isinstance(step, bytes):
                    with open(copy, "wb") as f:
                        f.write(step)
                    continue
                before = content()
                problems = sync.push(force=step == "force")
                if before not in (None, content()):
                    replaced.add(before)
                self.assertEqual(replaced - set(saved()), set(), "пропала версия")
                if step == "force":
                    self.assertEqual(problems, 0)
                    self.assertEqual(sync.read(copy), "rules v1\n")
        if os.path.isdir(root):
            self.assertTrue(all(os.listdir(os.path.join(root, name)) for name in os.listdir(root)), "пустая папка запуска")

    def test_pull_refuses_conflicting_edits_without_origin(self):
        self.run_sync("push")
        for root, text in ((".agents", "edit A\n"), (".codex", "edit B\n")):
            with open(self.home_path(f"{root}/skills/alpha/SKILL.md"), "w") as f:
                f.write(text)
        code, out = self.run_sync("pull", "alpha")
        self.assertEqual(code, 1)
        self.assertIn("--from", out)
        self.assertEqual(self.run_sync("pull", "alpha", "--from", "~/.codex/skills")[0], 0)
        self.assertEqual(self.text(os.path.join(self.repo, "skills/alpha/SKILL.md")), "edit B\n")

    def test_unwritable_place_is_reported_not_fatal(self):
        with open(self.home_path(".codex"), "w") as f:
            f.write("not a directory\n")
        code, out = self.run_sync("push")
        self.assertEqual(code, 1)
        self.assertIn("нет доступа", out)
        self.assertEqual(self.text(self.home_path(".agents/skills/alpha/SKILL.md")), "alpha v1\n")

    def test_pull_never_takes_an_outdated_copy(self):
        self.run_sync("push")
        self.put("skills/alpha/SKILL.md", "alpha v2\n")
        self.assertEqual(self.run_sync("pull", "alpha")[0], 0)
        self.assertEqual(self.text(os.path.join(self.repo, "skills/alpha/SKILL.md")), "alpha v2\n",
                         "pull откатил репозиторий к устаревшей копии")
        with open(self.home_path(".codex/skills/alpha/SKILL.md"), "w") as f:
            f.write("edit on site\n")
        self.assertEqual(self.run_sync("pull", "alpha")[0], 0, "устаревшая копия не должна спорить с правкой")
        self.assertEqual(self.text(os.path.join(self.repo, "skills/alpha/SKILL.md")), "edit on site\n")

    def test_pull_from_a_single_file(self):
        targets = json.loads(self.text(os.path.join(self.repo, "targets.json")))
        targets["files"]["global/AGENTS.md"] = ["~/AGENTS.md", "~/.claude/CLAUDE.md"]
        self.put("targets.json", json.dumps(targets))
        self.run_sync("push")
        for rel, text in (("AGENTS.md", "rules edited A\n"), (".claude/CLAUDE.md", "rules edited B\n")):
            with open(self.home_path(rel), "w") as f:
                f.write(text)
        self.assertEqual(self.run_sync("pull", "global/AGENTS.md")[0], 1)
        self.assertEqual(self.run_sync("pull", "global/AGENTS.md", "--from", "~/AGENTS.md")[0], 0)
        self.assertEqual(self.text(os.path.join(self.repo, "global/AGENTS.md")), "rules edited A\n")

    def test_from_without_value_is_an_error_not_a_crash(self):
        code, out = self.run_sync("pull", "alpha", "--from")
        self.assertEqual(code, 2)
        self.assertIn("--from", out)

    def test_non_utf8_copy_is_unreachable_not_a_crash(self):
        os.makedirs(self.home_path(".agents/skills/alpha"))
        with open(self.home_path(".agents/skills/alpha/SKILL.md"), "wb") as f:
            f.write(b"\xff\xfe broken")
        self.assertEqual(self.kinds()[0], "unreachable")
        code, _ = self.run_sync("push")
        self.assertEqual(code, 1)
        self.assertEqual(self.text(self.home_path(".codex/skills/alpha/SKILL.md")), "alpha v1\n")
        self.assertTrue(os.path.exists(self.home_path(".local/share/solo-sdd/state.json")))


if __name__ == "__main__":
    unittest.main(verbosity=1)
