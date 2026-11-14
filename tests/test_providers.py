#!/usr/bin/env python3
"""solo_sdd/providers.py: the registry, detection, doctor lines, the agents setting and the docs/agents.md table."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import layout, providers, settings  # noqa: E402


def cli(args, home, cwd, path):
    p = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=cwd, capture_output=True, text=True,
                       env=dict(os.environ, HOME=home, PATH=path, PYTHONPATH=REPO), stdin=subprocess.DEVNULL, timeout=120)
    return p.returncode, p.stdout


class Temp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.home)
        os.makedirs(self.bin)

    def command(self, name):
        path = os.path.join(self.bin, name)
        with open(path, "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(path, 0o755)


class Registry(Temp):
    """Requirement: Provider registry."""

    def test_entries(self):
        self.assertEqual(providers.ALL, ("claude", "codex", "cursor", "other"))
        for name, p in providers.PROVIDERS.items():
            for key in ("detect", "skills", "rules", "project_rules", "owns", "caps"):
                self.assertIn(key, p, name)
            for cap, checked in p["caps"].items():
                self.assertIn(cap, providers.GAPS)
                self.assertTrue(checked == "unverified" or re.fullmatch(r"\d+\.\d+\.\d+", checked), (name, cap, checked))

    def test_detection_by_command(self):
        self.command("codex")
        with mock.patch.dict(os.environ, {"PATH": self.bin}):
            self.assertEqual(providers.detected(self.home), ["codex", "other"])

    def test_detection_by_folder(self):
        os.makedirs(os.path.join(self.home, ".claude"))
        with mock.patch.dict(os.environ, {"PATH": self.bin}):
            self.assertEqual(providers.detected(self.home), ["claude", "other"])

    def test_cursor_by_command(self):
        self.command("cursor-agent")
        with mock.patch.dict(os.environ, {"PATH": self.bin}):
            self.assertEqual(providers.found("cursor", self.home), "cursor-agent in PATH")
            self.assertEqual(providers.detected(self.home), ["cursor", "other"])

    def test_cursor_by_folder(self):
        os.makedirs(os.path.join(self.home, ".cursor"))
        with mock.patch.dict(os.environ, {"PATH": self.bin}):
            self.assertEqual(providers.found("cursor", self.home), "~/.cursor")
            self.assertEqual(providers.detected(self.home), ["cursor", "other"])

    def test_nothing_detected_is_other(self):
        with mock.patch.dict(os.environ, {"PATH": self.bin}):
            self.assertEqual(providers.detected(self.home), ["other"])

    def test_parse(self):
        self.assertEqual(providers.parse("codex"), ["codex", "other"])
        self.assertEqual(providers.parse(" codex , claude "), ["claude", "codex", "other"])
        for bad in ("copilt", "codex,copilt", "", ","):
            with self.assertRaisesRegex(ValueError, "known: claude, codex, cursor, other"):
                providers.parse(bad)

    def test_owner(self):
        self.assertEqual(providers.owner("~/.claude/hooks/work_hooks.py"), "claude")
        self.assertEqual(providers.owner("~/.codex/AGENTS.md"), "codex")
        self.assertEqual(providers.owner("~/AGENTS.md"), "other")
        self.assertEqual(providers.owner("~/.agents/skills/ship/SKILL.md"), "other")
        self.assertIsNone(providers.owner("~/.local/bin/sdd-pr.py"))
        self.assertIsNone(providers.owner("~/.claudette/x"))


class Placement(Temp):
    """Requirement: Capability gaps named: a skill that needs capabilities goes only where they are present."""

    def test_needs_filter(self):
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(os.path.join(repo, "skills", "spec-dispatch"))
        with open(os.path.join(repo, "targets.json"), "w") as f:
            json.dump({"needs": {"spec-dispatch": ["subagents", "hooks"]},
                       "skills": {"spec-dispatch": ["other", "codex", "claude"]}, "files": {}}, f)
        with mock.patch.object(layout, "REPO", repo):
            places = [t for _, _, t, _ in layout.pairs(providers.ALL)]
            self.assertEqual(places, [os.path.join(layout.expand("~/.claude/skills"), "spec-dispatch", "SKILL.md")])
            with mock.patch.dict(providers.PROVIDERS["codex"]["caps"], {"hooks": "1.0.0"}):
                self.assertEqual(len(list(layout.pairs(providers.ALL))), 2)

    def test_cursor_not_probed(self):
        """Requirement: Cursor provider: without a recorded skill root only the `other` and shared copies."""
        self.assertFalse(providers.probed("cursor"))
        places = [t for _, _, t, _ in layout.pairs(["cursor", "other"])]
        self.assertTrue(places)
        self.assertEqual(places, [t for _, _, t, _ in layout.pairs(["other"])])

    def test_cursor_probed(self):
        """Requirement: Cursor provider, scenario Probed: a recorded skill root gets the skills."""
        with mock.patch.dict(providers.PROVIDERS["cursor"], {"skills": "~/.cursor/skills", "project_rules": "AGENTS.md"}):
            places = [t for _, _, t, _ in layout.pairs(["cursor", "other"])]
            level, detail = providers.row("cursor")
        self.assertEqual(level, "warn")
        self.assertNotIn("unverified", detail)
        self.assertTrue(detail.startswith("no hooks: CLAIM guard"), detail)
        self.assertIn(os.path.join(layout.expand("~/.cursor/skills"), "ship", "SKILL.md"), places)
        self.assertNotIn(os.path.join(layout.expand("~/.cursor/skills"), "spec-dispatch", "SKILL.md"), places)

    def test_install_cursor(self):
        code, out = cli(["install", "--agents", "cursor"], self.home, REPO, self.bin)
        self.assertEqual(code, 0, out)
        self.assertIn("cursor: unverified: skills, project rules: skills go to ~/.agents/skills, "
                      "project rules come from solo-sdd init", out)
        self.assertTrue(os.path.isfile(os.path.join(self.home, ".agents", "skills", "ship", "SKILL.md")))
        for agent_dir in (".cursor", ".claude", ".codex"):
            self.assertFalse(os.path.exists(os.path.join(self.home, agent_dir)), agent_dir)

    def test_real_targets(self):
        with open(os.path.join(REPO, "targets.json")) as f:
            targets = json.load(f)
        self.assertNotIn("roots", targets)
        for where in targets["skills"].values():
            self.assertTrue(set(where) <= set(providers.ALL), where)
        self.assertEqual(targets["needs"]["spec-dispatch"], ["subagents", "hooks"])


class Doctor(Temp):
    """Requirement: Capability gaps named; Requirement: Agents setting (its reader)."""

    def doctor(self, cwd=None):
        cwd = cwd or self.tmp
        return cli(["doctor"], self.home, cwd, self.bin)[1]

    def test_lines(self):
        self.assertEqual(cli(["install", "--agents", "claude,codex"], self.home, REPO, self.bin)[0], 0)
        out = self.doctor()
        self.assertIn("ok agent claude: hooks (2.1.312), subagents (2.1.312)", out)
        self.assertIn("warn agent codex: no hooks: CLAIM guard, secret guard and stop check not enforced", out)
        self.assertRegex(out, r"(?m)^warn agent other: no hooks: .*; no subagents: ")
        self.assertEqual(len(re.findall(r"(?m)^\w+ agent ", out)), 3)

    def test_cursor_unverified(self):
        self.assertEqual(cli(["install", "--agents", "cursor"], self.home, REPO, self.bin)[0], 0)
        out = self.doctor()
        self.assertIn("warn agent cursor: unverified: skills, project rules: skills go to ~/.agents/skills, project rules "
                      "come from solo-sdd init; no hooks: CLAIM guard, secret guard and stop check not enforced; "
                      "no subagents: spec-dispatch and independent review subagents not available", out)
        self.assertEqual(re.findall(r"(?m)^\w+ agent (\w+)", out), ["cursor", "other"])

    def test_only_chosen(self):
        self.assertEqual(cli(["install", "--agents", "codex"], self.home, REPO, self.bin)[0], 0)
        self.assertEqual(re.findall(r"(?m)^\w+ agent (\w+)", self.doctor()), ["codex", "other"])

    def test_project_agents_not_installed(self):
        self.assertEqual(cli(["install", "--agents", "claude"], self.home, REPO, self.bin)[0], 0)
        project = os.path.join(self.tmp, "project")
        os.makedirs(os.path.join(project, "solo-sdd", "changes"))
        self.assertNotIn("project-agents", self.doctor(project))
        with open(os.path.join(project, "solo-sdd", "config"), "w") as f:
            f.write("agents: codex\n")
        self.assertIn("warn project-agents: solo-sdd/config names codex, not installed; "
                      "solo-sdd install --agents claude,codex,other", self.doctor(project))


class AgentsSetting(Temp):
    """Requirement: Agents setting."""

    def test_registered_names(self):
        kind, allowed = settings.REGISTRY["agents"][:2]  # the settings block names them literally: it cannot import
        self.assertEqual((kind, allowed), ("list", providers.ALL))

    def test_unregistered_name_refused(self):
        project = os.path.join(self.tmp, "project")
        os.makedirs(os.path.join(project, "solo-sdd", "changes"))
        code, out = cli(["config", "set", "agents", "claude,copilot"], self.home, project, self.bin)
        self.assertEqual(code, 1)
        self.assertIn("agents takes claude, codex, cursor, other, not 'claude,copilot'", out)
        self.assertFalse(os.path.exists(os.path.join(project, "solo-sdd", "config")))
        self.assertEqual(cli(["config", "set", "agents", "codex, claude"], self.home, project, self.bin), (0, "agents: codex, claude\n"))

    def test_default_is_detected(self):
        project = os.path.join(self.tmp, "project")
        os.makedirs(os.path.join(project, "solo-sdd", "changes"))
        os.makedirs(os.path.join(self.home, ".codex"))
        self.assertEqual(cli(["config", "get", "agents"], self.home, project, self.bin), (0, "codex, other\n"))


class Probe(Temp):
    """Requirement: Probe without side effects, scenario No Cursor."""

    def test_no_cursor(self):
        p = subprocess.run([sys.executable, os.path.join(REPO, "tests", "stands", "provider-probe.py"), "cursor"],
                           cwd=self.tmp, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60,
                           env=dict(os.environ, HOME=self.home, PATH=self.bin))
        self.assertEqual(p.returncode, 0, p.stderr)
        lines = p.stdout.splitlines()
        self.assertEqual([l.split(":")[0] for l in lines[:-1]],
                         ["cursor - %s" % c for c in ("rules", "skills", "hooks", "subagents")])
        for line in lines[:-1]:
            self.assertIn(": not run — cursor-agent not in PATH; registry unverified", line)
        self.assertEqual(lines[-1], "summary: cursor not probed")
        self.assertEqual(os.listdir(self.home), [])
        self.assertEqual(sorted(os.listdir(self.tmp)), ["bin", "home"])


def tree(root):
    """Every file under root with its bytes: what a refused command must leave as it was."""
    out = {}
    for dp, _, names in os.walk(root):
        for n in names:
            with open(os.path.join(dp, n), "rb") as f:
                out[os.path.relpath(os.path.join(dp, n), root)] = f.read()
    return out


class VendorFilesPerSkill(Temp):
    """Requirement: Vendor files per skill."""

    def repo_copy(self, targets):
        """A repository copy with its own targets.json; commands run from outside it, the real map is not touched."""
        repo = os.path.join(self.tmp, "repo")
        for d in ("solo_sdd", "global", "skills", "templates", "integrations"):
            shutil.copytree(os.path.join(REPO, d), os.path.join(repo, d), ignore=shutil.ignore_patterns("__pycache__"))
        for f in ("sync.py", "ALGORITHM.md"):
            shutil.copy(os.path.join(REPO, f), repo)
        with open(os.path.join(repo, "targets.json"), "w") as f:
            json.dump(targets, f)
        return repo

    def run_in(self, repo, *args):
        """sync.py <args> of repo, or `-m solo_sdd <args>` from it when args start with -m."""
        cmd = [sys.executable, *args] if args[0] == "-m" else [sys.executable, os.path.join(repo, "sync.py"), *args]
        p = subprocess.run(cmd, cwd=self.tmp, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120,
                           env=dict(os.environ, HOME=self.home, PATH=self.bin, PYTHONPATH=repo))
        return p.returncode, p.stdout

    def test_the_same_layout(self):
        with open(os.path.join(REPO, "tests", "targets-before.json")) as f:
            before = self.repo_copy(json.load(f))
        os.makedirs(os.path.join(self.home, ".claude"))
        self.assertEqual(self.run_in(before, "push")[0], 0)
        with open(os.path.join(self.home, ".claude", "skills", "ui-check", "antislop", "core.md"), "a") as f:
            f.write("edited in place\n")
        os.remove(os.path.join(self.home, ".agents", "skills", "spec-audit", "security", "HUNTING.md"))
        rows = lambda out: sorted(" ".join(line.split()) for line in out.splitlines())
        code, old = self.run_in(before, "status")
        self.assertEqual(code, 0, old)
        code, new = self.run_in(REPO, "status")
        self.assertEqual(code, 0, new)
        self.assertEqual(rows(new), rows(old))
        self.assertIn("drift integrations/antislop/antislop.md ~/.claude/skills/ui-check/antislop/core.md", rows(new))
        self.assertTrue(any(r.startswith("missing ") and r.endswith("/.agents/skills/spec-audit/security/HUNTING.md")
                            for r in rows(new)), new)

    def test_one_agent_chosen(self):
        code, out = cli(["install", "--agents", "claude"], self.home, REPO, self.bin)
        self.assertEqual(code, 0, out)
        for skill in ("ui-check", "copy-check"):
            self.assertTrue(os.path.isfile(os.path.join(self.home, ".claude", "skills", skill, "antislop", "core.md")), skill)
        self.assertFalse(os.path.exists(os.path.join(self.home, ".codex")))

    def test_an_agent_without_a_skill_folder(self):
        code, out = cli(["install", "--agents", "cursor"], self.home, REPO, self.bin)
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(os.path.join(self.home, ".cursor")))
        folder = os.path.join(self.home, ".agents", "skills", "ui-check", "antislop")
        for name in ("core.md", "contrast-check.py", "references/WCAG.md"):
            self.assertTrue(os.path.isfile(os.path.join(folder, name)), name)

    def test_an_unknown_skill(self):
        with open(os.path.join(REPO, "targets.json")) as f:
            targets = json.load(f)
        targets["files"]["integrations/antislop/VERSION"] = {"skills": {"ui-check": "antislop/VERSION", "no-such-skill": "x"}}
        repo = self.repo_copy(targets)
        os.makedirs(os.path.join(self.home, ".claude"))
        for args in (("status",), ("push",), ("-m", "solo_sdd", "install"), ("-m", "solo_sdd", "status"),
                     ("-m", "solo_sdd", "uninstall")):
            code, out = self.run_in(repo, *args)
            self.assertEqual(code, 1, (args, out))
            self.assertIn("integrations/antislop/VERSION", out, args)
            self.assertIn("no-such-skill", out, args)
            self.assertEqual(tree(self.home), {}, args)

    def test_an_unknown_skill_keeps_connected_hooks(self):
        """uninstall with a bad map stops before the hooks are restored: settings.json and state.json stay as they were."""
        os.makedirs(os.path.join(self.home, ".claude"))
        code, out = cli(["install", "--agents", "claude", "--hooks"], self.home, REPO, self.bin)
        self.assertEqual(code, 0, out)
        with open(os.path.join(REPO, "targets.json")) as f:
            targets = json.load(f)
        targets["files"]["integrations/antislop/VERSION"] = {"skills": {"no-such-skill": "x"}}
        laid = tree(self.home)
        code, out = self.run_in(self.repo_copy(targets), "-m", "solo_sdd", "uninstall")
        self.assertEqual(code, 1, out)
        self.assertIn("no-such-skill", out)
        self.assertEqual(tree(self.home), laid)

    def test_skills_not_a_map_refused(self):
        with open(os.path.join(REPO, "targets.json")) as f:
            targets = json.load(f)
        targets["files"]["integrations/antislop/VERSION"] = {"skills": ["ui-check"]}
        code, out = self.run_in(self.repo_copy(targets), "status")
        self.assertEqual(code, 1, out)
        self.assertIn("integrations/antislop/VERSION: skills must map", out)

    def test_entries_name_skills_not_agent_folders(self):
        with open(os.path.join(REPO, "targets.json")) as f:
            self.assertIsNone(re.search(r"~/\.(claude|codex|agents)/skills", f.read()))


class Readme(unittest.TestCase):
    """docs/agents.md: the table generated from the registry."""

    def test_table_matches_the_registry(self):
        with open(os.path.join(REPO, "docs", "agents.md"), encoding="utf-8") as f:
            body = f.read()
        self.assertIn("\n" + providers.table(), body)


if __name__ == "__main__":
    unittest.main()
