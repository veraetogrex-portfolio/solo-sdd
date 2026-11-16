#!/usr/bin/env python3
"""solo_sdd/providers.py: the registry, detection, doctor lines, the agents setting and the docs/agents.md table."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from unittest import mock

from hypothesis import Phase, given, settings as hsettings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import hooks, layout, providers, settings  # noqa: E402
import marks  # noqa: E402


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
        with mock.patch.object(layout, "REPO", repo), mock.patch.dict(providers.PROVIDERS["codex"]["caps"], {"hooks": "unverified"}):
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
        self.assertIn("ok agent codex: hooks (0.159.2), subagents (0.159.2)", out)  # Codex hook probe, 2026-11-16
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

    def test_codex_hook_probe_without_codex(self):
        """Requirement: Codex hook probe, scenario The hook did not run: no codex command, nothing run."""
        p = subprocess.run([sys.executable, os.path.join(REPO, "tests", "stands", "provider-probe.py"), "codex"],
                           cwd=self.tmp, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60,
                           env=dict(os.environ, HOME=self.home, PATH=self.bin))
        self.assertIn("codex - hooks: unverified — codex not in PATH;", p.stdout)
        self.assertEqual(os.listdir(self.home), [])

    def test_codex_hook_probe_hook_did_not_run(self):
        """Requirement: Codex hook probe, scenario The hook did not run: a codex that runs no hook and lists none."""
        with open(os.path.join(self.bin, "codex"), "w") as f:
            f.write('#!/bin/sh\ncase "$1" in --version) echo "codex-cli 9.9.9";; features) echo "multi_agent stable true";; esac\n')
        os.chmod(os.path.join(self.bin, "codex"), 0o755)
        p = subprocess.run([sys.executable, os.path.join(REPO, "tests", "stands", "provider-probe.py"), "codex"],
                           cwd=self.tmp, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60,
                           env=dict(os.environ, HOME=self.home, PATH=self.bin + os.pathsep + "/usr/bin:/bin"))
        self.assertEqual(p.returncode, 0 if providers.PROVIDERS["codex"]["caps"]["hooks"] == "unverified" else 1, p.stderr)
        self.assertIn("codex 9.9.9 hooks: unverified — no-op hook ran: none (codex app-server hooks/list gave no answer)",
                      p.stdout)
        self.assertEqual(os.listdir(self.home), [])

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


def unverified_cli(home, *args):
    """`solo-sdd <args>` with the Codex `hooks` capability set back to unverified, as before the probe confirmed it."""
    code = ("import sys; from solo_sdd import cli, providers; providers.PROVIDERS['codex']['caps']['hooks'] = 'unverified'; "
            "sys.exit(cli.main(sys.argv[1:]))")
    p = subprocess.run([sys.executable, "-c", code, *args], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                       timeout=120, env=dict(os.environ, HOME=home, PATH=os.path.join(home, "no-bin"), PYTHONPATH=REPO))
    return p.returncode, p.stdout


class InstallForChosenAgents(Temp):
    """Requirement: Install for chosen agents, scenario Hooks without Claude."""

    def test_hooks_without_claude_unverified_codex(self):
        before = tree(self.home)
        code, out = unverified_cli(self.home, "install", "--agents", "codex", "--hooks")
        self.assertEqual(code, 1, out)
        self.assertIn("hooks need claude or a confirmed codex among the agents", out)
        self.assertEqual(tree(self.home), before)

    def test_hooks_without_claude_while_connected(self):
        self.assertEqual(unverified_cli(self.home, "install", "--agents", "claude,codex", "--hooks")[0], 0)
        self.assertFalse(os.path.exists(os.path.join(self.home, ".codex", "hooks.json")), "no codex entries while unverified")
        self.assertFalse(os.path.exists(os.path.join(self.home, ".codex", "hooks")), "no codex hook copies while unverified")
        before = tree(self.home)
        code, out = unverified_cli(self.home, "install", "--agents", "codex")
        self.assertEqual(code, 1, out)
        self.assertIn("hooks need claude or a confirmed codex among the agents", out)
        self.assertEqual(tree(self.home), before)

    def test_confirmed_codex_alone(self):
        self.assertTrue(providers.has("codex", "hooks"))
        code, out = cli(["install", "--agents", "codex", "--hooks"], self.home, self.tmp, self.bin)
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(os.path.join(self.home, ".claude")), "no Claude settings without claude")
        with open(os.path.join(self.home, ".codex", "hooks.json")) as f, mock.patch.object(layout, "HOME", self.home):
            self.assertEqual(json.load(f)["hooks"], hooks.codex_need())


FOREIGN = {"matcher": "Bash", "hooks": [{"type": "command", "command": "other-tool check"}]}


class CodexHookLayout(Temp):
    """Requirement: Codex hook layout."""

    def setUp(self):
        super().setUp()
        self.codex = os.path.join(self.home, ".codex")
        os.makedirs(self.codex)
        self.json = os.path.join(self.codex, "hooks.json")
        self.hook = os.path.join(self.codex, "hooks", "work_hooks.py")

    def install(self, *args):
        return cli(["install", *args], self.home, self.tmp, self.bin)

    def entries(self):
        with open(self.json) as f:
            return json.load(f)["hooks"]

    def test_a_clean_codex_home(self):
        code, out = self.install("--agents", "claude,codex", "--hooks")
        self.assertEqual(code, 0, out)
        with open(os.path.join(REPO, "global", "work_hooks.py"), "rb") as a, open(self.hook, "rb") as b:
            self.assertEqual(a.read(), b.read())
        with open(os.path.join(REPO, "global", "model-policy.json"), "rb") as a, open(os.path.join(self.codex, "hooks", "model-policy.json"), "rb") as b:
            self.assertEqual(a.read(), b.read())
        h = self.entries()
        self.assertEqual(sorted(h), ["PreToolUse", "SessionEnd", "SessionStart", "Stop"])
        for event, sub in (("PreToolUse", "guard"), ("SessionStart", "context"), ("SessionEnd", "end"), ("Stop", "stop")):
            self.assertEqual(len(h[event]), 1, event)
            self.assertTrue(h[event][0]["hooks"][0]["command"].endswith('"$f" ' + sub), h[event])
        self.assertEqual(h["PreToolUse"][0]["matcher"], "Bash|Write|Edit|MultiEdit|NotebookEdit|Agent")
        before = tree(self.home)
        self.assertEqual(self.install("--agents", "claude,codex", "--hooks")[0], 0)
        self.assertEqual(tree(self.home), before, "a second run changes no file")
        code, out = cli(["doctor"], self.home, self.tmp, self.bin)
        self.assertIn("ok codex hooks", out)
        self.assertRegex(out, r"ok +agent codex")

    def test_the_hand_copy(self):
        os.makedirs(os.path.dirname(self.hook))
        with open(self.hook, "w") as f:
            f.write("# a hand copy\n")
        code, out = self.install("--agents", "claude,codex", "--hooks")
        self.assertEqual(code, 1, out)
        self.assertIn("foreign ~/.codex/hooks/work_hooks.py: kept", out)
        self.assertEqual(open(self.hook).read(), "# a hand copy\n")
        code, out = self.install("--agents", "claude,codex", "--hooks", "--replace-foreign")
        self.assertEqual(code, 0, out)
        self.assertEqual(open(self.hook).read(), open(os.path.join(REPO, "global", "work_hooks.py")).read())
        backups = [os.path.join(d, f) for d, _, fs in os.walk(os.path.join(self.home, ".local/share/solo-sdd/backup"))
                   for f in fs if f == "work_hooks.py"]
        self.assertEqual([open(b).read() for b in backups], ["# a hand copy\n"])

    def test_a_foreign_entry_kept(self):
        with open(self.json, "w") as f:
            json.dump({"hooks": {"PreToolUse": [FOREIGN]}}, f)
        self.assertEqual(self.install("--agents", "claude,codex", "--hooks")[0], 0)
        h = self.entries()
        self.assertEqual(h["PreToolUse"][0], FOREIGN)
        self.assertEqual(len(h["PreToolUse"]), 2)
        self.assertTrue(any(n.startswith("hooks.json.bak-") for n in os.listdir(self.codex)), "backed up before the rewrite")

    def test_a_broken_hooks_file(self):
        with open(self.json, "w") as f:
            f.write("{broken")
        before = tree(self.codex)
        code, out = self.install("--agents", "claude,codex", "--hooks")
        self.assertEqual(code, 1, out)
        self.assertIn("~/.codex/hooks.json", out)
        self.assertEqual(tree(self.codex), before)

    def test_codex_dropped_from_the_choice(self):
        with open(self.json, "w") as f:
            json.dump({"hooks": {"PreToolUse": [FOREIGN]}}, f)
        self.assertEqual(self.install("--agents", "claude,codex", "--hooks")[0], 0)
        self.assertEqual(len(self.entries()["Stop"]), 1)
        self.assertTrue(os.path.exists(self.hook))
        code, out = self.install("--agents", "claude", "--hooks")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.entries(), {"PreToolUse": [FOREIGN]})
        self.assertFalse(os.path.exists(self.hook))
        self.assertFalse(os.path.exists(os.path.join(self.codex, "hooks", "model-policy.json")))


EVENTS = ("PreToolUse", "SessionStart", "SessionEnd", "Stop", "PostToolUse")
OURS = [g for gs in hooks.codex_need().values() for g in gs]
STALE = {"hooks": [{"type": "command", "command": "exec /usr/bin/python3 ~/.codex/hooks/work_hooks.py stop", "timeout": 5}]}
MIXED = {"matcher": "Bash", "hooks": [{"type": "command", "command": "other-tool mixed"}] + OURS[0]["hooks"]}
GROUPS = st.one_of(st.sampled_from(OURS + [STALE, MIXED]), st.builds(
    lambda m, c: {"matcher": m, "hooks": [{"type": "command", "command": "other-tool %s" % c}]},
    st.sampled_from(["Bash", "*", "Edit"]), st.text("abc", max_size=3)))
DOCS = st.dictionaries(st.sampled_from(EVENTS), st.lists(GROUPS, max_size=4)).map(lambda h: {"hooks": h})


def check_writer(apply, phases=tuple(Phase)):
    """Requirement Codex hook layout as a property of the writer: twice equals once, one solo-sdd entry per event,
    foreign handlers kept and in order (a foreign handler sharing an entry with ours included), entries already in
    place not moved."""
    need = hooks.codex_need()

    @hsettings(max_examples=marks.examples(200, 100), deadline=None, database=None, phases=phases)
    @given(DOCS)
    def prop(doc):
        once = apply(doc, True)
        assert apply(once, True) == once, doc
        for e in set(need) | set(doc["hooks"]):
            got = once["hooks"].get(e, [])
            assert [g for g in got if hooks._codex_ours(g)] == need.get(e, []), (doc, e)
            foreign = [g for g in map(hooks._strip, doc["hooks"].get(e, [])) if g is not None]
            assert [g for g in got if not hooks._codex_ours(g)] == foreign, (doc, e)
            if [g for g in doc["hooks"].get(e, []) if hooks._codex_ours(g)] == need.get(e, []) and e in doc["hooks"]:
                assert got == doc["hooks"][e], ("an entry in place moved", doc, e)
        off = apply(once, False)
        assert not any(hooks._codex_ours(g) for gs in off["hooks"].values() for g in gs), doc
        for e, gs in off["hooks"].items():
            assert gs == [g for g in map(hooks._strip, once["hooks"].get(e, [])) if g is not None], (doc, e)
    prop()


def appending(doc, on):
    """Mutant: appends the entries without removing the old ones."""
    s = json.loads(json.dumps(doc))
    for e, gs in (hooks.codex_need() if on else {}).items():
        s["hooks"].setdefault(e, []).extend(gs)
    return s


class CodexHookWriter(unittest.TestCase):
    """Requirement: Codex hook layout, the writer of ~/.codex/hooks.json as a property; the appending mutant fails it."""

    def test_writing_twice_equals_writing_once(self):
        check_writer(hooks.codex_apply)

    def test_mutant_appends_without_removing(self):
        with self.assertRaises(AssertionError):
            check_writer(appending, (Phase.explicit, Phase.generate))


if __name__ == "__main__":
    unittest.main()
