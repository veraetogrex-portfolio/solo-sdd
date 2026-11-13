"""The integration rows of `solo-sdd doctor` (solo_sdd/doctor.py): one row per enabled integration with its source,
points, tool and last run, and a `fail` row for a broken description or an enabled name with no folder.

Every test works on a temporary git project and a temporary home with the fictional marker-check."""
import contextlib
import datetime
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
from solo_sdd import doctor, integration_run as R, integrations  # noqa: E402

MARKER = "name: marker-check\nabout: refuses a marker line\npoints: checks\ncommand: ./check.sh\n"
FILE = "solo-sdd/integrations/marker-check/integration"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class Project(unittest.TestCase):
    """A temporary git project with a solo-sdd/ tree and a temporary home; PATH holds a `sometool` program."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="integration-doctor-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root, self.home, self.bin = (os.path.join(self.tmp, n) for n in ("proj", "home", "bin"))
        write(os.path.join(self.root, "solo-sdd", "changes", ".keep"), "")
        write(os.path.join(self.bin, "sometool"), "#!/bin/sh\n")
        os.chmod(os.path.join(self.bin, "sometool"), 0o755)
        os.makedirs(self.home)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.root, check=True, stdin=subprocess.DEVNULL)
        path = mock.patch.dict(os.environ, PATH=self.bin + os.pathsep + "/usr/bin:/bin")
        path.start()
        self.addCleanup(path.stop)
        bundled = mock.patch.object(integrations, "BUNDLED", os.path.join(self.tmp, "bundled"))  # tested on their own
        bundled.start()
        self.addCleanup(bundled.stop)

    def integration(self, extra="", text=MARKER, owner=False, name="marker-check"):
        base = os.path.join(self.home, ".local/share/solo-sdd/integrations") if owner else \
            os.path.join(self.root, "solo-sdd/integrations")
        write(os.path.join(base, name, "integration"), text + extra)
        self.script("#!/bin/sh\necho ok\n")

    def script(self, text):
        """./check.sh at the project root, the command of marker-check."""
        write(os.path.join(self.root, "check.sh"), text)
        os.chmod(os.path.join(self.root, "check.sh"), 0o755)

    def config(self, text):
        write(os.path.join(self.root, "solo-sdd", "config"), text)

    def rows(self):
        return list(doctor._integrations(self.root, self.home))

    def row(self, name):
        found = [r for r in self.rows() if r[1] == name]
        self.assertEqual(len(found), 1, self.rows())
        return found[0]

    def ran(self):
        with contextlib.redirect_stdout(io.StringIO()):
            R.run(["--point", "checks"], self.root, self.home)


class DoctorIntegrationRows(Project):
    """Requirement: Doctor integration rows."""

    def test_doctor_integration_rows_a_project_integration(self):
        self.integration("requires: sometool\n")
        self.config("integrations: marker-check\n")
        self.ran()
        today = datetime.date.today().isoformat()
        self.assertEqual(self.row("integration marker-check"),
                         ("ok", "integration marker-check", "project, points checks, requires sometool found, "
                          "last run PASS %s, command ./check.sh" % today))

    def test_doctor_integration_rows_a_missing_tool(self):
        self.integration("requires: no-such-tool\n")
        self.config("integrations: marker-check\n")
        level, _, detail = self.row("integration marker-check")
        self.assertEqual(level, "warn")
        self.assertIn("requires no-such-tool missing", detail)
        self.assertIn("last run none", detail)

    def test_doctor_integration_rows_nothing_enabled(self):
        self.integration()
        self.assertEqual(self.rows(), [("ok", "integrations", "none enabled")])

    def test_doctor_integration_rows_an_owner_integration(self):
        self.integration(owner=True)
        self.config("integrations: marker-check\n")
        level, _, detail = self.row("integration marker-check")
        self.assertEqual(level, "ok")
        self.assertTrue(detail.startswith("owner, points checks, requires none, last run none"), detail)
        self.assertNotIn("command", detail)

    def test_doctor_integration_rows_the_last_failed_run(self):
        self.integration()
        self.config("integrations: marker-check\n")
        self.ran()
        self.script("#!/bin/sh\nexit 1\n")
        self.ran()
        self.assertIn("last run FAIL ", self.row("integration marker-check")[2])

    def test_doctor_integration_rows_a_skip_is_not_a_run(self):
        self.integration("requires: no-such-tool\n")
        self.config("integrations: marker-check\n")
        self.ran()
        self.assertIn("last run none", self.row("integration marker-check")[2])

    def test_doctor_integration_rows_the_newest_run_across_trees(self):
        """Tree A fails, tree B passes, then tree A again runs only the ship point: the PASS of B stays the last
        run, though A's record file is written last."""
        self.integration(text=MARKER.replace("points: checks", "points: checks, ship"))
        self.config("integrations: marker-check\n")
        self.script("#!/bin/sh\nexit 1\n")
        self.ran()
        self.script("#!/bin/sh\necho ok\n")
        self.ran()
        self.script("#!/bin/sh\nexit 1\n")
        with contextlib.redirect_stdout(io.StringIO()):
            R.run(["--point", "ship"], self.root, self.home)
        self.assertIn("last run FAIL ", self.row("integration marker-check")[2])
        folder = R.repo_dir(self.root, self.home)
        for name in os.listdir(folder):  # the ship result gone: the checks PASS of tree B is the newest
            rec = R.read_json(os.path.join(folder, name))
            if "ship" in rec.get("points", {}):
                del rec["points"]["ship"]
                R.write_json(os.path.join(folder, name), rec)
        self.assertIn("last run PASS ", self.row("integration marker-check")[2])

    def test_doctor_integration_rows_a_record_that_is_not_a_file(self):
        self.integration()
        self.config("integrations: marker-check\n")
        self.ran()
        folder = R.repo_dir(self.root, self.home)
        os.mkfifo(os.path.join(folder, "fifo.json"))
        os.mkdir(os.path.join(folder, "dir.json"))
        with open(os.path.join(folder, "bad.json"), "w") as f:
            f.write('{"points": {"checks": {"results": 5, "time": "x"}, "ship": [], "audit": {"results": [1, {"name": 2}]}}}')
        self.assertIn("last run PASS ", self.row("integration marker-check")[2])

    def test_doctor_integration_rows_outside_a_project(self):
        self.assertEqual(list(doctor._integrations(self.tmp, self.home)), [])


