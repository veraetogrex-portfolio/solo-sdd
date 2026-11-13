#!/usr/bin/env python3
"""README.md and SOURCES.md: requirements Own features first, Sources are shipped third-party files and Line length."""
import os, re, subprocess, tempfile, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUICK = "## Quick start"
MOVE = "## Moving from OpenSpec"
QUICK_MUST = ("pip install", "solo-sdd install", "solo-sdd init", "/project-init", "/spec-plan", "/spec-next")
OTHERS = re.compile(r"gsd|spec kit|spec-kit|kiro", re.I)


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return f.read()


def readme_errors(text):
    """Errors of README text by Own features first; each names the line."""
    lines = text.splitlines()
    errors = []
    heads = [n for n, l in enumerate(lines, 1) if l.startswith("## ")]
    intro = "\n".join(lines[1:heads[0] - 1] if heads else lines[1:]).strip()
    sentences = len(re.findall(r"[.!?](?:\s|$)", intro))
    if not lines or lines[0] != "# solo-sdd" or not 1 <= sentences <= 2:
        errors.append("intro: `# solo-sdd` and at most two sentences before the first section, found %d" % sentences)
    quick = next((n for n, l in enumerate(lines, 1) if l == QUICK), None)
    if quick is None or quick >= 40 or heads[0] != quick:
        errors.append("quick start: the first section, heading before line 40, found at %s" % quick)
    else:
        body = "\n".join(lines[quick:]).split("\n## ", 1)[0]
        errors += ["quick start: no `%s`" % m for m in QUICK_MUST if m not in body]
    section = ""
    for n, line in enumerate(lines, 1):
        if line.startswith("## "):
            section = line
        if OTHERS.search(line):
            errors.append("line %d names another tool: %s" % (n, line.strip()[:80]))
        if "OpenSpec" in line and section != MOVE:
            errors.append("line %d names OpenSpec outside %s" % (n, MOVE))
    return errors


def vendor_copies(root=REPO):
    """{folder: (version, license)} of every pinned copy under integrations/, from its VERSION and LICENSE."""
    out = {}
    base = os.path.join(root, "integrations")
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if os.path.isdir(d):
            version = open(os.path.join(d, "VERSION"), encoding="utf-8").readline().split()[0]
            lic = open(os.path.join(d, "LICENSE"), encoding="utf-8").readline().split()[0]
            out["integrations/%s/" % name] = (version, lic)
    return out


def sources_errors(text, copies):
    """Errors of SOURCES text by Sources are shipped third-party files."""
    errors = []
    sections = ["## " + s for s in text.split("\n## ")[1:]]
    if len(sections) != len(copies):
        errors.append("%d sections for %d pinned copies" % (len(sections), len(copies)))
    for folder, (version, lic) in copies.items():
        own = [s for s in sections if folder in s]
        if len(own) != 1:
            errors.append("%s: %d sections name it" % (folder, len(own)))
            continue
        short = version[:7] if re.fullmatch(r"[0-9a-f]{40}", version) else version
        if short not in own[0] or lic not in own[0]:
            errors.append("%s: no version %s or license %s" % (folder, short, lic))
        if len(set(re.findall(r"\]\((https?://[^)]+)\)", own[0]))) != 1:
            errors.append("%s: one origin link expected" % folder)
    for n, line in enumerate(text.splitlines(), 1):
        if OTHERS.search(line) or "openspec" in line.lower():
            errors.append("line %d names another project: %s" % (n, line.strip()[:80]))
    return errors


class OwnFeaturesFirst(unittest.TestCase):
    """Requirement: Own features first."""

    def test_readme(self):
        errors = readme_errors(read("README.md"))
        self.assertEqual(errors, [], "\n".join(errors))

    def test_quick_start_position(self):
        """Scenario: Quick start position. A quick start after line 40 or a GSD line fails."""
        late = "# solo-sdd\n\nOne sentence.\n\n" + "\n" * 40 + QUICK + "\n" + " ".join(QUICK_MUST) + "\n"
        self.assertTrue(any("quick start" in e for e in readme_errors(late)))
        gsd = "# solo-sdd\n\nOne.\n\n" + QUICK + "\n" + " ".join(QUICK_MUST) + "\nUnlike GSD Core.\n"
        self.assertEqual(readme_errors(gsd), ["line 7 names another tool: Unlike GSD Core."])

    def test_openspec_only_in_move_section(self):
        """Scenario: OpenSpec only in the move section. The failure names the line."""
        head = "# solo-sdd\n\nOne.\n\n" + QUICK + "\n" + " ".join(QUICK_MUST) + "\n"
        self.assertEqual(readme_errors(head + MOVE + "\nFrom OpenSpec: `solo-sdd import openspec`.\n"), [])
        self.assertEqual(readme_errors(head + "## Commands\nLike OpenSpec.\n"),
                         ["line 8 names OpenSpec outside " + MOVE])

    def test_three_sentences_fail(self):
        self.assertTrue(readme_errors("# solo-sdd\n\nA. B. C.\n\n" + QUICK + "\n" + " ".join(QUICK_MUST) + "\n"))


