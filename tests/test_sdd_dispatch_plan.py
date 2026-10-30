"""Проверка sdd_dispatch_plan.py: готовые change, порядок, жёсткие конфликты."""
import importlib.util
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from hypothesis import example, given, settings, strategies as st

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "global/sdd_dispatch_plan.py"

_spec = importlib.util.spec_from_file_location("sdd_dispatch_plan", SCRIPT)
dp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dp)


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo)] + list(args),
                          capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL).stdout


def put(base, rel, text):
    p = pathlib.Path(base, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class Project:
    """Временный проект с openspec/changes; чистится сам."""

    def __init__(self, agents=None):
        self.main = pathlib.Path(tempfile.mkdtemp()).resolve()
        git(self.main, "init", "-q", "-b", "main")
        put(self.main, "README.md", "r\n")
        if agents:
            put(self.main, "AGENTS.md", agents)
        git(self.main, "add", "-A")
        git(self.main, "commit", "-qm", "init")

    def change(self, cid, deps="none", impact=(), reqs=(), cap="cli", claim=False, waiting=False, commit=True):
        d = "openspec/changes/" + cid
        imp = "\n".join("- `%s`" % i for i in impact)
        put(self.main, d + "/proposal.md", "# %s\n\n## Depends On\n\n%s\n\n## Impact\n\n%s\n" % (cid, deps, imp))
        if reqs:
            body = "## ADDED Requirements\n\n" + "".join("### Requirement: %s\nТекст\n\n" % r for r in reqs)
            put(self.main, d + "/specs/%s/spec.md" % cap, body)
        if claim:
            put(self.main, d + "/CLAIM", "x")
        if waiting:
            put(self.main, d + "/WAITING", "x")
        if commit:
            self.commit()

    def commit(self):
        git(self.main, "add", "-A")
        if git(self.main, "status", "--porcelain"):
            git(self.main, "commit", "-qm", "c")

    def archive(self, cid):
        put(self.main, "openspec/changes/archive/2026-01-01-%s/proposal.md" % cid, "x")

    def run(self, *extra):
        r = subprocess.run(["/usr/bin/python3", str(SCRIPT), str(self.main)] + list(extra),
                           capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        return r.returncode, r.stdout

    def close(self):
        shutil.rmtree(self.main, ignore_errors=True)


class Base(unittest.TestCase):
    def project(self, agents=None):
        p = Project(agents)
        self.addCleanup(p.close)
        return p


class PlanTests(Base):
    def test_depends_wait(self):
        p = self.project()
        p.change("add-words")
        p.change("add-lines")
        p.change("add-top-words", deps="`add-words`")
        code, out = p.run()
        self.assertEqual(code, 0)
        self.assertIn("запустить: add-words add-lines", out)
        self.assertIn("add-top-words — зависит от add-words", out)

    def test_depends_with_note(self):
        p = self.project()
        p.change("add-words")
        p.change("add-top-words", deps="- `add-words` (после merge)")
        p.change("tail", deps="add-words, add-top-words — оба нужны")
        _, out = p.run()
        self.assertIn("add-top-words — зависит от add-words", out)
        self.assertIn("tail — зависит от add-words, add-top-words", out)

    def test_shared_file(self):
        p = self.project()
        p.change("a", impact=["textkit/commands/words.py"])
        p.change("b", impact=["textkit/commands/words.py"])
        _, out = p.run()
        self.assertIn("запустить: a\n", out)
        self.assertIn("b — конфликт с a: файл textkit/commands/words.py", out)
        self.assertNotIn("вместе:", out)

    def test_shared_agents_and_capability(self):
        p = self.project()
        p.change("a", impact=["AGENTS.md"], reqs=["One"], cap="cli")
        p.change("b", impact=["AGENTS.md"], reqs=["Two"], cap="cli")
        _, out = p.run()
        self.assertIn("запустить: a b", out)
        self.assertIn("вместе: a и b — AGENTS.md\n", out)
        self.assertNotIn("ждут", out)

    def test_same_requirement(self):
        p = self.project()
        p.change("chars-bytes", reqs=["Character count command"], cap="chars")
        p.change("chars-empty", reqs=["Character count command"], cap="chars")
        _, out = p.run()
        self.assertIn("запустить: chars-bytes\n", out)
        self.assertIn("chars-empty — конфликт с chars-bytes: требование chars/Character count command", out)

    def test_critical_path_first(self):
        p = self.project("# P\n\n## Рабочая копия\n\n- Оркестраторов: 1\n")
        p.change("a-docs")
        p.change("b-core")
        p.change("c-1", deps="b-core")
        p.change("c-2", deps="`b-core`, `c-1`")
        _, out = p.run()
        self.assertIn("лимит: 1, работают: 0", out)
        self.assertIn("запустить: b-core\n", out)
        self.assertIn("a-docs — лимит", out)

    def test_default_limit(self):
        p = self.project("# P\n\n## Рабочая копия\n\n- Пути: `.env`\n")
        p.change("a")
        p.change("b")
        p.change("c")
        _, out = p.run()
        self.assertIn("лимит: 2, работают: 0", out)
        self.assertIn("запустить: a b\n", out)
        self.assertIn("c — лимит", out)

    def test_default_limit_in_skills(self):
        for skill in ("spec-dispatch", "project-init"):
            body = (SCRIPT.parents[1] / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertEqual(set(re.findall(r"по умолчанию (\d+)", body)), {str(dp.LIMIT)}, skill)

    def test_nothing_to_give(self):
        p = self.project()
        p.change("c", claim=True)
        p.change("w", waiting=True)
        p.change("x")
        git(p.main, "branch", "change/x")
        p.change("d", deps="- `nope`\n- `none`")
        _, out = p.run()
        self.assertIn("запустить: нет", out)
        for s in ("c — CLAIM", "w — WAITING", "x — не смёрджен: ветка change/x", "d — неизвестная зависимость: nope"):
            self.assertIn(s, out)

    def test_unmerged_names_worktree(self):
        p = self.project()
        p.change("y")
        wt = pathlib.Path(tempfile.mkdtemp()).resolve() / "wt-y"
        self.addCleanup(shutil.rmtree, wt.parent, True)
        git(p.main, "worktree", "add", "-q", "-b", "change/y", str(wt))
        _, out = p.run()
        self.assertIn("y — не смёрджен: ветка change/y, worktree %s" % wt, out)

    def test_failed_setup_discard_returns_to_queue(self):
        p = self.project(agents="## Рабочая копия\n- Подготовка: `echo partial > prep.log; exit 1`\n")
        p.change("y")
        wt = pathlib.Path(tempfile.mkdtemp()).resolve() / "wt-y"
        self.addCleanup(shutil.rmtree, wt.parent, True)
        git(p.main, "worktree", "add", "-q", "-b", "change/y", str(wt))
        tool = str(SCRIPT.parent / "sdd_worktree.py")
        for cmd, code in (("setup", 1), ("discard", 0)):
            r = subprocess.run(["/usr/bin/python3", tool, cmd, str(p.main), str(wt)],
                               capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
            self.assertEqual(r.returncode, code, r.stderr)
        _, out = p.run()
        self.assertTrue([ln for ln in out.splitlines() if ln.startswith("запустить:") and "y" in ln.split()], out)
        self.assertNotIn("не смёрджен", out)

    def test_archived_dependency_ready(self):
        p = self.project()
        p.archive("old")
        p.change("n", deps="old")
        _, out = p.run()
        self.assertIn("запустить: n", out)

    def test_running_blocks(self):
        p = self.project()
        p.change("r", reqs=["Same"], cap="k", claim=True)
        p.change("n", reqs=["Same"], cap="k")
        p.change("m")
        _, out = p.run("--running", "r")
        self.assertIn("лимит: 2, работают: 1", out)
        self.assertIn("запустить: m\n", out)
        self.assertIn("n — конфликт с r: требование k/Same", out)
        self.assertNotIn("r —", out)

    def test_dir_and_word_not_conflict(self):
        p = self.project()
        (p.main / "src").mkdir()
        p.change("a", impact=["src", "en", "docs/"])
        p.change("b", impact=["src", "en", "docs/"])
        _, out = p.run()
        self.assertIn("запустить: a b", out)

    def test_common_from_agents(self):
        p = self.project("## Рабочая копия\n\n- Общие: `docs/map.md`\n")
        p.change("a", impact=["docs/map.md"])
        p.change("b", impact=["docs/map.md"])
        _, out = p.run()
        self.assertIn("запустить: a b", out)

    def test_common_dir(self):
        p = self.project("## Рабочая копия\n\n- Общие: `docs/`\n")
        p.change("a", impact=["docs/cli.md", "x.py"])
        p.change("b", impact=["docs/cli.md", "y.py"])
        p.change("c", impact=["x.py"])
        _, out = p.run()
        self.assertIn("запустить: a b\n", out)
        self.assertIn("вместе: a и b — docs/cli.md\n", out)
        self.assertIn("c — конфликт с a: файл x.py", out)

    def test_common_dir_is_whole_segment(self):
        p = self.project("## Рабочая копия\n\n- Общие: `docs/`\n")
        p.change("a", impact=["docs-old/cli.md"])
        p.change("b", impact=["docs-old/cli.md"])
        _, out = p.run()
        self.assertIn("b — конфликт с a: файл docs-old/cli.md", out)
        self.assertNotIn("вместе:", out)

    def test_doc_without_common(self):
        p = self.project()
        p.change("a", impact=["skills/spec-dispatch/SKILL.md"])
        p.change("b", impact=["skills/spec-dispatch/SKILL.md"])
        _, out = p.run()
        self.assertIn("запустить: a\n", out)
        self.assertIn("b — конфликт с a: файл skills/spec-dispatch/SKILL.md", out)

    def test_common_path_with_running(self):
        p = self.project("## Рабочая копия\n\n- Общие: `apps/desktop/scenarios/`\n")
        p.change("a", impact=["apps/desktop/scenarios/login.md"], claim=True)
        p.change("b", impact=["apps/desktop/scenarios/login.md"])
        _, out = p.run("--running", "a")
        self.assertIn("запустить: b\n", out)
        self.assertIn("вместе: b и a — apps/desktop/scenarios/login.md\n", out)

    def test_pair_with_several_paths_is_one_line(self):
        p = self.project("## Рабочая копия\n\n- Общие: `docs/`, `tests/stand.sh`\n")
        p.change("a", impact=["docs/a.md", "docs/b.md", "tests/stand.sh"])
        p.change("b", impact=["docs/b.md", "tests/stand.sh"])
        _, out = p.run()
        self.assertIn("вместе: a и b — docs/b.md, tests/stand.sh\n", out)
        self.assertEqual(out.count("вместе:"), 1)

    def test_common_value_that_is_not_a_file(self):
        p = self.project("## Рабочая копия\n\n- Общие: `Makefile`, `docs/`\n")
        p.change("a", impact=["Makefile", "docs/"])
        p.change("b", impact=["Makefile", "docs/"])
        _, out = p.run()
        self.assertIn("запустить: a b\n", out)
        self.assertIn("вместе: a и b — Makefile, docs/\n", out)

    def test_renamed_requirement(self):
        p = self.project()
        p.change("a", reqs=["Old"], cap="k")
        p.change("b", cap="k")
        put(p.main, "openspec/changes/b/specs/k/spec.md",
            "## RENAMED Requirements\n\n- FROM: `### Requirement: Old`\n- TO: `### Requirement: New`\n")
        p.commit()
        _, out = p.run()
        self.assertIn("b — конфликт с a: требование k/Old", out)

    def test_read_error(self):
        p = self.project()
        r = subprocess.run(["/usr/bin/python3", str(SCRIPT), str(p.main)], capture_output=True, text=True,
                           stdin=subprocess.DEVNULL)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(r.stderr)

    def test_read_project(self):
        p = self.project()
        p.archive("old")
        p.change("a", deps="old, none", impact=["x/y.py", "en", "AGENTS.md"], reqs=["R"], cap="cap", waiting=True)
        ch, arch, limit = dp.read_project(str(p.main))
        self.assertEqual(arch, {"old"})
        self.assertEqual(limit, 2)
        self.assertEqual(ch["a"]["deps"], ["old"])
        self.assertEqual(ch["a"]["files"], {"x/y.py"})
        self.assertEqual(ch["a"]["shared"], {"AGENTS.md"})
        self.assertEqual(ch["a"]["reqs"], {("cap", "R")})
        self.assertTrue(ch["a"]["waiting"] and not ch["a"]["claim"] and not ch["a"]["branch"])


def run_raw(main, *extra):
    r = subprocess.run(["/usr/bin/python3", str(SCRIPT), str(main)] + list(extra),
                       capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout, r.stderr


class UnknownDependency(Base):
    def spec(self, p, name):
        put(p.main, "openspec/specs/%s/spec.md" % name, "x\n")

    def test_spec_in_depends(self):
        p = self.project()
        self.spec(p, "cli-participants")
        p.change("fix-pin", deps="`cli-participants`")
        _, out = p.run()
        self.assertIn("запустить: нет", out)
        self.assertIn("fix-pin — неизвестная зависимость: cli-participants (это спека, не change)", out)
        _, out = p.run("--ignore-dep", "fix-pin:cli-participants")
        self.assertIn("запустить: fix-pin\n", out)

    def test_typo(self):
        p = self.project()
        p.change("add-words")
        p.change("add-top-words", deps="`add-wrods`")
        _, out = p.run()
        self.assertIn("add-top-words — неизвестная зависимость: add-wrods\n", out + "\n")
        self.assertNotIn("спека", out)
        self.assertNotIn("зависит от", out)

    def test_several_unknown_mark_each_spec(self):
        p = self.project()
        self.spec(p, "s1")
        self.spec(p, "s2")
        p.change("t", deps="`s1`, `typo`, `s2`")
        _, out = p.run()
        self.assertIn("t — неизвестная зависимость: s1 (это спека, не change), typo, s2 (это спека, не change)", out)

    def test_none_values_mean_no_dependencies(self):
        for v in ["нет", "Нет.", "None", "НЕТ:", "Нет, всё независимое", "-.", "-", "—", "none,",
                  "`нет`", "`None` — всё независимое", "- нет\n- -."]:
            with self.subTest(v=v):
                p = self.project()
                p.change("x", deps=v)
                code, out = p.run()
                self.assertEqual(code, 0)
                self.assertIn("запустить: x\n", out)
                self.assertNotIn("ждут", out)

    def test_parse_deps_none_position(self):
        self.assertEqual(dp.parse_deps(["none, old"]), [])
        self.assertEqual(dp.parse_deps(["old, none"]), ["old"])
        self.assertEqual(dp.parse_deps(["`none`, `old`"]), [])
        self.assertEqual(dp.parse_deps(["`old`, `нет`"]), ["old"])
        self.assertEqual(dp.parse_deps(["- нет", "- old"]), ["old"])
        self.assertEqual(dp.parse_deps(["Пояснение: foo"]), [])
        self.assertEqual(dp.parse_deps(["Пояснение: foo, bar"]), ["bar"])

    def test_none_word_before_backticks(self):
        for v in ("Нет (см. ниже): `old`", "Нет, `old`", "нет: `old`", "none `old`"):
            self.assertEqual(dp.parse_deps([v]), [], v)
        self.assertEqual(dp.parse_deps(["`add-words` — x"]), ["add-words"])
        self.assertEqual(dp.parse_deps(["`None` — всё независимое"]), [])
        self.assertEqual(dp.parse_deps(["см. `old`"]), ["old"])
        self.assertEqual(dp.parse_deps(["`..`"]), [".."])

    def test_empty_section(self):
        self.assertEqual(dp.parse_deps([]), [])

    def test_open_and_unknown_together(self):
        p = self.project()
        p.change("add-words")
        p.change("t", deps="`add-words`, `add-wrods`")
        _, out = p.run()
        self.assertIn("t — неизвестная зависимость: add-wrods; зависит от add-words\n", out + "\n")
        _, out = p.run("--ignore-dep", "t:add-wrods")
        self.assertIn("t — зависит от add-words", out)
        self.assertNotIn("неизвестная", out)

    def test_archived_dependency_is_known(self):
        p = self.project()
        p.archive("old")
        p.change("t", deps="`old`")
        _, out = p.run()
        self.assertIn("запустить: t\n", out)

    def test_ignore_only_own_change_and_name(self):
        p = self.project()
        p.change("a", deps="`ghost`, `other`")
        p.change("b", deps="`ghost`")
        for arg in ("zz:ghost", "b:other", "a:nope"):
            _, out = p.run("--ignore-dep", arg)
            self.assertIn("a — неизвестная зависимость", out, arg)
            self.assertIn("b — неизвестная зависимость: ghost", out, arg)
        _, out = p.run("--ignore-dep", "a:ghost", "--ignore-dep", "a:other")
        self.assertIn("запустить: a\n", out)
        self.assertIn("b — неизвестная зависимость: ghost", out)

    def test_ignore_dep_function(self):
        ch = {"a": {"deps": ["x", "y"]}, "b": {"deps": ["x"]}}
        out = dp.apply_ignores(ch, [("a", "x"), ("zz", "y")])
        self.assertEqual((out["a"]["deps"], out["b"]["deps"]), (["y"], ["x"]))
        self.assertEqual(ch["a"]["deps"], ["x", "y"])

    def test_shared_key_with_running(self):
        p = self.project()
        p.change("a", impact=["docs/architecture.md"], claim=True)
        p.change("b", impact=["docs/architecture.md"])
        _, out = p.run("--running", "a")
        self.assertIn("b — конфликт с a: файл docs/architecture.md", out)
        for val in ("docs/architecture.md", "/docs/architecture.md", "docs/"):
            _, out = p.run("--running", "a", "--shared", val)
            self.assertIn("запустить: b\n", out, val)
            self.assertIn("вместе: b и a — docs/architecture.md\n", out, val)

    def test_bad_keys(self):
        p = self.project()
        p.change("a")
        for args in (["--ignore-dep", "foo"], ["--ignore-dep", ":x"], ["--ignore-dep", "a:"],
                     ["--ignore-dep"], ["--shared", ""], ["--shared"]):
            with self.subTest(args=args):
                code, out, err = run_raw(p.main, *args)
                self.assertEqual(code, 2)
                self.assertIn("Запуск:", err)
                self.assertEqual(out, "")

    def test_dotdot_is_not_a_spec(self):
        p = self.project()
        self.spec(p, "real")
        p.change("t", deps="`..`")
        _, out = p.run()
        self.assertIn("t — неизвестная зависимость: ..", out)
        self.assertNotIn("(это спека", out)

    def test_spec_names(self):
        p = self.project()
        self.assertEqual(dp.spec_names(str(p.main)), set())
        self.spec(p, "s1")
        put(p.main, "openspec/specs/file.md", "x")
        self.assertEqual(dp.spec_names(str(p.main)), {"s1"})


class UncommittedChangeArtifacts(Base):
    def test_untracked_folder(self):
        p = self.project()
        p.change("a", commit=False)
        _, out = p.run()
        self.assertIn("запустить: нет\n", out)
        self.assertIn("\n  a — не закоммичен", out)
        self.assertNotIn("Артефакты вне git", out)

    def test_modified_after_commit(self):
        p = self.project()
        p.change("a", reqs=["R"])
        put(p.main, "openspec/changes/a/tasks.md", "- [ ] 1\n")
        git(p.main, "add", "-A")
        git(p.main, "commit", "-qm", "t")
        put(p.main, "openspec/changes/a/tasks.md", "- [x] 1\n")
        _, out = p.run()
        self.assertIn("\n  a — не закоммичен\n", out + "\n")
        self.assertIn("запустить: нет\n", out)

    def test_claim_priority(self):
        p = self.project()
        p.change("a", claim=True, commit=False)
        _, out = p.run()
        self.assertIn("\n  a — CLAIM", out)
        self.assertNotIn("не закоммичен", out)

    def test_waiting_priority(self):
        p = self.project()
        p.change("a", waiting=True, commit=False)
        _, out = p.run()
        self.assertIn("\n  a — WAITING", out)
        self.assertNotIn("не закоммичен", out)

    def test_branch_priority(self):
        p = self.project()
        git(p.main, "branch", "change/a")
        p.change("a", commit=False)
        _, out = p.run()
        self.assertIn("\n  a — не смёрджен: ветка change/a", out)
        self.assertNotIn("не закоммичен", out)

    def test_uncommitted_before_unarchived_dependency(self):
        p = self.project()
        p.change("a", deps="`base`", commit=False)
        _, out = p.run()
        self.assertIn("\n  a — не закоммичен", out)
        self.assertNotIn("зависит от", out)

    def test_openspec_ignored(self):
        p = self.project()
        put(p.main, ".gitignore", "openspec/\n")
        git(p.main, "add", "-A")
        git(p.main, "commit", "-qm", "ignore")
        p.change("a", commit=False)
        _, out = p.run()
        self.assertIn("запустить: a\n", out)
        self.assertIn("\nАртефакты вне git: openspec/", out)
        self.assertNotIn("не закоммичен", out)

    def test_only_agents_ignored(self):
        p = self.project()
        put(p.main, ".gitignore", "AGENTS.md\n")
        git(p.main, "add", "-A")
        git(p.main, "commit", "-qm", "ignore")
        put(p.main, "AGENTS.md", "# P\n")
        p.change("a", commit=False)
        _, out = p.run()
        self.assertIn("\n  a — не закоммичен", out)
        self.assertIn("\nАртефакты вне git: AGENTS.md\n", out)

    def test_nothing_ignored(self):
        p = self.project()
        p.change("a")
        _, out = p.run()
        self.assertIn("запустить: a", out)
        self.assertNotIn("Артефакты вне git", out)


IDS = ["c%d" % i for i in range(6)]
POOL_R = [("cap", "r1"), ("cap", "r2"), ("cap", "r3")]
POOL_F = ["a/x.py", "b/y.py", "c.md", "c.md.bak", "a-old/z.py"]
POOL_C = ["a/", "b/", "b/y.py", "c.md"]


class AbandonedClaims(Base):
    SID = "quietsid-0000-4000-8000-000000000000"

    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.state = self.home / ".claude/hook-state"
        self.state.mkdir(parents=True)
        self.p = self.project()

    def label(self, cid, body, hours=0):
        self.p.change(cid)
        claim = self.p.main / "openspec/changes" / cid / "CLAIM"
        claim.write_bytes(body if isinstance(body, bytes) else body.encode())
        t = time.time() - hours * 3600
        os.utime(claim, (t, t))
        return claim

    def session(self, suffix, minutes, sid=None):
        f = self.state / ("%s.%s" % (sid or self.SID, suffix))
        f.write_text("{}")
        t = time.time() - minutes * 60
        os.utime(f, (t, t))

    def why(self, cid):
        r = subprocess.run(["/usr/bin/python3", str(SCRIPT), str(self.p.main)], capture_output=True, text=True,
                           timeout=60, stdin=subprocess.DEVNULL, env=dict(os.environ, HOME=str(self.home)))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.out = r.stdout
        for ln in r.stdout.splitlines():
            if ln.startswith("  %s — " % cid):
                return ln.split(" — ", 1)[1]
        return None

    def test_silent_session(self):
        ids = ["c%d" % i for i in range(8)]
        claims = [self.label(c, "claude 2026-10-21 session=%s\n" % self.SID) for c in ids]
        self.session("json", 7 * 60 + 5)
        self.session("claims", 7 * 60 + 30)
        for c in ids:
            self.assertEqual(self.why(c), "CLAIM брошен: сессия quietsid молчит 7 ч")
        self.assertIn("запустить: нет\n", self.out)
        self.assertTrue(all(c.exists() for c in claims))

    def test_no_session_traces(self):
        self.label("a", "claude 2026-10-21 session=stalesid-0000\n", hours=3)
        self.assertEqual(self.why("a"), "CLAIM брошен: сессия stalesid молчит 3 ч")

    def test_live_session_one_fresh_file_is_enough(self):
        self.label("a", "claude 2026-10-21 session=%s\n" % self.SID, hours=9)
        self.session("json", 300)
        self.session("claims", 5)
        self.assertEqual(self.why("a"), "CLAIM")

    def test_claim_removed_change_is_granted(self):
        claim = self.label("a", "claude 2026-10-21 session=%s\n" % self.SID, hours=3)
        self.assertTrue(self.why("a").startswith("CLAIM брошен"))
        claim.unlink()
        self.assertIsNone(self.why("a"))
        self.assertIn("запустить: a\n", self.out)

    def test_branch_wins(self):
        self.label("a", "claude 2026-10-21 session=%s\n" % self.SID, hours=3)
        self.session("json", 180)
        git(self.p.main, "branch", "change/a")
        self.assertEqual(self.why("a"), "не смёрджен: ветка change/a")

    def test_label_without_session_id(self):
        self.label("old", "codex 2026-10-21\n", hours=13)
        self.label("new", "codex 2026-10-21\n", hours=11)
        self.assertEqual(self.why("old"), "CLAIM брошен: метка 13 ч")
        self.assertEqual(self.why("new"), "CLAIM")

    def test_binary_label(self):
        self.label("a", b"\xff\xfe\x00")
        self.assertEqual(self.why("a"), "CLAIM")

    def test_unreadable_label_is_not_abandoned(self):
        claim = self.label("a", "codex 2026-10-21\n", hours=13)
        claim.chmod(0)
        self.addCleanup(claim.chmod, 0o644)
        self.assertEqual(self.why("a"), "CLAIM")

    def test_unreadable_state_is_not_abandoned(self):
        self.label("a", "claude 2026-10-21 session=%s\n" % self.SID, hours=3)
        self.state.chmod(0)
        self.addCleanup(self.state.chmod, 0o755)
        self.assertEqual(self.why("a"), "CLAIM")


@st.composite
def projects(draw):
    n = draw(st.integers(1, 6))
    ids = IDS[:n]
    archived = {"z0", "z1"}
    common = set(draw(st.lists(st.sampled_from(POOL_C), max_size=3)))
    changes = {}
    for cid in ids:
        impact = set(draw(st.lists(st.sampled_from(POOL_F), max_size=3)))
        changes[cid] = {
            "claim": draw(st.booleans()) and draw(st.booleans()),
            "waiting": draw(st.booleans()) and draw(st.booleans()),
            "branch": draw(st.booleans()) and draw(st.booleans()),
            "uncommitted": draw(st.booleans()) and draw(st.booleans()),
            "deps": draw(st.lists(st.sampled_from(IDS + ["z0", "z1"]), max_size=3, unique=True)),
            "reqs": set(draw(st.lists(st.sampled_from(POOL_R), max_size=2))),
            "impact": impact,
            "files": {f for f in impact if not dp.is_common(f, common)},
            "shared": {f for f in impact if dp.is_common(f, common)},
        }
    running = draw(st.lists(st.sampled_from(ids), unique=True, max_size=2))
    return changes, archived, draw(st.integers(1, 4)), running, common


def chain():
    ch = {c: dict(claim=False, waiting=False, branch=False, deps=[], reqs=set(), files=set(), shared=set())
          for c in IDS[:5]}
    for i in range(1, 5):
        ch[IDS[i]]["deps"] = [IDS[i - 1]]
    ch[IDS[0]]["deps"] = [IDS[4]]
    return ch


class Property(unittest.TestCase):
    @settings(max_examples=200, deadline=None)
    @given(projects())
    def test_ready_changes_and_waves_property(self, data):
        changes, archived, limit, running, common = data
        granted, waits = dp.plan(changes, archived, limit, running)

        def is_shared(f):
            return f in common or any(p.endswith("/") and f.startswith(p) for p in common)

        def hard(c):
            return {f for f in changes[c]["impact"] if not is_shared(f)}

        for f in POOL_F:
            self.assertEqual(dp.is_common(f, common), is_shared(f), f)
        for cid, why in waits:
            if "файл " in why:
                self.assertFalse(is_shared(why.rsplit("файл ", 1)[1]), why)
        expected = []
        for i, a in enumerate(granted):
            self.assertFalse(changes[a]["claim"] or changes[a]["waiting"] or changes[a]["branch"]
                             or changes[a]["uncommitted"])
            self.assertTrue(all(d in archived for d in changes[a]["deps"]))
            for b in granted[i + 1:] + running:
                self.assertFalse(changes[a]["reqs"] & changes[b]["reqs"])
                self.assertFalse(hard(a) & hard(b))
                paths = sorted(f for f in changes[a]["impact"] & changes[b]["impact"] if is_shared(f))
                if paths:
                    expected.append("вместе: %s и %s — %s" % (a, b, ", ".join(paths)))
        out = dp.render(granted, waits, limit, running, dp.together(changes, granted, running))
        self.assertEqual(sorted(ln for ln in out.splitlines() if ln.startswith("вместе:")), sorted(expected))
        self.assertLessEqual(len(granted), max(0, limit - len(running)))
        free = [c for c in changes if c not in running and not (changes[c]["claim"] or changes[c]["waiting"]
                or changes[c]["branch"] or changes[c]["uncommitted"]) and all(d in archived for d in changes[c]["deps"])
                and not any(changes[c]["reqs"] & changes[r]["reqs"] or hard(c) & hard(r)
                            for r in running)]
        if free and limit - len(running) > 0:
            self.assertTrue(granted)
        self.assertEqual(sorted(granted + [w[0] for w in waits] + running), sorted(changes))

    @settings(max_examples=200, deadline=None)
    @given(projects())
    def test_uncommitted_change_artifacts_property(self, data):
        changes, archived, limit, running, _ = data
        granted, waits = dp.plan(changes, archived, limit, running)
        why = dict(waits)
        for cid, c in changes.items():
            if not c["uncommitted"]:
                continue
            self.assertNotIn(cid, granted)
            if not (c["claim"] or c["waiting"] or c["branch"]) and cid not in running:
                self.assertEqual(why[cid], "не закоммичен")

    @settings(max_examples=120, deadline=None)
    @given(st.booleans(), st.sampled_from([None, 0, 59, 60, 61]), st.sampled_from([None, 0, 59, 60, 61]),
           st.sampled_from([11, 12, 13]), st.booleans(), st.booleans())
    def test_abandoned_claims_property(self, with_id, json_age, claims_age, label_age, branch, waiting):
        now = 2000000000
        p = Project()
        home = tempfile.mkdtemp()
        try:
            p.change("a", waiting=waiting)
            body = "claude 2026-10-21 session=stalesid-0000\n" if with_id else "codex 2026-10-21\n"
            claim = p.main / "openspec/changes/a/CLAIM"
            claim.write_text(body, encoding="utf-8")
            os.utime(claim, (now - label_age * 3600,) * 2)
            for suffix, age in (("json", json_age), ("claims", claims_age)):
                if age is not None:
                    f = pathlib.Path(home, "stalesid-0000." + suffix)
                    f.write_text("{}")
                    os.utime(f, (now - age * 60,) * 2)
            if branch:
                git(p.main, "branch", "change/a")
            with mock.patch.object(dp, "STATE", home), mock.patch.object(dp.time, "time", return_value=now):
                changes, archived, limit = dp.read_project(str(p.main))
            granted, waits = dp.plan(changes, archived, limit)
            self.assertEqual(claim.read_text(encoding="utf-8"), body)
            self.assertEqual(granted, [])
            marks = [a for a in (json_age, claims_age) if a is not None]
            if branch:
                want = "не смёрджен: ветка change/a"
            elif not with_id:
                want = "CLAIM брошен: метка %d ч" % label_age if label_age >= 12 else "CLAIM"
            elif not marks:
                want = "CLAIM брошен: сессия stalesid молчит %d ч" % label_age
            else:
                want = "CLAIM брошен: сессия stalesid молчит 1 ч" if min(marks) >= 60 else "CLAIM"
            self.assertEqual(dict(waits)["a"], want)
        finally:
            p.close()
            shutil.rmtree(home, ignore_errors=True)

    @settings(max_examples=300, deadline=None)
    @example(deps=["op-a", "ar-a", "sp-a", "no-a"], own=[], other=[])
    @given(st.lists(st.sampled_from(["op-a", "op-b", "ar-a", "ar-b", "sp-a", "sp-b", "no-a", "no-b"]),
                    max_size=6, unique=True),
           st.lists(st.sampled_from(["op-a", "ar-a", "sp-a", "sp-b", "no-a", "no-b"]), max_size=4, unique=True),
           st.lists(st.sampled_from(["op-a", "ar-a", "sp-a", "sp-b", "no-a", "no-b"]), max_size=4, unique=True))
    def test_unknown_dependency_property(self, deps, own, other):
        def mk(d):
            return dict(claim=False, waiting=False, branch=False, uncommitted=False, deps=list(d),
                        reqs=set(), files=set(), shared=set())
        changes = {"t": mk(deps), "op-a": mk([]), "op-b": mk([]), "o": mk(other)}
        archived, specs = {"ar-a", "ar-b"}, {"sp-a", "sp-b"}
        pairs = [("t", n) for n in own] + [("o", n) for n in other] + [("zz", n) for n in own]
        granted, waits = dp.plan(dp.apply_ignores(changes, pairs), archived, 10, specs=specs)
        left = [d for d in deps if d not in own and d not in archived]
        unknown = [d for d in left if not d.startswith("op-")]
        why = dict(waits).get("t")
        if not left:
            self.assertIn("t", granted)
            return
        self.assertNotIn("t", granted)
        parts = why.split("; ")
        seen_unknown, seen_open = [], []
        for part in parts:
            if part.startswith("неизвестная зависимость: "):
                for item in part[len("неизвестная зависимость: "):].replace(" (это спека, не change)", "*").split(", "):
                    name = item.rstrip("*")
                    self.assertNotIn(name, changes)
                    self.assertNotIn(name, archived)
                    self.assertEqual(item != name, name in specs, item)
                    seen_unknown.append(name)
            else:
                self.assertTrue(part.startswith("зависит от "), why)
                seen_open = part[len("зависит от "):].split(", ")
                for name in seen_open:
                    self.assertIn(name, changes)
        self.assertEqual(sorted(seen_unknown), sorted(unknown))
        self.assertEqual(sorted(seen_open), sorted(d for d in left if d.startswith("op-")))
        if unknown:
            self.assertTrue(why.startswith("неизвестная зависимость: "), why)

    def test_cycle_and_chain_terminate(self):
        granted, waits = dp.plan(chain(), set(), 4)
        self.assertEqual(granted, [])
        self.assertEqual(len(waits), 5)


if __name__ == "__main__":
    unittest.main()
