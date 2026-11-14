"""Public tree: no owner traces, only installable code, the license and the entry README."""
import json
import os
import pathlib
import re
import subprocess
import tempfile
import unittest
import marks

from hypothesis import given, settings, strategies as st

REPO = pathlib.Path(__file__).resolve().parents[1]

# placeholders <user>, <name> do not match the character class; you is excluded explicitly
HOME_RE = re.compile(r"/(?:Users|home)/(?!you/)[A-Za-z0-9_.-]+/")
SESSION_RE = re.compile(r"(?:session=|session )[0-9a-f]{8,}", re.I)
CLONE_RE = re.compile(r"(?:Desktop|Code/tools/sdd)/solo-sdd")
CLONE_SCOPE = ("skills/", "global/", "templates/", "scripts/")
CLONE_FILES = ("ALGORITHM.md", "README.md")
SKIP_PREFIXES = ("solo-sdd/",)
SPECS = "solo-sdd/specs/"  # main specs: only the local list (history under solo-sdd/changes/ stays unchecked)
# a skill named in backquotes: `/name`, `plugin:name` or a hyphenated `name`, each maybe with arguments
REF_RE = re.compile(r"`(/?)([a-z][a-z0-9]*(?:-[a-z0-9]+)*)(:[a-z0-9-]+)?(?: [^`]*)?`")
REF_TEXTS = ("ALGORITHM.md", "global/AGENTS.md")
# backquoted hyphenated words of the shipped texts that are not skills
NOT_SKILLS = {
    "solo-sdd", "land-local", "add-csv",  # the CLI and its subcommands
    "read-only", "workspace-write", "/worktree", "/effort",  # Codex sandbox modes, Codex and Claude Code commands
    "fast-check", "mcp-server", "orchestrator-status",  # a library, an example capability, a capability
    "antislop", "file",  # `antislop:start` marker, `file:line`
}
SKIP_FILES = ("docs/waiting.md", "tests/test_public_tree.py")
# a cited work with a date and no address on the line: the citation gives way to the idea itself
CITE_RE = re.compile(r"(?<![\w-])(?:article|talk|paper|post)s?(?![\w-])", re.I)
DATE_RE = re.compile(r"(?<!\d)(?:\d{1,2}\.\d{1,2}\.\d{4}|\d{4}-\d{2}-\d{2})(?!\d)")
CITE_TEXTS = ("README.md", "ALGORITHM.md", "global/AGENTS.md")
# \xXX, \uXXXX, \UXXXXXXXX: a trace written with escapes in a literal is matched like plain text
ESC_RE = re.compile(r"\\(?:x([0-9a-fA-F]{2})|u([0-9a-fA-F]{4})|U([0-9a-fA-F]{8}))")


def unescape(line):
    def ch(m):
        n = int(m.group(1) or m.group(2) or m.group(3), 16)
        return chr(n) if n <= 0x10FFFF else m.group()
    return ESC_RE.sub(ch, line)


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL).stdout


def find_in_line(line, deny_regexes, clone=False, deny_only=False):
    """Fragments found in one line (not the whole line: lines can be 100 KB)."""
    line = unescape(line)
    rxs = list(deny_regexes) if deny_only else [HOME_RE, SESSION_RE, *deny_regexes] + ([CLONE_RE] if clone else [])
    return [m.group() for rx in rxs for m in rx.finditer(line)]


def load_denylist(root):
    common = git(root, "rev-parse", "--git-common-dir").strip()
    path = os.path.join(root, common, "info", "public-denylist.txt")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", errors="ignore") as f:
        words = [w.strip() for w in f.read().splitlines() if w.strip()]
    return [re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)", re.I) for w in words]


def scan(root):
    root = str(root)
    deny = load_denylist(root)
    found = []
    for rel in git(root, "ls-files", "-z").split("\0"):
        specs = rel.startswith(SPECS)
        if not rel or (rel.startswith(SKIP_PREFIXES) and not specs) or rel in SKIP_FILES:
            continue
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        with open(full, "rb") as f:
            text = f.read().decode("utf-8", errors="ignore")
        clone = rel.startswith(CLONE_SCOPE) or rel in CLONE_FILES
        for n, line in enumerate(text.splitlines(), 1):
            for frag in find_in_line(line, deny, clone, deny_only=specs):
                found.append(f"{rel}:{n}: {frag}")
    return found


