#!/usr/bin/env python3
"""solo-sdd: entry point, wheel, install and the rules block, on a temporary home folder."""
import atexit, contextlib, hashlib, io, json, os, re, shutil, subprocess, sys, tempfile, unittest, zipfile
import marks
from unittest import mock

from hypothesis import assume, example, given, settings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import __version__, cli, hooks, keywords, layout, providers, rules_block  # noqa: E402

RULES = "global/AGENTS.md"
NET = ("Could not find a version", "No matching distribution", "Temporary failure", "ConnectionError", "Max retries")
DATA_DIRS = ("solo_sdd", "global", "skills", "templates", "integrations")


def run(args, home, cwd=REPO, path=None, extra=None):
    env = dict(os.environ, HOME=home)
    if path is not None:
        env["PATH"] = path
    env.update(extra or {})
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def make_home(home):
    """A temporary home where Claude Code and Codex are detected by their folders, whatever PATH holds."""
    for d in (".claude", ".codex"):
        os.makedirs(os.path.join(home, d))


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def copy_repo(dest):
    """A copy of the repository data: pull writes into it, not into the real global/AGENTS.md."""
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
        make_home(self.home)

    def test_version(self):
        code, out, _ = run([sys.executable, "-m", "solo_sdd", "--version"], self.home)
        self.assertEqual((code, out.strip()), (0, __version__))

    def test_no_command_and_unknown(self):
        for args in ([], ["bogus"], ["--bogus"], ["status", "--bogus"], ["sync"], ["sync", "push"]):
            code, out, err = run([sys.executable, "-m", "solo_sdd", *args], self.home)
            self.assertEqual(code, 2, args)
            self.assertIn("solo-sdd commands", out)
            self.assertEqual(bool(args), "wrong command or arguments: " + " ".join(args) in err, (args, err))

    def test_help(self):
        for args in (["--help"], ["-h"], ["help"], ["validate", "--help"], ["install", "-h"]):
            code, out, err = run([sys.executable, "-m", "solo_sdd", *args], self.home)
            self.assertEqual((code, err), (0, ""), args)
            self.assertIn("solo-sdd commands", out)

    def test_status_matches_sync_py(self):
        code, out, _ = run([sys.executable, "-m", "solo_sdd", "status"], self.home)
        self.assertEqual(code, 0)
        first, _, rest = out.partition("\n")
        self.assertTrue(first.startswith("source: "), first)
        self.assertEqual(rest, run([sys.executable, "sync.py", "status"], self.home)[1])

    def test_status_first_line_clean_home(self):
        code, out, _ = run([sys.executable, "-m", "solo_sdd", "status"], self.home)
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0], f"source: {layout.REPO} {__version__}")

    def test_status_first_line_from_state(self):
        data = os.path.join(self.home, ".local", "share", "solo-sdd")
        os.makedirs(data)
        with open(os.path.join(data, "state.json"), "w") as f:
            json.dump({"_source": "/somewhere/else", "_version": "9.9.9"}, f)
        code, out, _ = run([sys.executable, "-m", "solo_sdd", "status"], self.home)
        self.assertEqual((code, out.splitlines()[0]), (0, "source: /somewhere/else 9.9.9"))

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
            f.write("\nedit in place\n")
        code, out, err = run([sys.executable, "-m", "solo_sdd", "sync", "pull", "spec-next"], self.home,
                             cwd=repo, extra=env)
        self.assertEqual(code, 0, err)
        with open(os.path.join(repo, "skills/spec-next/SKILL.md"), encoding="utf-8") as f:
            self.assertIn("edit in place", f.read())
        return out

    HINT = "source is the installed package: the edit is lost on upgrade, move it to a clone"

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
        self.assertEqual(cli.upgrade_hint("/usr", git), f"git pull in {git}")
        self.assertEqual(cli.upgrade_hint("/usr", plain),
                         "python3 -m pip install --upgrade solo-sdd")

    @marks.release
    def test_wheel(self):
        wheels = os.path.join(self.tmp, "wheels")
        code, _, err = run([sys.executable, "-m", "pip", "wheel", ".", "-w", wheels, "--no-deps"], self.home)
        if code != 0 and any(mark in err for mark in NET):
            self.skipTest("the builder is unavailable because of the network")
        self.assertEqual(code, 0, err[-2000:])
        wheel = os.path.join(wheels, os.listdir(wheels)[0])
        folder = os.path.join(self.tmp, "unpacked")
        with zipfile.ZipFile(wheel) as z:
            names = z.namelist()
            for need in ("solo_sdd/data/skills/spec-next/SKILL.md", "solo_sdd/data/targets.json", "solo_sdd/data/sync.py"):
                self.assertIn(need, names)
            z.extractall(folder)
        expected = len(list(layout.pairs(providers.ALL, False)))  # a clean home: no global rules block
        code, out, err = run([sys.executable, os.path.join(folder, "solo_sdd", "data", "sync.py"), "status"],
                             self.home, cwd=self.tmp)
        self.assertEqual((code, len(out.splitlines())), (0, expected), err)
        code, out, err = run([sys.executable, "-m", "solo_sdd", "status"], self.home, cwd=self.tmp,
                             extra={"PYTHONPATH": folder})
        self.assertEqual(code, 0, err)
        self.assertTrue(out.startswith("source: " + os.path.join(folder, "solo_sdd", "data") + " "), out)


class Install(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        make_home(self.home)

    def snapshot(self):
        files, dirs = {}, set()
        for d, subdirs, names in os.walk(self.home):
            dirs.update(os.path.join(d, s) for s in subdirs)
            for n in names:
                p = os.path.join(d, n)
                with open(p, "rb") as f:
                    files[p] = (f.read(), os.stat(p).st_mtime_ns)
        return files, dirs

    def install(self, empty=None):
        """solo-sdd install as a process with no openspec anywhere in PATH."""
        empty = empty or os.path.join(self.tmp, "empty")
        os.makedirs(empty, exist_ok=True)
        return run([sys.executable, "-m", "solo_sdd", "install"], self.home, path=empty)

    def test_clean_home_without_openspec(self):
        code, out, err = self.install()
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("openspec", (out + err).lower())
        for _, _, target, _ in layout.pairs(providers.ALL, False):
            self.assertTrue(os.path.exists(target.replace(layout.HOME, self.home, 1)), target)
        self.assertFalse(os.path.exists(os.path.join(self.home, ".local/bin/openspec-after-update.py")))
        self.assertTrue(os.path.exists(os.path.join(self.home, ".local/share/solo-sdd/templates/solo-sdd/project.md")))
        self.assertFalse(os.path.exists(os.path.join(self.home, ".local/share/openspec")))
        with open(os.path.join(self.home, ".local/share/solo-sdd/state.json")) as f:
            state = json.load(f)
        self.assertEqual((state["_source"], state["_version"]), (layout.REPO, __version__))

    def test_update_prints_upgrade_hint_last(self):
        for problems in (1, 0):
            with mock.patch.object(layout, "push", lambda **_: problems):
                code, out = inproc(self.home, "update", prefix="/x/uv/tools/solo-sdd")
            self.assertEqual(code, problems)
            self.assertEqual(out.splitlines()[-1], "uv tool upgrade solo-sdd")
        code, out = inproc(self.home, "update", prefix="/x/uv/tools/solo-sdd")
        self.assertNotIn("openspec", out.lower())

    def test_repeat_changes_nothing(self):
        self.assertEqual(self.install()[0], 0)
        before = self.snapshot()
        code, out, _ = self.install()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.snapshot(), before)
        self.assertIn("all laid out", out)
        self.assertFalse(os.path.isdir(os.path.join(self.home, ".local/share/solo-sdd/backup")))

    def plant(self, key, text, recorded):
        """A copy an earlier version laid out: the file and its digest in the state."""
        path = os.path.join(self.home, key[2:])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        state_file = os.path.join(self.home, ".local/share/solo-sdd/state.json")
        with open(state_file) as f:
            state = json.load(f)
        state[key] = digest(recorded)
        with open(state_file, "w") as f:
            json.dump(state, f)
        return path

    def test_old_schema_copies(self):
        self.assertEqual(self.install()[0], 0)
        script = "~/.local/bin/openspec-after-update.py"
        test = "~/.local/bin/test_openspec_after_update.py"
        template = "~/.local/share/solo-sdd/templates/openspec/config.yaml"
        same = self.plant(script, "old script\n", "old script\n")
        edited = self.plant(test, "old test, edited\n", "old test\n")
        tpl = self.plant(template, "schema: solo\n", "schema: solo\n")
        job = os.path.join(self.home, "Library/LaunchAgents/local.openspec-after-update.plist")
        os.makedirs(os.path.dirname(job))
        with open(job, "w") as f:
            f.write("<plist/>\n")
        code, out, err = self.install()
        self.assertEqual(code, 0, out + err)
        lines = out.splitlines()
        self.assertFalse(os.path.exists(same))
        self.assertFalse(os.path.exists(tpl))
        self.assertFalse(os.path.exists(os.path.dirname(tpl)), "the emptied templates/openspec/ folder is left")
        self.assertTrue(any(l.startswith("removed") and script in l for l in lines), out)
        self.assertTrue(any(l.startswith("removed") and template in l for l in lines), out)
        with open(edited) as f:
            self.assertEqual(f.read(), "old test, edited\n")
        self.assertTrue(any(l.startswith("kept") and test in l and "drift" in l for l in lines), out)
        with open(job) as f:
            self.assertEqual(f.read(), "<plist/>\n")
        self.assertTrue(any("~/Library/LaunchAgents/local.openspec-after-update.plist" in l for l in lines), out)
        with open(os.path.join(self.home, ".local/share/solo-sdd/state.json")) as f:
            state = json.load(f)
        self.assertNotIn(script, state)
        self.assertNotIn(template, state)
        self.assertIn(test, state)
        # a repeat: the removed copy stays gone, the edited one is named again and untouched
        code, out, _ = self.install()
        self.assertEqual(code, 0, out)
        self.assertNotIn(script, out)
        self.assertIn(test, out)
        stray = os.path.join(self.home, ".local/share/solo-sdd/templates/openspec/analyze.md")
        os.makedirs(os.path.dirname(stray), exist_ok=True)
        with open(stray, "w") as f:
            f.write("never laid out\n")
        code, out, _ = self.install()
        self.assertIn("not laid out by solo-sdd", next(l for l in out.splitlines() if "openspec/analyze.md" in l))
        os.remove(stray)
        os.remove(edited)
        os.remove(job)
        code, out, _ = self.install()
        self.assertNotIn("openspec", out.lower())
        with open(os.path.join(self.home, ".local/share/solo-sdd/state.json")) as f:
            self.assertNotIn(test, json.load(f))

    def test_sync_push_retires_too(self):
        self.assertEqual(self.install()[0], 0)
        same = self.plant("~/.local/bin/openspec-after-update.py", "old\n", "old\n")
        code, out, _ = run([sys.executable, "sync.py", "push"], self.home, path=os.path.join(self.tmp, "empty"))
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(same))
        self.assertIn("removed    ~/.local/bin/openspec-after-update.py — no longer laid out", out.splitlines())


