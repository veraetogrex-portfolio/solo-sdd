"""Shared repository fixtures: a git fixture folder built once per process and key, a fresh copy of it per test.

template(key, build) runs build(folder) once for the key and returns (folder, what build returned); copy(folder)
copies the whole folder (every repository, remote and worktree in it) into a new temporary folder (or a given new
one) and rewrites every text that names the template folder (a remote URL, a worktree's gitdir, a file the fixture
wrote) to name the copy.
Git objects and the index are left as they are: they hold no absolute path a fixture writes. The caller removes the
copy; the templates are removed when the process exits.
"""
import atexit
import os
import pathlib
import shutil
import tempfile

_TEMPLATES = {}
_SKIP = {"objects", "index"}  # zlib-compressed objects and the binary index: rewriting would corrupt them


def template(key, build):
    """(folder, value): the folder build(folder) filled once for this key in this process, and what build returned."""
    if key not in _TEMPLATES:
        folder = pathlib.Path(tempfile.mkdtemp(prefix="shared-repo-")).resolve()
        atexit.register(shutil.rmtree, folder, True)
        try:
            value = build(folder)
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        _TEMPLATES[key] = (folder, value)
    return _TEMPLATES[key]


def copy(src, dst=None, also=None):
    """The folder dst (by default a new temporary one) with the content of src, in which no path names src any more.

    also maps more folders to the folders their paths become, for a src that is a part of a template whose other
    parts its files name (a clone's reflog names the repository it was cloned from)."""
    src = pathlib.Path(src).resolve()
    if dst is None:
        dst = pathlib.Path(tempfile.mkdtemp(prefix="shared-copy-")).resolve()
        shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)
    else:
        dst = pathlib.Path(dst).resolve()
        shutil.copytree(src, dst, symlinks=True)
    pairs = [(os.fsencode(str(src)), os.fsencode(str(dst)))]
    pairs += [(os.fsencode(str(pathlib.Path(o).resolve())), os.fsencode(str(n))) for o, n in (also or {}).items()]
    for d, dirs, files in os.walk(dst):
        if os.path.basename(d) == ".git" or os.path.isfile(os.path.join(d, "HEAD")):
            dirs[:] = [x for x in dirs if x not in _SKIP]  # a git folder (or a bare repository)
            files = [f for f in files if f not in _SKIP]
        for f in files:
            p = os.path.join(d, f)
            if os.path.islink(p):
                target = os.fsencode(os.readlink(p))
                for old, new in pairs:
                    if target == old or target.startswith(old + b"/"):
                        os.unlink(p)
                        os.symlink(new + target[len(old):], p)
                        break
                continue
            with open(p, "rb") as h:
                data = h.read()
            out = data
            for old, new in pairs:
                out = out.replace(old, new)
            if out != data:
                with open(p, "wb") as h:
                    h.write(out)
    return dst
