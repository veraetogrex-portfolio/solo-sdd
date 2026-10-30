#!/usr/bin/env python3
"""Проверка поиска проектов и восстановления правил без изменения живых проектов."""
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "after_update", Path(__file__).with_name("openspec-after-update.py"))
script = importlib.util.module_from_spec(spec)

with tempfile.TemporaryDirectory() as tmp:
    with patch.dict(os.environ, {"HOME": tmp}):
        spec.loader.exec_module(script)
    env_patch = patch.dict(os.environ, {"OPENSPEC_PKG": f"{tmp}/package"})
    env_patch.start()
    os.environ.pop("SOLO_SDD_REPO", None)
    script.BREW_PKGS = (f"{tmp}/нет-brew-1", f"{tmp}/нет-brew-2")
    script.CALL_PATH = "/нет-такой-папки"
    home = Path(tmp)
    projects = [home / "Desktop/project/Переименованный проект",
                home / "Documents/Другой проект"]
    ignored = [home / ".cache/пример", home / "Desktop/app/node_modules/пример",
               home / "Library/пример", projects[0] / "openspec/пример"]
    for project in projects + ignored:
        (project / "openspec").mkdir(parents=True)
        skill = project / ".agents/skills/openspec-apply-change/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: openspec-apply-change\n---\n\nИсходный текст\n")
    pkg = home / "package"
    (pkg / "schemas/spec-driven").mkdir(parents=True)
    (pkg / "schemas/spec-driven/schema.yaml").write_text("name: spec-driven\n")
    (pkg / "package.json").write_text(json.dumps({"version": "test"}))
    script.STAMP = str(home / "stamp")
    Path(script.STAMP).write_text("test")
    script.log = print
    script.notify = lambda text: None
    script.sys.argv = ["openspec-after-update.py"]

    assert script.main() == 0
    for project in projects:
        skill = project / ".agents/skills/openspec-apply-change/SKILL.md"
        assert "<!-- solo-override -->" in skill.read_text(), f"Проект пропущен: {project}"

    updated = []
    script.build_solo = lambda pkg: []
    script.run = lambda cmd, cwd=None: (updated.append(cwd) or
        type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    Path(script.STAMP).write_text("old")
    assert script.main() == 0
    assert set(updated) == {str(p) for p in projects}, updated
    assert Path(script.STAMP).read_text() == "test"
    assert script.main() == 0
    assert len(updated) == len(projects), "Повторный запуск обновил проекты заново"
    for project in projects:
        text = (project / ".agents/skills/openspec-apply-change/SKILL.md").read_text()
        assert text.count("<!-- solo-override -->") == 1
        assert text.endswith("Исходный текст\n")
    for project in ignored:
        text = (project / ".agents/skills/openspec-apply-change/SKILL.md").read_text()
        assert "<!-- solo-override -->" not in text
    # Устаревший блок владельца заменяется текущим, текст скилла не теряется.
    old = projects[0] / ".agents/skills/openspec-apply-change/SKILL.md"
    old.write_text("---\nname: openspec-apply-change\n---\n\n<!-- solo-override -->\n> старое правило\n"
                   "<!-- /solo-override -->\n\nИсходный текст\n")
    assert script.main() == 0
    text = old.read_text()
    assert "старое правило" not in text and "spec-analyze" in text, text
    assert text.count("<!-- solo-override -->") == 1 and text.endswith("Исходный текст\n")
    before = text
    assert script.main() == 0
    assert old.read_text() == before, "Актуальный блок переписан повторно"
    # Скиллы раскладывает sync.py из репозитория solo-sdd; его вывод попадает в лог.
    repo = home / "solo-sdd"; repo.mkdir()
    (repo / "sync.py").write_text("import sys\nprint('обновлено spec-analyze', ' '.join(sys.argv[1:]))\n")
    state_file = home / ".local/share/solo-sdd/state.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(json.dumps({"_source": str(repo)}))
    logged = []
    script.log = logged.append
    assert script.main() == 0
    assert any(str(repo) in line and "раскладка из" in line for line in logged), logged
    assert any("solo-sdd: обновлено spec-analyze push --quiet" in line for line in logged), logged
    state_file.write_text(json.dumps({"_source": str(home / "нет-такого")}))
    logged.clear()
    assert script.main() == 0
    assert any("не найден" in line for line in logged), logged
    script.log = print
    env_patch.stop()
print("OK: вложенные проекты без config.yaml найдены, правила сохранены, служебные папки пропущены, устаревший блок обновлён, sync.py вызывается")


# ---- Поиск пакета, источник раскладки, --schema-only: настоящий subprocess с поддельными npm и openspec ----
def sh(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def load(home, mocks=True):
    """Свежий модуль под своей домашней папкой; BREW_PKGS и CALL_PATH не ведут на настоящие."""
    with patch.dict(os.environ, {"HOME": str(home)}):
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    m.BREW_PKGS = (str(home / "нет-brew-1"), str(home / "нет-brew-2"))
    m.CALL_PATH = "/нет-такой-папки"
    m.ENV["PATH"] = m.CALL_PATH
    m.logged = []
    if mocks:
        m.log = m.logged.append
        m.notified = []
        m.notify = m.notified.append
    return m


def fake_pkg(prefix, mark, extra=""):
    """<префикс>/lib/node_modules/@fission-ai/openspec и <префикс>/bin/openspec, пишущий свой PATH в mark."""
    pkg = prefix / "lib/node_modules/@fission-ai/openspec"
    (pkg / "schemas/spec-driven/templates").mkdir(parents=True)
    (pkg / "schemas/spec-driven/schema.yaml").write_text("\n".join(a for a, _ in script.PATCHES) + extra)
    (pkg / "schemas/spec-driven/templates/proposal.md").write_text("# proposal\n")
    (pkg / "package.json").write_text(json.dumps({"version": "9.9"}))
    sh(prefix / "bin/openspec", f'echo "$PATH" > "{mark}"\necho "Schema solo is valid"\n')
    return str(pkg)


def fake_npm(folder, root):
    sh(folder / "npm", f'echo "{root}"\n')
    return str(folder)


def fake_repo(folder, mark):
    folder.mkdir(parents=True)
    (folder / "sync.py").write_text(f"open({str(mark)!r}, 'w').write('x')\nprint('разложено')\n")
    return str(folder)


def run_main(m, *argv, **env):
    """main() с чистыми OPENSPEC_PKG и SOLO_SDD_REPO; env добавляет свои."""
    with patch.dict(os.environ, env), patch.object(sys, "argv", ["openspec-after-update.py", *argv]):
        for k in ("OPENSPEC_PKG", "SOLO_SDD_REPO"):
            if k not in env:
                os.environ.pop(k, None)
        return m.main()


def old_solo(m):
    Path(m.SOLO).mkdir(parents=True)
    (Path(m.SOLO) / "old.txt").write_text("прежняя")


def old_solo_intact(m):
    return (Path(m.SOLO) / "old.txt").read_text() == "прежняя" and not (Path(m.SOLO) / "schema.yaml").exists() \
        and not os.path.exists(m.SOLO + ".new")


def solo_text(m):
    return (Path(m.SOLO) / "schema.yaml").read_text()


# 1. npm root -g: пакет найден, схема установлена, PATH дочернего openspec начинается с <префикс>/bin, пакет в журнале
with tempfile.TemporaryDirectory() as t:
    home = Path(t); w = home / ".w"; m = load(home); mark = w / "mark"
    pkg = fake_pkg(w / "p1", mark)
    npm = fake_npm(w / "npmbin", w / "p1/lib/node_modules")
    assert run_main(m, "--schema-only", PATH=npm) == 0, m.logged
    assert "name: solo" in solo_text(m)
    assert mark.read_text().startswith(f"{w}/p1/bin:"), mark.read_text()
    assert any(pkg in line for line in m.logged), m.logged

# 2. OPENSPEC_PKG главнее npm; неподходящий OPENSPEC_PKG пропускается
with tempfile.TemporaryDirectory() as t:
    home = Path(t); w = home / ".w"; mark = w / "mark"
    npm_pkg = fake_pkg(w / "p1", mark)
    env_pkg = fake_pkg(w / "p2", mark, extra="\n# из-OPENSPEC_PKG")
    npm = fake_npm(w / "npmbin", w / "p1/lib/node_modules")
    m = load(home)
    assert run_main(m, "--schema-only", PATH=npm, OPENSPEC_PKG=env_pkg) == 0
    assert "# из-OPENSPEC_PKG" in solo_text(m) and any(env_pkg in line for line in m.logged), m.logged
    (home / "пустая").mkdir()
    m = load(home)
    assert run_main(m, "--schema-only", PATH=npm, OPENSPEC_PKG=str(home / "пустая")) == 0
    assert "# из-OPENSPEC_PKG" not in solo_text(m) and any(npm_pkg in line for line in m.logged), m.logged
    # Короткий путь (нет <префикс>/lib/node_modules/...) не роняет поиск.
    cwd = os.getcwd(); os.chdir(env_pkg + "/..")
    with patch.dict(os.environ, {"OPENSPEC_PKG": "openspec"}):
        assert m.find_pkg()[0] == "openspec"
    os.chdir(cwd)

# 3. Пакета нет: код 1, четыре источника в журнале, прежняя схема цела, sync не вызывался
for npm_exists in (True, False):
    with tempfile.TemporaryDirectory() as t:
        home = Path(t); w = home / ".w"; m = load(home)
        (w / "empty").mkdir(parents=True)
        npm = fake_npm(w / "npmbin", w / "empty") if npm_exists else str(w / "нет-npm")
        synced = w / "synced"
        repo = fake_repo(w / "repo", synced)
        old_solo(m)
        assert run_main(m, PATH=npm, SOLO_SDD_REPO=repo) == 1
        log_text = "\n".join(m.logged)
        assert "OPENSPEC_PKG (не задан)" in log_text and "npm root -g" in log_text, log_text
        assert all(b in log_text for b in m.BREW_PKGS), log_text
        assert npm_exists or "npm недоступен" in log_text, log_text
        assert old_solo_intact(m) and not synced.exists()

# 4. openspec не запускается: код 1, прежняя схема с меткой цела, новая не осталась, в журнале причина
for argv in ((), ("--schema-only",)):
    with tempfile.TemporaryDirectory() as t:
        home = Path(t); w = home / ".w"; m = load(home)
        pkg = fake_pkg(w / "p1", w / "mark")
        (w / "p1/bin/openspec").unlink()
        old_solo(m)
        assert run_main(m, *argv, PATH=str(w / "пусто"), OPENSPEC_PKG=pkg) == 1, m.logged
        assert old_solo_intact(m) and any("не запускается" in line for line in m.logged), m.logged

# 5. notify вне macOS не запускает osascript
with tempfile.TemporaryDirectory() as t:
    m = load(Path(t), mocks=False)
    for platform, calls in (("linux", 0), ("darwin", 1)):
        with patch.object(sys, "platform", platform), patch.object(m.subprocess, "run") as fake_run:
            m.notify("текст")
        assert fake_run.call_count == calls, (platform, fake_run.call_count)
        assert calls == 0 or fake_run.call_args[0][0][0] == "osascript"

# 6. Источник раскладки; проекты обходятся и при пропуске раскладки
with tempfile.TemporaryDirectory() as t:
    home = Path(t); w = home / ".w"; mark = w / "mark"
    pkg = fake_pkg(w / "p1", mark)
    state = home / ".local/share/solo-sdd/state.json"
    state.parent.mkdir(parents=True)
    project = home / "проект"
    (project / "openspec").mkdir(parents=True)
    skill = project / ".agents/skills/openspec-apply-change/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: x\n---\n\nтекст\n")
    ra, rb = w / "a-synced", w / "b-synced"
    repo_a, repo_b = fake_repo(w / "repo-a", ra), fake_repo(w / "repo-b", rb)
    state.write_text(json.dumps({"_source": repo_a}))
    m = load(home)
    assert run_main(m, "--force", OPENSPEC_PKG=pkg) == 0, m.logged
    assert ra.exists() and any("раскладка из " + repo_a in line for line in m.logged), m.logged
    assert any(pkg in line and "OpenSpec" in line for line in m.logged), m.logged
    ra.unlink()
    m = load(home)
    assert run_main(m, "--force", OPENSPEC_PKG=pkg, SOLO_SDD_REPO=repo_b) == 0
    assert rb.exists() and not ra.exists() and any("раскладка из " + repo_b in line for line in m.logged)
    rb.unlink()
    m = load(home)
    assert run_main(m, "--force", OPENSPEC_PKG=pkg, SOLO_SDD_REPO=str(w / "без-sync")) == 0
    assert not ra.exists() and not rb.exists() and any("не найден" in line for line in m.logged), m.logged
    for bad in ("{сломан", "[]", json.dumps({"_source": 5}), json.dumps({})):
        state.write_text(bad)
        shutil.rmtree(Path(m.DATA) / "schemas", ignore_errors=True)
        skill.write_text("---\nname: x\n---\n\nтекст\n")
        m = load(home)
        assert run_main(m, "--force", OPENSPEC_PKG=pkg) == 0, (bad, m.logged)
        assert sum("не найден" in line for line in m.logged) == 1, m.logged
        assert not ra.exists() and "name: solo" in solo_text(m)
        assert "<!-- solo-override -->" in skill.read_text(), "проекты не обойдены"

# 7. --schema-only: без sync, без обхода проектов, без STAMP, без notify; схема есть
with tempfile.TemporaryDirectory() as t:
    home = Path(t); w = home / ".w"
    pkg = fake_pkg(w / "p1", w / "mark")
    synced = w / "synced"
    repo = fake_repo(w / "repo", synced)
    project = home / "проект"
    (project / "openspec").mkdir(parents=True)
    skill = project / ".agents/skills/openspec-apply-change/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: x\n---\n\nтекст\n")
    m = load(home)
    m.find_projects = lambda: (_ for _ in ()).throw(AssertionError("обход проектов"))
    Path(m.STAMP).parent.mkdir(parents=True, exist_ok=True)
    Path(m.STAMP).write_text("прежняя")
    assert run_main(m, "--schema-only", "--force", OPENSPEC_PKG=pkg, SOLO_SDD_REPO=repo) == 0, m.logged
    assert not synced.exists() and m.notified == [] and Path(m.STAMP).read_text() == "прежняя"
    assert "solo-override" not in skill.read_text() and "name: solo" in solo_text(m)
