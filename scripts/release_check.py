#!/usr/bin/env python3
"""Release check: the tag against the versions, the release files built from what git tracks, a smoke run of each.

Usage: python3 scripts/release_check.py <tag> [--out DIR] | --notes <tag>

Builds into DIR (default dist/ of the repository) the sdist, the wheel from that sdist and the npm tarball.
Exit code 0 when every check passed, 1 otherwise; each failure is one line starting with "fail".
--notes prints the CHANGELOG.md section of the tag's version without its heading: the GitHub release text.
"""
import json, os, re, shutil, subprocess, sys, tarfile, tempfile, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOT_SHIPPED = ("tests/", "solo-sdd/", "docs/", ".github/", "examples/", "scripts/")
SDIST_NOT_SHIPPED = ("solo-sdd/",)
OWN_FILES = re.compile(r"^(solo_sdd-.+\.(tar\.gz|whl)|solo-sdd-.+\.tgz)$")


def read_versions(root):
    """The version fields a release must agree on, by file."""
    with open(os.path.join(root, "package.json"), encoding="utf-8") as f:
        package = json.load(f).get("version", "")
    with open(os.path.join(root, "solo_sdd", "__init__.py"), encoding="utf-8") as f:
        init = f.read()
    found = re.search(r'^__version__\s*=\s*"([^"]*)"', init, re.M)
    return {"package.json": package, "solo_sdd/__init__.py": found.group(1) if found else ""}


def version_errors(tag, versions):
    """Lines for every field whose version is not the tag without its leading v."""
    want = tag[1:] if tag.startswith("v") else None
    if want is None:
        return [f"fail tag {tag}: a release tag is v<version>"]
    return [f"fail version {name}: {value or 'none'}, tag {tag} wants {want}"
            for name, value in versions.items() if value != want]


def changelog_section(root, version):
    """The lines under "## <version>" of CHANGELOG.md up to the next "## " heading, or None without that section or
    when it is empty: a release text must name the changes."""
    try:
        with open(os.path.join(root, "CHANGELOG.md"), encoding="utf-8") as f:
            lines = [line.rstrip() for line in f.read().splitlines()]
    except FileNotFoundError:
        return None
    heading = "## " + version
    if heading not in lines:
        return None
    start = lines.index(heading) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    body = "\n".join(lines[start:end]).strip()
    return body + "\n" if body else None


def changelog_errors(root, version):
    if changelog_section(root, version) is None:
        return [f"fail changelog: CHANGELOG.md has no section ## {version}"]
    return []


def tracked(root):
    """The paths git tracks, or None when root is not a git repository."""
    out = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return set(p for p in out.stdout.split("\0") if p)


def uncommitted(root):
    """Tracked files whose text differs from the commit: a release is built from what is committed."""
    out = subprocess.run(["git", "-C", root, "diff", "--no-renames", "--name-only", "-z", "HEAD"],
                         capture_output=True, text=True)
    return sorted(p for p in out.stdout.split("\0") if p)


def wheel_paths(names):
    """Repository paths of the wheel entries: solo_sdd/data/<x> is <x>, metadata is skipped."""
    paths = []
    for name in names:
        if name.endswith("/") or ".dist-info/" in name:
            continue
        paths.append(name[len("solo_sdd/data/"):] if name.startswith("solo_sdd/data/") else name)
    return paths


def prefixed_paths(names, generated=()):
    """Repository paths of an archive whose entries sit under one top folder (sdist, npm tarball)."""
    paths = []
    for name in names:
        rest = name.split("/", 1)[1] if "/" in name else ""
        if rest and not name.endswith("/") and rest not in generated:
            paths.append(rest)
    return paths


def content_errors(package, paths, known, banned=NOT_SHIPPED):
    """Lines for packed paths git does not track and for paths under the folders the package must not hold."""
    errors = []
    for path in sorted(set(paths)):
        if path not in known:
            errors.append(f"fail {package}: {path} is not tracked by git")
        elif path.startswith(banned):
            errors.append(f"fail {package}: {path} lies in a folder that is not shipped")
    return errors


