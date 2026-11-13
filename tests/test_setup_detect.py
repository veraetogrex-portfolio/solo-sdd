#!/usr/bin/env python3
"""solo_sdd/setup_detect.py: detection on toy repositories with a fake gh, and the proposed settings."""
import os, shutil, subprocess, sys, tempfile, unittest
import marks
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import setup_detect  # noqa: E402

GH = {"protected": 'case "$1" in repo) echo main;; api) echo true;; esac\n',
      "open": 'case "$1" in repo) echo main;; api) echo false;; esac\n',
      "error": 'echo "HTTP 404" >&2\nexit 1\n',
      "slow": 'sleep 5\necho main\n'}


def git(root, *args, author=None):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    who = ["-c", "user.name=%s" % (author or "A"), "-c", "user.email=%s@example.com" % (author or "a").lower()]
    subprocess.run(["git", *who, *args], cwd=root, check=True, capture_output=True, env=env, stdin=subprocess.DEVNULL)


class Toy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root, self.bin, self.home = (os.path.join(self.tmp, n) for n in ("proj", "bin", "home"))
        for d in (self.root, self.bin, self.home):
            os.makedirs(d)
        git(self.root, "init", "-q")
        patch = mock.patch.dict(os.environ, {"PATH": self.bin + ":/usr/bin:/bin"})
        patch.start()
        self.addCleanup(patch.stop)

    def commit(self, author):
        git(self.root, "commit", "-q", "--allow-empty", "-m", "c", author=author)

    def gh(self, kind):
        path = os.path.join(self.bin, "gh")
        with open(path, "w") as f:
            f.write("#!/bin/sh\n" + GH[kind])
        os.chmod(path, 0o755)

    def detect(self):
        return setup_detect.detect(self.root, self.home)


class Detection(Toy):
    """Requirement: Project detection."""

    def test_authors(self):
        for a in ("Ann", "Bob", "Cid", "Ann"):
            self.commit(a)
        self.assertEqual(self.detect()["authors"], 3)

    def test_empty_repository(self):
        d = self.detect()
        self.assertEqual((d["authors"], d["remote"], d["protection"], d["codeowners"]), (0, None, "no remote", None))

    def test_not_a_repository(self):
        shutil.rmtree(os.path.join(self.root, ".git"))
        self.assertIsNone(self.detect()["authors"])

    def test_codeowners(self):
        os.makedirs(os.path.join(self.root, ".github"))
        open(os.path.join(self.root, ".github/CODEOWNERS"), "w").close()
        self.assertEqual(self.detect()["codeowners"], ".github/CODEOWNERS")

    def test_no_gh(self):
        git(self.root, "remote", "add", "origin", "https://example.com/x.git")
        d = self.detect()
        self.assertEqual((d["remote"], d["protection"]), ("origin", "unknown"))

    def test_origin_first(self):
        for name in ("fork", "origin"):
            git(self.root, "remote", "add", name, "https://example.com/%s.git" % name)
        self.assertEqual(self.detect()["remote"], "origin")

    def test_gh_answers(self):
        git(self.root, "remote", "add", "origin", "https://example.com/x.git")
        for kind, want in (("protected", "protected"), ("open", "not protected"), ("error", "unknown")):
            self.gh(kind)
            self.assertEqual(self.detect()["protection"], want, kind)

    @marks.slow
    def test_gh_timeout(self):
        git(self.root, "remote", "add", "origin", "https://example.com/x.git")
        self.gh("slow")
        with mock.patch.object(setup_detect, "TIMEOUT", 0.2):
            self.assertEqual(self.detect()["protection"], "unknown")

    def workflow(self, name):
        os.makedirs(os.path.join(self.root, ".github/workflows"), exist_ok=True)
        open(os.path.join(self.root, ".github/workflows", name), "w").close()

    def test_ci_detection_a_workflow(self):
        self.assertIsNone(self.detect()["ci"])
        self.workflow("test.yml")
        self.assertEqual(self.detect()["ci"], ".github/workflows/test.yml")

    def test_ci_detection_an_empty_folder(self):
        self.workflow("README.md")
        os.makedirs(os.path.join(self.root, ".github/workflows/sub"))
        open(os.path.join(self.root, ".github/workflows/sub/x.yaml"), "w").close()
        self.assertIsNone(self.detect()["ci"])

    @unittest.skipIf(os.geteuid() == 0, "root reads a folder with mode 0")
    def test_ci_detection_an_unreadable_folder(self):
        self.workflow("test.yaml")
        folder = os.path.join(self.root, ".github/workflows")
        os.chmod(folder, 0)
        self.addCleanup(os.chmod, folder, 0o755)
        self.assertIsNone(self.detect()["ci"])

    def test_agents(self):
        os.makedirs(os.path.join(self.home, ".codex"))
        self.assertEqual(self.detect()["agents"], [("codex", "~/.codex"), ("other", "always")])


class Proposal(Toy):
    """Requirement: Proposed settings."""

    def test_team(self):
        for a in ("Ann", "Bob", "Cid"):
            self.commit(a)
        git(self.root, "remote", "add", "origin", "https://example.com/x.git")
        self.gh("protected")
        os.makedirs(os.path.join(self.root, ".github/workflows"))
        open(os.path.join(self.root, ".github/workflows/test.yml"), "w").close()
        p = setup_detect.propose(self.detect())
        self.assertEqual(p["mode"], ("team", "3 authors in 90 days, no CODEOWNERS, default branch protected"))
        self.assertEqual(p["delivery.mode"], ("pr", "remote origin, CI .github/workflows/test.yml"))

    def test_remote_without_ci(self):
        git(self.root, "remote", "add", "origin", "https://example.com/x.git")
        self.assertEqual(setup_detect.propose(self.detect())["delivery.mode"],
                         ("local", "remote origin, no CI workflow in .github/workflows"))

    def test_team_by_codeowners_alone(self):
        self.commit("Ann")
        open(os.path.join(self.root, "CODEOWNERS"), "w").close()
        self.assertEqual(setup_detect.propose(self.detect())["mode"][0], "team")

    def test_solo(self):
        self.commit("Ann")
        p = setup_detect.propose(self.detect())
        self.assertEqual(p["mode"], ("solo", "1 author in 90 days, no CODEOWNERS, no remote"))
        self.assertEqual(p["delivery.mode"], ("local", "no remote"))
        self.assertEqual(p["agents"], ("other", "other: always"))


if __name__ == "__main__":
    unittest.main()
