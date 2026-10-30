"""Точка входа solo-sdd: разбор команд и сборка схемы solo."""
import os, shutil, subprocess, sys

from solo_sdd import __version__, doctor, hooks, layout, resources

layout.PULL_HINT = "solo-sdd sync pull"

COMMANDS = """команды solo-sdd:
  --version                          версия
  status                             состояние всех копий
  install [--hooks]                  разложить скиллы и правила, собрать схему solo; --hooks подключает хуки в settings.json
  uninstall [--purge]                снять копии и хуки; --purge удаляет ещё схему solo и данные solo-sdd
  doctor                             проверить окружение: python, openspec, схему, копии, хуки, gh
  update                             повторить раскладку и сборку схемы, подсказать обновление пакета
  sync pull <имя> [--from <место>]   забрать правку, сделанную на месте, в репозиторий"""


def upgrade_hint(prefix, root):
    if "/uv/tools/" in prefix:
        return "uv tool upgrade solo-sdd"
    if "/pipx/venvs/" in prefix:
        return "pipx upgrade solo-sdd"
    if "node_modules" in root:
        return "npm update -g solo-sdd"
    if os.path.exists(os.path.join(root, ".git")):
        return f"git pull в {root}"
    return "python3 -m pip install --upgrade git+https://github.com/veraetogrex-portfolio/solo-sdd"


def build_schema(force):
    if shutil.which("openspec") is None:
        print("fail openspec: не найден; поставьте: npm i -g @fission-ai/openspec")
        return 1
    if not force and os.path.exists(os.path.join(layout.HOME, ".local/share/openspec/schemas/solo/schema.yaml")):
        return 0
    result = subprocess.run(
        [sys.executable, os.path.join(resources.ROOT, "schema", "openspec-after-update.py"), "--schema-only"],
        capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL,
        env=dict(os.environ, HOME=layout.HOME))
    if result.returncode != 0:
        lines = [l for l in (result.stdout + "\n" + result.stderr).splitlines() if l.strip()]
        print(f"fail openspec: схема solo не собрана: {lines[-1].strip() if lines else 'нет вывода'}")
        return 1
    return 0


def install(with_hooks=False):
    before = layout.load_state()
    problems = layout.push()
    force = before != layout.load_state()
    schema = build_schema(force)
    connected = hooks.setup() if with_hooks else 0
    return 1 if problems or schema or connected else 0


def uninstall(purge=False):
    steps = layout.load_state().get("_hooks")
    code = hooks.restore(steps) if steps else 0
    if code == 0:
        state = layout.load_state()
        if state.pop("_hooks", None) is not None:
            layout.save_state(state)
    return 1 if layout.uninstall(purge) or code else 0


def update():
    problems = layout.push()
    schema = build_schema(True)
    print(upgrade_hint(sys.prefix, layout.REPO))
    return 1 if problems or schema else 0


def status():
    state = layout.load_state()
    print(f"источник: {state.get('_source', layout.REPO)} {state.get('_version', __version__)}")
    layout.status()
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv == ["--version"]:
        print(__version__)
        return 0
    if argv in (["status"], ["update"], ["doctor"]):
        return {"status": status, "update": update, "doctor": doctor.run}[argv[0]]()
    if argv and argv[0] == "install" and argv[1:] in ([], ["--hooks"]):
        return install(bool(argv[1:]))
    if argv and argv[0] == "uninstall" and argv[1:] in ([], ["--purge"]):
        return uninstall(bool(argv[1:]))
    if argv[:2] == ["sync", "pull"]:
        return layout.main(argv[1:])
    print(COMMANDS)
    return 2
