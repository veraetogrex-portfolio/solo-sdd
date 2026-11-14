#!/usr/bin/env python3
"""Release check (scripts/release_check.py) and the release workflow (.github/workflows/release.yml)."""
import importlib.util, json, os, re, shutil, subprocess, sys, tarfile, tempfile, unittest, zipfile
import marks
from hypothesis import given, settings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "release_check.py")
WORKFLOW = os.path.join(REPO, ".github", "workflows", "release.yml")
WORKFLOWS = os.path.join(REPO, ".github", "workflows")
NET = ("Could not find a version", "No matching distribution", "Failed to establish", "Temporary failure",
       "Name or service not known", "ProxyError", "Network is unreachable")


def load():
    spec = importlib.util.spec_from_file_location("release_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def can_build():
    return (importlib.util.find_spec("build") is not None and shutil.which("npm") is not None
            and shutil.which("git") is not None)


def copy_tree(dest):
    """The committed tree plus files not yet committed (not ignored), as one commit of a new repository."""
    files = subprocess.run(["git", "-C", REPO, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                           capture_output=True, text=True, check=True).stdout.split("\0")
    for rel in filter(None, files):
        src = os.path.join(REPO, rel)
        if not os.path.isfile(src):
            continue
        os.makedirs(os.path.dirname(os.path.join(dest, rel)) or dest, exist_ok=True)
        shutil.copy2(src, os.path.join(dest, rel))
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "tree"]):
        subprocess.run(["git", "-C", dest] + args, check=True, env=env, capture_output=True)


def run_check(root, tag, out):
    return subprocess.run([sys.executable, os.path.join(root, "scripts", "release_check.py"), tag, "--out", out],
                          capture_output=True, text=True, cwd=tempfile.gettempdir(), stdin=subprocess.DEVNULL)


def holds(version_errors, tag, a, b):
    """Release versions property: no error exactly when both fields equal the tag without v."""
    errors = version_errors(tag, {"package.json": a, "solo_sdd/__init__.py": b})
    return (not errors) == (a == tag[1:] and b == tag[1:])


class Versions(unittest.TestCase):
    def setUp(self):
        self.m = load()

    def test_mismatch_names_tag_and_version(self):
        errors = self.m.version_errors("v0.2.1", {"package.json": "0.2.0", "solo_sdd/__init__.py": "0.2.0"})
        self.assertEqual(len(errors), 2)
        for line in errors:
            self.assertTrue(line.startswith("fail version"))
            self.assertIn("v0.2.1", line)
            self.assertIn("0.2.0", line)

    def test_tag_without_v(self):
        errors = self.m.version_errors("0.2.0", {"package.json": "0.2.0", "solo_sdd/__init__.py": "0.2.0"})
        self.assertEqual(errors, ["fail tag 0.2.0: a release tag is v<version>"])

    def test_match(self):
        self.assertEqual(self.m.version_errors("v0.2.0", {"package.json": "0.2.0", "solo_sdd/__init__.py": "0.2.0"}), [])

    def test_repository_versions_agree(self):
        v = self.m.read_versions(REPO)
        self.assertEqual(len(set(v.values())), 1, v)

    @settings(max_examples=300, deadline=None)
    @given(st.sampled_from(["0.2.0", "0.2.1", "1.0.0", ""]), st.sampled_from(["0.2.0", "0.2.1", "1.0.0", ""]),
           st.sampled_from(["v0.2.0", "v0.2.1", "v1.0.0"]))
    def test_release_versions_property(self, a, b, tag):
        self.assertTrue(holds(self.m.version_errors, tag, a, b))

    def test_property_catches_single_field_compare(self):
        def mutant(tag, versions):
            return [] if versions["package.json"] == tag[1:] else ["fail"]
        self.assertFalse(holds(mutant, "v0.2.0", "0.2.0", "0.1.0"))


