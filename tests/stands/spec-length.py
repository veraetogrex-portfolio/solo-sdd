"""Стенд spec-requirement-length: открытые change репозитория и игрушечный change demo.

Запуск из корня репозитория: python3 tests/stands/spec-length.py. Временную папку создаёт и убирает сам."""
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
import test_spec_length as t  # noqa: E402

ok = True


def step(name, got, want):
    global ok
    good = got == want
    ok &= good
    print("%s %s: %s" % ("ok " if good else "ПРОВАЛ", name, got if got else "длинных нет"))


step("открытые change репозитория", t.check(ROOT), [])

with tempfile.TemporaryDirectory() as d:
    rel = "openspec/changes/demo/specs/foo/spec.md"
    t.write(d, rel, t.delta("а" * 612, name="Длинное"))
    step("demo, требование 612 знаков", t.check(d), ["demo specs/foo Длинное: 612 > 500"])
    t.write(d, rel, t.delta("а" * 300 + "\n\n#### Scenario: Примеры\n- **WHEN** " + "б" * 312 + "\n- **THEN** ок",
                            name="Длинное"))
    step("demo после выноса примеров в сценарий", t.check(d), [])
    t.write(d, "openspec/specs/foo/spec.md", "# foo\n\n## Requirements\n\n### Requirement: Старое\n" + "в" * 900 + "\n")
    step("основная спека 900 знаков, только с --all", (t.check(d), t.check(d, main_specs=True)),
         ([], ["specs/foo Старое: 900 > 500"]))

print("итог: %s" % ("все шаги как ожидалось" if ok else "есть провалы"))
sys.exit(0 if ok else 1)