def tracked_archive(root):
    """`tracked: <path>` for each path under solo-sdd/changes/archive/ that git tracks (the archive stays out of git)."""
    return ["tracked: " + p for p in git(str(root), "ls-files", "-z", "--", "solo-sdd/changes/archive").split("\0") if p]


def optional_tools(root, text=None):
    """Words before the colon or dash of each bullet in the README optional tools list."""
    path = os.path.join(root, "README.md")
    if text is None:
        text = pathlib.Path(path).read_text(encoding="utf-8") if os.path.exists(path) else ""
    part = text.split("Some skills use extra tools", 1)[-1].split("\n## ", 1)[0] if "Some skills use extra tools" in text else ""
    words = set()
    for line in part.splitlines():
        if line.startswith("- "):
            words |= set(re.findall(r"[a-z][a-z0-9-]*", re.split(r":| — ", line[2:], 1)[0].lower()))
    return words


def skill_refs(root):
    """Skills the shipped texts name that are neither tracked in skills/ nor optional tools."""
    root = str(root)
    tracked = git(root, "ls-files", "skills").split("\n")
    shipped = {p.split("/")[1] for p in tracked if p.count("/") >= 2}
    known = shipped | optional_tools(root)
    texts = [p for p in tracked if re.fullmatch(r"skills/[^/]+/SKILL\.md", p)]
    texts += [p for p in REF_TEXTS if git(root, "ls-files", p).strip()]
    found = []
    for rel in texts:
        with open(os.path.join(root, rel), encoding="utf-8", errors="ignore") as f:
            found += refs_in(rel, f.read(), known)
    return found


def refs_in(rel, text, known):
    """`rel:line: name` for each skill named in `text` that is not in `known`."""
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in REF_RE.finditer(line):
            slash, name = m.group(1), m.group(2)
            if not (slash or m.group(3) or "-" in name) or slash + name in NOT_SKILLS or name in known:
                continue
            found.append(f"{rel}:{n}: {slash}{name}")
    return found


def unsourced_citations(root):
    """`rel:line` for each line of the rules and skills that cites a dated work without an http address."""
    root = str(root)
    texts = [p for p in git(root, "ls-files", "skills").split("\n") if re.fullmatch(r"skills/[^/]+/SKILL\.md", p)]
    texts += [p for p in CITE_TEXTS if git(root, "ls-files", p).strip()]
    found = []
    for rel in sorted(texts):
        with open(os.path.join(root, rel), encoding="utf-8", errors="ignore") as f:
            for n, line in enumerate(f.read().splitlines(), 1):
                if CITE_RE.search(line) and DATE_RE.search(line) and "http" not in line:
                    found.append(f"{rel}:{n}")
    return found