class Contents(unittest.TestCase):
    def setUp(self):
        self.m = load()

    def test_wheel_paths_map_data_folder(self):
        names = ["solo_sdd/cli.py", "solo_sdd/data/skills/spec-plan/SKILL.md", "solo_sdd/data/targets.json",
                 "solo_sdd-0.2.0.dist-info/METADATA", "solo_sdd-0.2.0.dist-info/licenses/LICENSE"]
        self.assertEqual(self.m.wheel_paths(names), ["solo_sdd/cli.py", "skills/spec-plan/SKILL.md", "targets.json"])

    def test_prefixed_paths(self):
        self.assertEqual(self.m.prefixed_paths(["package/bin/solo-sdd.js", "package/", "solo_sdd-0.2.0/PKG-INFO"],
                                               ("PKG-INFO",)), ["bin/solo-sdd.js"])

    def test_untracked_path_named(self):
        errors = self.m.content_errors("npm", ["skills/my-skill/SKILL.md", "README.md"], {"README.md"})
        self.assertEqual(errors, ["fail npm: skills/my-skill/SKILL.md is not tracked by git"])

    def test_not_shipped_folder_named(self):
        errors = self.m.content_errors("wheel", ["docs/layout.md"], {"docs/layout.md"})
        self.assertEqual(errors, ["fail wheel: docs/layout.md lies in a folder that is not shipped"])

    def test_sdist_may_hold_tests(self):
        self.assertEqual(self.m.content_errors("sdist", ["tests/test_cli.py"], {"tests/test_cli.py"},
                                               self.m.SDIST_NOT_SHIPPED), [])

    def test_sdist_refuses_process_tree(self):
        path = "solo-sdd/changes/archive/x/verification.md"
        self.assertEqual(self.m.content_errors("sdist", [path], {path}, self.m.SDIST_NOT_SHIPPED),
                         ["fail sdist: %s lies in a folder that is not shipped" % path])

    def test_not_a_git_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "solo_sdd"))
            with open(os.path.join(tmp, "package.json"), "w") as f:
                f.write('{"version": "0.2.0"}')
            with open(os.path.join(tmp, "solo_sdd", "__init__.py"), "w") as f:
                f.write('__version__ = "0.2.0"\n')
            with open(os.path.join(tmp, "CHANGELOG.md"), "w") as f:
                f.write("# Changelog\n\n## 0.2.0\n\n- a\n")
            self.assertEqual(self.m.check(tmp, "v0.2.0", os.path.join(tmp, "dist")),
                             ["fail git: %s is not a git repository" % tmp])