class DoctorBrokenIntegration(Project):
    """Requirement: Doctor broken integration."""

    def test_doctor_broken_integration_a_broken_description(self):
        self.integration(text="name: marker-check\nabout: x\nnosuchkey: 1\npoints: checks\ncommand: ./check.sh\n")
        self.integration(name="other-check", text=MARKER.replace("marker-check", "other-check"))
        self.config("integrations: marker-check, other-check\n")
        level, _, detail = self.row("integration marker-check")
        self.assertEqual(level, "fail")
        self.assertTrue(detail.startswith(FILE + ":3: unknown key nosuchkey"), detail)
        self.assertEqual(self.row("integration other-check")[0], "ok")

    def test_doctor_broken_integration_doctor_exits_1(self):
        self.integration(text="name: marker-check\nabout: x\nnosuchkey: 1\n")
        self.config("integrations: marker-check\n")
        quiet = {n: (lambda *a, **k: iter(())) for n in (
            "_python", "_layout", "_hooks", "_policy", "_hook_errors", "_guard", "_sandbox", "_depth", "_source",
            "_providers", "_gh", "_agents", "_rules_size")}
        out = io.StringIO()
        with mock.patch.multiple(doctor, **quiet), mock.patch.object(doctor.layout, "load_state", lambda: {}), \
                mock.patch.dict(os.environ, HOME=self.home), contextlib.redirect_stdout(out):
            cwd = os.getcwd()
            os.chdir(self.root)
            try:
                code = doctor.run()
            finally:
                os.chdir(cwd)
        self.assertEqual(code, 1, out.getvalue())
        self.assertTrue(out.getvalue().startswith("fail integration marker-check: %s:3: " % FILE), out.getvalue())
        self.config("")
        self.integration()
        with mock.patch.multiple(doctor, **quiet), mock.patch.object(doctor.layout, "load_state", lambda: {}), \
                mock.patch.dict(os.environ, HOME=self.home), contextlib.redirect_stdout(io.StringIO()):
            os.chdir(self.root)
            try:
                self.assertEqual(doctor.run(), 0)
            finally:
                os.chdir(cwd)

    def test_doctor_broken_integration_a_listed_name_with_no_folder(self):
        self.integration()
        self.config("integrations: marker-check, gone-check\n")
        level, _, detail = self.row("integration gone-check")
        self.assertEqual(level, "fail")
        self.assertIn("listed in integrations of solo-sdd/config, no folder in", detail)
        self.assertEqual(self.row("integration marker-check")[0], "ok")

    def test_doctor_broken_integration_a_broken_project_integration_not_enabled(self):
        self.integration(text="name: marker-check\nabout: x\nnosuchkey: 1\n")
        rows = self.rows()
        self.assertIn(("ok", "integrations", "none enabled"), rows)
        self.assertEqual([r[0] for r in rows if r[1] == "integration marker-check"], ["fail"], rows)

    def test_doctor_broken_integration_a_broken_owner_integration_not_enabled(self):
        self.integration(text="name: marker-check\nabout: x\nnosuchkey: 1\n", owner=True)
        self.assertEqual(self.rows(), [("ok", "integrations", "none enabled")])

    def test_doctor_broken_integration_a_broken_config(self):
        self.config("integrations marker-check\n")
        self.assertEqual(self.rows(), [("fail", "integrations", 'solo-sdd/config:1: not "key: value": integrations marker-check')])


if __name__ == "__main__":
    unittest.main()