class Agents(unittest.TestCase):
    """Requirement: Install for chosen agents; Capability gaps named (spec-dispatch placement)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.home)
        os.makedirs(self.bin)

    def cli(self, *args):
        return run([sys.executable, "-m", "solo_sdd", *args], self.home, path=self.bin)

    def skills(self, agent):
        root = os.path.join(self.home, providers.PROVIDERS[agent]["skills"][2:])
        return sorted(d for d in os.listdir(root) if os.path.isfile(os.path.join(root, d, "SKILL.md"))) if os.path.isdir(root) else []

    def tree(self):
        return sorted(os.path.relpath(os.path.join(d, f), self.home) for d, _, fs in os.walk(self.home) for f in fs)

    def state(self):
        with open(os.path.join(self.home, ".local/share/solo-sdd/state.json")) as f:
            return json.load(f)

    def test_only_codex(self):
        code, out, _ = self.cli("install", "--agents", "codex")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(os.path.join(self.home, ".claude")))
        self.assertIn("spec-next", self.skills("codex"))
        self.assertIn("spec-next", self.skills("other"))
        self.assertEqual(self.state()["_agents"], ["codex", "other"])
        out = self.cli("status")[1]
        self.assertNotIn("~/.claude", out)
        self.assertIn("~/.codex/skills/spec-next/SKILL.md", out)

    def test_state_from_an_earlier_version(self):
        self.assertEqual(self.cli("install", "--agents", "claude,codex")[0], 0)
        state = self.state()
        del state["_agents"]
        with open(os.path.join(self.home, ".local/share/solo-sdd/state.json"), "w") as f:
            json.dump(state, f)
        shutil.rmtree(os.path.join(self.home, ".claude/skills/ship"))  # nothing detected in PATH: all three still apply
        self.assertIn("missing", self.cli("status")[1])
        code, out, _ = self.cli("update")
        self.assertEqual(code, 0, out)
        self.assertIn("ship", self.skills("claude"))
        self.assertEqual(self.state()["_agents"], list(providers.LEGACY))

    def test_unknown_agent(self):
        before = self.tree()
        code, out, _ = self.cli("install", "--agents", "copilt")
        self.assertEqual(code, 1)
        self.assertIn("unknown agent copilt; known: claude, codex, cursor, other", out)
        self.assertEqual(self.tree(), before)

    def test_repeated_install_keeps_the_choice(self):
        self.assertEqual(self.cli("install", "--agents", "codex")[0], 0)
        with open(os.path.join(self.bin, "claude"), "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(os.path.join(self.bin, "claude"), 0o755)
        self.assertEqual(self.cli("install")[0], 0)
        self.assertEqual(self.skills("claude"), [])
        self.assertEqual(self.state()["_agents"], ["codex", "other"])

    def test_first_install_takes_the_detected(self):
        os.makedirs(os.path.join(self.home, ".codex"))
        self.assertEqual(self.cli("install")[0], 0)
        self.assertEqual(self.state()["_agents"], ["codex", "other"])
        self.assertEqual(self.skills("claude"), [])

    def test_narrowed_choice(self):
        self.assertEqual(self.cli("install", "--agents", "claude,codex")[0], 0)
        edited = os.path.join(self.home, ".claude/skills/ship/SKILL.md")
        with open(edited, "a") as f:
            f.write("mine\n")
        code, out, _ = self.cli("install", "--agents", "codex")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.skills("claude"), ["ship"])
        self.assertRegex(out, r"kept +ship +~/.claude/skills/ship/SKILL.md — edited in place")
        self.assertFalse(os.path.exists(os.path.join(self.home, ".claude/hooks/work_hooks.py")))
        self.assertFalse(os.path.exists(os.path.join(self.home, ".claude/CLAUDE.md")))  # solo-sdd created it
        self.assertRegex(out, r"removed +\d+ copies of agents no longer chosen")
        self.assertIn("spec-next", self.skills("codex"))
        self.assertIn("~/.claude/skills/ship/SKILL.md", self.state())
        self.assertNotIn("~/.claude/skills/spec-next/SKILL.md", self.state())

    def test_hooks_without_claude(self):
        before = self.tree()
        code, out, _ = self.cli("install", "--agents", "codex", "--hooks")
        self.assertEqual(code, 1)
        self.assertIn("hooks need claude", out)
        self.assertEqual(self.tree(), before)

    def test_narrowing_with_connected_hooks(self):
        self.assertEqual(self.cli("install", "--agents", "claude,codex", "--hooks")[0], 0)
        before = self.tree()
        code, out, _ = self.cli("install", "--agents", "codex")
        self.assertEqual(code, 1)
        self.assertIn("hooks need claude", out)
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.cli("uninstall")[0], 0)
        self.assertEqual(self.cli("install", "--agents", "codex")[0], 0)

    def test_kept_copy_can_be_pulled(self):
        repo = os.path.join(self.tmp, "repo")
        copy_repo(repo)
        sdd = lambda *a: run([sys.executable, "-m", "solo_sdd", *a], self.home, cwd=repo, path=self.bin)
        self.assertEqual(sdd("install", "--agents", "claude")[0], 0)
        with open(os.path.join(self.home, ".claude/skills/ship/SKILL.md"), "a") as f:
            f.write("mine\n")
        self.assertEqual(sdd("install", "--agents", "codex")[0], 0)
        code, out, _ = sdd("sync", "pull", "ship")
        self.assertEqual(code, 0, out)
        self.assertIn("ship: taken from ~/.claude/skills/ship/SKILL.md", out)
        self.assertTrue(layout.read(os.path.join(repo, "skills/ship/SKILL.md")).endswith("mine\n"))

    def test_spec_dispatch_placement(self):
        self.assertEqual(self.cli("install", "--agents", "claude,codex")[0], 0)
        self.assertIn("spec-dispatch", self.skills("claude"))
        self.assertNotIn("spec-dispatch", self.skills("codex"))
        self.assertNotIn("spec-dispatch", self.skills("other"))

    def test_uninstall_removes_every_agent(self):
        self.assertEqual(self.cli("install", "--agents", "claude,codex")[0], 0)
        self.assertEqual(self.cli("uninstall")[0], 0)
        self.assertEqual([p for p in self.tree() if p.endswith("SKILL.md")], [])
        self.assertNotIn("_agents", self.state())


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
        self.set_state()

    def sync(self, *args, repo=REPO):
        """sync.py; push turns the global rules block on, the subject of these tests."""
        args = args + ("--global-rules",) if args[:1] == ("push",) else args
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
        """The state with entries; the global rules block is on, as after an install with --global-rules."""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(dict(_global_rules=True, **entries), f)

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
        mine = "mes règles\nsans saut de ligne à la fin".encode()
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
        lines = [l for l in self.get().decode().splitlines(True) if l.strip() not in (rules_block.BEGIN, rules_block.END)]
        self.assertEqual("".join(lines), self.source)

    def test_migration_with_new_source(self):
        old = "old text\n"
        self.put(old.encode())
        self.set_state(**{"~/.claude/CLAUDE.md": digest(old)})
        self.assertEqual(self.sync("push")[0], 0)
        self.assertEqual(self.get(), rules_block.block(self.body).encode())
        self.assertEqual(self.backups(), [old.encode()])

    def test_edit_inside_block_is_drift_and_pull_takes_body(self):
        self.assertEqual(self.sync("push")[0], 0)
        edited = self.get().decode().replace(self.body.splitlines()[0], "EDIT IN PLACE", 1)
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
        self.put("someone else's rules\n".encode())
        self.assertEqual(self.kind(), "first")
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(repo)
        copy_repo(repo)
        code, out = self.sync("pull", RULES, repo=repo)
        self.assertEqual(code, 0)
        with open(os.path.join(repo, RULES), encoding="utf-8") as f:
            self.assertEqual(f.read(), self.source)

    @marks.slow
    def test_broken_marks_are_never_written(self):
        b, e = rules_block.BEGIN, rules_block.END
        for bad in (f"a\n{b}\nx\n", f"{e}\nx\n{b}\n", f"{b}\n1\n{e}\n{b}\n2\n{e}\n", f"{e}\n"):
            self.put(bad.encode())
            self.assertEqual(self.kind(), "drift", bad)
            for args in (("push",), ("push", "--force")):
                code, out = self.sync(*args)
                self.assertEqual(code, 1)
                self.assertIn("broken solo-sdd markers", out)
                self.assertEqual(self.get(), bad.encode())

    def erased(self):
        """The block was there, the markers were erased, a person added text."""
        self.assertEqual(self.sync("push")[0], 0)
        text = self.get().decode().replace(rules_block.BEGIN + "\n", "").replace(rules_block.END + "\n", "")
        text += "personal addition\n"
        self.put(text.encode())
        return text.encode()

    def test_erased_marks_are_never_written_or_pulled(self):
        mine = self.erased()
        self.assertEqual(self.kind(), "drift")
        for args in (("push",), ("push", "--force")):
            code, out = self.sync(*args)
            self.assertEqual(code, 1)
            self.assertIn("broken solo-sdd markers", out)
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
        self.assertNotIn("no copy differs from the repository", out)
        with open(os.path.join(repo, RULES), encoding="utf-8") as f:
            self.assertEqual(f.read(), self.source)

    def test_old_layout_edited_in_place_force_appends_block(self):
        mine = ("old deployment\n" + self.source + "edit\n").encode()
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
        human = f"see {rules_block.BEGIN} in the middle of a line\n".encode()
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
            json.dump({"skills": {},
                       "files": {RULES: {"mode": "block", "copies": ["~/AGENTS.md"]}}}, f)

    def source(self, text):
        with open(os.path.join(self.repo, RULES), "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return rules_block.norm(layout.read(os.path.join(self.repo, RULES)))

    human = st.one_of(
        st.just(""), st.text(alphabet=" \t\n\r", max_size=6),
        st.text(max_size=20).filter(lambda t: not t.endswith("\n")),
        st.just("x\n<!-- not a marker\n"), st.just("<!--"), st.just("a\r\nb\r\n"), st.just("a\x0bb\x85c\n"),
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
            self.assertEqual((disk(), layout.load_state()), snapshot, "a repeated deployment changed something")
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


def rules_key():
    return "~/.claude/CLAUDE.md"


AGENTS_BIN = tempfile.mkdtemp()  # fake `claude` and `codex`: in-process runs detect both, whatever the machine has
atexit.register(shutil.rmtree, AGENTS_BIN, True)
for _name in ("claude", "codex"):
    with open(os.path.join(AGENTS_BIN, _name), "w") as _f:
        _f.write("#!/bin/sh\n")
    os.chmod(os.path.join(AGENTS_BIN, _name), 0o755)


def inproc(home, *args, repo=None, prefix=None):
    """cli.main in this process on a temporary home folder, with PATH holding only fake `claude` and `codex`."""
    data = os.path.join(home, ".local", "share", "solo-sdd")
    out = io.StringIO()
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.multiple(layout, HOME=home, DATA=data, STATE=os.path.join(data, "state.json")))
        stack.enter_context(mock.patch.dict(os.environ, {"HOME": home, "PATH": AGENTS_BIN}))
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
        self.assertIn("subagent depth 2: written", out)
        baks = self.baks()
        self.assertEqual(len(baks), 1)
        self.assertEqual(self.get(os.path.join(os.path.dirname(self.settings), baks[0])), raw.encode())
        steps = self.state()["_hooks"]
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["env"], {D: "2"})
        self.assertEqual(steps[0]["backup"], "~/.claude/" + baks[0])
        s = json.loads(text)
        for event in ("SessionStart", "PreToolUse", "SubagentStart", "PostToolUse", "PostToolUseFailure",
                      "Stop", "UserPromptSubmit", "SubagentStop", "SessionEnd"):
            self.assertIn("work_hooks.py", json.dumps(s["hooks"][event]), event)
        self.assertIn("echo mine", json.dumps(s["hooks"]["Stop"]))
        self.assertIn("work_hooks.py", s["statusLine"]["command"])
        allow = s["autoMode"]["allow"]
        self.assertEqual(allow[0], "$defaults")
        self.assertEqual(len([x for x in allow if x.startswith(hooks.P)]), 1)

    # Requirement: Process guard connected
    PG_DENY = ["Bash(%s *)" % n for n in ("pkill", "killall", "kill", "osascript", "launchctl", "shutdown")] + ["Read(**/.env)"]

    def pg_groups(self):
        return [g for g in json.loads(self.get()).get("hooks", {}).get("PreToolUse", []) if "process-guard.py" in json.dumps(g)]

    def test_process_guard_connected_a_fresh_home(self):
        os.rmdir(os.path.dirname(self.settings))
        self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        groups = self.pg_groups()
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["matcher"], "Bash|Monitor")
        self.assertEqual(groups[0]["hooks"][0]["command"], 'exec /usr/bin/python3 "$HOME/.claude/hooks/process-guard.py"')
        self.assertEqual(json.loads(self.get())["permissions"]["deny"], self.PG_DENY)
        self.assertIn("ok process guard: connected", inproc(self.home, "doctor")[1].splitlines())
        self.assertEqual(inproc(self.home, "uninstall")[0], 0)
        self.assertFalse(os.path.exists(self.settings))
        self.put("{}")
        self.assertIn("warn process guard: not connected", inproc(self.home, "doctor")[1].splitlines())

    def test_process_guard_connected_connected_by_hand(self):
        mine = {"matcher": "Bash|Monitor", "hooks": [{"type": "command", "command": 'exec /usr/bin/python3 "$HOME/.claude/hooks/process-guard.py"', "timeout": 5}]}
        self.put(json.dumps({"hooks": {"PreToolUse": [mine]}, "permissions": {"deny": ["Bash(kill *)", "Read(x)"]}}))
        self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        self.assertEqual(self.pg_groups(), [mine])
        self.assertEqual(json.loads(self.get())["permissions"]["deny"], ["Bash(kill *)", "Read(x)"] + [x for x in self.PG_DENY if x != "Bash(kill *)"])
        self.assertNotIn("process-guard.py", json.dumps(self.state()["_hooks"]))
        self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        self.assertEqual(len(self.state()["_hooks"]), 1)
        self.assertEqual(inproc(self.home, "uninstall")[0], 0)
        self.assertEqual(json.loads(self.get()), {"hooks": {"PreToolUse": [mine]}, "permissions": {"deny": ["Bash(kill *)", "Read(x)"]}})

    def test_process_guard_connected_later_copy_of_a_rule_stays(self):
        self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        s = json.loads(self.get())
        s["permissions"]["deny"].append("Bash(pkill *)")
        self.put(json.dumps(s))
        self.assertEqual(inproc(self.home, "uninstall")[0], 0)
        self.assertEqual(json.loads(self.get())["permissions"]["deny"], ["Bash(pkill *)"])

    # Requirement: Deny rules for secret files
    def test_deny_rules_for_secret_files_a_round_trip(self):
        self.put(json.dumps({"permissions": {"deny": ["Read(./secrets/**)"]}}))
        self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        self.assertEqual(json.loads(self.get())["permissions"]["deny"].count("Read(**/.env)"), 1)
        self.assertIn("Read(**/.env)", self.state()["_hooks"][0]["deny"])
        self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        self.assertEqual(json.loads(self.get())["permissions"]["deny"].count("Read(**/.env)"), 1)
        self.assertEqual(inproc(self.home, "uninstall")[0], 0)
        self.assertEqual(json.loads(self.get())["permissions"]["deny"], ["Read(./secrets/**)"])

    def test_deny_rules_for_secret_files_an_entry_the_owner_wrote(self):
        self.put(json.dumps({"permissions": {"deny": ["Read(**/.env)"]}}))
        self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        self.assertNotIn("Read(**/.env)", self.state()["_hooks"][0]["deny"])
        self.assertEqual(inproc(self.home, "uninstall")[0], 0)
        self.assertEqual(json.loads(self.get())["permissions"]["deny"], ["Read(**/.env)"])

    # Requirement: Sandbox read deny for secret files
    def test_sandbox_read_deny_sandbox_on(self):
        raw = json.dumps({"sandbox": {"enabled": True}}, indent=4).encode()
        self.put(raw)
        with mock.patch.object(hooks.sys, "platform", "darwin"):
            code, out = inproc(self.home, "install", "--hooks")
            doc = inproc(self.home, "doctor")[1].splitlines()
        self.assertEqual(code, 0)
        s = json.loads(self.get())
        self.assertEqual(s["sandbox"], {"enabled": True})
        self.assertEqual(s["permissions"]["deny"].count("Read(**/.env)"), 1)
        self.assertIn("Read(**/.env)", self.state()["_hooks"][0]["deny"])
        self.assertIn("sandbox read deny: expected active, Read(**/.env) in permissions.deny applies to sandboxed commands (read from Claude Code, not run)", out)
        self.assertIn("ok sandbox read: expected active, Read(**/.env) in permissions.deny applies to sandboxed commands (read from Claude Code, not run)", doc)
        self.assertEqual(inproc(self.home, "uninstall")[0], 0)
        self.assertEqual(self.get(), raw)
        with mock.patch.object(hooks.sys, "platform", "linux"):
            out = inproc(self.home, "install", "--hooks")[1]
        self.assertIn("sandbox read deny: not active, Claude Code ignores glob Read rules in the sandbox on linux", out)
        with mock.patch.object(hooks.sys, "platform", "win32"):
            self.assertEqual(hooks.sandbox_read({"sandbox": {"enabled": True}, "permissions": {"deny": ["Read(**/.env)"]}})[0], "gap")
        self.put(json.dumps({"sandbox": {"enabled": True}}))
        self.assertIn("warn sandbox read: not active, Read(**/.env) missing from permissions.deny; run solo-sdd install --hooks",
                      inproc(self.home, "doctor")[1].splitlines())
        self.put("{")
        self.assertTrue(any(x.startswith("warn sandbox read: unknown, settings unreadable") for x in inproc(self.home, "doctor")[1].splitlines()))

    def test_sandbox_read_deny_sandbox_off(self):
        for settings in ({}, {"sandbox": {"enabled": False}}, {"sandbox": "on"}):
            self.put(json.dumps(settings))
            code, out = inproc(self.home, "install", "--hooks")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(self.get()).get("sandbox"), settings.get("sandbox"))
            self.assertIn("sandbox read deny: off, it needs the sandbox (sandbox.enabled in ~/.claude/settings.json)", out)
            self.assertIn("ok sandbox read: off, it needs the sandbox (sandbox.enabled in ~/.claude/settings.json)", inproc(self.home, "doctor")[1].splitlines())
            self.assertEqual(inproc(self.home, "uninstall")[0], 0)

    def test_guard_matcher_reads(self):
        self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        m = [g["matcher"] for g in json.loads(self.get())["hooks"]["PreToolUse"] if g["hooks"][0]["command"].endswith('"$f" guard')]
        self.assertTrue(m and {"Read", "Grep", "Bash"} <= set(m[0].split("|")), m)

    def test_depth_changed_by_human_is_not_ours(self):
        self.put(json.dumps(MINE))
        inproc(self.home, "install", "--hooks")
        s = json.loads(self.get())
        s["env"][D] = "3"
        self.put(json.dumps(s))
        code, out = inproc(self.home, "install", "--hooks")
        self.assertEqual(code, 0, out)
        self.assertIn("subagent depth 3: set by the owner, not changed", out)

    def test_backup_name_taken_keeps_both(self):
        raw = json.dumps(MINE)
        self.put(raw)
        with mock.patch.object(hooks.time, "strftime", return_value="20260101-000000"):
            self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
            first = self.get().decode()
            s = json.loads(first)
            del s["statusLine"]
            self.put(json.dumps(s))
            changed = self.get()
            self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        baks = self.baks()
        self.assertEqual(len(baks), 2)
        folder = os.path.dirname(self.settings)
        self.assertEqual(self.get(os.path.join(folder, baks[0])), raw.encode())
        self.assertEqual(self.get(os.path.join(folder, baks[1])), changed)

    @unittest.skipIf(os.geteuid() == 0, "root reads any files")
    def test_unreadable_settings(self):
        self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        os.chmod(self.settings, 0)
        self.addCleanup(os.chmod, self.settings, 0o644)
        code, out = inproc(self.home, "install", "--hooks")
        self.assertEqual(code, 1)
        self.assertIn("fail settings: no access", out)
        code, out = inproc(self.home, "uninstall")
        self.assertEqual(code, 1)
        self.assertIn("fail settings:", out)
        self.assertIn("_hooks", self.state())

    def test_uninstall_edited_skill_then_install_sees_drift(self):
        inproc(self.home, "install")
        edited = os.path.join(self.home, ".codex/skills/spec-next/SKILL.md")
        with open(edited, "a") as f:
            f.write("edit\n")
        mine = self.get(edited)
        inproc(self.home, "uninstall")
        key = "~/.codex/skills/spec-next/SKILL.md"
        self.assertEqual(list(self.state()), [key])
        code, out = inproc(self.home, "install")
        self.assertEqual(code, 1)
        self.assertIn("skipped", out)
        self.assertEqual(self.get(edited), mine)
        self.assertRegex(inproc(self.home, "status")[1], r"(?m)^drift .*\.codex/skills/spec-next/SKILL\.md")

    def test_uninstall_edited_block_keeps_record(self):
        rules = os.path.join(self.home, ".claude", "CLAUDE.md")
        inproc(self.home, "install", "--global-rules")
        text = self.get(rules).decode().replace("\n", "\nedit\n", 3)
        self.put(text.encode(), rules)
        self.assertEqual(inproc(self.home, "uninstall")[0], 0)
        self.assertEqual(self.get(rules), text.encode())
        self.assertIn(rules_key(), self.state()["_blocks"])
        self.assertEqual(inproc(self.home, "uninstall")[0], 0)
        self.assertEqual(self.get(rules), text.encode())

    def test_block_only_file_removed_empty_file_stays(self):
        rules = os.path.join(self.home, ".claude", "CLAUDE.md")
        inproc(self.home, "install", "--global-rules")
        inproc(self.home, "uninstall")
        self.assertFalse(os.path.exists(rules))
        self.put(b"", rules)
        inproc(self.home, "install", "--global-rules")
        self.assertNotEqual(self.get(rules), b"")
        inproc(self.home, "uninstall")
        self.assertEqual(self.get(rules), b"")

    def test_uninstall_ignores_copy_without_record(self):
        inproc(self.home, "install")
        state = self.state()
        del state["~/.codex/skills/spec-next/SKILL.md"]
        self.put(json.dumps(state), self.state_file)
        code, out = inproc(self.home, "uninstall")
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(os.path.join(self.home, ".codex/skills/spec-next/SKILL.md")))
        self.assertNotIn(".codex/skills/spec-next", out)

    def test_depth_of_owner_kept(self):
        self.put(json.dumps({"env": {D: "3"}}))
        code, out = inproc(self.home, "install", "--hooks")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.get())["env"], {D: "3"})
        self.assertNotIn("env", self.state()["_hooks"][0])
        self.assertIn("subagent depth 3: set by the owner, not changed", out)

    def test_repeat_changes_nothing(self):
        self.put(json.dumps(MINE, indent=4))
        inproc(self.home, "install", "--hooks")
        before = self.tree()
        code, out = inproc(self.home, "install", "--hooks")
        self.assertEqual(code, 0)
        self.assertEqual(self.tree(), before)
        self.assertEqual(len(self.state()["_hooks"]), 1)
        self.assertIn("subagent depth 2: written", out)

    def test_missing_settings_created_and_removed(self):
        os.rmdir(os.path.dirname(self.settings))
        self.assertEqual(inproc(self.home, "install", "--hooks")[0], 0)
        self.assertTrue(os.path.isfile(self.settings))
        self.assertIsNone(self.state()["_hooks"][0]["backup"])
        self.assertEqual(inproc(self.home, "uninstall")[0], 0)
        self.assertFalse(os.path.exists(self.settings))
        self.assertNotIn("_hooks", self.state())

    def test_hostile_input(self):
        for bad in ('{"hooks": {"Stop": [', "[]", '{"hooks": []}', '{"env": 1}', '{"autoMode": []}', '{"permissions": []}',
                    '{"permissions": {"deny": {}}}',
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
        self.assertIn("ok: hooks connected", out)
        self.assertEqual(self.get(), self.get(os.path.join(other, ".claude", "settings.json")))
        with open(os.path.join(other, ".local/share/solo-sdd/state.json")) as f:
            self.assertEqual(len(json.load(f)["_hooks"]), 1)

    def test_uninstall_returns_as_it_was(self):
        rules = os.path.join(self.home, ".claude", "CLAUDE.md")
        mine = "mes règles\r\nsans fin".encode()
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
            f.write("edit\n")
        code, out = inproc(self.home, "uninstall")
        self.assertEqual(code, 0)
        self.assertIn("kept", out)
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
        self.assertEqual(inproc(self.home, "install", "--global-rules", repo=repo)[0], 0)
        with open(os.path.join(repo, RULES), "a", encoding="utf-8") as f:
            f.write("\nnew line\n")
        self.assertEqual(inproc(self.home, "install", "--global-rules", repo=repo)[0], 0)
        self.assertIn("new line", self.get(rules).decode())
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
            f.write("after\n")
        code, out = inproc(self.home, "uninstall")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(self.get()), {"model": "x", "added": [1]})
        self.assertEqual(self.get(rules), "human\nafter\n".encode())

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
        inproc(self.home, "install", "--global-rules")
        rules = os.path.join(self.home, ".claude", "CLAUDE.md")
        bad = (self.get(rules).decode() + rules_block.BEGIN + "\n").encode()
        self.put(bad, rules)
        code, out = inproc(self.home, "uninstall")
        self.assertEqual(code, 0)
        self.assertIn("broken solo-sdd markers", out)
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

    # Requirement: Purge keeps what solo-sdd did not write
    def purge_setup(self):
        data = os.path.join(self.home, ".local/share/solo-sdd")
        os.makedirs(os.path.join(self.home, ".local/share/openspec/schemas/solo"))
        self.assertEqual(inproc(self.home, "install")[0], 0)
        owner = os.path.join(data, "integrations/demo/integration")
        os.makedirs(os.path.dirname(owner))
        with open(owner, "w") as f:
            f.write("name: demo\n")
        for own in ("checks/repo-0123/tree.json", "backup/20260101-000000-1-1/x"):
            os.makedirs(os.path.dirname(os.path.join(data, own)))
            with open(os.path.join(data, own), "w") as f:
                f.write("{}")
        return data, owner

    def test_purge_keeps_owner_integration(self):
        data, owner = self.purge_setup()
        code, out = inproc(self.home, "uninstall", "--purge")
        self.assertEqual(code, 0, out)
        with open(owner) as f:
            self.assertEqual(f.read(), "name: demo\n")
        kept = [line.split()[1] for line in out.splitlines() if line.startswith("kept")]
        self.assertEqual(kept, ["~/.local/share/solo-sdd/integrations"], out)
        self.assertEqual(os.listdir(data), ["integrations"])
        self.assertFalse(os.path.exists(os.path.join(self.home, ".local/share/openspec/schemas/solo")))

    @unittest.skipIf(os.geteuid() == 0, "root deletes in a read-only folder")
    def test_purge_undeletable_entry(self):
        data, owner = self.purge_setup()
        locked = os.path.join(data, "backup/20260101-000000-1-1")
        os.chmod(locked, 0o500)
        self.addCleanup(os.chmod, locked, 0o700)
        code, out = inproc(self.home, "uninstall", "--purge")
        self.assertEqual(code, 1, out)
        self.assertTrue([line for line in out.splitlines()
                         if line.startswith("no access") and "/.local/share/solo-sdd/backup" in line], out)
        self.assertTrue(os.path.isfile(owner))
        self.assertFalse(os.path.exists(os.path.join(data, "state.json")))
        self.assertFalse(os.path.exists(os.path.join(data, "checks")))

    @unittest.skipIf(os.geteuid() == 0, "root deletes in a read-only folder")
    def test_purge_data_folder_not_removable(self):
        share = os.path.join(self.home, ".local/share")
        self.assertEqual(inproc(self.home, "install")[0], 0)
        os.chmod(share, 0o500)
        self.addCleanup(os.chmod, share, 0o700)
        code, out = inproc(self.home, "uninstall", "--purge")
        self.assertEqual(code, 1, out)
        self.assertTrue([line for line in out.splitlines()
                         if line.startswith("no access") and line.split()[2] == "~/.local/share/solo-sdd:"], out)
        self.assertEqual(os.listdir(os.path.join(share, "solo-sdd")), [])

    @unittest.skipIf(os.geteuid() == 0, "root deletes in a read-only folder")
    def test_purge_kept_entry_under_read_only_share(self):
        data, owner = self.purge_setup()
        share = os.path.dirname(data)
        os.chmod(share, 0o500)
        self.addCleanup(os.chmod, share, 0o700)
        code, out = inproc(self.home, "uninstall", "--purge")
        self.assertEqual(code, 0, out)
        self.assertNotIn("no access", out)
        self.assertEqual(os.listdir(data), ["integrations"])

    def test_unknown_flags(self):
        self.assertEqual(inproc(self.home, "install", "--bogus")[0], 2)
        self.assertEqual(inproc(self.home, "uninstall", "--hooks")[0], 2)
        self.assertEqual(inproc(self.home, "install", "--purge")[0], 2)


class GlobalRules(unittest.TestCase):
    """Requirement: Global rules opt-in."""
    COPIES = ("AGENTS.md", ".codex/AGENTS.md", ".claude/CLAUDE.md")

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        make_home(self.home)
        self.state_file = os.path.join(self.home, ".local/share/solo-sdd/state.json")

    def files(self):
        out = {}
        for rel in self.COPIES:
            p = os.path.join(self.home, rel)
            if os.path.exists(p):
                with open(p, "rb") as f:
                    out[rel] = f.read()
        return out

    def state(self):
        with open(self.state_file) as f:
            return json.load(f)

    def test_new_home_gets_no_global_rules(self):
        code, out = inproc(self.home, "install")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.files(), {})
        self.assertIs(self.state()["_global_rules"], False)
        self.assertNotIn("CLAUDE.md", inproc(self.home, "status")[1])
        self.assertEqual((inproc(self.home, "update")[0], self.files()), (0, {}))

    def test_earlier_deployment_keeps_the_block(self):
        """A state from a version before the choice records the block: install and update keep laying it out."""
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(repo)
        copy_repo(repo)
        self.assertEqual(inproc(self.home, "install", "--global-rules", repo=repo)[0], 0)
        state = self.state()
        del state["_global_rules"]
        with open(self.state_file, "w") as f:
            json.dump(state, f)
        with open(os.path.join(repo, RULES), "a", encoding="utf-8") as f:
            f.write("\nnew rule\n")
        code, out = inproc(self.home, "install", repo=repo)
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(self.files()), sorted(self.COPIES))
        for data in self.files().values():
            self.assertIn(b"new rule", data)
        self.assertIs(self.state()["_global_rules"], True)
        rows = [l for l in inproc(self.home, "status", repo=repo)[1].splitlines() if "global/AGENTS.md" in l]
        self.assertEqual([l.split()[0] for l in rows], ["ok"] * 3)

    def test_round_trip(self):
        with open(os.path.join(self.home, "AGENTS.md"), "wb") as f:
            f.write(b"my own rules\r\nno newline")
        before = self.files()
        self.assertEqual(inproc(self.home, "install")[0], 0)
        self.assertEqual(inproc(self.home, "install", "--global-rules")[0], 0)
        self.assertEqual(sorted(self.files()), sorted(self.COPIES))
        self.assertEqual(inproc(self.home, "install")[0], 0)  # the choice is remembered
        self.assertEqual(sorted(self.files()), sorted(self.COPIES))
        code, out = inproc(self.home, "uninstall", "--global-rules")
        self.assertEqual((code, self.files()), (0, before), out)
        self.assertIn("global rules removed: 3", out)
        self.assertTrue(os.path.exists(os.path.join(self.home, ".claude/skills/spec-next/SKILL.md")))
        self.assertEqual((inproc(self.home, "install")[0], self.files()), (0, before))
        self.assertFalse([k for k in self.state() if k in ("~/AGENTS.md", "~/.codex/AGENTS.md", "~/.claude/CLAUDE.md")])

    def test_edited_block_survives_uninstall_rules(self):
        inproc(self.home, "install", "--global-rules")
        rules = os.path.join(self.home, ".claude/CLAUDE.md")
        edited = self.files()[".claude/CLAUDE.md"].replace(b"\n", b"\nedit\n", 3)
        with open(rules, "wb") as f:
            f.write(edited)
        code, out = inproc(self.home, "uninstall", "--global-rules")
        self.assertEqual(code, 0)
        self.assertIn("kept", out)
        self.assertEqual(self.files(), {".claude/CLAUDE.md": edited})

    def test_kept_edited_block_does_not_turn_rules_back_on(self):
        """After a full uninstall that kept an edited global block, a plain install writes no global rules."""
        for opt_out in (False, True):
            shutil.rmtree(self.home)
            make_home(self.home)
            inproc(self.home, "install", "--global-rules")
            mine = os.path.join(self.home, "AGENTS.md")
            with open(mine, "rb") as f:
                edited = f.read().replace(b"\n", b"\nedit\n", 3)
            with open(mine, "wb") as f:
                f.write(edited)
            if opt_out:
                inproc(self.home, "uninstall", "--global-rules")
            inproc(self.home, "uninstall")
            self.assertIs(self.state()["_global_rules"], False)
            code, out = inproc(self.home, "install")
            self.assertEqual((code, self.files()), (0, {"AGENTS.md": edited}), (opt_out, out))

    def test_flags(self):
        for args in (("install", "--global-rules", "--global-rules"), ("uninstall", "--global-rules", "--purge")):
            self.assertEqual(inproc(self.home, *args)[0], 2, args)


class Doctor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.bin = os.path.join(self.tmp, "bin")
        make_home(self.home)
        os.makedirs(self.bin)
        self.state_file = os.path.join(self.home, ".local/share/solo-sdd/state.json")

    def installed(self):
        self.assertEqual(run([sys.executable, "sync.py", "push"], self.home, path=self.bin)[0], 0)

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
        self.installed()
        code, out, _ = self.go("doctor", extra={"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "2"})
        self.assertEqual(code, 0, out)
        text = out.replace(os.path.realpath(REPO), "").replace(REPO, "")  # the clone path may hold the word
        self.assertNotIn("openspec", text.lower())
        self.assertNotIn("schema", text)

    def test_all_good(self):
        self.installed()
        code, out, _ = self.go("doctor", extra={"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "2"})
        self.assertEqual(code, 0, out)
        for name in ("python", "layout", "hooks", "depth"):
            self.assertRegex(out, r"(?m)^(ok|warn) %s: " % name)
        self.assertNotRegex(out, r"(?m)^fail ", "a fail row; the word alone may be in the clone path")

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

    @unittest.skipUnless(os.path.exists("/usr/bin/python3"), "no /usr/bin/python3")
    def test_python_hooks_ok(self):
        self.assertRegex(self.go("doctor")[1], r"(?m)^ok python-hooks: ")

    def test_drift(self):
        self.installed()
        self.go("install")
        target = os.path.join(self.home, ".claude/skills/spec-next/SKILL.md")
        with open(target, "a") as f:
            f.write("\nedit\n")
        code, out, _ = self.go("doctor")
        self.assertEqual(code, 1)
        self.assertRegex(out, r"(?m)^fail layout: .*drift 1")

    def test_hooks_removed(self):
        self.installed()
        self.assertEqual(self.go("install", "--hooks")[0], 0)
        self.assertIn("ok hooks: in place", self.go("doctor")[1])
        os.remove(os.path.join(self.home, ".claude/settings.json"))
        code, out, _ = self.go("doctor")
        self.assertEqual(code, 1)
        self.assertIn("fail hooks:", out)

    def test_hooks_not_connected_and_copy_missing(self):
        self.installed()
        self.assertIn("ok hooks: not connected", self.go("doctor")[1])
        os.remove(os.path.join(self.home, ".claude/skills/spec-next/SKILL.md"))
        code, out, _ = self.go("doctor")
        self.assertEqual(code, 1)
        self.assertRegex(out, r"(?m)^fail layout: ")

    @unittest.skipIf(os.geteuid() == 0, "root reads any files")
    def test_unreadable_settings_fails_hooks(self):
        self.installed()
        self.assertEqual(self.go("install", "--hooks")[0], 0)
        settings = os.path.join(self.home, ".claude/settings.json")
        os.chmod(settings, 0)
        self.addCleanup(os.chmod, settings, 0o644)
        code, out, _ = self.go("doctor")
        self.assertEqual(code, 1)
        self.assertRegex(out, r"(?m)^fail hooks: ")

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
        self.assertIn("warn source: laid out from", out)

    # Requirement: Doctor hook errors
    def elog(self, lines):
        d = os.path.join(self.home, ".claude/hook-state")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "errors.log"), "w") as f:
            f.write("".join(l + "\n" for l in lines))

    @staticmethod
    def ago(days):
        import datetime
        return (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat(timespec="seconds")

    def test_doctor_hook_errors_a_broken_policy(self):
        self.installed()
        self.assertEqual(self.go("install", "--hooks")[0], 0)
        self.assertIn("ok model policy: parsed", self.go("doctor")[1].splitlines())
        with open(os.path.join(self.home, ".claude/hooks/model-policy.json"), "w") as f:
            f.write("{")
        code, out, _ = self.go("doctor")
        self.assertEqual(code, 1)
        self.assertRegex(out, r"(?m)^fail model policy: .*line 1 column 2")
        os.remove(os.path.join(self.home, ".claude/hooks/model-policy.json"))
        self.assertRegex(self.go("doctor")[1], r"(?m)^fail model policy: .*No such file")

    def test_doctor_hook_errors_recent_errors(self):
        self.installed()
        last = self.ago(1) + " stop ValueError('b')"
        self.elog([self.ago(1.2) + " guard ValueError('a')", last, self.ago(30) + " guard old"])
        out = self.go("doctor")[1]
        self.assertIn("warn hook errors: 2 in the last 7 days, last: " + last, out.splitlines())
        self.assertNotIn("model policy", out, "hooks are not connected: no policy line")

    def test_doctor_hook_errors_one_count_with_the_hook(self):
        # Requirement: Tests use the block check (shared-blocks)
        r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "sync_blocks.py"), "--check"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_doctor_hook_errors_a_clean_log(self):
        self.installed()
        self.assertIn("ok hook errors: none", self.go("doctor")[1].splitlines())
        self.elog([self.ago(30) + " guard old", "no time here"])
        self.assertIn("ok hook errors: none", self.go("doctor")[1].splitlines())


class RulesSize(unittest.TestCase):
    """Doctor rules size: bytes Codex loads as instructions against project_doc_max_bytes."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.codex = os.path.join(self.tmp, "codex")
        self.repo = os.path.join(self.tmp, "repo")
        self.sub = os.path.join(self.repo, "a", "b")
        os.makedirs(self.codex)
        os.makedirs(self.sub)
        os.makedirs(os.path.join(self.repo, ".git"))

    def put(self, path, size, config=None):
        path = os.path.join(self.tmp, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(config if config is not None else "x" * size)
        return path

    def line(self, cwd=None):
        from solo_sdd import doctor
        with mock.patch.dict(os.environ, {"CODEX_HOME": self.codex}):
            rows = list(doctor._rules_size(cwd or self.sub))
        self.assertEqual(len(rows), 1)
        level, name, detail = rows[0]
        self.assertEqual(name, "rules-size")
        return f"{level} {name}: {detail}"

    def test_default_limit_passed(self):
        self.put("codex/AGENTS.md", 9000)
        self.put("repo/AGENTS.md", 20000)
        self.put("repo/a/AGENTS.md", 13000)
        line = self.line()
        self.assertTrue(line.startswith("fail rules-size: 33000 of 32768 bytes;"), line)
        self.assertIn("drops everything after 32768 bytes", line)

    def test_global_outside_budget(self):
        glob = self.put("codex/AGENTS.md", 30000)
        self.put("repo/AGENTS.md", 3000)
        line = self.line()
        self.assertTrue(line.startswith("ok rules-size: 3000 of 32768 bytes;"), line)
        self.assertTrue(line.endswith(f"; global {glob} 30000 outside the budget"), line)

    def test_fail_exits_1(self):
        self.put("repo/AGENTS.md", 33000)
        from solo_sdd import doctor
        old = os.getcwd()
        os.chdir(self.sub)
        self.addCleanup(os.chdir, old)
        with mock.patch.dict(os.environ, {"CODEX_HOME": self.codex}), contextlib.redirect_stdout(io.StringIO()) as out:
            code = doctor.run()
        self.assertEqual(code, 1)
        self.assertRegex(out.getvalue(), r"(?m)^fail rules-size: ")

    def test_raised_limit(self):
        self.put("codex/config.toml", 0, "model = 'x'\nproject_doc_max_bytes = 65536\n\n[profiles.a]\nproject_doc_max_bytes = 1\n")
        self.put("repo/AGENTS.md", 20000)
        self.put("repo/a/AGENTS.md", 13000)
        self.assertTrue(self.line().startswith("ok rules-size: 33000 of 65536 bytes"), self.line())

    def test_close_to_limit(self):
        self.put("repo/AGENTS.md", 26215)  # 80% of 32768 is 26214.4
        self.assertTrue(self.line().startswith("warn rules-size:"), self.line())
        self.put("repo/AGENTS.md", 26214)
        self.assertTrue(self.line().startswith("ok rules-size:"), self.line())
        self.put("repo/AGENTS.md", 32768)
        self.assertTrue(self.line().startswith("warn rules-size:"), self.line())
        self.put("repo/AGENTS.md", 32769)
        self.assertTrue(self.line().startswith("fail rules-size:"), self.line())

    def test_override_and_fallback(self):
        self.put("codex/config.toml", 0, 'project_doc_fallback_filenames = [\n  "TEAM.md",\n  ".agents.md",\n  "../OUT.md", "b/X.md", "",\n]\n')
        self.put("repo/a/OUT.md", 5000)
        self.put("repo/a/b/b/X.md", 5000)
        override = self.put("repo/AGENTS.override.md", 100)
        self.put("repo/AGENTS.md", 5000)
        team = self.put("repo/a/TEAM.md", 300)
        self.put("repo/a/b/NOTES.md", 700)
        line = self.line()
        self.assertTrue(line.startswith("ok rules-size: 400 of 32768 bytes"), line)
        self.assertIn(f"{team} 300", line)
        self.assertIn(f"{override} 100", line)
        self.assertNotIn(os.path.join(self.repo, "AGENTS.md"), line)
        self.assertNotIn("NOTES.md", line)
        self.assertNotIn("OUT.md", line)
        self.assertNotIn("X.md", line)

    def test_global_override(self):
        glob = self.put("codex/AGENTS.override.md", 10)
        self.put("codex/AGENTS.md", 9000)
        self.assertEqual(self.line(), f"ok rules-size: 0 of 32768 bytes; no project instructions; global {glob} 10 outside the budget")

    def test_blank_project_file(self):
        self.put("repo/AGENTS.override.md", 0, " \n\t\n")
        self.put("repo/AGENTS.md", 50)
        self.assertEqual(self.line(), "ok rules-size: no Codex instructions found")
        self.put("repo/AGENTS.override.md", 0, "\u00a0\u3000\n")
        self.assertEqual(self.line(), "ok rules-size: no Codex instructions found")
        self.put("repo/AGENTS.override.md", 0, "")
        self.assertEqual(self.line(), "ok rules-size: no Codex instructions found")

    @unittest.skipIf(os.geteuid() == 0, "root reads any file")
    def test_unreadable_project_file(self):
        override = self.put("repo/AGENTS.override.md", 10)
        self.put("repo/AGENTS.md", 50)
        os.chmod(override, 0)
        self.addCleanup(os.chmod, override, 0o644)
        self.assertEqual(self.line(), "ok rules-size: no Codex instructions found")

    def test_blank_global_override(self):
        self.put("codex/AGENTS.override.md", 0, "  \n")
        glob = self.put("codex/AGENTS.md", 20)
        self.assertTrue(self.line().endswith(f"; global {glob} 20 outside the budget"), self.line())

    def test_no_instructions(self):
        self.assertEqual(self.line(), "ok rules-size: no Codex instructions found")

    def test_disabled(self):
        self.put("codex/config.toml", 0, "project_doc_max_bytes = 0\n")
        line = self.line()
        self.assertTrue(line.startswith("warn rules-size:"), line)
        self.assertIn("Codex loads no project instructions", line)
        self.put("repo/AGENTS.md", 50)
        self.assertTrue(self.line().startswith("warn rules-size:"))

    def test_unreadable_config(self):
        self.put("codex/config.toml", 0, "project_doc_max_bytes = = [\n")
        self.put("repo/AGENTS.md", 50)
        line = self.line()
        self.assertTrue(line.startswith("ok rules-size: 50 of 32768 bytes"), line)
        self.assertIn("config.toml unreadable", line)

    def test_outside_git(self):
        os.rmdir(os.path.join(self.repo, ".git"))
        self.put("repo/AGENTS.md", 5000)
        self.put("repo/a/AGENTS.md", 300)
        here = self.put("repo/a/b/AGENTS.md", 70)
        glob = self.put("codex/AGENTS.md", 20)
        self.assertEqual(self.line(), f"ok rules-size: 70 of 32768 bytes; {here} 70; global {glob} 20 outside the budget")

    def test_git_file_marks_root(self):
        os.rmdir(os.path.join(self.repo, ".git"))
        self.put("repo/a/.git", 0, "gitdir: elsewhere\n")
        self.put("repo/AGENTS.md", 5000)
        self.put("repo/a/AGENTS.md", 300)
        self.assertIn("ok rules-size: 300 of 32768 bytes", self.line())

    def test_two_files_largest_first(self):
        glob = self.put("codex/AGENTS.md", 9000)
        proj = self.put("repo/AGENTS.md", 20000)
        self.assertEqual(self.line(), f"ok rules-size: 20000 of 32768 bytes; {proj} 20000; global {glob} 9000 outside the budget")
        small = self.put("repo/a/AGENTS.md", 300)
        self.assertIn(f"{proj} 20000, {small} 300; global", self.line())

    def test_minimal_toml_parser(self):
        from solo_sdd import doctor
        text = "project_doc_max_bytes = 65_536 # comment\nproject_doc_fallback_filenames = ['A.md', \"B.md\"]\n[x]\nproject_doc_max_bytes = 1\n"
        self.assertEqual(doctor._toml_keys(text), {"project_doc_max_bytes": 65536, "project_doc_fallback_filenames": ["A.md", "B.md"]})
        self.assertEqual(doctor._toml_keys('project_doc_fallback_filenames = ["A.md", # "B.md"\n "a]b.md"]\n'),
                         {"project_doc_fallback_filenames": ["A.md", "a]b.md"]})
        for bad in ("project_doc_max_bytes = 'x'\n", "project_doc_fallback_filenames = 1\n",
                    "x = [\n[1]\n]\nproject_doc_max_bytes = 65536\n", "[x]\nproject_doc_max_bytes = 1\n"):
            with self.assertRaises(ValueError):
                doctor._toml_keys(bad)

    def test_bad_values_unreadable(self):
        from solo_sdd import doctor
        for text in ("project_doc_max_bytes = -1\n", "project_doc_max_bytes = true\n", "project_doc_fallback_filenames = 'A.md'\n"):
            self.put("codex/config.toml", 0, text)
            self.assertEqual(doctor._codex_config(self.codex), (32768, [], "config.toml unreadable, defaults used"), text)

    def test_unreadable_config_without_tomllib(self):
        self.put("codex/config.toml", 0, "project_doc_max_bytes = = [\n")
        self.put("repo/AGENTS.md", 50)
        with mock.patch.dict(sys.modules, {"tomllib": None}):
            self.assertIn("config.toml unreadable", self.line())

    @settings(max_examples=300, deadline=None)
    @given(st.lists(st.integers(1, 40000), max_size=6), st.integers(1, 70000), st.one_of(st.none(), st.integers(1, 90000)))
    def test_rules_size_detail_property(self, sizes, limit, glob):
        from solo_sdd import doctor
        files = [(f"/f{i}", s) for i, s in enumerate(sizes)]
        level, detail = doctor._size_row(files, limit, glob and ("/g", glob))
        if glob:
            self.assertTrue(detail.endswith(f"; global /g {glob} outside the budget"), detail)
            detail = detail.rsplit("; global ", 1)[0]
        if not files:
            self.assertEqual((level, detail), ("ok", f"0 of {limit} bytes; no project instructions" if glob else "no Codex instructions found"))
            return
        total = sum(sizes)
        self.assertTrue(detail.startswith(f"{total} of {limit} bytes"), detail)
        listed = [int(part.rsplit(" ", 1)[1]) for part in detail.rsplit("; ", 1)[1].split(", ")]
        self.assertEqual(listed, sorted(sizes, reverse=True))
        self.assertEqual(level, "fail" if total > limit else "warn" if total * 5 >= limit * 4 else "ok")


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
        prefixed = hooks.P + " old version"
        auto = st.one_of(
            st.just({}), st.just({"allow": []}), st.just({"allow": ["$defaults"]}),
            st.just({"allow": ["$defaults", prefixed, "foreign"]}), st.just({"allow": ["foreign", prefixed, "more", prefixed + "2"]}),
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

    @marks.slow
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


class PurgeProperty(unittest.TestCase):
    """Requirement: Purge keeps what solo-sdd did not write."""
    OWN = {"state.json", "backup", "checks", "algorithm.md", "templates"}  # lower case: the file system may fold case
    name = st.one_of(
        st.sampled_from([".hidden", ".state.json.x.tmp", "state.json.bak", "templatesx", "ALGORITHM.md~", "integrations",
                         "checks2", "backups"]),
        st.text("abcXYZ019._-", min_size=1, max_size=8)).filter(lambda n: n not in (".", "..") and n.lower() not in PurgeProperty.OWN)

    @staticmethod
    def snapshot(path):
        if os.path.islink(path):
            return ("link", os.readlink(path))
        if os.path.isfile(path):
            with open(path, "rb") as f:
                return ("file", f.read())
        return {n: PurgeProperty.snapshot(os.path.join(path, n)) for n in sorted(os.listdir(path))}

    @marks.slow
    @settings(max_examples=20, deadline=None)
    @given(st.lists(st.tuples(name, st.booleans()), unique_by=lambda e: e[0].lower(), max_size=4), st.booleans())
    @example([(".hidden", False), ("state.json.bak", False), ("templatesx", True)], True)
    def test_purge_keeps_what_solo_sdd_did_not_write(self, entries, link):
        tmp = tempfile.mkdtemp()
        try:
            home = os.path.join(tmp, "home")
            make_home(home)
            data = os.path.join(home, ".local/share/solo-sdd")
            self.assertEqual(inproc(home, "install")[0], 0)
            for name, nested in entries:
                path = os.path.join(data, name, "sub", "deep", "f") if nested else os.path.join(data, name)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(name)
            foreign = [name for name, _ in entries]
            if link:
                outside = os.path.join(tmp, "outside")
                os.makedirs(outside)
                with open(os.path.join(outside, "f"), "w") as f:
                    f.write("outside")
                os.symlink(outside, os.path.join(data, "checks"))
                foreign.append("checks")
            before = {n: self.snapshot(os.path.join(data, n)) for n in foreign}
            code, out = inproc(home, "uninstall", "--purge")
            self.assertEqual(code, 0, out)
            self.assertEqual({n: self.snapshot(os.path.join(data, n)) for n in foreign}, before)
            if link:
                self.assertEqual(self.snapshot(outside), {"f": ("file", b"outside")})
            kept = {line.split()[1] for line in out.splitlines() if line.startswith("kept")}
            self.assertEqual(kept, {"~/.local/share/solo-sdd/" + n for n in foreign}, out)
            if foreign:
                self.assertEqual(sorted(os.listdir(data)), sorted(foreign))
            else:
                self.assertFalse(os.path.lexists(data))
        finally:
            shutil.rmtree(tmp, True)


def old(name):
    """Pre-English keyword by its English name, from the migration table (tests hold no old words)."""
    pairs = [(o, n) for o, n in keywords.OLD_SECTIONS.items()] + [p for v in keywords.OLD_ITEMS.values() for p in v]
    return next(o for o, n in pairs if n == name)


def load(rel, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


OLD_AGENTS = ("# P\n\nintro\n\n## %s\n\n- %s 3\n- %s `docs/x.md`\n\n## %s\n\n- %s pr\n- Merge: squash\n- %s `x/**`\n\n"
              "## Other\n\n- %s keep\n" % (old("Working copy"), old("Orchestrators:"), old("Paths:"), old("Delivery"),
                                          old("Mode:"), old("Owner only:"), old("Mode:")))
NEW_AGENTS = ("# P\n\nintro\n\n## Working copy\n\n- Orchestrators: 3\n- Paths: `docs/x.md`\n\n## Delivery\n\n- Mode: pr\n"
              "- Merge: squash\n- Owner only: `x/**`\n\n## Other\n\n- %s keep\n" % old("Mode:"))
CYRILLIC = range(0x400, 0x500)


class Keywords(unittest.TestCase):
    """Requirements: English keyword set; Old keywords are named, not ignored silently; AGENTS.md migration."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        make_home(self.home)

    def project(self, text):
        d = os.path.join(self.tmp, "p")
        os.makedirs(os.path.join(d, "openspec", "changes"), exist_ok=True)
        with open(os.path.join(d, "AGENTS.md"), "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return d

    def cli(self, *args, cwd=REPO):
        return run([sys.executable, "-m", "solo_sdd", *args], self.home, cwd=cwd, extra={"PYTHONPATH": REPO})

    def test_copies_match_the_table(self):
        # Requirement: Tests use the block check (shared-blocks)
        r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "sync_blocks.py"), "--check"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_table_without_cyrillic(self):
        with open(os.path.join(REPO, "solo_sdd/keywords.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertFalse([c for c in src if ord(c) in CYRILLIC], "keywords.py holds a Cyrillic letter")
        self.assertIn("\\u0420", src)
        self.assertTrue(all(ord(c) in CYRILLIC for c in old("Working copy") if c.isalpha()))

    def test_migrate_text(self):
        new, found = keywords.migrate_agents(OLD_AGENTS)
        self.assertEqual(new, NEW_AGENTS)
        self.assertEqual(found, ["Working copy", "Orchestrators:", "Paths:", "Delivery", "Mode:", "Owner only:"])
        self.assertEqual(keywords.migrate_agents(NEW_AGENTS), (NEW_AGENTS, []))
        crlf = OLD_AGENTS.replace("\n", "\r\n")
        self.assertEqual(keywords.migrate_agents(crlf)[0], NEW_AGENTS.replace("\n", "\r\n"))
        table = "## %s\n\n| What | Command |\n|---|---|\n| %s | `make test` |\n" % (old("Commands"), old("Tests"))
        self.assertEqual(keywords.migrate_agents(table)[0], "## Commands\n\n| What | Command |\n|---|---|\n| Tests | `make test` |\n")

    def test_cli_dry_run_write_repeat(self):
        d = self.project(OLD_AGENTS)
        path = os.path.join(d, "AGENTS.md")
        code, out, _ = self.cli("migrate-agents", d)
        self.assertEqual(code, 0)
        self.assertIn("-## " + old("Working copy") + "\n", out)
        self.assertIn("+## Working copy\n", out)
        self.assertIn("--write", out)
        with open(path, encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), OLD_AGENTS, "dry run changed the file")
        code, out, _ = self.cli("migrate-agents", d, "--write")
        self.assertEqual(code, 0)
        self.assertIn("rewritten", out)
        with open(path, encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), NEW_AGENTS)
        code, out, _ = self.cli("migrate-agents", "--write", d)
        self.assertEqual((code, out.strip()), (0, path + ": nothing to change"))
        with open(path, encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), NEW_AGENTS)

    def test_cli_without_agents_md(self):
        code, out, _ = self.cli("migrate-agents", self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("no AGENTS.md", out)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "AGENTS.md")))
        self.assertEqual(self.cli("migrate-agents", "a", "b")[0], 2)

    @settings(max_examples=200, deadline=None)
    @given(st.lists(st.one_of(
        st.text(st.characters(blacklist_characters="\n"), max_size=25),
        st.sampled_from(["## " + h for h in list(keywords.OLD_SECTIONS) + list(keywords.OLD_SECTIONS.values()) + ["Other"]]),
        st.sampled_from([b + o + t for items in keywords.OLD_ITEMS.values() for o, _ in items
                         for b in ("- ", "* ", "  - ", "| ") for t in ("", " `v`", ": x")])), max_size=25),
        st.sampled_from(["\n", "\r\n"]))
    def test_migration_property(self, lines, eol):
        text = eol.join(lines) + eol
        new, found = keywords.migrate_agents(text)
        before, after = text.split("\n"), new.split("\n")
        self.assertEqual(len(before), len(after))
        olds = [(o, n) for o, n in keywords.OLD_SECTIONS.items()] + [p for v in keywords.OLD_ITEMS.values() for p in v]
        for a, b in zip(before, after):
            if a != b:  # only a mapped heading or item changed, by exactly its English name
                self.assertTrue(any(a.replace(o, n, 1) == b for o, n in olds), (a, b))
        self.assertEqual(keywords.migrate_agents(new), (new, []), "second run changes nothing")
        self.assertEqual(bool(found), new != text)

    def test_doctor_names_old_keywords(self):
        d = self.project(OLD_AGENTS)
        code, out, _ = self.cli("doctor", cwd=d)
        line = next(ln for ln in out.splitlines() if ln.startswith("warn agents: "))
        for part in ("AGENTS.md", "Working copy", "Orchestrators:", "solo-sdd migrate-agents"):
            self.assertIn(part, line)
        self.assertFalse([c for c in line if ord(c) in CYRILLIC], "old keywords are named by their English names")
        self.project(NEW_AGENTS)
        self.assertIn("ok agents: English keywords", self.cli("doctor", cwd=d)[1])

    def test_plan_reader(self):
        d = self.project(OLD_AGENTS)
        code, out, err = run(["/usr/bin/python3", os.path.join(REPO, "global/sdd_dispatch_plan.py"), d], self.home)
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines()[0], "limit: 2, running: 0, waiting for merge: 0", "the old item takes no effect")
        self.assertIn(os.path.join(d, "AGENTS.md"), err)
        self.assertIn("solo-sdd migrate-agents", err)
        self.project(NEW_AGENTS)
        code, out, err = run(["/usr/bin/python3", os.path.join(REPO, "global/sdd_dispatch_plan.py"), d], self.home)
        self.assertEqual((out.splitlines()[0], err), ("limit: 3, running: 0, waiting for merge: 0", ""))

    def test_worktree_reader(self):
        wt = load("global/sdd_worktree.py", "sdd_worktree_kw")
        d = self.project(OLD_AGENTS)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            paths = wt.section(d)[0]
            wt.section(d)
        self.assertEqual(paths, [], "the old Paths item takes no effect")
        self.assertEqual(err.getvalue().count("solo-sdd migrate-agents"), 1, err.getvalue())
        self.assertIn(os.path.join(d, "AGENTS.md"), err.getvalue())
        self.project(NEW_AGENTS)
        self.assertEqual(wt.section(d)[0], ["docs/x.md"])

    def test_pr_reader(self):
        pr = load("global/sdd_pr.py", "sdd_pr_kw")
        d = self.project(OLD_AGENTS)
        err = io.StringIO()
        with mock.patch.object(pr, "pr_files", return_value=(["x/a.py"], {})), contextlib.redirect_stderr(err):
            hits = pr.owner_gate("o/r", 1, d, None)
        self.assertEqual(hits, [pr.OLD_OWNER_HIT], "the old item is not read, but the merge waits for the owner")
        self.assertIn("solo-sdd migrate-agents", err.getvalue())
        with open(os.path.join(d, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write("## %s\n\n- %s 2\n" % (old("Working copy"), old("Orchestrators:")))
        with mock.patch.object(pr, "pr_files", return_value=(["x/a.py"], {})), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(pr.owner_gate("o/r", 1, d, None), [], "no old Owner only item: nothing to wait for")
        self.project(NEW_AGENTS)
        with mock.patch.object(pr, "pr_files", return_value=(["x/a.py"], {})):
            self.assertEqual(pr.owner_gate("o/r", 1, d, None), ["x/a.py"])

    def test_eval_replay_migrates_copy(self):
        ev = load("global/sdd_eval.py", "sdd_eval_kw")
        out = ev.patch_agents(OLD_AGENTS, ["Orchestrators: 4", "Orchestrator: solo"])
        self.assertIn("## Working copy\n\n- Orchestrators: 1\n- Orchestrator: solo\n", out)
        self.assertIn("## Delivery\n\n- Mode: local\n", out)
        self.assertEqual(keywords.migrate_agents(out)[1], [])



if __name__ == "__main__":
    unittest.main()