@unittest.skipUnless(can_build(), "python -m build, npm or git is missing")
class Build(unittest.TestCase):
    """Real builds on a copy of the tree, run from outside the copy."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "repo")
        os.makedirs(self.root)
        copy_tree(self.root)
        self.out = os.path.join(self.tmp, "dist")
        self.version = load().read_versions(self.root)["package.json"]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def check(self, tag):
        r = run_check(self.root, tag, self.out)
        if r.returncode != 0 and any(mark in r.stdout + r.stderr for mark in NET):
            self.skipTest("the builder is unavailable because of the network")
        return r

    @marks.slow
    def test_mismatch_builds_nothing(self):
        r = self.check("v9.9.9")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("v9.9.9", r.stdout)
        self.assertIn(self.version, r.stdout)
        self.assertFalse(os.path.exists(self.out))

    @marks.slow
    def test_ignored_files_on_disk_stay_out(self):
        for rel in ("global/claude-gui.py", "global/claude-safe.py"):
            os.makedirs(os.path.dirname(os.path.join(self.root, rel)), exist_ok=True)
            with open(os.path.join(self.root, rel), "w") as f:
                f.write("private\n")
        r = self.check("v" + self.version)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        v = self.version
        files = sorted(os.listdir(self.out))
        self.assertEqual(files, sorted([f"solo-sdd-{v}.tgz", f"solo_sdd-{v}-py3-none-any.whl", f"solo_sdd-{v}.tar.gz"]))
        self.assertIn(f"wheel --version: {v}", r.stdout)
        self.assertIn(f"npm --version: {v}", r.stdout)
        with zipfile.ZipFile(os.path.join(self.out, f"solo_sdd-{v}-py3-none-any.whl")) as z:
            names = z.namelist()
        for archive in (f"solo-sdd-{v}.tgz", f"solo_sdd-{v}.tar.gz"):
            with tarfile.open(os.path.join(self.out, archive)) as t:
                names += t.getnames()
        self.assertFalse([n for n in names if "claude-gui" in n or "claude-safe" in n])

    @marks.slow
    def test_locally_excluded_skill_refused(self):
        """A personal skill kept out of git by the clone's own info/exclude is still on disk: the check refuses it."""
        with open(os.path.join(self.root, ".git", "info", "exclude"), "a") as f:
            f.write("skills/my-skill/\n")
        os.makedirs(os.path.join(self.root, "skills", "my-skill"))
        with open(os.path.join(self.root, "skills", "my-skill", "SKILL.md"), "w") as f:
            f.write("private\n")
        r = self.check("v" + self.version)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("fail npm: skills/my-skill/SKILL.md is not tracked by git", r.stdout)

    @marks.slow
    def test_no_process_tree_in_sdist(self):
        r = self.check("v" + self.version)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with tarfile.open(os.path.join(self.out, "solo_sdd-%s.tar.gz" % self.version)) as t:
            names = t.getnames()
        self.assertFalse([n for n in names if n.split("/", 1)[-1].startswith("solo-sdd/")])
        self.assertTrue([n for n in names if n.endswith("/tests/test_release.py")])

    @marks.slow
    def test_uncommitted_edit_refused(self):
        with open(os.path.join(self.root, "skills", "spec-plan", "SKILL.md"), "a") as f:
            f.write("UNCOMMITTED\n")
        r = self.check("v" + self.version)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("fail uncommitted: skills/spec-plan/SKILL.md differs from the commit", r.stdout)
        self.assertFalse(os.path.exists(self.out))

    @marks.slow
    def test_staged_rename_names_both_paths(self):
        subprocess.run(["git", "-C", self.root, "mv", "LICENSE", "LICENSE2"], check=True, capture_output=True)
        self.assertEqual(load().uncommitted(self.root), ["LICENSE", "LICENSE2"])

    @marks.slow
    def test_untracked_shipped_file_refused(self):
        with open(os.path.join(self.root, "skills", "stray.txt"), "w") as f:
            f.write("not in git\n")
        r = self.check("v" + self.version)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("fail npm: skills/stray.txt is not tracked by git", r.stdout)
        self.assertIn("fail wheel: skills/stray.txt is not tracked by git", r.stdout)

    @marks.slow
    def test_not_shipped_folder_refused(self):
        path = os.path.join(self.root, "package.json")
        with open(path) as f:
            package = json.load(f)
        package["files"].append("docs/")
        with open(path, "w") as f:
            json.dump(package, f, indent=2)
        subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "docs"],
                       check=True, capture_output=True)
        r = self.check("v" + self.version)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("fail npm: docs/layout.md lies in a folder that is not shipped", r.stdout)


def jobs(text):
    """Job name -> its block of lines, from the two-space indented keys under jobs:."""
    body = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([a-z][a-z-]*):\n", body, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def plain_scalar_errors(text):
    """Lines whose plain (unquoted, not block) value holds ': ' or ' #', which YAML reads as a mapping or a comment."""
    errors = []
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*(?:- )?[\w-]+: (.+)$", line)
        if not m:
            continue
        value = m.group(1)
        if value[0] in "|>'\"[{" or value.startswith("${{"):
            continue
        if ": " in value or " #" in value:
            errors.append("line %d: %s" % (n, line.strip()[:80]))
    return errors


class WorkflowYaml(unittest.TestCase):
    """Both workflows parse: GitHub rejects the whole file on a YAML error and runs nothing (0 s failures)."""

    def test_workflows_have_no_broken_plain_scalars(self):
        for name in ("test.yml", "release.yml"):
            with open(os.path.join(REPO, ".github", "workflows", name), encoding="utf-8") as f:
                self.assertEqual(plain_scalar_errors(f.read()), [], name)

    def test_broken_line_found(self):
        line = '        run: if [ -d x ]; then a; else echo "no x/: nothing to check"; fi\n'
        self.assertEqual(len(plain_scalar_errors(line)), 1)

    def test_valid_lines_pass(self):
        text = 'on:\n  push:\n    tags: ["v*"]\n      - run: |\n          echo "a: b"\n        name: x\n'
        self.assertEqual(plain_scalar_errors(text), [])


