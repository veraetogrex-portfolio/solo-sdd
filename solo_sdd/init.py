"""solo-sdd init: подготовить git-репозиторий проекта к работе по спекам."""
import os, re, shutil, subprocess

from solo_sdd import resources

INSTALL = "fail openspec: не найден; поставьте: npm i -g @fission-ai/openspec"


def _openspec(args, folder):
    try:
        return subprocess.run(["openspec", *args], cwd=folder, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(args, 1, "", f"openspec {' '.join(args)}: {e}")


def _copy(folder, src, dst, replace=False):
    target = os.path.join(folder, dst)
    if os.path.exists(target) and not replace:
        return
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copyfile(os.path.join(resources.ROOT, "templates", src), target)
    print(f"создано {dst}")


def run(folder="."):
    folder = os.path.abspath(folder)
    if not os.path.exists(os.path.join(folder, ".git")):
        print("не git-репозиторий: git init")
        return 1
    config = os.path.join(folder, "openspec", "config.yaml")
    had_config = os.path.exists(config)
    if not os.path.isdir(os.path.join(folder, "openspec")):
        if shutil.which("openspec") is None:
            print(INSTALL)
            return 1
        p = _openspec(["init", "--tools", "claude,codex"], folder)
        if p.returncode != 0:
            print("\n".join((p.stdout + p.stderr).strip().splitlines()[-10:]))
            return 1
    if had_config:
        with open(config, encoding="utf-8", errors="replace") as f:
            m = re.search(r"^schema:\s*(\S+)", f.read(), re.M)
        print(f"config.yaml уже есть: schema {m.group(1) if m else '?'}")
    else:
        _copy(folder, "openspec/config.yaml", "openspec/config.yaml", replace=True)
    _copy(folder, "openspec/analyze.md", "openspec/analyze.md")
    _copy(folder, "docs/waiting.md", "docs/waiting.md")
    if shutil.which("openspec") and not re.search(r"(?m)^\s*solo\b", _openspec(["schemas"], folder).stdout):
        print("warn: схемы solo нет в openspec schemas")
    print("дальше: /project-init в Claude Code или Codex")
    return 0
