"""Change integration-skills: the skills/<skill>/SKILL.md of an owner integration laid out into every chosen agent's
skill root, shown as integration:<name> status rows, refused when taken or hostile, and removed with their source."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from hypothesis import given, settings as hsettings, strategies as st


REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import layout  # noqa: E402

AGENTS = ["claude", "codex", "other"]
ROOTS = (".claude/skills", ".codex/skills", ".agents/skills")
SHIP = "solo-sdd ship\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.repo = os.path.join(self.tmp, "repo")
        for d in (".claude", ".codex"):
            os.makedirs(os.path.join(self.home, d))
        self.put(self.repo, "skills/ship/SKILL.md", SHIP)
        self.put(self.repo, "targets.json", json.dumps({"skills": {"ship": ["other", "codex", "claude"]}, "files": {}}))
        data = os.path.join(self.home, ".local", "share", "solo-sdd")
        patch = mock.patch.multiple(layout, REPO=self.repo, HOME=self.home, DATA=data,
                                    STATE=os.path.join(data, "state.json"))
        patch.start()
        self.addCleanup(patch.stop)
        self.owner = os.path.join(data, "integrations")

    @staticmethod
    def put(base, rel, text):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb" if isinstance(text, bytes) else "w", encoding=None if isinstance(text, bytes) else "utf-8") as f:
            f.write(text)
        return path

    def integration(self, name, skills=None, description=None):
        self.put(self.owner, name + "/integration",
                 description or "name: %s\nabout: test skills\npoints: checks\ncommand: true\n" % name)
        for skill, text in (skills or {}).items():
            self.put(self.owner, "%s/skills/%s/SKILL.md" % (name, skill), text)

    def copy(self, root, skill):
        return os.path.join(self.home, root, skill, "SKILL.md")

    def text(self, path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def call(self, fn, *args, **kw):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = fn(*args, **kw)
        return code, out.getvalue()

    def install(self):
        return self.call(layout.push, agents=AGENTS)

    def update(self):
        return self.call(layout.push)

    def rows(self):
        """[(kind, name, path)] of solo-sdd status."""
        rows = self.call(layout.status)[0]
        return [(k, n, layout.short(t)) for k, n, t in rows]


class IntegrationSkillsLaidOut(Base):
    def test_integration_skills_laid_out_reaches_every_agent(self):
        self.integration("dup-scan", {"dup-scan-review": "review v1\n"})
        self.assertEqual(self.install()[0], 0)
        for root in ROOTS:
            self.assertEqual(self.text(self.copy(root, "dup-scan-review")), "review v1\n", root)
        self.integration("dup-scan", {"dup-scan-review": "review v2\n"})
        self.assertEqual(self.update()[0], 0)
        for root in ROOTS:
            self.assertEqual(self.text(self.copy(root, "dup-scan-review")), "review v2\n", root)

    def test_integration_skills_laid_out_edited_copy_is_drift(self):
        self.integration("dup-scan", {"dup-scan-review": "review v1\n"})
        self.install()
        edited = self.copy(".claude/skills", "dup-scan-review")
        with open(edited, "w") as f:
            f.write("my edit\n")
        self.integration("dup-scan", {"dup-scan-review": "review v2\n"})
        code, out = self.update()
        self.assertEqual(code, 1)
        self.assertEqual(self.text(edited), "my edit\n")
        self.assertIn("integration:dup-scan", out)
        self.assertIn(("drift", "integration:dup-scan", "~/.claude/skills/dup-scan-review/SKILL.md"), self.rows())
        self.assertEqual(self.text(self.copy(".codex/skills", "dup-scan-review")), "review v2\n")

    def test_integration_skills_laid_out_not_from_a_broken_integration(self):
        self.integration("dup-scan", {"dup-scan-review": "review\n"}, "name: dup-scan\npoints: nowhere\n")
        code, out = self.install()
        self.assertEqual(code, 1)
        self.assertIn("integration:dup-scan", out)
        self.assertIn("integrations/dup-scan/integration", out)
        self.assertFalse(any(os.path.lexists(self.copy(r, "dup-scan-review")) for r in ROOTS))
        self.assertEqual(self.text(self.copy(".claude/skills", "ship")), SHIP)

    def test_integration_skills_laid_out_only_to_chosen_agents(self):
        self.integration("dup-scan", {"dup-scan-review": "review\n"})
        self.install()
        self.assertEqual(self.call(layout.push, agents=["claude", "other"])[0], 0)
        self.assertFalse(os.path.lexists(self.copy(".codex/skills", "dup-scan-review")))
        self.assertTrue(os.path.exists(self.copy(".claude/skills", "dup-scan-review")))


class IntegrationSkillStatusRows(Base):
    def test_integration_skill_status_rows(self):
        self.integration("dup-scan", {"dup-scan-review": "review\n"})
        self.install()
        rows = [r for r in self.rows() if r[1] == "integration:dup-scan"]
        self.assertEqual(sorted(rows), sorted(("ok", "integration:dup-scan", "~/%s/dup-scan-review/SKILL.md" % r)
                                              for r in ROOTS))
        out = self.call(layout.status)[1]
        self.assertIn("ok integration:dup-scan", " ".join(out.split()))


class SkillNameTaken(Base):
    def test_skill_name_taken_by_solo_sdd(self):
        self.integration("dup-scan", {"ship": "hijack\n", "dup-scan-review": "review\n"})
        code, out = self.install()
        self.assertEqual(code, 1)
        self.assertIn("the name ship is taken by solo-sdd", out)
        for root in ROOTS:
            self.assertEqual(self.text(self.copy(root, "ship")), SHIP)
            self.assertEqual(self.text(self.copy(root, "dup-scan-review")), "review\n")

    def test_skill_name_taken_by_an_earlier_integration(self):
        self.integration("alpha", {"common": "alpha\n"})
        self.integration("beta", {"common": "beta\n", "beta-own": "own\n"})
        code, out = self.install()
        self.assertEqual(code, 1)
        self.assertIn("integrations/beta/skills/common: the name common is taken by integration alpha", out)
        for root in ROOTS:
            self.assertEqual(self.text(self.copy(root, "common")), "alpha\n")
            self.assertEqual(self.text(self.copy(root, "beta-own")), "own\n")

    def test_skill_name_taken_refuses_hostile_skills(self):
        outside = os.path.join(self.tmp, "outside")
        self.put(outside, "evil/SKILL.md", "outside\n")
        cases = {
            "Upper": ("not a skill name", None),
            "-lead": ("not a skill name", None),
            "a..b": ("not a skill name", None),
            "linked-file": ("a link", lambda p: os.symlink(os.path.join(outside, "evil/SKILL.md"), os.path.join(p, "SKILL.md"))),
            "linked-folder": ("a link", lambda p: (os.rmdir(p), os.symlink(os.path.join(outside, "evil"), p))),
            "no-file": ("No such file", lambda p: None),
            "too-big": ("larger than", lambda p: self.put(p, "SKILL.md", "x" * (layout.SKILL_MAX_BYTES + 1))),
            "not-utf8": ("not UTF-8", lambda p: self.put(p, "SKILL.md", b"\xff\xfe")),
        }
        for name, (reason, make) in cases.items():
            with self.subTest(name):
                shutil.rmtree(self.owner, True)
                self.integration("dup-scan", {"fine": "fine\n"})
                folder = os.path.join(self.owner, "dup-scan/skills", name)
                os.makedirs(folder)
                if make is None:
                    self.put(folder, "SKILL.md", "named badly\n")
                else:
                    make(folder)
                code, out = self.install()
                self.assertEqual(code, 1, out)
                line = [ln for ln in out.splitlines() if "skills/" + ascii(name).strip("'") in ln or name in ln]
                self.assertTrue(line and reason in line[0], out)
                for root in ROOTS:
                    self.assertFalse(os.path.lexists(self.copy(root, name)), (name, root))
                    self.assertEqual(self.text(self.copy(root, "fine")), "fine\n")
                shutil.rmtree(folder, True) if not os.path.islink(folder) else os.remove(folder)

    def test_skill_name_taken_refuses_a_linked_skills_folder(self):
        outside = os.path.join(self.tmp, "outside")
        self.put(outside, "evil/SKILL.md", "outside\n")
        self.integration("dup-scan")
        os.symlink(outside, os.path.join(self.owner, "dup-scan", "skills"))
        code, out = self.install()
        self.assertEqual(code, 1)
        self.assertIn("dup-scan/skills: a link or not a folder", out)
        self.assertFalse(any(os.path.lexists(self.copy(r, "evil")) for r in ROOTS))


class IntegrationSkillsRemovedWithTheirSource(Base):
    def snapshot(self):
        out = {}
        for d, _, files in os.walk(self.home):
            if "/.local/share/solo-sdd" in d:
                continue
            for f in files:
                p = os.path.join(d, f)
                out[p] = (self.text(p), os.stat(p).st_mtime_ns)
        return out

    def test_integration_skills_removed_with_their_source_folder_deleted(self):
        self.integration("dup-scan", {"dup-scan-review": "review\n"})
        self.integration("keep", {"keep-skill": "kept\n"})
        self.install()
        edited = self.copy(".claude/skills", "dup-scan-review")
        with open(edited, "w") as f:
            f.write("my edit\n")
        others = {p: v for p, v in self.snapshot().items() if "dup-scan-review" not in p}
        shutil.rmtree(os.path.join(self.owner, "dup-scan"))
        code, out = self.update()
        for root in (".codex/skills", ".agents/skills"):
            self.assertFalse(os.path.lexists(os.path.dirname(self.copy(root, "dup-scan-review"))), root)
            self.assertIn("removed integration:dup-scan", " ".join(out.split()))
            self.assertIn("~/%s/dup-scan-review/SKILL.md" % root, out)
        self.assertEqual(self.text(edited), "my edit\n")
        self.assertIn("~/.claude/skills/dup-scan-review/SKILL.md — drift", out)
        self.assertEqual(code, 0)
        after = self.snapshot()
        self.assertEqual({p: v for p, v in after.items() if "dup-scan-review" not in p}, others)
        state = layout.load_state()
        self.assertEqual(sorted(k for k, v in state[layout.SKILLS].items() if v == "integration:dup-scan"),
                         ["~/.claude/skills/dup-scan-review/SKILL.md"])
        self.assertEqual(self.update()[1].count("removed"), 0)

    def fresh(self):
        shutil.rmtree(self.home, True)
        for d in (".claude", ".codex"):
            os.makedirs(os.path.join(self.home, d))

    @unittest.skipIf(os.geteuid() == 0, "root reads a closed file")
    def test_integration_skills_removed_with_their_source_not_when_unreadable(self):
        folders = ("", "dup-scan", "dup-scan/skills")
        cases = [(rel, mode) for rel in folders for mode in (0, 0o444, 0o111)]
        cases += [(rel, mode) for rel in ("dup-scan/integration", "dup-scan/skills/dup-scan-review/SKILL.md")
                  for mode in (0, 0o111)]
        for rel, mode in cases:
            with self.subTest(rel=rel or "the owner source", mode=oct(mode)):
                self.fresh()
                self.integration("dup-scan", {"dup-scan-review": "review\n"})
                self.install()
                closed = os.path.join(self.owner, rel) if rel else self.owner
                os.chmod(closed, mode)
                try:
                    code, out = self.update()
                finally:
                    os.chmod(closed, 0o755)
                self.assertNotIn("removed", out)
                if (rel, mode) != ("dup-scan", 0o111):  # a folder that can be entered is read as usual
                    self.assertEqual(code, 1, out)
                    self.assertIn("Permission denied", out)
                for root in ROOTS:
                    self.assertEqual(self.text(self.copy(root, "dup-scan-review")), "review\n", root)

    @unittest.skipIf(os.geteuid() == 0, "root reads a closed file")
    def test_integration_skills_removed_with_their_source_held_names_stay_reserved(self):
        for rel in ("alpha", "alpha/skills/common/SKILL.md"):
            with self.subTest(rel):
                self.fresh()
                self.integration("alpha", {"common": "alpha\n"})
                self.install()
                self.integration("beta", {"common": "beta\n"})
                os.chmod(os.path.join(self.owner, rel), 0)
                try:
                    code, out = self.update()
                finally:
                    os.chmod(os.path.join(self.owner, rel), 0o755)
                self.assertIn("the name common is taken by integration alpha", out)
                for root in ROOTS:
                    self.assertEqual(self.text(self.copy(root, "common")), "alpha\n", root)

    def test_integration_skills_removed_with_their_source_a_link_is_not_a_closed_source(self):
        self.integration("dup-scan", {"dup-scan-review": "review\n"})
        self.install()
        target = self.put(self.tmp, "a-file", "not a folder\n")
        shutil.rmtree(os.path.join(self.owner, "dup-scan"))
        os.symlink(target, os.path.join(self.owner, "dup-scan"))
        code, out = self.update()
        self.assertEqual(out.count("its integration skill is gone"), 3, out)
        self.assertFalse(any(os.path.lexists(self.copy(r, "dup-scan-review")) for r in ROOTS))

    def test_integration_skills_removed_with_their_source_skips_mapped_paths(self):
        self.integration("dup-scan", {"later": "integration\n"})
        self.install()
        shutil.rmtree(os.path.join(self.owner, "dup-scan"))
        self.put(self.repo, "skills/later/SKILL.md", "solo-sdd later\n")
        self.put(self.repo, "targets.json", json.dumps(
            {"skills": {"ship": ["other", "codex", "claude"], "later": ["other", "codex", "claude"]}, "files": {}}))
        code, out = self.update()
        self.assertNotIn("removed", out)
        for root in ROOTS:
            self.assertEqual(self.text(self.copy(root, "later")), "solo-sdd later\n")
        self.assertNotIn(layout.SKILLS, layout.load_state())

    def test_integration_skills_removed_by_uninstall(self):
        self.integration("dup-scan", {"dup-scan-review": "review\n"})
        self.install()
        shutil.rmtree(os.path.join(self.owner, "dup-scan"))
        code, out = self.call(layout.uninstall)
        self.assertEqual(code, 0)
        self.assertFalse(any(os.path.lexists(self.copy(r, "dup-scan-review")) for r in ROOTS))
        self.assertNotIn(layout.SKILLS, layout.load_state())

    OPS = st.lists(st.tuples(st.sampled_from(["add", "delete-skill", "delete-integration", "edit", "update"]),
                             st.sampled_from(["i1", "i2", "i3"]), st.sampled_from(["s1", "s2", "ship"]),
                             st.sampled_from(ROOTS)), max_size=14)

    @hsettings(max_examples=150, deadline=None)
    @given(OPS)
    def test_integration_skills_removed_with_their_source_property(self, ops):
        shutil.rmtree(self.home, True)
        for d in (".claude", ".codex"):
            os.makedirs(os.path.join(self.home, d))
        # a copy an earlier solo-sdd version laid out and the map no longer names: no integration's to remove
        old = self.put(self.home, ".agents/skills/old/SKILL.md", "old\n")
        self.call(layout.push, agents=AGENTS)
        state = layout.load_state()
        state["~/.agents/skills/old/SKILL.md"] = layout.digest("old\n")
        layout.save_state(state)
        have, edited, n = {}, {}, 0  # have: integration -> {skill: text}; edited: copy path -> text
        for op, integ, skill, root in ops:
            n += 1
            if op == "add":
                have.setdefault(integ, {})[skill] = "%s %s %d\n" % (integ, skill, n)
                self.integration(integ, have[integ])
            elif op == "delete-skill" and skill in have.get(integ, {}):
                del have[integ][skill]
                shutil.rmtree(os.path.join(self.owner, integ, "skills", skill))
            elif op == "delete-integration" and integ in have:
                del have[integ]
                shutil.rmtree(os.path.join(self.owner, integ))
            elif op == "edit" and skill != "ship" and os.path.exists(self.copy(root, skill)):
                edited[self.copy(root, skill)] = "edit %d\n" % n
                with open(self.copy(root, skill), "w") as f:
                    f.write(edited[self.copy(root, skill)])
            elif op == "update":
                self.update()
        self.update()
        owner = {}
        for integ in sorted(have):
            for skill, text in have[integ].items():
                owner.setdefault(skill, text)
        for skill in ("s1", "s2"):
            for root in ROOTS:
                path = self.copy(root, skill)
                want = edited.get(path, owner.get(skill))
                self.assertEqual(self.text(path) if os.path.exists(path) else None, want, (path, ops))
        for root in ROOTS:
            self.assertEqual(self.text(self.copy(root, "ship")), SHIP)
        self.assertEqual(self.text(old) if os.path.exists(old) else None, "old\n")
        before = self.snapshot()
        self.update()
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