class TempRepo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name
        git(self.root, "init", "-q")

    def put(self, rel, text):
        p = pathlib.Path(self.root, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        git(self.root, "add", "-f", rel)

    def deny(self, *words):
        p = pathlib.Path(self.root, ".git", "info")
        p.mkdir(parents=True, exist_ok=True)
        (p / "public-denylist.txt").write_text("\n".join(words) + "\n", encoding="utf-8")


class TestScan(TempRepo):
    def test_clean_tree_is_empty(self):
        self.put("README.md", "cd /Users/<user>/x and /home/you/y\n")
        self.deny("Zeta")
        self.assertEqual(scan(self.root), [])

    def test_forgotten_path_found(self):
        self.put("README.md", "first\ncd /Users/realname/x\n")
        res = scan(self.root)
        self.assertEqual(len(res), 1)
        self.assertIn("README.md:2", res[0])
        self.assertIn("/Users/realname/", res[0])

    def test_session_id_found(self):
        self.put("a.md", "session=abcdef12\n")
        self.put("b.md", "session ABCDEF12 here\n")
        res = scan(self.root)
        self.assertTrue(any(r.startswith("a.md:1") for r in res), res)
        self.assertTrue(any(r.startswith("b.md:1") for r in res), res)

    def test_no_denylist_still_finds_path(self):
        self.put("README.md", "ok\n/home/bob/x\n")
        self.assertFalse(os.path.exists(os.path.join(self.root, ".git", "info", "public-denylist.txt")))
        self.assertEqual(len(scan(self.root)), 1)

    def test_denylist_case_insensitive(self):
        self.deny("Secret")
        self.put("a.md", "here SECRET word\n")
        res = scan(self.root)
        self.assertEqual(len(res), 1)
        self.assertIn("a.md:1", res[0])

    def test_unpublished_paths_skipped(self):
        self.deny("secret")
        self.put("solo-sdd/x.md", "secret /Users/real/\n")
        self.put("docs/waiting.md", "secret\n")
        self.assertEqual(scan(self.root), [])

    def test_escaped_traces(self):
        """Requirement: Escaped traces. An escaped denylisted word and an escaped home path are found."""
        self.deny("Rok")
        self.put("a.py", "x = '\\u0052ok'\n")
        self.put("b.py", "y = '/Users/\\u0061nna/'\n")
        self.put("c.py", "z = '\\U00110000 \\u0052ok'\n")  # out of range: kept raw, the scan goes on
        res = scan(self.root)
        self.assertEqual(res, ["a.py:1: Rok", "b.py:1: /Users/anna/", "c.py:1: Rok"])

    def test_word_inside_word(self):
        self.deny("Rok")
        self.put("a.md", "the broken one\n")
        self.assertEqual(scan(self.root), [])
        self.put("b.md", "here Rok\n")
        self.put("c.md", ".rok-notes\n")
        res = scan(self.root)
        self.assertEqual(len(res), 2, res)

    def test_empty_denylist_line_no_findings(self):
        self.deny("", "  ")
        self.put("a.md", "any text\n")
        self.assertEqual(scan(self.root), [])

    def test_clone_path_in_skill_found(self):
        self.put("skills/project-init/SKILL.md", "see ~/Code/tools/sdd/solo-sdd/templates/\n")
        res = scan(self.root)
        self.assertEqual(len(res), 1, res)
        self.assertIn("skills/project-init/SKILL.md:1", res[0])

    def test_clone_path_desktop_in_global_found(self):
        self.put("global/x", "~/Desktop/solo-sdd\n")
        self.assertEqual(len(scan(self.root)), 1)

    def test_clone_path_outside_scope_ok(self):
        self.put("solo-sdd/changes/x/verification.md", "~/Code/tools/sdd/solo-sdd\n")
        self.put("tests/x.py", "~/Desktop/solo-sdd\n")
        self.assertEqual(scan(self.root), [])

    def test_denylist_in_main_spec_found(self):
        self.deny("Zeta")
        self.put("solo-sdd/specs/x/spec.md", "ok\n- **WHEN** as in Zeta\n")
        self.put("solo-sdd/changes/archive/2026-01-01-a/proposal.md", "Zeta\n")
        self.put("solo-sdd/changes/b/proposal.md", "Zeta\n")
        self.assertEqual(scan(self.root), ["solo-sdd/specs/x/spec.md:2: Zeta"])

    def test_main_spec_paths_and_sessions_not_checked(self):
        self.put("solo-sdd/specs/x/spec.md", "session=157c88ff /Users/real/ ~/Desktop/solo-sdd\n")
        self.assertEqual(scan(self.root), [])

    def test_missing_file_skipped(self):
        self.put("a.md", "x\n")
        os.remove(os.path.join(self.root, "a.md"))
        self.assertEqual(scan(self.root), [])


class TestOwnerTools(TempRepo):
    """Rules name no owner tools: a denylisted tool name in a skill is named with its file and line."""

    def test_notes_app_in_skill_named(self):
        self.deny("NotesApp")
        self.put("skills/context-resume/SKILL.md", "# x\n   - start with the index of NotesApp\n")
        self.put("skills/other/SKILL.md", "a notes vault, if the project names one\n")
        self.assertEqual(scan(self.root), ["skills/context-resume/SKILL.md:2: NotesApp"])


class TestUnsourcedCitations(TempRepo):
    """No unsourced citations: a dated work without an address fails, one with its address passes."""

    def test_dated_article_named(self):
        self.put("ALGORITHM.md", "x\n7. Handoffs lose precision (an article of 22.10.2026 calls it so).\n")
        self.assertEqual(unsourced_citations(self.root), ["ALGORITHM.md:2"])

    def test_citation_with_address_passes(self):
        self.put("skills/a/SKILL.md", "as a post of 2026-10-22 says: https://example.com/p\n")
        self.assertEqual(unsourced_citations(self.root), [])

    def test_other_texts_and_words(self):
        self.put("README.md", "a talk at 2026-01-02\n`post-draft` of 2026-01-02\nan article, no date\n")
        self.put("global/AGENTS.md", "Papers of 1.2.2026\n")
        self.put("docs/x.md", "an article of 22.10.2026\n")
        self.assertEqual(unsourced_citations(self.root), ["README.md:1", "global/AGENTS.md:1"])


class TestArchiveOutsideGit(TempRepo):
    """Change archive outside git: a branch cut before the ignore line commits its archived folder."""

    def test_each_tracked_archive_path_named(self):
        self.put("solo-sdd/specs/x/spec.md", "s\n")
        self.put("solo-sdd/changes/y/tasks.md", "t\n")
        self.put("solo-sdd/changes/archive/2026-11-11-a/tasks.md", "t\n")
        self.put("solo-sdd/changes/archive/2026-11-11-a/specs/x/spec.md", "s\n")
        self.assertEqual(tracked_archive(self.root), ["tracked: solo-sdd/changes/archive/2026-11-11-a/specs/x/spec.md",
                                                      "tracked: solo-sdd/changes/archive/2026-11-11-a/tasks.md"])


class TestSkillRefs(TempRepo):
    README = "# x\n\nSome skills use extra tools:\n\n- toolbox (the `trace-calls` skill): `debug-profile`;\n" \
             "- `codex` (Codex CLI) — `codex-orchestration`;\n\n## Installation\n\n- `post-draft`: not a tool\n"

    def setUp(self):
        super().setUp()
        self.put("README.md", self.README)
        self.put("skills/debug-profile/SKILL.md", "use `toolbox:trace` or `trace-calls`\n")

    def test_unshipped_skill_named(self):
        self.put("ALGORITHM.md", "x\n| a disputed decision | `my-skill` |\n`/demo-brief topic`, `/debug-profile map`\n")
        self.assertEqual(skill_refs(self.root), ["ALGORITHM.md:2: my-skill", "ALGORITHM.md:3: /demo-brief"])

    def test_skill_only_on_disk(self):
        os.makedirs(os.path.join(self.root, "skills", "my-skill"))
        pathlib.Path(self.root, "skills/my-skill/SKILL.md").write_text("x\n", encoding="utf-8")
        self.put("global/AGENTS.md", "`/my-skill`: a council · `/debug-profile`: debugging\n")
        self.assertEqual(skill_refs(self.root), ["global/AGENTS.md:1: /my-skill"])

    def test_optional_tool_and_shipped_no_finding(self):
        self.put("ALGORITHM.md", "`debug-profile`, `/debug-profile`, `codex`, `ship`, `land-local`\n")
        self.assertEqual(skill_refs(self.root), [])

    def test_bullet_outside_list_not_optional(self):
        self.put("skills/debug-profile/SKILL.md", "for posts `post-draft`\n")
        self.assertEqual(skill_refs(self.root), ["skills/debug-profile/SKILL.md:1: post-draft"])

    def test_unknown_plugin(self):
        self.put("ALGORITHM.md", "`acme:plan`\n")
        self.assertEqual(skill_refs(self.root), ["ALGORITHM.md:1: acme"])


class TestProperty(unittest.TestCase):
    @settings(max_examples=200, deadline=None)
    @given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_.-", min_size=1).filter(lambda n: n != "you"))
    def test_no_owner_traces_home_path_found_for_any_name(self, name):
        bad = f"cd /Users/{name}/p; ls /home/{name}/q"
        self.assertGreaterEqual(len(find_in_line(bad, [])), 2)
        self.assertEqual(find_in_line("cd /Users/<user>/p; ls /home/<user>/q", []), [])


    @settings(max_examples=200, deadline=None)
    @given(st.sampled_from(["Rok", "/Users/anna/", "\u03b1\u03b2\u03b3"]), st.data())
    def test_escaped_traces(self, trace, data):
        """Requirement: Escaped traces. Any subset of the characters escaped gives the plain finding."""
        deny = [re.compile(r"(?<!\w)" + re.escape(trace) + r"(?!\w)", re.I)] if not trace.startswith("/") else []
        forms = [lambda c: "\\x%02x" % ord(c) if ord(c) < 256 else "\\u%04x" % ord(c),
                 lambda c: "\\u%04x" % ord(c), lambda c: "\\U%08x" % ord(c)]
        mask = data.draw(st.lists(st.sampled_from([None, 0, 1, 2]), min_size=len(trace), max_size=len(trace)))
        line = "s = '" + "".join(c if m is None else forms[m](c) for c, m in zip(trace, mask)) + "'"
        self.assertEqual(find_in_line(line, deny), find_in_line("s = '%s'" % trace, deny))
        self.assertIn(trace, find_in_line(line, deny))


class TestRealTree(unittest.TestCase):
    @marks.slow
    def test_tree_clean(self):
        self.assertEqual(scan(REPO), [], "\n".join(scan(REPO)))

    def test_no_unsourced_citations(self):
        self.assertEqual(unsourced_citations(REPO), [], "\n".join(unsourced_citations(REPO)))

    def test_idea_without_citation(self):
        line = next(l for l in (REPO / "ALGORITHM.md").read_text(encoding="utf-8").splitlines() if l.startswith("7. "))
        self.assertIn("every handoff between agents loses precision", line.lower())
        self.assertNotIn("article", line.lower())

    def test_referenced_skills_exist(self):
        self.assertEqual(skill_refs(REPO), [], "\n".join(skill_refs(REPO)))

    def test_only_installable_code(self):
        targets = json.loads((REPO / "targets.json").read_text(encoding="utf-8"))
        docs = ["README.md"] + [p for p in git(REPO, "ls-files", "docs/*.md").split("\n") if p]
        readme = "\n".join((REPO / p).read_text(encoding="utf-8") for p in docs)
        for rel in git(REPO, "ls-files", "global").split("\n"):
            if rel and not os.path.basename(rel).startswith("test_"):
                self.assertTrue(rel in targets["files"] or rel in readme, f"not installed and not described: {rel}")
        tracked = git(REPO, "ls-files", "skills").split("\n")
        names = {p.split("/")[1] for p in tracked if p.count("/") >= 2}
        for name in names:
            self.assertIn(name, targets["skills"], f"skill outside targets.json: {name}")
        for name in targets["skills"]:
            self.assertIn(name, names, f"skill from targets.json is not tracked by git: {name}")
        self.assertEqual(subprocess.run(["git", "grep", "-n", "mcp__", "--", "skills"], cwd=REPO, capture_output=True, text=True).stdout, "")

    def test_owner_files_not_tracked(self):
        """Single-owner file: in .gitignore and not in the index; docs/waiting.md left in github-publish."""
        text = (REPO / ".gitignore").read_text(encoding="utf-8")
        paths = [p for p in text.split("# single owner", 1)[1].splitlines()[1:] if p]
        self.assertGreaterEqual(len(paths), 10)
        for path in paths:
            if path != "docs/waiting.md":
                self.assertEqual(git(REPO, "ls-files", "--", path), "", f"tracked: {path}")

    def test_archive_not_tracked(self):
        """Change archive outside git: ignored and not in the index; the main specs stay tracked."""
        self.assertEqual(tracked_archive(REPO), [], "\n".join(tracked_archive(REPO)))
        self.assertEqual(git(REPO, "check-ignore", "solo-sdd/changes/archive/x").strip(), "solo-sdd/changes/archive/x")
        self.assertTrue(git(REPO, "ls-files", "solo-sdd/specs").strip())

    def test_license(self):
        text = (REPO / "LICENSE").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("MIT License"))
        self.assertIn("Copyright (c) 2026 Vyacheslav Larionov", text)


if __name__ == "__main__":
    unittest.main()
