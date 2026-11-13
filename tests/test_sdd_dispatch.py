"""Checks sdd_dispatch.py: accept (status acceptance) and land-local (merge in local mode)."""
import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import marks
import shared_repo

from hypothesis import given, settings, strategies as st

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "global/sdd_dispatch.py"
WORKTREE = SCRIPT.parent / "sdd_worktree.py"


def dispatch(script, *args, env=None):
    return subprocess.run([sys.executable, str(script)] + [str(a) for a in args], capture_output=True, text=True,
                          timeout=120, stdin=subprocess.DEVNULL, env=env)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dispatch-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


ARCH = "changes/archive/2026-11-11-x"  # outside solo-sdd/: a solo-sdd/ folder switches VALIDATE to the own tree


def verification(wt, scenario):
    d = os.path.join(wt, ARCH)
    os.makedirs(d, exist_ok=True)
    pathlib.Path(d, "verification.md").write_text("## Live Scenario\n\n%s\n## Needs\n\nnone\n" % scenario, encoding="utf-8")


class AcceptTest(Base):
    def put_verification(self, scenario):
        verification(self.tmp, scenario)

    def status(self, text):
        p = os.path.join(self.tmp, "status.txt")
        pathlib.Path(p).write_text(text, encoding="utf-8")
        return p

    def block(self, validate="true", live="echo ok -> ok", wt=None, st="archived", fence=False, indent="", scenario=None, arch=ARCH):
        """scenario: the Live Scenario section of ARCHIVE/verification.md; by default one step with the LIVE command."""
        if scenario is None:
            scenario = "1. Run `%s`.\n" % live.partition(" -> ")[0]
        if scenario is not False:
            self.put_verification(scenario)
        lines = ["STATUS: " + st, "CHANGE: x", "WORKTREE: " + (wt if wt is not None else self.tmp),
                 "VALIDATE: " + validate, "TESTS: touch %s/tests-ran -> exit 0" % self.tmp, "LIVE: " + live,
                 "ARCHIVE: " + arch]
        lines = [indent + l for l in lines]
        text = "\n".join(lines) + "\n"
        return self.status("```\n" + text + "```\n" if fence else "report\n" + text)

    def test_converges(self):
        r = dispatch(SCRIPT, "accept", self.block())
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "status matches"))

    def test_tests_never_run(self):
        dispatch(SCRIPT, "accept", self.block())
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "tests-ran")))

    def test_validate_exit1(self):
        r = dispatch(SCRIPT, "accept", self.block(validate="sh -c 'echo bad; exit 1'"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("VALIDATE", r.stdout)
        self.assertIn("exit 1", r.stdout)
        self.assertIn("bad", r.stdout)

    def test_live_exit1_with_text(self):
        r = dispatch(SCRIPT, "accept", self.block(live="sh -c 'echo ok; exit 1' -> ok"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("LIVE", r.stdout)
        self.assertIn("«ok»", r.stdout)
        self.assertIn("exit 1", r.stdout)

    def test_live_text_missing_and_tail3(self):
        r = dispatch(SCRIPT, "accept", self.block(live="seq 1 5 | sed 's/^/line/' -> wanted text"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("«wanted text»", r.stdout)
        self.assertIn("text missing", r.stdout)
        for l in ("line3", "line4", "line5"):
            self.assertIn(l, r.stdout)
        self.assertNotIn("line2", r.stdout)

    def test_long_output_only_three_lines(self):
        r = dispatch(SCRIPT, "accept", self.block(validate="seq 1 500; exit 1"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("500", r.stdout)
        self.assertIn("498", r.stdout)
        self.assertNotIn("497", r.stdout)

    def test_not_ready_commands_not_run(self):
        marker = os.path.join(self.tmp, "ran")
        r = dispatch(SCRIPT, "accept", self.block(st="not_ready", validate="touch " + marker, live="touch %s -> x" % marker))
        self.assertEqual(r.returncode, 2)
        self.assertIn("not_ready", r.stdout)
        self.assertFalse(os.path.exists(marker))

    def test_no_status_line(self):
        r = dispatch(SCRIPT, "accept", self.status("WORKTREE: /tmp\nVALIDATE: true\n"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("STATUS", r.stdout)

    def test_fenced_and_indented(self):
        r = dispatch(SCRIPT, "accept", self.block(fence=True, indent="  "))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_first_occurrence_counts(self):
        p = self.block()
        pathlib.Path(p).write_text(pathlib.Path(p).read_text() + "VALIDATE: false\n")
        self.assertEqual(dispatch(SCRIPT, "accept", p).returncode, 0)

    def test_hostile_inputs_exit2_no_commands(self):
        marker = os.path.join(self.tmp, "ran")
        cases = {
            "empty": (lambda: self.status(""), "empty"),
            "missing": (lambda: os.path.join(self.tmp, "no-such"), "not readable"),
            "live no arrow": (lambda: self.block(live="touch %s" % marker), "' -> '"),
            "live empty text": (lambda: self.block(live="touch %s -> " % marker), "' -> '"),
            "no worktree dir": (lambda: self.block(validate="touch " + marker, wt=os.path.join(self.tmp, "none")), "no WORKTREE folder"),
            "empty validate": (lambda: self.block(validate="", live="touch %s -> x" % marker), "field VALIDATE empty"),
            "empty worktree": (lambda: self.block(wt="", validate="touch " + marker), "field WORKTREE empty"),
        }
        for name, (path, reason) in cases.items():
            with self.subTest(name):
                r = dispatch(SCRIPT, "accept", path())
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn(reason, r.stdout)
                self.assertNotIn("Traceback", r.stderr)
                self.assertFalse(os.path.exists(marker))

    def test_live_exit_code_under_pipe(self):
        r = dispatch(SCRIPT, "accept", self.block(live="sh -c 'echo ok; exit 1' | cat -> ok"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("LIVE", r.stdout)
        self.assertIn("exit 1", r.stdout)

    def test_non_utf8_output(self):
        r = dispatch(SCRIPT, "accept", self.block(live="printf '\\377\\376ok' -> ok"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_status_comparison_extra_spaces_in_output(self):
        for cmd in ("printf 'Tests  19 passed\\n'", "printf 'Tests\\t19\\n  passed\\n'"):
            r = dispatch(SCRIPT, "accept", self.block(live=cmd + " -> Tests 19 passed"))
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "status matches"), cmd)

    def test_status_comparison_changed_word_shows_raw_output(self):
        r = dispatch(SCRIPT, "accept", self.block(live="printf 'Tests  19 passed\\n' -> Tests 18 passed"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("text missing", r.stdout)
        self.assertIn("    Tests  19 passed", r.stdout)

    def test_usage(self):
        r = dispatch(SCRIPT, "accept")
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage", r.stderr)

    # Requirement: LIVE from the Live Scenario
    def test_live_from_the_live_scenario_an_invented_command(self):
        marker = os.path.join(self.tmp, "ran")
        live = "touch %s && echo ok" % marker
        r = dispatch(SCRIPT, "accept", self.block(live=live + " -> ok", scenario="1. Run `python3 tests/stands/words.py`.\n"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("LIVE: %s — not in the Live Scenario" % live, r.stdout)
        self.assertFalse(os.path.exists(marker))
        r = dispatch(SCRIPT, "accept", self.block(scenario="1. Check that echo ok prints ok (`echo`).\n"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("not in the Live Scenario", r.stdout)

    def test_live_from_the_live_scenario_a_part_of_a_command(self):
        r = dispatch(SCRIPT, "accept", self.block(live="echo ok -> ok", scenario="1. `echo ok --all` -> ok.\n"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("not in the Live Scenario", r.stdout)

    def test_live_from_the_live_scenario_a_command_from_the_scenario(self):
        scenario = ("1. A fixture `x`, then ``printf  'a`b\\n' | grep -c b`` -> 1.\n"
                    "<!-- `echo hidden` -->\n2. Then `echo second`.\n")
        r = dispatch(SCRIPT, "accept", self.block(live="printf 'a`b\\n' | grep -c b -> 1", scenario=scenario))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "status matches"), r.stdout)
        r = dispatch(SCRIPT, "accept", self.block(live="echo hidden -> hidden", scenario=scenario))
        self.assertEqual(r.returncode, 1, "a code span inside an HTML comment does not count: " + r.stdout)
        r = dispatch(SCRIPT, "accept", self.block(live="echo second -> wrong", scenario=scenario))
        self.assertIn("LIVE: echo second — stated «wrong», got text missing", r.stdout)
        verification(self.tmp, "1. text\n")
        p = pathlib.Path(self.tmp, ARCH, "verification.md")
        p.write_text(p.read_text() + "## Result\n\n`echo ok`\n")
        r = dispatch(SCRIPT, "accept", self.block(scenario=False))
        self.assertIn("not in the Live Scenario", r.stdout, "a span of another section does not count")

    def test_live_from_the_live_scenario_no_verification_file(self):
        marker = os.path.join(self.tmp, "ran")
        r = dispatch(SCRIPT, "accept", self.block(live="touch %s -> x" % marker, scenario=False))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("LIVE: no Live Scenario in %s" % os.path.join(self.tmp, ARCH, "verification.md"), r.stdout)
        self.assertFalse(os.path.exists(marker))
        outside = tempfile.mkdtemp(prefix="dispatch-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        verification(outside, "1. `touch %s`\n" % marker)
        for arch in ("", os.path.join(outside, ARCH), "../" + os.path.basename(outside) + "/" + ARCH):
            r = dispatch(SCRIPT, "accept", self.block(live="touch %s -> x" % marker, scenario=False, arch=arch))
            self.assertEqual(r.returncode, 1, (arch, r.stdout))
            self.assertIn("LIVE: no Live Scenario in", r.stdout)
            self.assertFalse(os.path.exists(marker), arch)

    def test_live_from_the_live_scenario_read_as_the_validator_reads_it(self):
        cases = {  # verification.md text -> whether `echo ok` is a step of its Live Scenario
            "\ufeff## Live Scenario\n\n1. `echo ok`\n": True,
            "## Live Scenario\n\n```bash\n# a comment\n```\n2. `echo ok`\n": True,
            "## Live Scenario\n\n<!--\n## Needs\n-->\n2. `echo ok`\n": True,
            "## Live Scenario\n\n# Not a section end\n2. `echo ok`\n": True,
            "<!--\n## Live Scenario\n\n`echo ok`\n-->\n## Live Scenario\n\n1. `echo no`\n": False,
            "## Live Scenario\n\n```\necho ok\n```\n": False,
            "## Live Scenario\n\n1. `echo no`\n\n## Live Scenario\n\n1. `echo ok`\n": True,  # the last one, as validate
        }
        for text, good in cases.items():
            with self.subTest(text):
                os.makedirs(os.path.join(self.tmp, ARCH), exist_ok=True)
                pathlib.Path(self.tmp, ARCH, "verification.md").write_text(text, encoding="utf-8")
                r = dispatch(SCRIPT, "accept", self.block(scenario=False))
                self.assertEqual(r.returncode, 0 if good else 1, r.stdout)

    # Requirement: Command timeouts
    @marks.slow
    def test_command_timeouts_a_hanging_live(self):
        mod = load_dispatch()
        old = os.environ.pop("SDD_DISPATCH_TIMEOUT", None)
        try:
            self.assertEqual(mod.timeout(), 600)
        finally:
            if old is not None:
                os.environ["SDD_DISPATCH_TIMEOUT"] = old
        r = dispatch(SCRIPT, "accept", self.block(live="sleep 100 -> ok"), env=dict(os.environ, SDD_DISPATCH_TIMEOUT="1"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("LIVE: timeout after 1 s", r.stdout)

    @marks.slow
    def test_command_timeouts_a_child_keeps_the_output_open(self):
        t = time.monotonic()
        r = dispatch(SCRIPT, "accept", self.block(live="sleep 100 | cat -> ok"), env=dict(os.environ, SDD_DISPATCH_TIMEOUT="1"))
        self.assertLess(time.monotonic() - t, 10)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("LIVE: timeout after 1 s", r.stdout)
        r = dispatch(SCRIPT, "accept", self.block(validate="sleep 100 | cat"), env=dict(os.environ, SDD_DISPATCH_TIMEOUT="1"))
        self.assertIn("VALIDATE: timeout after 1 s", r.stdout)

    def test_command_timeouts_a_broken_value(self):
        mod = load_dispatch()
        old = os.environ.get("SDD_DISPATCH_TIMEOUT")
        try:
            for v, want in (("abc", 600), ("0", 600), ("\u0661\u0662", 600), ("-5", 600), ("", 600), ("7", 7),
                            ("99999999999999999999", 600), ("2147484", 600), ("2147483", 2147483)):
                os.environ["SDD_DISPATCH_TIMEOUT"] = v
                self.assertEqual(mod.timeout(), want, v)
        finally:
            os.environ.pop("SDD_DISPATCH_TIMEOUT")
            if old is not None:
                os.environ["SDD_DISPATCH_TIMEOUT"] = old
        for v in ("2147483", "2147484", "99999999999999999999"):  # the largest wait and above it run, no traceback
            r = dispatch(SCRIPT, "accept", self.block(), env=dict(os.environ, SDD_DISPATCH_TIMEOUT=v))
            self.assertEqual((r.returncode, r.stdout.strip(), r.stderr), (0, "status matches", ""), v)


def load_dispatch():
    spec = importlib.util.spec_from_file_location("sdd_dispatch_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WORD = st.text("abc019.:-", min_size=1, max_size=4)
WS = st.text(" \t\n\r", min_size=1, max_size=3)


@st.composite
def live_case(draw):
    words = draw(st.lists(WORD, min_size=1, max_size=6))
    seps = draw(st.lists(WS, min_size=len(words) + 1, max_size=len(words) + 1))
    i = draw(st.integers(0, len(words) - 1))
    j = draw(st.integers(i + 1, len(words)))
    wide = draw(st.lists(st.tuples(st.booleans(), WS), min_size=len(seps), max_size=len(seps)))
    return words, seps, (i, j), wide


def join(words, seps):
    return seps[0] + "".join(w + s for w, s in zip(words, seps[1:]))


class StatusComparisonPropertyTest(unittest.TestCase):
    live_matches = staticmethod(load_dispatch().live_matches)

    @settings(max_examples=300, deadline=None)
    @given(live_case(), st.data())
    def test_status_comparison_whitespace_and_words(self, case, data):
        words, seps, (i, j), wide = case
        # the ends of the output may have no whitespace at all
        seps = [("" if k in (0, len(seps) - 1) and keep else s) for k, (s, (keep, _)) in enumerate(zip(seps, wide))]
        out = join(words, seps)
        inner = data.draw(st.lists(WS, min_size=j - i - 1, max_size=j - i - 1))
        stated = words[i] + "".join(x + w for x, w in zip(inner, words[i + 1:j]))
        self.assertTrue(self.live_matches(stated, out), (stated, out))
        widened = join(words, [s + w if s else (w if keep else "") for s, (keep, w) in zip(seps, wide)])
        self.assertTrue(self.live_matches(stated, widened), (stated, widened))
        k = data.draw(st.integers(i, j - 1))
        new = data.draw(WORD.filter(lambda n: all(n not in w for w in words)))
        changed = " ".join(words[i:k] + [new] + words[k + 1:j])
        self.assertFalse(self.live_matches(changed, widened), (changed, widened))

    def test_status_comparison_space_is_a_word_boundary(self):
        self.assertFalse(self.live_matches("ab c", "a bc"))
        self.assertTrue(self.live_matches("Tests  19\tpassed", "Tests 19 passed"))


def g(repo, *args, check=True):
    p = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo)] + list(args),
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if check and p.returncode:
        raise AssertionError(p.stderr)
    return p.stdout.strip()


def build_land(root):
    """The fake openspec and the main folder of LandBase in root."""
    os.makedirs(os.path.join(root, "bin"))
    fake = os.path.join(root, "bin", "openspec")
    pathlib.Path(fake).write_text("#!/bin/sh\nexit 0\n")
    os.chmod(fake, 0o755)
    main = os.path.join(root, "main")
    os.makedirs(main)
    g(main, "init", "-q", "-b", "main")
    LandBase.put(None, main, "README.md", "base\n")
    LandBase.put(None, main, "AGENTS.md", "rules\n")
    g(main, "add", "-A")
    g(main, "commit", "-q", "-m", "init")


class LandBase(Base):
    """A main folder, a worktree of change/c and land-local run against them; the main folder is a copy of one built
    once (tests/shared_repo.py)."""

    BUILD = staticmethod(build_land)  # a subclass with more fixture names its own build

    def setUp(self):
        folder, _ = shared_repo.template(("LandBase", self.BUILD), self.BUILD)
        self.tmp = str(shared_repo.copy(folder))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.main = os.path.join(self.tmp, "main")
        self.wt = os.path.join(self.tmp, "wt")
        self.bin = os.path.join(self.tmp, "bin")
        self.env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"],  # the script's merge commit: CI has no global git identity
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def put(self, base, rel, text):
        p = pathlib.Path(base, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def make_change(self, cid="c", rel="feature.txt", text="new\n"):
        g(self.main, "worktree", "add", "-q", "-b", "change/" + cid, self.wt)
        subprocess.run([sys.executable, str(WORKTREE), "setup", self.main, self.wt], capture_output=True,
                       stdin=subprocess.DEVNULL, check=True)
        self.put(self.wt, rel, text)
        g(self.wt, "add", "-A")
        g(self.wt, "commit", "-q", "-m", "change")

    def land(self, *extra, cid="c", script=SCRIPT):
        return dispatch(script, "land-local", self.main, self.wt, cid, *extra, env=self.env)

    def assert_rolled_back(self, head):
        self.assertEqual(g(self.main, "rev-parse", "HEAD"), head)
        self.assertFalse(os.path.exists(os.path.join(self.main, ".git", "MERGE_HEAD")))
        self.assertTrue(os.path.isdir(self.wt))
        self.assertIn("change/c", g(self.main, "branch", "--list", "change/c"))

    def fake_worktree(self, body):
        d = os.path.join(self.tmp, "fake")
        os.makedirs(d, exist_ok=True)
        shutil.copy(SCRIPT, d)
        shutil.copy(SCRIPT.parent / "sdd_pr.py", d)
        shutil.copy(WORKTREE, os.path.join(d, "real_wt.py"))
        pathlib.Path(d, "sdd-worktree.py").write_text(
            "import subprocess, sys, os\nsub = sys.argv[1]\n%s\n"
            "sys.exit(subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'real_wt.py')] + sys.argv[1:]).returncode)\n" % body)
        return os.path.join(d, "sdd_dispatch.py")


class LandTest(LandBase):
    OWNER_RULE = "## Delivery\n\n- Owner only: `global/*.py`\n"

    def owner_main(self, text=None, ignore=False):
        self.put(self.main, "AGENTS.md", text or self.OWNER_RULE)
        if ignore:
            self.put(self.main, ".gitignore", "AGENTS.md\n")
            g(self.main, "rm", "-q", "--cached", "AGENTS.md")
        g(self.main, "add", "-A")
        g(self.main, "commit", "-q", "-m", "rules")

    def assert_waits(self, r, path, head):
        self.assertEqual(r.returncode, 8, r.stdout + r.stderr)
        self.assertIn("waits for the owner", r.stdout)
        self.assertIn(path, r.stdout)
        self.assert_rolled_back(head)

    def test_owner_path_waits(self):
        self.owner_main()
        self.make_change(rel="global/work_hooks.py")
        head = g(self.main, "rev-parse", "HEAD")
        self.assert_waits(self.land(), "global/work_hooks.py", head)

    def test_old_owner_item_waits_and_names_migrate(self):
        # Requirement: Old keywords are named, not ignored silently. The old item is not read; the merge waits
        old = "## \u041f\u043e\u0441\u0442\u0430\u0432\u043a\u0430\n\n- \u0422\u043e\u043b\u044c\u043a\u043e \u0432\u043b\u0430\u0434\u0435\u043b\u0435\u0446: `other/**`\n"
        self.owner_main(old)
        self.make_change(rel="src/x.py")
        head = g(self.main, "rev-parse", "HEAD")
        r = self.land()
        self.assert_waits(r, "pre-English «Owner only:»", head)
        self.assertIn("solo-sdd migrate-agents", r.stderr)

    def test_workflow_waits_without_rule(self):
        self.make_change(rel=".github/workflows/ci.yml")
        head = g(self.main, "rev-parse", "HEAD")
        self.assert_waits(self.land(), ".github/workflows/ci.yml", head)

    def test_owner_rule_edited_outside_git_waits(self):
        self.owner_main(ignore=True)
        self.make_change()
        self.put(self.wt, "AGENTS.md", "## Delivery\n\n- Owner only: `docs/*.md`\n")
        head = g(self.main, "rev-parse", "HEAD")
        self.assert_waits(self.land(), "AGENTS.md", head)
        self.assertFalse(os.path.exists(os.path.join(self.main, "feature.txt")))

    def test_owner_rule_edited_in_branch_waits(self):
        self.owner_main()
        self.make_change(rel="AGENTS.md", text="## Delivery\n\n- Owner only: `docs/*.md`\n")
        head = g(self.main, "rev-parse", "HEAD")
        self.assert_waits(self.land(), "AGENTS.md", head)

    def test_owner_rule_no_match_lands(self):
        self.owner_main()
        self.make_change()
        r = self.land()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_human_merge_waits(self):
        # Requirement: Waiting for a human merge, scenario Local delivery: nothing merges, the branch and worktree stay
        self.make_change()
        self.put(self.main, "solo-sdd/config", "mode: team\ndelivery.mode: local\n")
        head = g(self.main, "rev-parse", "HEAD")
        r = self.land()
        self.assertEqual((r.returncode, r.stdout.strip()), (8, "not merged: waits for human merge: branch change/c"), r.stderr)
        self.assert_rolled_back(head)
        self.assertFalse(os.path.exists(os.path.join(self.main, "feature.txt")))
        self.put(self.main, "solo-sdd/config", "delivery.merge-by: bot\n")
        r = self.land()
        self.assertEqual(r.returncode, 1)
        self.assertIn("not merged: settings: solo-sdd/config:1", r.stdout)
        self.put(self.main, "solo-sdd/config", "mode: team\ndelivery.merge-by: agent\n")
        self.assertEqual(self.land().returncode, 0)

    def test_human_merge_in_the_skills(self):
        # Requirement: Waiting for a human merge, scenario Two changes: the report line and the exit from the waiting list
        skills = SCRIPT.parent.parent / "skills"
        text = (skills / "spec-dispatch/SKILL.md").read_text(encoding="utf-8")
        for want in ("Code 8 with `waits for human merge: <url>`", "the change is not failed, the report shows `waits for human merge` with the URL",
                     "the change leaves `--waiting` and is in no list", "land <MAIN> <WORKTREE> <url> --after-merge",
                     "`waits for human merge` with the PR URL"):
            self.assertIn(want, text)
        self.assertIn("<link>, waits for human merge", (skills / "ship/SKILL.md").read_text(encoding="utf-8"))

    def test_clean_merge(self):
        self.make_change()
        r = self.land()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        head = g(self.main, "rev-parse", "HEAD")
        self.assertIn("merged " + head, r.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.main, "feature.txt")))
        self.assertFalse(os.path.exists(self.wt))
        self.assertEqual(g(self.main, "branch", "--list", "change/c"), "")

    def test_merge_conflict(self):
        self.make_change(rel="README.md", text="change\n")
        self.put(self.main, "README.md", "other\n")
        g(self.main, "commit", "-q", "-am", "other")
        head = g(self.main, "rev-parse", "HEAD")
        r = self.land()
        self.assertEqual(r.returncode, 6, r.stdout)
        self.assertIn("README.md", r.stdout)
        self.assert_rolled_back(head)

    def test_transport_conflict(self):
        self.make_change()
        head = g(self.main, "rev-parse", "HEAD")
        script = self.fake_worktree("if sub == 'transport':\n    print('conflict, MAIN not changed: openspec/x.md')\n    sys.exit(3)")
        r = self.land(script=script)
        self.assertEqual(r.returncode, 6, r.stdout)
        self.assertIn("openspec/x.md", r.stdout)
        self.assert_rolled_back(head)
        self.assertFalse(os.path.exists(os.path.join(self.main, "feature.txt")))

    def test_transport_other_failure_rolls_back(self):
        self.make_change()
        head = g(self.main, "rev-parse", "HEAD")
        script = self.fake_worktree("if sub == 'transport':\n    print('error: broken')\n    sys.exit(1)")
        r = self.land(script=script)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("transport", r.stdout)
        self.assertEqual(g(self.main, "rev-parse", "HEAD"), head)

    def test_not_transferred_passes_through(self):
        self.make_change()
        script = self.fake_worktree("if sub == 'transport':\n    print('not transported: docs/a.md')\n    sys.exit(0)")
        r = self.land(script=script)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("not transported: docs/a.md", r.stdout)

    def test_dirty_main(self):
        self.make_change()
        self.put(self.main, "AGENTS.md", "someone else's edit\n")
        head = g(self.main, "rev-parse", "HEAD")
        r = self.land()
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("AGENTS.md", r.stdout)
        self.assertEqual(g(self.main, "rev-parse", "HEAD"), head)
        self.assertFalse(os.path.exists(os.path.join(self.main, "feature.txt")))

    def test_red_junction(self):
        self.make_change(rel="archive-c.txt")
        head = g(self.main, "rev-parse", "HEAD")
        check = "if [ -e archive-c.txt ]; then seq 1 30; exit 1; fi"
        r = self.land("--check", check)
        self.assertEqual(r.returncode, 3, r.stdout)
        lines = r.stdout.splitlines()
        i = lines.index("not merged: check red with the change: " + check)
        self.assertEqual(lines[i + 1:], ["    %d" % n for n in range(11, 31)])
        self.assert_rolled_back(head)
        self.assertFalse(os.path.exists(os.path.join(self.main, "archive-c.txt")))

    def test_main_red(self):
        self.make_change()
        head = g(self.main, "rev-parse", "HEAD")
        r = self.land("--check", "echo broken; exit 1")
        self.assertEqual(r.returncode, 4, r.stdout)
        self.assertIn("main red", r.stdout)
        self.assertIn("broken", r.stdout)
        self.assert_rolled_back(head)

    def test_check_runs_once_after_merge_and_once_on_main(self):
        self.make_change()
        cnt = os.path.join(self.tmp, "count")
        self.land("--check", "echo x >> %s; exit 1" % cnt)
        self.assertEqual(len(pathlib.Path(cnt).read_text().split()), 2)
        shutil.rmtree(self.wt, ignore_errors=True)

    @marks.slow
    def test_command_timeouts_a_hanging_check_in_land_local(self):
        self.make_change()
        head = g(self.main, "rev-parse", "HEAD")
        check = "if [ -e feature.txt ]; then sleep 100 | cat; fi"
        self.env["SDD_DISPATCH_TIMEOUT"] = "1"
        r = self.land("--check", check)
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("not merged: check red with the change: " + check, r.stdout)
        self.assertIn("%s: timeout after 1 s" % check, r.stdout)
        self.assert_rolled_back(head)

    @marks.slow
    def test_command_timeouts_a_hanging_git_step_in_land_local(self):
        self.make_change()
        head = g(self.main, "rev-parse", "HEAD")
        hook = pathlib.Path(self.main, ".git", "hooks", "post-merge")
        hook.write_text("#!/bin/sh\nsleep 100\n")
        hook.chmod(0o755)
        self.env["SDD_DISPATCH_TIMEOUT"] = "1"
        r = self.land()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("not merged: merge: git merge -q --no-ff --no-edit change/c: timeout after 1 s", r.stdout)
        self.assert_rolled_back(head)
        self.assertFalse(os.path.exists(os.path.join(self.main, "feature.txt")))
        hook.rename(hook.with_name("pre-merge-commit"))  # before the merge commit: git leaves the merged tree staged
        r = self.land()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("timeout after 1 s", r.stdout)
        self.assert_rolled_back(head)
        self.assertEqual(g(self.main, "status", "--porcelain", "--untracked-files=no"), "")
        self.assertFalse(os.path.exists(os.path.join(self.main, "feature.txt")))

    def test_check_runs_once_when_green(self):
        self.make_change()
        cnt = os.path.join(self.tmp, "count")
        r = self.land("--check", "echo x >> " + cnt)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(len(pathlib.Path(cnt).read_text().split()), 1)

    def test_openspec_validate_failure_is_check(self):
        self.make_change()
        pathlib.Path(self.bin, "openspec").write_text("#!/bin/sh\necho invalid spec\nexit 1\n")
        r = self.land()
        self.assertEqual(r.returncode, 4, r.stdout)
        self.assertIn("main red: openspec validate --all --strict --no-interactive", r.stdout.splitlines())
        self.assertIn("    invalid spec", r.stdout.splitlines())

    def test_missing_branch(self):
        head = g(self.main, "rev-parse", "HEAD")
        r = self.land(cid="none")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("diff", r.stdout)
        self.assertEqual(g(self.main, "rev-parse", "HEAD"), head)

    def test_remove_failure_keeps_merge(self):
        self.make_change()
        script = self.fake_worktree("if sub == 'remove':\n    print('error: busy')\n    sys.exit(1)")
        r = self.land(script=script)
        self.assertEqual(r.returncode, 1, r.stdout)
        head = g(self.main, "rev-parse", "HEAD")
        self.assertIn("merged %s, not cleaned: remove" % head, r.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.main, "feature.txt")))

    def test_check_exit_code_under_pipe(self):
        self.make_change(rel="archive-c.txt")
        self.put(self.tmp, "check.sh", "[ -e archive-c.txt ] && exit 1\nexit 0\n")
        r = self.land("--check", "sh %s/check.sh | cat" % self.tmp)
        self.assertEqual(r.returncode, 3, r.stdout)

    def test_rollback_failure_reports_reason_and_stuck_merge(self):
        self.make_change()
        script = self.fake_worktree("if sub == 'undo':\n    print('error: undo broken')\n    sys.exit(1)")
        check = "seq 1 25; exit 1"
        r = self.land("--check", check, script=script)
        self.assertEqual(r.returncode, 1, r.stdout)
        lines = r.stdout.splitlines()
        i = lines.index("check red: " + check)
        self.assertEqual(lines[i + 1:i + 21], ["    %d" % n for n in range(6, 26)])
        head = g(self.main, "rev-parse", "HEAD")
        self.assertTrue(lines[-1].startswith("merged %s, rollback failed: undo" % head), lines[-1])
        self.assertTrue(os.path.exists(self.wt))

    def test_transport_failure_rollback_failure(self):
        self.make_change()
        script = self.fake_worktree("if sub == 'transport':\n    print('error: broken')\n    sys.exit(1)\n"
                                    "if sub == 'undo':\n    print('error: undo broken')\n    sys.exit(1)")
        r = self.land(script=script)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("not merged: transport", r.stdout)
        self.assertIn("rollback failed: undo", r.stdout)

    def test_branch_delete_failure_keeps_merge(self):
        self.make_change()
        script = self.fake_worktree(
            "if sub == 'remove':\n    subprocess.run(['git', '-C', sys.argv[3], '-c', 'user.name=t', '-c', 'user.email=t@t',"
            " 'commit', '-q', '--allow-empty', '-m', 'late'])")
        r = self.land(script=script)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        head = g(self.main, "rev-parse", "HEAD")
        self.assertIn("merged %s, not cleaned: branch -d" % head, r.stdout)
        self.assertEqual(len(g(self.main, "rev-list", "--parents", "-n", "1", "HEAD").split()), 3)

    def test_usage(self):
        r = dispatch(SCRIPT, "land-local", self.main)
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage", r.stderr)
        r = dispatch(SCRIPT, "land-local", self.main, self.wt, "c", "--check")
        self.assertEqual(r.returncode, 2)


class ArchiveRemovalLandTest(LandBase):
    """Requirement: Change archive outside git. The merge of the branch that removes solo-sdd/changes/archive/ from the
    index deletes the tracked archive from MAIN's disk and transport puts it back from WORKTREE."""

    OLD = ("solo-sdd/changes/archive/2026-11-01-a/tasks.md", "solo-sdd/changes/archive/2026-11-02-b/specs/x/spec.md")
    NEW = "solo-sdd/changes/archive/2026-11-11-c"

    @staticmethod
    def BUILD(root):
        """LandBase's fixture plus a tracked archive in MAIN and a worktree branch that moves it outside git."""
        build_land(root)
        cls, main, wt = ArchiveRemovalLandTest, os.path.join(root, "main"), os.path.join(root, "wt")
        fake = os.path.join(root, "bin", "solo-sdd")  # a solo-sdd/ tree validates by the solo-sdd command
        pathlib.Path(fake).write_text("#!/bin/sh\nexit 0\n")
        os.chmod(fake, 0o755)
        cls.put(None, main, "solo-sdd/project.md", "p\n")
        for rel in cls.OLD:
            cls.put(None, main, rel, rel + "\n")
        g(main, "add", "-A")
        g(main, "commit", "-q", "-m", "tracked archive")
        g(main, "worktree", "add", "-q", "-b", "change/c", wt)
        subprocess.run([sys.executable, str(WORKTREE), "setup", main, wt], capture_output=True,
                       stdin=subprocess.DEVNULL, check=True)
        cls.put(None, wt, ".gitignore", "solo-sdd/changes/archive/\n")
        g(wt, "rm", "-r", "-q", "--cached", "solo-sdd/changes/archive")
        cls.put(None, wt, cls.NEW + "/tasks.md", "t\n")
        g(wt, "add", "-A")
        g(wt, "commit", "-q", "-m", "archive outside git")

    def setUp(self):
        super().setUp()
        self.prev = g(self.main, "rev-parse", "HEAD")

    def assert_old_on_disk(self):
        for rel in self.OLD:
            self.assertEqual(pathlib.Path(self.main, rel).read_text(), rel + "\n")

    def test_rollback_keeps_archive_on_disk(self):
        r = self.land("--check", "test ! -d " + self.NEW)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("not merged: check red with the change", r.stdout)
        self.assert_rolled_back(self.prev)
        self.assertEqual(g(self.main, "ls-files", "solo-sdd/changes/archive").split(), sorted(self.OLD))
        self.assert_old_on_disk()
        self.assertFalse(os.path.exists(os.path.join(self.main, self.NEW)))
        self.assertEqual(g(self.main, "status", "--porcelain"), "")

    def test_failed_reset_keeps_archive_on_disk(self):
        self.put(self.wt, "README.md", "changed\n")
        g(self.wt, "commit", "-q", "-am", "readme")
        r = self.land("--check", "echo dirty >> README.md; false")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("rollback failed: reset", r.stdout)
        self.assert_old_on_disk()

    def test_merge_keeps_archive_on_disk(self):
        r = self.land()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(g(self.main, "ls-files", "solo-sdd/changes/archive"), "")
        self.assert_old_on_disk()
        self.assertEqual(pathlib.Path(self.main, self.NEW, "tasks.md").read_text(), "t\n")
        self.assertEqual(g(self.main, "status", "--porcelain"), "")


class StaleArchiveBranchTest(LandBase):
    """Requirement: Change archive outside git. A branch cut before the ignore line that edits an archived file would
    overwrite MAIN's ignored copy (and `merge --abort` would delete it): land-local refuses before the merge."""

    OLD = "solo-sdd/changes/archive/2026-11-01-a/tasks.md"

    @staticmethod
    def BUILD(root):
        """LandBase's fixture plus a worktree cut before MAIN moved its tracked archive outside git."""
        build_land(root)
        cls, main, wt = StaleArchiveBranchTest, os.path.join(root, "main"), os.path.join(root, "wt")
        fake = os.path.join(root, "bin", "solo-sdd")
        pathlib.Path(fake).write_text("#!/bin/sh\nexit 0\n")
        os.chmod(fake, 0o755)
        cls.put(None, main, "solo-sdd/project.md", "p\n")
        cls.put(None, main, cls.OLD, "t\n")
        g(main, "add", "-A")
        g(main, "commit", "-q", "-m", "tracked archive")
        g(main, "worktree", "add", "-q", "-b", "change/c", wt)
        cls.put(None, main, ".gitignore", "solo-sdd/changes/archive/\n")
        g(main, "rm", "-r", "-q", "--cached", "solo-sdd/changes/archive")
        g(main, "add", "-A")
        g(main, "commit", "-q", "-m", "archive outside git")

    def setup_stale(self):
        """The stale branch is part of the fixture (BUILD), built once and copied per test."""

    def test_refused_before_merge(self):
        self.setup_stale()
        self.put(self.main, self.OLD, "t\nmain only\n")
        self.put(self.wt, self.OLD, "t\nbranch\n")
        g(self.wt, "commit", "-q", "-am", "edit archived")
        head = g(self.main, "rev-parse", "HEAD")
        r = self.land()
        self.assertEqual(r.returncode, 6, r.stdout + r.stderr)
        self.assertIn("not merged: merge would overwrite untracked files: " + self.OLD, r.stdout)
        self.assert_rolled_back(head)
        self.assertEqual(pathlib.Path(self.main, self.OLD).read_text(), "t\nmain only\n")

    def test_equal_content_refused(self):
        """An edit to the content MAIN's copy already has would still be deleted by `merge --abort`."""
        self.setup_stale()
        self.put(self.main, self.OLD, "same\n")
        self.put(self.wt, self.OLD, "same\n")
        g(self.wt, "commit", "-q", "-am", "edit archived")
        head = g(self.main, "rev-parse", "HEAD")
        r = self.land()
        self.assertEqual(r.returncode, 6, r.stdout + r.stderr)
        self.assertIn("would overwrite untracked files: " + self.OLD, r.stdout)
        self.assert_rolled_back(head)
        self.assertEqual(pathlib.Path(self.main, self.OLD).read_text(), "same\n")

    def test_deletion_not_refused(self):
        self.setup_stale()
        g(self.wt, "rm", "-q", self.OLD)
        g(self.wt, "commit", "-q", "-m", "drop archived")
        r = self.land()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(pathlib.Path(self.main, self.OLD).read_text(), "t\n")


class OwnTreeTest(Base):
    """Requirement: Validation command by tree. A solo-sdd/ tree is validated by solo-sdd, then the module, never openspec."""

    def setUp(self):
        super().setUp()
        self.wt = os.path.join(self.tmp, "wt")
        self.bin = os.path.join(self.tmp, "bin")
        self.log = os.path.join(self.tmp, "calls")
        os.makedirs(os.path.join(self.wt, "solo-sdd"))
        pathlib.Path(self.wt, "solo-sdd", "project.md").write_text("# p\n")
        os.makedirs(self.bin)
        self.tool("openspec", 0)
        # PATH without any real solo-sdd: only this bin and the folders of the system tools
        keep = [d for d in os.environ["PATH"].split(os.pathsep) if d and not os.path.exists(os.path.join(d, "solo-sdd"))]
        self.env = dict(os.environ, PATH=os.pathsep.join([self.bin] + keep))
        self.env.pop("PYTHONPATH", None)

    def tool(self, name, code):
        p = os.path.join(self.bin, name)
        pathlib.Path(p).write_text('#!/bin/sh\necho "%s $*" >> "%s"\nexit %d\n' % (name, self.log, code))
        os.chmod(p, 0o755)

    def calls(self):
        return pathlib.Path(self.log).read_text().splitlines() if os.path.exists(self.log) else []

    def accept(self, validate="openspec validate --all --strict --no-interactive -> exit 0"):
        st = os.path.join(self.tmp, "status.txt")
        verification(self.wt, "1. `echo ok`\n")
        pathlib.Path(st).write_text("STATUS: archived\nWORKTREE: %s\nVALIDATE: %s\nLIVE: echo ok -> ok\nARCHIVE: %s\n" % (self.wt, validate, ARCH))
        return dispatch(SCRIPT, "accept", st, env=self.env)

    def test_command_decides(self):
        self.tool("solo-sdd", 0)
        r = self.accept()
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "status matches"), r.stdout)
        self.assertEqual(self.calls(), ["solo-sdd validate --all"])
        self.tool("solo-sdd", 1)
        r = self.accept()
        self.assertEqual(r.returncode, 1)
        self.assertIn("VALIDATE: solo-sdd validate --all — stated exit 0, got exit 1", r.stdout)
        self.assertFalse([c for c in self.calls() if c.startswith("openspec")])

    def test_module_without_command(self):
        self.env["PYTHONPATH"] = str(SCRIPT.parents[1])
        r = self.accept()
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "status matches"), r.stdout)
        os.makedirs(os.path.join(self.wt, "solo-sdd", "changes", "bad"))
        pathlib.Path(self.wt, "solo-sdd", "changes", "bad", "proposal.md").write_text("# x\n")
        r = self.accept()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("VALIDATE: python3 -m solo_sdd validate --all — stated exit 0, got exit 1", r.stdout)
        self.assertEqual(self.calls(), [])

    def test_neither(self):
        self.tool("python3", 1)
        r = self.accept()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("VALIDATE: solo-sdd not found", r.stdout)
        self.assertFalse([c for c in self.calls() if c.startswith("openspec")])

    @marks.slow
    def test_command_timeouts_a_hanging_solo_sdd_probe(self):
        p = os.path.join(self.bin, "python3")
        pathlib.Path(p).write_text("#!/bin/sh\nsleep 100\n")
        os.chmod(p, 0o755)
        self.env["SDD_DISPATCH_TIMEOUT"] = "1"
        r = self.accept()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("VALIDATE: timeout after 1 s", r.stdout)
        self.assertNotIn("not found", r.stdout)

    def test_openspec_tree_keeps_stated(self):
        shutil.rmtree(os.path.join(self.wt, "solo-sdd"))
        os.makedirs(os.path.join(self.wt, "openspec"))
        self.tool("solo-sdd", 0)
        r = self.accept()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.calls(), ["openspec validate --all --strict --no-interactive"])

    def test_land_local_validates_own_tree(self):
        """Requirement: Process root in other capabilities. land-local checks the merged main with solo-sdd."""
        main = os.path.join(self.tmp, "main")
        self.tool("solo-sdd", 0)
        env = dict(self.env, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        os.makedirs(os.path.join(main, "solo-sdd"))
        pathlib.Path(main, "solo-sdd", "project.md").write_text("# p\n")
        pathlib.Path(main, "AGENTS.md").write_text("rules\n")
        g(main, "init", "-q", "-b", "main")
        g(main, "add", "-A")
        g(main, "commit", "-q", "-m", "init")
        wt = os.path.join(self.tmp, "wt2")
        g(main, "worktree", "add", "-q", "-b", "change/c", wt)
        pathlib.Path(wt, "feature.txt").write_text("new\n")
        g(wt, "add", "-A")
        g(wt, "commit", "-q", "-m", "change")
        r = dispatch(SCRIPT, "land-local", main, wt, "c", "--check", "echo check >> " + self.log, env=env)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.calls(), ["check", "solo-sdd validate --all"])


if __name__ == "__main__":
    unittest.main()
