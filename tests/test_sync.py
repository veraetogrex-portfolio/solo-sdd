#!/usr/bin/env python3
"""sync.py on a temporary home folder and a temporary copy of the repository: live places are not touched."""
import contextlib, importlib.util, io, json, os, re, shutil, subprocess, sys, tempfile, unittest
import marks
from unittest import mock

from hypothesis import given, settings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
SECOND = "20261021-145202"
# A sync.py run in which time and pid do not change: all runs land in the same second with the same pid.
FROZEN = ("import os, runpy, sys, time; time.strftime = lambda *a: %r; os.getpid = lambda: 1; "
          "sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')" % SECOND)


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, "home")
        self.repo = os.path.join(self.tmp, "repo")
        for d in (".claude", ".codex"):  # the agents detected by their folders, whatever PATH holds
            os.makedirs(os.path.join(self.home, d))
        os.makedirs(os.path.join(self.repo, "skills", "alpha"))
        os.makedirs(os.path.join(self.repo, "global"))
        shutil.copy(os.path.join(REPO, "sync.py"), self.repo)
        shutil.copytree(os.path.join(REPO, "solo_sdd"), os.path.join(self.repo, "solo_sdd"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        self.put("skills/alpha/SKILL.md", "alpha v1\n")
        self.put("global/AGENTS.md", "rules v1\n")
        self.put("targets.json", json.dumps({
            "skills": {"alpha": ["other", "codex"]},
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
        """{run folder name: [backup texts]}."""
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

    def source(self):
        with open(self.home_path(".local/share/solo-sdd/state.json")) as f:
            return os.path.realpath(json.load(f)["_source"])

    def test_push_records_source_repo(self):
        self.assertEqual(self.run_sync("push")[0], 0)
        self.assertEqual(self.source(), os.path.realpath(self.repo))
        self.assertEqual(self.kinds(), ["ok", "ok", "ok"])
        self.assertEqual(self.run_sync("pull", "alpha")[0], 0)

    def test_push_with_drift_still_records_source(self):
        self.run_sync("push")
        with open(self.home_path(".codex/skills/alpha/SKILL.md"), "w") as f:
            f.write("edited\n")
        state_file = self.home_path(".local/share/solo-sdd/state.json")
        with open(state_file) as f:
            state = json.load(f)
        del state["_source"]
        with open(state_file, "w") as f:
            json.dump(state, f)
        self.assertEqual(self.run_sync("push")[0], 1)
        self.assertEqual(self.source(), os.path.realpath(self.repo))

    def test_edit_on_site_is_kept_and_pulled(self):
        self.run_sync("push")
        edited = self.home_path(".codex/skills/alpha/SKILL.md")
        with open(edited, "w") as f:
            f.write("alpha improved by codex\n")
        self.assertEqual(self.kinds(), ["ok", "drift", "ok"])
        code, out = self.run_sync("push")
        self.assertEqual(code, 1)
        self.assertIn("pull alpha", out)
        self.assertEqual(self.text(edited), "alpha improved by codex\n", "the edit in place was overwritten")
        self.assertEqual(self.run_sync("pull", "alpha")[0], 0)
        self.assertEqual(self.text(os.path.join(self.repo, "skills/alpha/SKILL.md")), "alpha improved by codex\n")
        self.assertEqual(self.run_sync("push")[0], 0)
        self.assertEqual(self.text(self.home_path(".agents/skills/alpha/SKILL.md")), "alpha improved by codex\n")
        self.assertEqual(self.kinds(), ["ok", "ok", "ok"])

    def test_algorithm_and_templates_folder(self):
        self.put("ALGORITHM.md", "algorithm\n")
        os.makedirs(os.path.join(self.repo, "templates", "openspec"))
        self.put("templates/openspec/config.yaml", "schema: solo\n")
        self.put("templates/.hidden", "x\n")
        self.put("targets.json", json.dumps({
            "skills": {},
            "files": {"ALGORITHM.md": ["~/.local/share/solo-sdd/ALGORITHM.md"],
                      "templates/**": ["~/.local/share/solo-sdd/templates/"]},
        }))
        self.assertEqual(self.run_sync("push")[0], 0)
        algo = self.home_path(".local/share/solo-sdd/ALGORITHM.md")
        cfg = self.home_path(".local/share/solo-sdd/templates/openspec/config.yaml")
        self.assertEqual(self.text(algo), "algorithm\n")
        self.assertEqual(self.text(cfg), "schema: solo\n")
        self.assertFalse(os.path.exists(self.home_path(".local/share/solo-sdd/templates/.hidden")))
        with open(cfg, "w") as f:
            f.write("edited\n")
        self.assertEqual(self.kinds(), ["ok", "drift"])
        self.assertEqual(self.run_sync("push")[0], 1)
        self.assertEqual(self.text(cfg), "edited\n", "the template edit in place was overwritten")

    def test_first_adoption_keeps_backup(self):
        os.makedirs(self.home_path(".agents/skills/alpha"))
        with open(self.home_path(".agents/skills/alpha/SKILL.md"), "w") as f:
            f.write("old local alpha\n")
        self.assertEqual(self.kinds()[0], "first")
        code, out = self.run_sync("push", "--replace-foreign")
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
        self.assertEqual(self.run_frozen("push", "--replace-foreign")[0], 0)
        with open(self.home_path("AGENTS.md"), "w") as f:
            f.write("EDIT2\n")
        code, out = self.run_frozen("push", "--force")
        self.assertEqual(code, 0)
        self.assertIn(f"saved: ~/.local/share/solo-sdd/backup/{SECOND}-1-2/AGENTS.md", out)
        self.assertEqual(self.backups(), {f"{SECOND}-1-1": ["ORIGINAL\n"], f"{SECOND}-1-2": ["EDIT2\n"]})

    def test_real_run_folder_has_time_pid_and_number(self):
        with open(self.home_path("AGENTS.md"), "w") as f:
            f.write("ORIGINAL\n")
        self.run_sync("push", "--replace-foreign")
        name, = self.backups()
        self.assertRegex(name, r"^\d{8}-\d{6}-\d+-1$")

    def test_occupied_backup_path_keeps_both_files(self):
        outside = os.path.join(self.tmp, "outside", "rules.md")
        inside = self.home_path(outside.lstrip("/"))
        for path, text in ((outside, "mine\n"), (inside, "theirs\n")):
            os.makedirs(os.path.dirname(path))
            with open(path, "w") as f:
                f.write(text)
        self.put("targets.json", json.dumps({"skills": {},
                                             "files": {"global/AGENTS.md": [outside, "~/" + outside.lstrip("/")]}}))
        code, out = self.run_sync("push", "--replace-foreign")
        self.assertEqual(code, 1)
        self.assertEqual(self.text(outside), "rules v1\n")
        self.assertEqual(self.text(inside), "theirs\n", "the copy was replaced without a backup")
        self.assertRegex(out, r"(?m)^no access  .*" + re.escape(outside.lstrip("/")) + ": backup already exists$")
        self.assertEqual(list(self.backups().values()), [["mine\n"]], "the backup was replaced")

    def test_push_without_overwrite_makes_no_backup_folder(self):
        self.assertEqual(self.run_sync("push")[0], 0)
        self.assertEqual(self.run_sync("push")[0], 0)
        self.assertEqual(self.backups(), {})

    def load_sync(self, home):
        """An own sync.py instance on the home folder home, without starting a process: faster in the property test."""
        spec = importlib.util.spec_from_file_location("sync_under_test", os.path.join(self.repo, "solo_sdd", "layout.py"))
        sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sync)
        sync.REPO = self.repo
        sync.HOME, sync.DATA = home, os.path.join(home, ".local", "share", "solo-sdd")
        sync.STATE = os.path.join(sync.DATA, "state.json")
        return sync

    @marks.slow
    @settings(max_examples=60, deadline=None)
    @given(st.sampled_from([19, 20, 21]),
           st.lists(st.one_of(st.sampled_from(["push", "force"]),
                              st.sampled_from(["", "rules v1\n", "a\n", "a\r\nb\n", "c\rd"]).map(str.encode),
                              st.text(max_size=8).map(str.encode)), max_size=30))
    def test_backup_never_overwritten_property(self, earlier, steps):
        """Requirement: Backup never overwritten, with Backup retention. Time and pid do not change over the
        whole sequence; earlier run folders of an older second and a longer name, and a foreign entry, lie in
        backup/ before it. force is push --force --replace-foreign."""
        home = tempfile.mkdtemp(dir=self.tmp)
        sync = self.load_sync(home)
        copy, root = os.path.join(home, "AGENTS.md"), os.path.join(sync.DATA, "backup")
        for n in range(1, earlier + 1):
            os.makedirs(os.path.join(root, f"20260101-000000-99999999-{n}"))
            with open(os.path.join(root, f"20260101-000000-99999999-{n}", "seed"), "w") as f:
                f.write(f"seed {n}\n")
        os.makedirs(os.path.join(root, "mine"))
        runs = []  # texts replaced by each run that wrote a backup, oldest first

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
                before, folders = content(), set(os.listdir(root))
                problems = sync.push(force=step == "force", replace_foreign=step == "force")
                new = set(os.listdir(root)) - folders
                self.assertLessEqual(len(new), 1)
                if new:
                    runs.append({before} if before not in (None, content()) else set())
                    self.assertTrue(os.listdir(os.path.join(root, *new)), "empty run folder")
                else:
                    self.assertIn(before, (None, content()), "replaced without a backup")
                self.assertIn("mine", os.listdir(root))
                self.assertLessEqual(len([e for e in os.listdir(root) if e != "mine"]), 20 if runs else earlier)
                self.assertEqual(set().union(*runs[-20:]) - set(saved()), set(), "a version was lost")
                if step == "force":
                    self.assertEqual(problems, 0)
                    self.assertEqual(sync.read(copy), "rules v1\n")

    # Requirement: State written atomically; Broken state refused.
    def tree(self):
        """{path under the home: bytes} of every file in the home folder."""
        found = {}
        for d, _, files in os.walk(self.home):
            for f in files:
                with open(os.path.join(d, f), "rb") as fh:
                    found[os.path.relpath(os.path.join(d, f), self.home)] = fh.read()
        return found

    def run_cli(self, *args):
        """The real solo-sdd package on the temporary home."""
        result = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=REPO, stdin=subprocess.DEVNULL,
                                env=dict(os.environ, HOME=self.home), capture_output=True, text=True)
        return result.returncode, result.stdout

    def put_state(self, text):
        os.makedirs(self.home_path(".local/share/solo-sdd"), exist_ok=True)
        with open(self.home_path(".local/share/solo-sdd/state.json"), "w") as f:
            f.write(text)

    def test_state_written_atomically_a_stopped_write(self):
        self.assertEqual(self.run_sync("push")[0], 0)
        state_file = self.home_path(".local/share/solo-sdd/state.json")
        old = self.text(state_file)
        sync = self.load_sync(self.home)
        state = json.loads(old)
        state["_source"] = "elsewhere"
        with mock.patch.object(sync.os, "replace", side_effect=OSError("stopped")):
            with self.assertRaises(OSError):
                sync.save_state(state)
        self.assertEqual(self.text(state_file), old)
        json.loads(self.text(state_file))
        self.assertEqual(sorted(os.listdir(os.path.dirname(state_file))), ["state.json"], "a temporary file was left")
        sync.save_state(state)
        self.assertEqual(json.loads(self.text(state_file))["_source"], "elsewhere")

    def test_copy_written_atomically_keeps_mode_and_link(self):
        self.assertEqual(self.run_sync("push")[0], 0)
        real = self.home_path("real-alpha.md")
        link = self.home_path(".codex/skills/alpha/SKILL.md")
        shutil.move(link, real)
        os.symlink(real, link)
        os.chmod(real, 0o640)
        self.put("skills/alpha/SKILL.md", "alpha v2\n")
        self.assertEqual(self.run_sync("push")[0], 0)
        self.assertTrue(os.path.islink(link), "the link was replaced by a file")
        self.assertEqual(self.text(real), "alpha v2\n")
        self.assertEqual(os.stat(real).st_mode & 0o777, 0o640)

    def test_broken_state_refused_a_truncated_state(self):
        self.assertEqual(self.run_cli("install", "--agents", "claude")[0], 0)
        self.put_state('{"skills/ship/SKILL.md"')
        with open(self.home_path(".claude/skills/spec-next/SKILL.md"), "a") as f:
            f.write("edited\n")
        before = self.tree()
        code, out = self.run_cli("install")
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^fail state: ~/\.local/share/solo-sdd/state\.json: ")
        self.assertEqual(self.tree(), before, "a copy or a backup was written")

    @marks.slow
    def test_broken_state_refused_by_every_command(self):
        for text in ('{"skills/ship/SKILL.md"', "[]", "\xff"):
            os.makedirs(self.home_path(".local/share/solo-sdd"), exist_ok=True)
            with open(self.home_path(".local/share/solo-sdd/state.json"), "wb") as f:
                f.write(text.encode("latin-1"))
            before = self.tree()
            for args in (("status",), ("install",), ("update",), ("uninstall",), ("uninstall", "--global-rules"),
                         ("sync", "pull", "spec-next"), ("doctor",)):
                code, out = self.run_cli(*args)
                self.assertEqual(code, 1, (text, args, out))
                self.assertIn("fail state: ~/.local/share/solo-sdd/state.json: ", out, (text, args))
                self.assertEqual(self.tree(), before, (text, args))
            for args in (("status",), ("push",), ("pull", "alpha")):
                code, out = self.run_sync(*args)
                self.assertEqual(code, 1, (text, args, out))
                self.assertIn("fail state: ", out, (text, args))
                self.assertEqual(self.tree(), before, (text, args))

    def test_broken_state_refused_doctor_on_a_broken_state(self):
        self.put_state("[]")
        code, out = self.run_cli("doctor")
        self.assertIn("fail state: ~/.local/share/solo-sdd/state.json: not a JSON object", out)
        self.assertEqual(code, 1)

    def test_broken_state_unreadable_and_missing(self):
        os.makedirs(self.home_path(".local/share/solo-sdd/state.json"))  # a folder: cannot be read
        code, out = self.run_sync("status")
        self.assertEqual(code, 1)
        self.assertIn("fail state: ", out)
        os.rmdir(self.home_path(".local/share/solo-sdd/state.json"))
        self.assertEqual(self.run_sync("status")[0], 0, "a missing state is a fresh deployment")

    # Requirement: Foreign copy kept.
    def test_foreign_copy_kept_a_foreign_skill(self):
        ship = self.home_path(".claude/skills/ship/SKILL.md")
        os.makedirs(os.path.dirname(ship))
        with open(ship, "wb") as f:
            f.write(b"another tool's ship\r\n")
        with open(self.home_path(".claude/skills/ship/helper.md"), "w") as f:
            f.write("neighbour\n")
        code, out = self.run_cli("install", "--agents", "claude")
        self.assertEqual(code, 1, out)
        with open(ship, "rb") as f:
            self.assertEqual(f.read(), b"another tool's ship\r\n")
        self.assertIn("foreign ~/.claude/skills/ship/SKILL.md: kept (install --replace-foreign replaces it)", out)
        self.assertEqual(self.text(self.home_path(".claude/skills/spec-next/SKILL.md")),
                         self.text(os.path.join(REPO, "skills/spec-next/SKILL.md")))
        self.assertFalse(os.path.exists(self.home_path(".local/share/solo-sdd/backup")))
        self.assertEqual(self.run_cli("install")[0], 1, "a repeated install replaced the foreign file")

    def test_foreign_copy_kept_replaced_on_request(self):
        ship = self.home_path(".claude/skills/ship/SKILL.md")
        os.makedirs(os.path.dirname(ship))
        with open(ship, "w") as f:
            f.write("another tool's ship\n")
        code, out = self.run_cli("install", "--agents", "claude", "--replace-foreign")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.text(ship), self.text(os.path.join(REPO, "skills/ship/SKILL.md")))
        self.assertIn(["another tool's ship\n"], self.backups().values())
        self.assertEqual(self.run_cli("install")[0], 0)

    def test_foreign_copy_kept_by_push_and_update(self):
        target = self.home_path(".agents/skills/alpha/SKILL.md")
        os.makedirs(os.path.dirname(target))
        with open(target, "w") as f:
            f.write("old local alpha\n")
        for args in (("push",), ("push", "--force")):
            code, out = self.run_sync(*args)
            self.assertEqual(code, 1, args)
            self.assertIn("foreign ~/.agents/skills/alpha/SKILL.md: kept", out)
            self.assertEqual(self.text(target), "old local alpha\n")
            self.assertEqual(self.text(self.home_path(".codex/skills/alpha/SKILL.md")), "alpha v1\n")
        self.assertEqual(self.run_sync("push", "--replace-foreign")[0], 0)
        self.assertEqual(self.text(target), "alpha v1\n")
        self.assertEqual(list(self.backups().values()), [["old local alpha\n"]])
        ship = self.home_path(".claude/skills/ship/SKILL.md")
        os.makedirs(os.path.dirname(ship))
        with open(ship, "w") as f:
            f.write("theirs\n")
        self.assertEqual(self.run_cli("install", "--agents", "claude")[0], 1)
        code, out = self.run_cli("update")
        self.assertEqual(code, 1, out)
        self.assertIn("foreign ~/.claude/skills/ship/SKILL.md: kept", out)
        self.assertEqual(self.run_cli("update", "--replace-foreign")[0], 0)
        self.assertEqual(self.text(ship), self.text(os.path.join(REPO, "skills/ship/SKILL.md")))

    def test_foreign_copy_equal_to_source_is_adopted(self):
        target = self.home_path(".agents/skills/alpha/SKILL.md")
        os.makedirs(os.path.dirname(target))
        with open(target, "w") as f:
            f.write("alpha v1\n")
        self.assertEqual(self.run_sync("push")[0], 0)
        self.assertEqual(self.backups(), {})
        self.put("skills/alpha/SKILL.md", "alpha v2\n")
        self.assertEqual(self.kinds()[0], "outdated", "the adopted copy has no state entry")

    def test_foreign_copy_kept_a_foreign_rules_file(self):
        rules = self.home_path(".claude/CLAUDE.md")
        with open(rules, "w") as f:
            f.write("owner's own rules\n")
        code, out = self.run_cli("install", "--agents", "claude", "--global-rules")
        self.assertEqual(code, 0, out)
        self.assertNotIn("foreign", out)
        text = self.text(rules)
        self.assertTrue(text.startswith("owner's own rules\n"), text)
        self.assertIn("<!-- solo-sdd:begin", text)

    # Requirement: Backup retention.
    def seed_backups(self, count, second="20260101-000000", pid=99999999):
        root = self.home_path(".local/share/solo-sdd/backup")
        names = []
        for n in range(1, count + 1):
            name = f"{second}-{pid}-{n}"
            os.makedirs(os.path.join(root, name))
            with open(os.path.join(root, name, "AGENTS.md"), "w") as f:
                f.write(f"seed {n}\n")
            os.utime(os.path.join(root, name), (1000 + n, 1000 + n))
            names.append(name)
        return root, names

    def test_backup_retention_many_backups(self):
        root, _ = self.seed_backups(25)
        self.assertEqual(self.run_sync("push")[0], 0)
        with open(self.home_path("AGENTS.md"), "w") as f:
            f.write("edited\n")
        code, out = self.run_sync("push", "--force")
        self.assertEqual(code, 0, out)
        self.assertIn("pruned backups: 6", out)
        left = sorted(os.listdir(root))
        self.assertEqual(len(left), 20)
        self.assertIn(["edited\n"], self.backups().values(), "the current run's folder was deleted")
        self.assertEqual(left[:19], [f"20260101-000000-99999999-{n}" for n in sorted(range(7, 26), key=str)])

    def test_backup_retention_a_foreign_entry(self):
        root, _ = self.seed_backups(21)
        os.makedirs(os.path.join(root, "mine"))
        with open(os.path.join(root, "notes.txt"), "w") as f:
            f.write("x\n")
        os.makedirs(os.path.join(root, "20250101-000000-1-1.old"))
        with open(self.home_path("AGENTS.md"), "w") as f:
            f.write("edited\n")
        code, out = self.run_sync("push", "--replace-foreign")
        self.assertEqual(code, 0, out)
        self.assertIn("pruned backups: 2", out)
        left = os.listdir(root)
        for entry in ("mine", "notes.txt", "20250101-000000-1-1.old"):
            self.assertIn(entry, left)
        self.assertEqual(len(left), 23)

    def test_backup_retention_folders_of_an_earlier_version(self):
        root = self.home_path(".local/share/solo-sdd/backup")
        names = [f"202610{n:02d}-120000" for n in range(1, 22)]
        for name in names:
            os.makedirs(os.path.join(root, name))
        with open(self.home_path("AGENTS.md"), "w") as f:
            f.write("edited\n")
        code, out = self.run_sync("push", "--replace-foreign")
        self.assertEqual(code, 0, out)
        self.assertIn("pruned backups: 2", out)
        self.assertEqual(sorted(set(names) - set(os.listdir(root))), names[:2])

    def test_backup_retention_only_ascii_run_names(self):
        root = self.home_path(".local/share/solo-sdd/backup")
        odd = ["20260101-000000\n", "\u0662" * 8 + "-000000-1-1", "20260101-000000-1-1x"]
        for name in odd + [f"20260101-0000{n:02d}" for n in range(1, 21)]:
            os.makedirs(os.path.join(root, name))
        with open(self.home_path("AGENTS.md"), "w") as f:
            f.write("edited\n")
        code, out = self.run_sync("push", "--replace-foreign")
        self.assertEqual(code, 0, out)
        self.assertIn("pruned backups: 1", out)
        for name in odd:
            self.assertIn(name, os.listdir(root))

    @unittest.skipIf(os.geteuid() == 0, "root writes any file")
    def test_write_protected_copy_is_refused(self):
        self.assertEqual(self.run_sync("push")[0], 0)
        target = self.home_path(".codex/skills/alpha/SKILL.md")
        os.chmod(target, 0o444)
        self.put("skills/alpha/SKILL.md", "alpha v2\n")
        code, out = self.run_sync("push")
        self.assertEqual(code, 1)
        self.assertRegex(out, r"(?m)^no access  alpha .*\.codex/skills/alpha/SKILL\.md: Permission denied$")
        self.assertEqual(self.text(target), "alpha v1\n")
        self.assertEqual(self.text(self.home_path(".agents/skills/alpha/SKILL.md")), "alpha v2\n")
        os.chmod(target, 0o644)

    def test_backup_retention_a_run_without_a_backup(self):
        root, names = self.seed_backups(25)
        code, out = self.run_sync("push")
        self.assertEqual(code, 0, out)
        self.assertNotIn("pruned backups", out)
        self.assertEqual(sorted(os.listdir(root)), sorted(names))

    def test_backup_retention_orders_by_time_then_mtime(self):
        root = self.home_path(".local/share/solo-sdd/backup")
        # Name time decides first; for the same second the modification time decides, not the name.
        for name, mtime in (("20260102-000000-5-1", 100), ("20260101-000000-9-1", 300),
                            ("20260102-000000-1-1", 200), ("20260102-000000-1-2", 50)):
            os.makedirs(os.path.join(root, name))
            os.utime(os.path.join(root, name), (mtime, mtime))
        sync = self.load_sync(self.home)
        with mock.patch.object(sync, "KEEP_BACKUPS", 3), contextlib.redirect_stdout(io.StringIO()) as out:
            current = sync.run_folder()
            sync.prune_backups(current)
        self.assertEqual(sorted(os.listdir(root)), sorted(["20260102-000000-5-1", "20260102-000000-1-1",
                                                           os.path.basename(current)]))
        self.assertIn("pruned backups: 2", out.getvalue())

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
        with open(self.home_path(".codex/skills"), "w") as f:
            f.write("not a directory\n")
        code, out = self.run_sync("push")
        self.assertEqual(code, 1)
        self.assertIn("no access", out)
        self.assertEqual(self.text(self.home_path(".agents/skills/alpha/SKILL.md")), "alpha v1\n")

    def test_state_from_an_earlier_version_keeps_every_agent(self):
        """Requirement: Install for chosen agents, scenario A state from an earlier version."""
        self.assertEqual(self.run_sync("push")[0], 0)
        state_file = self.home_path(".local/share/solo-sdd/state.json")
        state = json.loads(self.text(state_file))
        self.assertEqual(state.pop("_agents"), ["claude", "codex", "other"])
        with open(state_file, "w") as f:
            json.dump(state, f)
        shutil.rmtree(self.home_path(".codex"))  # Codex is no longer detected: no folder, no command in PATH
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty)
        p = subprocess.run([sys.executable, os.path.join(self.repo, "sync.py"), "push"],
                           env=dict(os.environ, HOME=self.home, PATH=empty), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(self.text(self.home_path(".codex/skills/alpha/SKILL.md")), "alpha v1\n")
        self.assertEqual(json.loads(self.text(state_file))["_agents"], ["claude", "codex", "other"])

    def test_pull_never_takes_an_outdated_copy(self):
        self.run_sync("push")
        self.put("skills/alpha/SKILL.md", "alpha v2\n")
        self.assertEqual(self.run_sync("pull", "alpha")[0], 0)
        self.assertEqual(self.text(os.path.join(self.repo, "skills/alpha/SKILL.md")), "alpha v2\n",
                         "pull rolled the repository back to an outdated copy")
        with open(self.home_path(".codex/skills/alpha/SKILL.md"), "w") as f:
            f.write("edit on site\n")
        self.assertEqual(self.run_sync("pull", "alpha")[0], 0, "an outdated copy must not compete with an edit")
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


class VendorFilesPerSkillPairs(unittest.TestCase):
    """Requirement: Vendor files per skill: the skill entries of targets.json expand to the pairs the per-agent
    lists of the previous map (tests/targets-before.json) gave, for every agent choice and global rules on and off."""

    def test_expanded_pairs_equal_the_previous_map(self):
        import itertools
        from solo_sdd import layout, providers
        with open(os.path.join(REPO, "tests", "targets-before.json")) as f:
            before = json.load(f)
        current = layout.load_targets()
        self.assertTrue(any(isinstance(c, dict) and "skills" in c for c in current["files"].values()))
        for n in range(len(providers.ALL) + 1):
            for agents in itertools.combinations(providers.ALL, n):
                for rules in (False, True):
                    new = layout.pairs(list(agents), rules)
                    with mock.patch.object(layout, "load_targets", lambda: before):
                        old = layout.pairs(list(agents), rules)
                    self.assertEqual(sorted(new), sorted(old), (agents, rules))
                    self.assertEqual(len(new), len(set(new)), (agents, rules))


if __name__ == "__main__":
    unittest.main(verbosity=1)