class Workflow(unittest.TestCase):
    def setUp(self):
        with open(WORKFLOW, encoding="utf-8") as f:
            self.text = f.read()
        self.jobs = jobs(self.text)

    def test_trigger_is_version_tags(self):
        self.assertIn('on:\n  push:\n    tags: ["v*"]\n', self.text)
        self.assertIn("permissions:\n  contents: read\n", self.text)

    def test_jobs_and_order(self):
        self.assertEqual(sorted(self.jobs), ["check", "github-release", "npm", "pypi"])
        self.assertIn("needs: check", self.jobs["pypi"])
        self.assertIn("needs: check", self.jobs["npm"])
        self.assertIn("needs: [pypi, npm]", self.jobs["github-release"])

    def test_id_token_only_for_publishing(self):
        with_token = sorted(name for name, block in self.jobs.items() if "id-token: write" in block)
        self.assertEqual(with_token, ["npm", "pypi"])

    def test_check_job(self):
        block = self.jobs["check"]
        self.assertIn('git merge-base --is-ancestor "$GITHUB_SHA" origin/main', block)
        self.assertIn("fetch-depth: 0", block)
        self.assertIn('scripts/release_check.py "$GITHUB_REF_NAME"', block)
        self.assertIn("/usr/bin/python3 tests/run.py --tier release < /dev/null", block)
        self.assertIn("github.event.repository.private", block)
        self.assertIn("upload-artifact", block)
        self.assertIn('scripts/release_check.py --notes "$GITHUB_REF_NAME"', block)

    def test_publishing_jobs_do_not_build(self):
        for name in ("pypi", "npm", "github-release"):
            block = self.jobs[name]
            self.assertIn("download-artifact", block, name)
            for build in ("-m build", "npm pack", "release_check.py", "actions/checkout"):
                self.assertNotIn(build, block, name)

    def test_pypi_job(self):
        block = self.jobs["pypi"]
        self.assertIn("name: pypi", block)
        self.assertIn('https://pypi.org/pypi/solo-sdd/$v/json', block)
        self.assertIn("already published on PyPI", block)
        self.assertRegex(block, r"pypa/gh-action-pypi-publish@[0-9a-f]{40}\n")
        self.assertIn("skip-existing: true", block)
        self.assertNotIn("if:", block)

    def test_npm_job(self):
        block = self.jobs["npm"]
        self.assertIn("name: npm", block)
        self.assertIn("npm install -g npm@^11.5.1", block)
        self.assertIn('npm view "solo-sdd@$v" version', block)
        self.assertIn("already published on npm", block)
        self.assertIn("NPM_TOKEN: ${{ secrets.NPM_TOKEN }}", block)
        self.assertIn('if [ -n "$NPM_TOKEN" ]', block)
        self.assertIn("--provenance", block)

    def test_release_job(self):
        block = self.jobs["github-release"]
        self.assertIn("contents: write", block)
        self.assertIn("--verify-tag", block)
        self.assertIn("--clobber", block)
        self.assertIn("--notes-file", block)
        self.assertNotIn("--generate-notes", block)


def tree(root, version, changelog=None, archive=None):
    """A minimal tree: both version fields, CHANGELOG.md when given, solo-sdd/changes/archive/<names> when given."""
    os.makedirs(os.path.join(root, "solo_sdd"), exist_ok=True)
    with open(os.path.join(root, "package.json"), "w") as f:
        json.dump({"version": version}, f)
    with open(os.path.join(root, "solo_sdd", "__init__.py"), "w") as f:
        f.write('__version__ = "%s"\n' % version)
    if changelog is not None:
        with open(os.path.join(root, "CHANGELOG.md"), "w") as f:
            f.write(changelog)
    for name in archive or ():
        os.makedirs(os.path.join(root, "solo-sdd", "changes", "archive", name))


def changelog_errors(m, root):
    """Changelog: the current version has a section, and with solo-sdd/changes/archive/ each listed change has its
    folder there; the archive is kept only in the working folder, so a fresh clone (CI) has solo-sdd/ without it."""
    version = m.read_versions(root)["solo_sdd/__init__.py"]
    section = m.changelog_section(root, version)
    if section is None:
        return ["CHANGELOG.md: no section ## %s for the version of solo_sdd/__init__.py" % version]
    archive = os.path.join(root, "solo-sdd", "changes", "archive")
    if not os.path.isdir(archive):
        return []
    folders = os.listdir(archive)
    errors = []
    for line in section.splitlines():
        if line.startswith("- "):
            change = line[2:].strip()
            if not any(re.fullmatch(r"\d{4}-\d{2}-\d{2}-" + re.escape(change), f) for f in folders):
                errors.append("CHANGELOG.md ## %s: %s has no folder in solo-sdd/changes/archive" % (version, change))
    return errors