BLOB = "https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/"


def relative_file_links(text):
    """Link targets that are neither an address nor a heading of the same file: they break on the PyPI and npm pages."""
    return [link for link in re.findall(r"\]\(([^)\s]+)\)", text) if "://" not in link and not link.startswith("#")]


def broken_links(rel, text=None):
    """Relative links of a Markdown file that point to no file and in-page anchors that match no heading."""
    text = read(rel) if text is None else text
    anchors = {re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")
               for h in re.findall(r"^#+ (.+)$", text, re.M)}
    bad = []
    for link in re.findall(r"\]\(([^)\s]+)\)", text):
        base = os.path.dirname(rel)
        if link.startswith(BLOB):
            link, base = link[len(BLOB):], ""
        elif "://" in link:
            continue
        path, _, anchor = link.partition("#")
        if path and not os.path.exists(os.path.join(REPO, base, path)):
            bad.append(link)
        elif not path and anchor not in anchors:
            bad.append(link)
    return bad


class StopConditions(unittest.TestCase):
    """Requirement: Stop conditions in the README: every enforcing file exists; README links resolve."""

    def test_enforcing_files_exist(self):
        section = read("README.md").split("\n## How solo-sdd stops\n", 1)[1].split("\n## ", 1)[0]
        rows = [r for r in section.splitlines() if r.startswith("| ") and r.count("|") == 4]
        paths = {p for r in rows for p in re.findall(r"`([\w./-]+\.(?:md|py))`", r.split("|")[3])}
        self.assertGreater(len(paths), 5)
        self.assertEqual(sorted(p for p in paths if not os.path.isfile(os.path.join(REPO, p))), [])

    def test_links_resolve(self):
        for rel in ("README.md", "SOURCES.md", "docs/layout.md"):
            self.assertEqual(broken_links(rel), [], rel)


