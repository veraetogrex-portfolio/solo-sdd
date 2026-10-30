#!/usr/bin/env python3
"""Проверка поиска проектов и восстановления правил без изменения живых проектов."""
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "after_update", Path(__file__).with_name("openspec-after-update.py"))
script = importlib.util.module_from_spec(spec)

with tempfile.TemporaryDirectory() as tmp:
    with patch.dict(os.environ, {"HOME": tmp}):
        spec.loader.exec_module(script)
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
    script.PKG = str(home / "package")
    Path(script.PKG).mkdir()
    (Path(script.PKG) / "package.json").write_text(json.dumps({"version": "test"}))
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
    script.build_solo = lambda: []
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
    script.SDD_REPO = str(repo)
    logged = []
    script.log = logged.append
    assert script.main() == 0
    assert any("solo-sdd: обновлено spec-analyze push --quiet" in line for line in logged), logged
    script.SDD_REPO = str(home / "нет-такого")
    logged.clear()
    assert script.main() == 0
    assert any("не найден" in line for line in logged), logged
    script.log = print
print("OK: вложенные проекты без config.yaml найдены, правила сохранены, служебные папки пропущены, устаревший блок обновлён, sync.py вызывается")