class Changelog(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_repository_changelog(self):
        self.assertEqual(changelog_errors(self.m, REPO), [])

    def test_version_bump_without_section(self):
        tree(self.tmp, "0.3.0", "# Changelog\n\n## 0.2.0\n\n- a\n", ["2026-11-10-a"])
        errors = changelog_errors(self.m, self.tmp)
        self.assertEqual(len(errors), 1)
        self.assertIn("0.3.0", errors[0])

    def test_change_not_archived(self):
        tree(self.tmp, "0.2.0", "# Changelog\n\n## 0.2.0\n\n- a\n- no-such-change\n", ["2026-11-10-a"])
        errors = changelog_errors(self.m, self.tmp)
        self.assertEqual(len(errors), 1)
        self.assertIn("no-such-change", errors[0])

    def test_folder_name_is_date_and_change(self):
        tree(self.tmp, "0.2.0", "## 0.2.0\n- ci\n", ["2026-11-10-release-ci"])
        self.assertEqual(len(changelog_errors(self.m, self.tmp)), 1)

    def test_public_tree(self):
        tree(self.tmp, "0.2.0", "# Changelog\n\n## 0.2.0\n\n- no-such-change\n")
        self.assertEqual(changelog_errors(self.m, self.tmp), [])

    def test_fresh_clone_without_archive(self):
        tree(self.tmp, "0.2.0", "# Changelog\n\n## 0.2.0\n\n- no-such-change\n")
        os.makedirs(os.path.join(self.tmp, "solo-sdd", "specs", "x"))
        self.assertEqual(changelog_errors(self.m, self.tmp), [])

    def test_changelog_fail_before_building(self):
        tree(self.tmp, "0.3.0", "# Changelog\n\n## 0.2.0\n\n- a\n")
        out = os.path.join(self.tmp, "dist")
        self.assertEqual(self.m.check(self.tmp, "v0.3.0", out), ["fail changelog: CHANGELOG.md has no section ## 0.3.0"])
        self.assertFalse(os.path.exists(out))

    def test_empty_section_refused(self):
        tree(self.tmp, "0.3.0", "# Changelog\n\n## 0.3.0\n\n## 0.2.0\n\n- a\n")
        self.assertEqual(self.m.check(self.tmp, "v0.3.0", os.path.join(self.tmp, "dist")),
                         ["fail changelog: CHANGELOG.md has no section ## 0.3.0"])

    def test_no_changelog_file(self):
        tree(self.tmp, "0.3.0")
        self.assertEqual(self.m.check(self.tmp, "v0.3.0", os.path.join(self.tmp, "dist")),
                         ["fail changelog: CHANGELOG.md has no section ## 0.3.0"])


class ReleaseText(unittest.TestCase):
    TEXT = ("# Changelog\n\n## 0.3.1\n\n- later\n\n## 0.2.0\n\n- registry-release\n- release-ci\n\n"
            "## 0.1.0\n\n- earlier\n")

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        tree(self.tmp, "0.2.0", self.TEXT)
        os.makedirs(os.path.join(self.tmp, "scripts"))
        shutil.copy2(SCRIPT, os.path.join(self.tmp, "scripts"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def notes(self, tag):
        return subprocess.run([sys.executable, os.path.join(self.tmp, "scripts", "release_check.py"), "--notes", tag],
                              capture_output=True, text=True, cwd=tempfile.gettempdir(), stdin=subprocess.DEVNULL)

    def test_section_only(self):
        r = self.notes("v0.2.0")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip().splitlines(), ["- registry-release", "- release-ci"])

    def test_missing_section(self):
        r = self.notes("v0.3.0")
        self.assertEqual(r.returncode, 1)
        self.assertIn("0.3.0", r.stdout)
        self.assertTrue(r.stdout.startswith("fail changelog"), r.stdout)

    def test_repository_notes(self):
        m = load()
        version = m.read_versions(REPO)["solo_sdd/__init__.py"]
        self.assertTrue(m.changelog_section(REPO, version).strip())


def unpinned(text):
    """uses: values that do not end with @ and a full 40-digit commit hash."""
    values = re.findall(r"^\s*(?:- )?uses:\s*(\S+)", text, re.M)
    return [v for v in values if not re.search(r"@[0-9a-f]{40}$", v)]


class WorkflowPermissions(unittest.TestCase):
    def setUp(self):
        self.files = {}
        for name in sorted(os.listdir(WORKFLOWS)):
            if name.endswith(".yml"):
                with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as f:
                    self.files[name] = f.read()

    def test_both_workflows_read(self):
        self.assertLessEqual({"test.yml", "release.yml"}, set(self.files))

    def test_actions_pinned_by_hash(self):
        found = ["%s: %s" % (name, v) for name, text in self.files.items() for v in unpinned(text)]
        self.assertEqual(found, [])
        for name, text in self.files.items():
            self.assertTrue(re.search(r"uses:", text), name)

    def test_tag_and_branch_found(self):
        text = "      - uses: actions/checkout@v4\n      - uses: pypa/gh-action-pypi-publish@release/v1\n" \
               "      - uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020\n"
        self.assertEqual(unpinned(text), ["actions/checkout@v4", "pypa/gh-action-pypi-publish@release/v1"])

    def test_contents_read_at_top(self):
        for name, text in self.files.items():
            self.assertIn("\npermissions:\n  contents: read\n", text.split("\njobs:\n", 1)[0], name)

    def test_write_only_for_github_release(self):
        where = [(name, job) for name, text in self.files.items() for job, block in jobs(text).items()
                 if "contents: write" in block]
        self.assertEqual(where, [("release.yml", "github-release")])
        for name, text in self.files.items():
            self.assertNotIn("contents: write", text.split("\njobs:\n", 1)[0], name)
            self.assertNotIn("write-all", text, name)

    def test_release_text_handed_over(self):
        text = self.files["release.yml"]
        check, release = jobs(text)["check"], jobs(text)["github-release"]
        self.assertIn('> "$RUNNER_TEMP/notes/notes.md"', check)
        self.assertIn("name: notes\n          path: ${{ runner.temp }}/notes/\n", check)
        self.assertIn("name: notes\n          path: notes\n", release)
        self.assertIn("--notes-file notes/notes.md", release)

    def test_lint_before_tests(self):
        text = self.files["test.yml"]
        self.assertIn("pyflakes==3.4.0", text)
        self.assertIn("/usr/bin/python3 -m pyflakes solo_sdd global scripts sync.py", text)
        self.assertLess(text.index("name: Lint"), text.index("name: Run tests"))


def steps(block):
    """The steps of a job block: dicts of name, if and run, from the six-space indented `- ` items."""
    out = []
    for item in re.split(r"^      - ", block, flags=re.M)[1:]:
        step = {}
        for key in ("name", "if"):
            m = re.search(r"^(?:        )?%s: (.+)$" % key, item, re.M)
            step[key] = m.group(1) if m else None
        m = re.search(r"^(?:        )?run: (?:\|\n)?((?:.+\n?)+)", item, re.M)
        step["run"] = m.group(1) if m else ""
        out.append(step)
    return out


def evaluate(expr, event, ref):
    """A GitHub expression of `&&`, `||`, `!`, `==`, `!=`, startsWith and fromJSON for one event and ref."""
    expr = expr.strip()
    if expr.startswith("${{") and expr.endswith("}}"):
        expr = expr[3:-2]
    py = re.sub(r"!(?!=)", " not ", expr.replace("&&", " and ").replace("||", " or "))
    github = type("github", (), {"event_name": event, "ref": ref})
    return eval(py, {"__builtins__": {}}, {"github": github, "fromJSON": json.loads,
                                            "startsWith": lambda a, b: a.startswith(b)})


EVENTS = {("push", "refs/heads/main"): (["ubuntu-latest"], "slow"),
          ("pull_request", "refs/pull/1/merge"): (["ubuntu-latest"], "slow"),
          ("push", "refs/tags/v0.3.0"): (["macos-latest"], "release"),
          ("workflow_dispatch", "refs/heads/main"): (["ubuntu-latest", "macos-latest"], "release")}


def os_errors(text):
    """Continuous integration: the operating systems the matrix of test.yml selects for each event."""
    m = re.search(r"^\s*os: (\$\{\{.+\}\})$", text, re.M)
    if not m:
        return ["test.yml: no os: expression in the matrix"]
    errors = []
    for (event, ref), (want, _) in EVENTS.items():
        got = evaluate(m.group(1), event, ref)
        if sorted(got) != sorted(want):
            errors.append("%s %s: %s, expected %s" % (event, ref, got, want))
    return errors


def runner_tiers(block, event, ref):
    """The tiers of the `tests/run.py` steps of a job that run for the event."""
    tiers = []
    for step in steps(block):
        if "tests/run.py" in step["run"] and (step["if"] is None or evaluate(step["if"], event, ref)):
            tiers += re.findall(r"tests/run\.py --tier (\w+)", step["run"])
    return tiers


class ContinuousIntegration(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(WORKFLOWS, "test.yml"), encoding="utf-8") as f:
            self.text = f.read()

    def test_triggers(self):
        self.assertIn('on:\n  push:\n    branches: [main]\n    tags: ["v*"]\n  pull_request:\n    branches: [main]\n'
                      '  workflow_dispatch:\n', self.text)

    def test_operating_systems_by_event(self):
        self.assertEqual(os_errors(self.text), [])

    def test_operating_systems_mutant_fails(self):
        mutant = self.text.replace("""|| '["ubuntu-latest"]'""", """|| '["ubuntu-latest", "macos-latest"]'""")
        self.assertNotEqual(mutant, self.text)
        errors = os_errors(mutant)
        self.assertTrue(any(e.startswith("pull_request") for e in errors), errors)


class CiRunCost(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(WORKFLOWS, "test.yml"), encoding="utf-8") as f:
            self.text = f.read()
        with open(WORKFLOW, encoding="utf-8") as f:
            self.release = f.read()

    def test_concurrency(self):
        head = self.text.split("\njobs:\n", 1)[0]
        self.assertIn("\nconcurrency:\n  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: true\n",
                      head)

    def test_workflow_text_tiers(self):
        block = jobs(self.text)["test"]
        for (event, ref), (_, tier) in EVENTS.items():
            self.assertEqual(runner_tiers(block, event, ref), [tier], (event, ref))
        self.assertEqual(runner_tiers(jobs(self.release)["check"], "push", "refs/tags/v0.3.0"), ["release"])
        self.assertNotIn("for t in tests/test_*.py", self.text + self.release)

    def test_lint_before_runner(self):
        names = [s["name"] for s in steps(jobs(self.text)["test"])]
        runners = [i for i, s in enumerate(steps(jobs(self.text)["test"])) if "tests/run.py" in s["run"]]
        self.assertEqual(len(runners), 2)
        self.assertLess(names.index("Lint"), min(runners))

    def test_evaluate(self):
        self.assertEqual(evaluate("${{ !startsWith(github.ref, 'refs/tags/') && github.event_name != 'x' }}",
                                  "push", "refs/heads/main"), True)
        self.assertEqual(evaluate("github.event_name == 'x' && 'a' || 'b'", "x", ""), "a")


class MergeOnlyOnGreen(unittest.TestCase):
    """Requirement: Merge only on green CI."""

    def test_rule_in_both_files(self):
        for rel in ("AGENTS.md", os.path.join("docs", "release.md")):
            with open(os.path.join(REPO, rel), encoding="utf-8") as f:
                text = " ".join(f.read().split())
            for words in ("`sdd-pr.py merge`", "`CI: green`", "`CI: red`", "`CI: infra`", "`CI: codeql`",
                          "is still not green waits for the owner",
                          "never merges around a red or missing check"):
                self.assertTrue(words in text, "%s: %s" % (rel, words))
            for words in ("spending limit", "starts no jobs"):
                self.assertFalse(words in text, "%s: %s" % (rel, words))


if __name__ == "__main__":
    unittest.main()