# 8. Homebrew как источник: второй путь BREW_PKGS, npm недоступен, OPENSPEC_PKG не задан
with tempfile.TemporaryDirectory() as t:
    home = Path(t); w = home / ".w"; mark = w / "mark"; m = load(home)
    pkg = fake_pkg(w / "brew", mark)
    m.BREW_PKGS = (str(home / "нет-brew-1"), pkg)
    assert run_main(m, "--schema-only", PATH=str(w / "пусто")) == 0, m.logged
    assert "name: solo" in solo_text(m) and mark.read_text().startswith(f"{w}/brew/bin:"), mark.read_text()
    assert any(pkg in line for line in m.logged), m.logged

# 9. npm только в CALL_PATH: PATH процесса — пустая папка
with tempfile.TemporaryDirectory() as t:
    home = Path(t); w = home / ".w"; mark = w / "mark"; m = load(home)
    pkg = fake_pkg(w / "p1", mark)
    m.CALL_PATH = fake_npm(w / "npmbin", w / "p1/lib/node_modules")
    (w / "пусто").mkdir()
    assert run_main(m, "--schema-only", PATH=str(w / "пусто")) == 0, m.logged
    assert "name: solo" in solo_text(m) and any(pkg in line for line in m.logged), m.logged

# 10. openspec не принимает схему: ошибка и код 1, прежняя схема цела, текст ошибки в журнале
with tempfile.TemporaryDirectory() as t:
    home = Path(t); w = home / ".w"; m = load(home)
    pkg = fake_pkg(w / "p1", w / "mark")
    sh(w / "p1/bin/openspec", 'echo "ошибка-схемы-xyz" >&2\nexit 1\n')
    old_solo(m)
    assert run_main(m, "--schema-only", OPENSPEC_PKG=pkg) == 1, m.logged
    assert old_solo_intact(m) and any("ошибка-схемы-xyz" in line for line in m.logged), m.logged
print("OK: пакет ищется через OPENSPEC_PKG, npm и Homebrew, PATH и источник раскладки, --schema-only")