class RegistryInstall(unittest.TestCase):
    """Requirement: Registry install documented."""

    def test_no_relative_file_links(self):
        self.assertEqual(relative_file_links(read("README.md")), [])

    def test_relative_link_found(self):
        self.assertEqual(relative_file_links("[a](docs/layout.md) [b](#quick-start) [c](%sLICENSE)" % BLOB),
                         ["docs/layout.md"])

    def test_absolute_link_to_a_missing_file_is_broken(self):
        text = "# T\n\n[a](%sno-such.md) [b](%sLICENSE)\n" % (BLOB, BLOB)
        self.assertEqual(broken_links("README.md", text), ["no-such.md"])

    def test_registry_commands(self):
        text = read("README.md")
        quick = text.split("\n## Quick start\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("pip install solo-sdd\n", quick)
        install = text.split("\n## Installation\n", 1)[1].split("\n## ", 1)[0]
        for command in ("pip install solo-sdd\n", "uv tool install solo-sdd\n", "pipx install solo-sdd\n",
                        "npm i -g solo-sdd\n", "pip install git+https://github.com/veraetogrex-portfolio/solo-sdd"):
            self.assertIn(command, install)

    def test_release_doc(self):
        text = read("docs/release.md")
        for part in ("public", "pending publisher", "NPM_TOKEN", "trusted publisher", "scripts/release_check.py", "git tag"):
            self.assertIn(part, text)


class SourcesShipped(unittest.TestCase):
    """Requirement: Sources are shipped third-party files."""

    def test_sources(self):
        errors = sources_errors(read("SOURCES.md"), vendor_copies())
        self.assertEqual(errors, [], "\n".join(errors))

    def test_the_pinned_copies(self):
        """Scenario: The pinned copies. A missing copy, a missing license or another project fails."""
        copies = {"integrations/a/": ("v1.2", "MIT"), "integrations/b/": ("c" * 40, "MIT")}
        good = "# Sources\n\n## a\n[a](https://x/a), v1.2, MIT license, `integrations/a/`.\n\n" \
               "## b\n[b](https://x/b), commit ccccccc, MIT license, `integrations/b/`.\n"
        self.assertEqual(sources_errors(good, copies), [])
        self.assertTrue(sources_errors(good.split("## b")[0], copies))
        self.assertTrue(sources_errors(good.replace("v1.2, MIT", "v1.2"), copies))
        self.assertTrue(sources_errors(good + "\n## Kiro\nIdeas.\n", copies))
        self.assertTrue(sources_errors(good.replace("MIT license, `integrations/b/`.", "MIT, `integrations/b/`, like Spec Kit."), copies))


LIMIT = 600
FENCE = re.compile(r"[ ]{0,3}(`{3,}|~{3,})(.*)$")


def long_lines(name, text, limit=LIMIT):
    """Lines of a Markdown text longer than `limit` code points outside fenced code blocks, as `name:line (length)`."""
    out, fence = [], None
    for n, line in enumerate(text.splitlines(), 1):
        m = FENCE.match(line)
        if fence is None and m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            fence = m.group(1)
            continue
        if fence and m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
            fence = None
            continue
        if fence is None and len(line) > limit:
            out.append("%s:%d (%d)" % (name, n, len(line)))
    return out


def tracked_docs(root=REPO):
    """`README.md`, `ALGORITHM.md` and `skills/*/SKILL.md` that git tracks under root."""
    run = subprocess.run(["git", "ls-files", "-z", "--", "README.md", "ALGORITHM.md", "skills/*/SKILL.md"],
                         cwd=root, capture_output=True, check=True, stdin=subprocess.DEVNULL)
    return [f for f in run.stdout.decode("utf-8").split("\0") if f]


def tree_long_lines(root=REPO):
    out = []
    for rel in tracked_docs(root):
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            out += long_lines(rel, f.read())
    return out


class LineLength(unittest.TestCase):
    """Requirement: Line length."""

    def test_line_length_of_the_tree(self):
        docs = tracked_docs()
        self.assertTrue({"README.md", "ALGORITHM.md", "skills/spec-dispatch/SKILL.md"} <= set(docs), docs)
        errors = tree_long_lines()
        self.assertEqual(errors, [], "lines over %d characters:\n%s" % (LIMIT, "\n".join(errors)))

    def test_a_long_paragraph(self):
        text = "# Skill\n\nShort.\n\n" + "x" * 700 + "\n"
        self.assertEqual(long_lines("skills/a/SKILL.md", text), ["skills/a/SKILL.md:5 (700)"])
        self.assertEqual(long_lines("a", "\u2192" * 600 + "\n"), [])

    def test_a_long_code_line(self):
        for fence in ("```", "~~~", "````"):
            text = "# Skill\n\n%sbash\n%s\n%s\nafter\n" % (fence, "x" * 700, fence)
            self.assertEqual(long_lines("s", text), [], fence)
        self.assertEqual(long_lines("s", "```\n```\n" + "x" * 700 + "\n"), ["s:3 (700)"])
        self.assertEqual(long_lines("s", "````\n```\n" + "x" * 700 + "\n````\n"), [])

    def test_a_long_table_row(self):
        text = "# solo-sdd\n\n| a | b |\n|---|---|\n| x | %s |\n" % ("y" * 692)
        self.assertEqual(long_lines("README.md", text), ["README.md:5 (700)"])

    def test_an_untracked_skill(self):
        with tempfile.TemporaryDirectory() as root:
            run = lambda *a: subprocess.run(a, cwd=root, check=True, capture_output=True, stdin=subprocess.DEVNULL)
            run("git", "init", "-q")
            for name, body in (("tracked", "short\n"), ("mine", "x" * 700 + "\n")):
                os.makedirs(os.path.join(root, "skills", name))
                with open(os.path.join(root, "skills", name, "SKILL.md"), "w", encoding="utf-8") as f:
                    f.write(body)
            run("git", "add", "skills/tracked/SKILL.md")
            self.assertEqual(tracked_docs(root), ["skills/tracked/SKILL.md"])
            self.assertEqual(tree_long_lines(root), [])
            run("git", "add", "skills/mine/SKILL.md")
            self.assertEqual(tree_long_lines(root), ["skills/mine/SKILL.md:1 (700)"])


if __name__ == "__main__":
    unittest.main()
