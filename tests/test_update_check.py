#!/usr/bin/env python3
"""solo_sdd/update_check.py: the version check, the registry answer, the update steps, on a temporary home folder.

The network goes through update_check.fetch and the update commands through update_check.run only: the rows replace
those two. The stand tests/stands/update-check.py drives the same through a real menu, server and upgrade.
"""
import contextlib, io, json, os, shutil, socket, sys, tempfile, threading, time, unittest, urllib.error
from unittest import mock

from hypothesis import example, given, settings as hsettings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import cli, doctor, layout, settings_ui, update_check as uc  # noqa: E402

UV = "/home/u/.local/share/uv/tools/solo-sdd"


def pypi(version):
    return json.dumps({"info": {"version": version}, "releases": {}}).encode()


@contextlib.contextmanager
def machine(home, prefix=UV, repo=None, version="0.2.0", env=None):
    """layout, the environment and the install method pointed at a temporary home; the check on, nothing fetched."""
    data = os.path.join(home, ".local", "share", "solo-sdd")
    clean = {k: v for k, v in os.environ.items() if k not in (uc.OFF, uc.ADDRESS)}
    clean.update(HOME=home, **(env or {}))
    with mock.patch.multiple(layout, HOME=home, DATA=data, STATE=os.path.join(data, "state.json"), REPO=repo or REPO), \
            mock.patch.dict(os.environ, clean, clear=True), mock.patch.object(cli.sys, "prefix", prefix), \
            mock.patch.object(uc, "__version__", version):
        yield