def run(args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def build(root, out):
    """sdist, the wheel built from it (python -m build does that) and npm pack; the error text or None."""
    r = run([sys.executable, "-m", "build", "--outdir", out, root])
    if r.returncode != 0:
        if "No module named build" in r.stderr:
            return "python -m build is missing: python3 -m pip install build"
        return "python -m build failed:\n" + (r.stdout + r.stderr)[-2000:]
    npm = shutil.which("npm")
    if not npm:
        return "npm is missing: Node 20+ with npm is needed"
    r = run([npm, "pack", "--pack-destination", out], cwd=root)
    if r.returncode != 0:
        return "npm pack failed:\n" + (r.stdout + r.stderr)[-2000:]
    return None


def smoke(out, files, version):
    """--version from a new venv with the wheel and from a new npm prefix with the tarball."""
    errors = []
    with tempfile.TemporaryDirectory() as tmp:
        venv = os.path.join(tmp, "venv")
        r = run([sys.executable, "-m", "venv", venv])
        pip = os.path.join(venv, "bin", "pip")
        if r.returncode == 0:
            r = run([pip, "install", "--no-deps", "--no-index", os.path.join(out, files["wheel"])])
        got = run([os.path.join(venv, "bin", "solo-sdd"), "--version"]).stdout.strip() if r.returncode == 0 else ""
        print(f"wheel --version: {got or 'not installed'}")
        if got != version:
            errors.append(f"fail wheel smoke: --version printed {got or 'nothing'}, wants {version}"
                          + ("" if r.returncode == 0 else "\n" + (r.stdout + r.stderr)[-1000:]))
        prefix = os.path.join(tmp, "npm")
        env = dict(os.environ, npm_config_cache=os.path.join(tmp, "cache"))
        r = run([shutil.which("npm"), "i", "-g", "--prefix", prefix, os.path.join(out, files["npm"])], env=env)
        got = run([os.path.join(prefix, "bin", "solo-sdd"), "--version"]).stdout.strip() if r.returncode == 0 else ""
        print(f"npm --version: {got or 'not installed'}")
        if got != version:
            errors.append(f"fail npm smoke: --version printed {got or 'nothing'}, wants {version}"
                          + ("" if r.returncode == 0 else "\n" + (r.stdout + r.stderr)[-1000:]))
    return errors


def check(root, tag, out):
    versions = read_versions(root)
    errors = version_errors(tag, versions)
    if errors:
        return errors
    version = tag[1:]
    errors = changelog_errors(root, version)
    if errors:
        return errors
    known = tracked(root)
    if known is None:
        return [f"fail git: {root} is not a git repository"]
    errors = [f"fail uncommitted: {path} differs from the commit" for path in uncommitted(root)]
    if errors:
        return errors
    os.makedirs(out, exist_ok=True)
    for name in os.listdir(out):
        if OWN_FILES.match(name):
            os.remove(os.path.join(out, name))
    failed = build(root, out)
    if failed:
        return ["fail build: " + failed]
    files = {"sdist": f"solo_sdd-{version}.tar.gz", "wheel": f"solo_sdd-{version}-py3-none-any.whl",
             "npm": f"solo-sdd-{version}.tgz"}
    built = sorted(n for n in os.listdir(out) if OWN_FILES.match(n))
    errors += [f"fail file {n}: not the version {version}" for n in built if n not in files.values()]
    errors += [f"fail file {f}: not built" for f in files.values() if f not in built]
    if errors:
        return errors
    for kind in ("sdist", "wheel", "npm"):
        print(f"{files[kind]} {os.path.getsize(os.path.join(out, files[kind]))}")
    with tarfile.open(os.path.join(out, files["sdist"])) as t:
        errors += content_errors("sdist", prefixed_paths(t.getnames(), ("PKG-INFO",)), known, SDIST_NOT_SHIPPED)
    with zipfile.ZipFile(os.path.join(out, files["wheel"])) as z:
        errors += content_errors("wheel", wheel_paths(z.namelist()), known)
    with tarfile.open(os.path.join(out, files["npm"])) as t:
        errors += content_errors("npm", prefixed_paths(t.getnames()), known)
    if errors:
        return errors
    return smoke(out, files, version)


def notes(root, tag):
    version = tag[1:] if tag.startswith("v") else None
    if version is None:
        print(f"fail tag {tag}: a release tag is v<version>")
        return 1
    section = changelog_section(root, version)
    if section is None:
        print(changelog_errors(root, version)[0])
        return 1
    print(section, end="")
    return 0


def main(argv):
    args = list(argv)
    if args[:1] == ["--notes"]:
        if len(args) != 2:
            print(__doc__.strip().splitlines()[2])
            return 2
        return notes(ROOT, args[1])
    out = os.path.join(ROOT, "dist")
    if "--out" in args:
        i = args.index("--out")
        if i + 1 >= len(args):
            print(__doc__.strip().splitlines()[2])
            return 2
        out = os.path.abspath(args[i + 1])
        del args[i:i + 2]
    if len(args) != 1:
        print(__doc__.strip().splitlines()[2])
        return 2
    errors = check(ROOT, args[0], out)
    for line in errors:
        print(line)
    if not errors:
        print(f"ok release {args[0]}: {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