class Base(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)
        self.urls = []

    def answer(self, *bodies):
        """fetch replaced: each call records its URL and gives the next body, or raises it when an exception."""
        queue = list(bodies)

        def fetch(url):
            self.urls.append(url)
            got = queue.pop(0) if len(queue) > 1 else queue[0]
            if isinstance(got, BaseException):
                raise got
            return got
        return mock.patch.object(uc, "fetch", fetch)

    def cache(self, **fields):
        os.makedirs(os.path.dirname(uc.path()), exist_ok=True)
        with open(uc.path(), "w") as f:
            json.dump(fields, f)

    def raw(self):
        try:
            with open(uc.path(), "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None


class VersionCheck(Base):
    """Requirements: Version check; Skip and switch off."""

    def test_answers(self):
        for installed, answer, level, notice in (("0.2.0", "0.3.0", "warn", "0.3.0"), ("0.2.0", "0.2.0", "ok", None),
                                                 ("0.3.0", "0.2.0", "ok", None), ("0.2.0", "0.3.0rc1", "ok", None),
                                                 ("0.2.0", "0.10.0", "warn", "0.10.0")):
            with self.subTest(installed=installed, answer=answer), machine(self.home, version=installed), \
                    self.answer(pypi(answer)):
                if os.path.exists(uc.path()):
                    os.remove(uc.path())
                got = uc.row(True)
                self.assertEqual(got[0], level, got)
                self.assertEqual(uc.notice(uc.load()), notice)
                if level == "warn":
                    self.assertIn("uv tool upgrade solo-sdd", got[2])
                elif answer == "0.3.0rc1":
                    self.assertIn("the latest is unknown: the answer is not a version", got[2])
                else:
                    self.assertIn("is the latest", got[2])
        self.assertTrue(all(u == "https://pypi.org/pypi/solo-sdd/json" for u in self.urls), self.urls)

    def test_fresh_and_stale_cache(self):
        with machine(self.home), self.answer(pypi("0.4.0")):
            now = time.time()
            self.cache(checked=now - 3 * 3600, latest="0.3.0")
            self.assertEqual(uc.notice(uc.check(True, now)), "0.3.0")
            self.assertEqual(self.urls, [], "a 3 hour old answer is used")
            self.cache(checked=now - 25 * 3600, latest="0.3.0")
            self.assertEqual(uc.notice(uc.check(True, now)), "0.4.0")
            self.assertEqual(len(self.urls), 1)
            self.cache(checked=now + 3600, latest="0.3.0")  # a clock set back: the time is not trusted
            uc.check(True, now)
            self.assertEqual(len(self.urls), 2)
            self.assertEqual(uc.check(False, now + 2 * 86400)["checked"], now, "without network nothing is asked")

    def test_timeout_keeps_the_answer_and_waits_a_day(self):
        for error in (TimeoutError(), urllib.error.URLError(socket.timeout())):
            with self.subTest(error=error), machine(self.home), self.answer(error):
                now = time.time()
                self.cache(checked=now - 2 * 86400, latest="0.3.0")
                cache = uc.check(True, now)
                self.assertEqual((cache["latest"], cache["error"], cache["checked"]), ("0.3.0", "timed out", now))
                self.assertEqual(uc.row(True)[0], "warn", "the version answered before stays")
                self.cache(checked=now - 2 * 86400)
                self.assertEqual(uc.row(True)[:2], ("ok", "version"))
                self.assertIn("the latest is unknown: timed out", uc.row(True)[2])
                self.assertIsNone(uc.notice(uc.load()))
                calls = len(self.urls)
                uc.row(True)
                self.assertEqual(len(self.urls), calls, "a failed attempt also counts for the day")

    def test_npm_asks_npm_and_a_clone_asks_nothing(self):
        npm = os.path.join(self.home, "lib", "node_modules", "solo-sdd")
        with machine(self.home, prefix="/usr", repo=npm), self.answer(json.dumps({"version": "0.3.0"}).encode()):
            self.assertEqual(uc.row(True)[0], "warn")
            self.assertIn("npm update -g solo-sdd", uc.row(True)[2])
        self.assertEqual(self.urls, ["https://registry.npmjs.org/solo-sdd/latest"])
        clone = os.path.join(self.home, "clone")
        os.makedirs(os.path.join(clone, ".git"))
        with machine(self.home, prefix="/usr", repo=clone), self.answer(pypi("0.3.0")):
            got = uc.row(True)
            self.assertEqual(got[0], "ok")
            self.assertIn("a clone: not checked", got[2])
            self.assertEqual(uc.check(True), {}, "the cache of an earlier install is no notice")
        self.assertEqual(len(self.urls), 1, "a clone is never checked")

    def test_skip_until_newer(self):
        with machine(self.home), self.answer(pypi("0.3.0"), pypi("0.3.1")):
            now = time.time()
            uc.skip("0.3.0")
            self.assertIsNone(uc.notice(uc.check(True, now)))
            self.assertEqual(uc.row(False)[0], "warn", "doctor still names the newer version")
            self.assertEqual(uc.notice(uc.check(True, now + 86400)), "0.3.1")

    def test_variable_and_switch(self):
        with self.answer(pypi("0.3.0")):
            with machine(self.home, env={uc.OFF: "1"}):
                self.cache(checked=0, latest="0.3.0")
                self.assertEqual(uc.check(True), {}, "no request and no notice from the cache")
                self.assertIn("off: SOLO_SDD_NO_UPDATE_CHECK=1", uc.row(True)[2])
            with machine(self.home):
                uc.switch(False)
                self.assertEqual(uc.check(True), {})
                self.assertIn("switched off in the Machine section", uc.row(True)[2])
                self.assertEqual(self.urls, [])
                uc.switch(True)
                uc.check(True)
                self.assertEqual(len(self.urls), 1)

    def test_doctor_and_purge(self):
        with machine(self.home), self.answer(pypi("0.3.0")), contextlib.redirect_stdout(io.StringIO()) as out:
            doctor.run()
            self.assertEqual(len(self.urls), 1, "doctor asks")
            self.assertEqual([r for r in doctor.rows() if r[1] == "version"][0][0], "warn")
            self.assertEqual(len(self.urls), 1, "the rows the settings screen reads ask nothing")
            self.assertEqual(cli.main(["uninstall", "--purge"]), 0)
            self.assertIsNone(self.raw(), "purge removes the cache")
        self.assertIn("warn version: 0.3.0 available", out.getvalue())


class RegistryAnswer(Base):
    """Requirement: Registry answer checked."""

    HOSTILE = [b"x" * (uc.LIMIT + 1), b'{"info":{"version":"0.3.0"},"pad":"' + b"a" * uc.LIMIT + b'"}',
               b'{"info":{"version":"0.3.0"', b"<html>0.3.0</html>", b"\xff\xfe0.3.0", b'{"info": 5}', b"[]",
               b'{"version": "0.3.0"}', b"[" * 100000 + b"]" * 100000] + [pypi(v) for v in (
                   "0.3", "v0.3.0", "0.3.0a1", "٠.٣.٠", "0.3.0\n", "0.3.0 ", "0.3.0\u0000",
                   "0.3.0\u001b[2J; rm -rf ~", "0.3.0; rm -rf ~", "$(rm -rf ~)", "1" * 10 + ".0.0")]

    def test_hostile_answers(self):
        for body in self.HOSTILE:
            with self.subTest(body=body[:40]), machine(self.home), self.answer(body):
                if os.path.exists(uc.path()):
                    os.remove(uc.path())
                got = uc.row(True)
                self.assertEqual(got[0], "ok")
                self.assertIn("the answer is not a version", got[2])
                self.assertIsNone(uc.notice(uc.load()))
                self.assertEqual(set(json.loads(self.raw())), {"checked", "error"}, "nothing of the answer is stored")
                self.assertNotIn("rm", got[2])

    def test_registry_error_text_is_not_shown(self):
        error = urllib.error.HTTPError("u", 500, "\u001b[2J rm -rf ~", {}, None)
        with machine(self.home), self.answer(error):
            got = uc.row(True)
        self.assertIn("the registry refused the request", got[2])
        self.assertNotIn("rm", got[2])

    def test_broken_cache(self):
        for body in (b"{broken", b"\xff", b"[]", json.dumps({"checked": "x", "latest": "0.3.0\u001b[2J",
                                                               "skip": 5, "error": "\u001b[2J", "off": "yes"}).encode()):
            with self.subTest(body=body), machine(self.home), self.answer(TimeoutError()):
                os.makedirs(os.path.dirname(uc.path()), exist_ok=True)
                with open(uc.path(), "wb") as f:
                    f.write(body)
                self.assertEqual(uc.load(), {})
                got = uc.row(False)
                self.assertEqual(got[0], "ok")
                self.assertNotIn("\u001b", got[2])


COMMAND_WORDS = ["status", "install", "uninstall", "init", "update", "sync", "migrate-agents", "validate", "list",
                 "new", "archive", "config", "settings", "integrations", "check", "import", "--version", "help",
                 "bogus"]
ARG_WORDS = ["--all", "--json", "--yes", "--purge", "--hooks", "--global-rules", "--replace-foreign", "get", "set",
             "list", "mode", "x", "pull", "openspec", "--point", "checks", "review", "--changed", "--specs", "--write",
             "--agents", "claude", "describe", "enable", "-h"]


class NoNetworkElsewhere(Base):
    """Requirement: No network elsewhere."""

    @hsettings(max_examples=60, deadline=None)
    @given(st.one_of(st.just([]), st.tuples(st.sampled_from(COMMAND_WORDS), st.lists(st.sampled_from(ARG_WORDS),
                                                                                    max_size=3)).map(
        lambda t: [t[0], *t[1]])))
    @example([])
    @example(["bogus"])
    @example(["list"])
    @example(["validate", "--all"])
    @example(["config", "get", "mode"])
    def test_no_network_elsewhere_property(self, argv):
        home, cwd = tempfile.mkdtemp(), os.getcwd()
        try:
            folder = os.path.join(home, "folder")
            os.makedirs(folder)
            os.chdir(folder)
            with machine(home, repo=REPO), self.answer(pypi("0.3.0")), mock.patch.object(sys, "stdin", io.StringIO()), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.cache(checked=0, latest="0.2.5")
                before = self.raw()
                cli.main(list(argv))
                after = self.raw()
            self.assertEqual(self.urls, [], argv)
            if not (argv[:1] == ["uninstall"] and "--purge" in argv and after is None):
                self.assertEqual(after, before, argv)
        finally:
            os.chdir(cwd)
            shutil.rmtree(home, True)
            self.urls.clear()


class UpdateFromMenu(Base):
    """Requirements: Update from the menu; Skip this version in the menu; the Machine switch."""

    def text(self, menu):
        return " ".join(" ".join(menu.draw(120, 40)[0]).split())

    def menu(self):
        d = os.path.join(self.home, "p")
        os.makedirs(os.path.join(d, "solo-sdd", "changes"), exist_ok=True)
        return settings_ui.Home(d)

    def test_notice_after_the_menu_draws(self):
        gate = threading.Event()

        def fetch(url):
            gate.wait(10)
            return pypi("0.3.0")
        with machine(self.home), mock.patch.object(uc, "fetch", fetch):
            menu = self.menu()
            menu.pos = len(menu.entries) - 1  # on Quit
            menu.start_check()
            self.assertNotIn("available", self.text(menu), "the menu draws before the answer")
            self.assertTrue(menu.waiting())
            gate.set()
            menu.checker.join(10)
            self.assertTrue(menu.waiting(), "the loop wakes until the answer is drawn")
            text = self.text(menu)
            self.assertFalse(menu.waiting())
        self.assertIn("solo-sdd 0.2.0 0.3.0 available", text)
        self.assertEqual(menu.entries[-3:], ["Update to 0.3.0", settings_ui.SKIP, "Quit"])
        self.assertEqual(menu.entries[menu.pos], "Quit", "the cursor stays on its entry")

    def test_failing_check_is_no_notice(self):
        with machine(self.home), self.answer(OSError("down")):
            menu = self.menu()
            menu.start_check()
            menu.checker.join(10)
            text = self.text(menu)
        self.assertNotIn("available", text)
        self.assertNotIn("Update to", text)

    def open_update(self, menu):
        menu.found = "0.3.0"
        menu.pos = menu.entries.index("Update to 0.3.0")
        return menu.handle("enter")

    def test_command_and_link_per_method(self):
        npm = os.path.join(self.home, "lib", "node_modules", "solo-sdd")
        for prefix, repo, command in ((UV, None, "uv tool upgrade solo-sdd"),
                                      ("/home/u/.local/pipx/venvs/solo-sdd", None, "pipx upgrade solo-sdd"),
                                      ("/usr", npm, "npm update -g solo-sdd"),
                                      ("/usr", self.home, "python3 -m pip install --upgrade solo-sdd")):
            with self.subTest(command=command), machine(self.home, prefix=prefix, repo=repo), \
                    mock.patch.object(uc, "run") as run:
                menu = self.menu()
                self.assertIsNone(self.open_update(menu))
                text = self.text(menu)
                self.assertIn("Runs: " + command, text)
                self.assertIn("Release notes: https://github.com/veraetogrex-portfolio/solo-sdd/releases/tag/v0.3.0", text)
                self.assertIn("y update n back", text)
                self.assertIsNone(menu.handle("n"))
                self.assertIn("Enter open", self.text(menu))
                run.assert_not_called()
                argv = uc.method()[2]
                self.assertEqual(argv, [sys.executable] + command.split()[1:] if command.startswith("python3")
                                 else command.split())
                self.open_update(menu)
                self.assertEqual(menu.handle("y"), "update", "y hands the steps to the caller off the full screen")

    def steps(self, codes, doctor_out="", answer="y", root=None):
        calls = []

        def run(argv, cwd=None, capture=False):
            calls.append((argv, cwd))
            return codes.pop(0) if codes else 0, doctor_out if capture else ""
        with machine(self.home), mock.patch.object(uc, "run", run), mock.patch("builtins.input", lambda q: answer), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            ok = uc.update("0.3.0", root)
        return ok, calls, out.getvalue()

    def test_upgrade_fails(self):
        ok, calls, out = self.steps([1])
        self.assertFalse(ok)
        self.assertEqual(calls, [("uv tool upgrade solo-sdd".split(), None)])
        self.assertIn("fail: uv tool upgrade solo-sdd exited 1; solo-sdd install did not run", out)

    def test_confirmed_with_older_rules(self):
        root = os.path.join(self.home, "p")
        older = "ok python: 3\nwarn project-rules: the solo-sdd block in AGENTS.md is from an older solo-sdd; refresh: solo-sdd init\n"
        ok, calls, out = self.steps([], older, "y", root)
        self.assertTrue(ok)
        upgrade, install, doctor_ = ("uv tool upgrade solo-sdd".split(), None), (uc.program("install"), None), \
            (uc.program("doctor"), root)
        self.assertEqual(calls, [upgrade, install, doctor_, (uc.program("init", root), root)])
        self.assertIn("restart solo-sdd", out)
        ok, calls, _ = self.steps([], older, "n", root)
        self.assertEqual(calls, [upgrade, install, doctor_], "init only after its question")
        ok, calls, _ = self.steps([], "ok project-rules: current\n", "y", root)
        self.assertEqual(len(calls), 3, "current rules: no init")
        ok, calls, out = self.steps([0, 2], older, "y", root)
        self.assertFalse(ok)
        self.assertEqual(len(calls), 2, "a failed install stops the steps after it")
        self.assertNotIn("restart", out)

    def test_program_is_the_installed_package(self):
        argv = uc.program("install")
        self.assertEqual(argv[:2], [sys.executable, "-c"])
        self.assertEqual(argv[3:], [uc.PACKAGE, "install"])
        self.assertTrue(os.path.isfile(os.path.join(uc.PACKAGE, "solo_sdd", "__main__.py")))

    def test_skip_in_the_menu(self):
        with machine(self.home):
            menu = self.menu()
            menu.found = "0.3.0"
            menu.pos = menu.entries.index(settings_ui.SKIP)
            menu.handle("enter")
            self.assertEqual(uc.load()["skip"], "0.3.0")
            text = self.text(menu)
        self.assertIn("0.3.0 skipped", text)
        self.assertNotIn("Update to", text)
        self.assertEqual(menu.entries[menu.pos], "Quit")

    def test_machine_switch(self):
        with machine(self.home), self.answer(pypi("0.3.0")):
            s = settings_ui.Screen(None, None, home=self.home)
            s.open_machine()
            s.mpos = s.machine_items().index(("updates", None))
            self.assertIn("[x] update check", " ".join(s.draw(120, 40)[0]))
            s.handle("space")
            self.assertIn("[ ] update check", " ".join(s.draw(120, 40)[0]))
            self.assertFalse(s.machine_pending(), "nothing waits for a")
            self.assertEqual(uc.load(), {"off": True})
            self.cache(checked=0, off=True)
            self.assertEqual(uc.check(True), {})
            self.assertEqual(self.urls, [])


if __name__ == "__main__":
    unittest.main()
