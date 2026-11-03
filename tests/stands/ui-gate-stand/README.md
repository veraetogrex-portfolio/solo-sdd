# ui-gate-stand

Стенд для живого сценария `ui-check-gate` (`openspec/changes/ui-check-gate/verification.md`): лендинг с намеренно заложенными нарушениями. Заложены: `#pricing` без раздела, `#999999` на `#FFFFFF`, «10K+ users», кликабельный div, форма без `<label>`, кнопка «Get Started», заглушка отзывов, «Fast — and simple» и «Осень — приложение для заметок». Всё остальное чисто. Ожидаемый вердикт — `EXPECTED.md`.

## Подготовка

```
cd /путь/к/solo-sdd
cp -r tests/stands/ui-gate-stand /tmp/ui-gate-stand
cd /tmp/ui-gate-stand
mkdir /tmp/ui-gate-aux
mv EXPECTED.md DESIGN-step3.md stand-form.patch /tmp/ui-gate-aux/
rm -rf openspec/changes/stand-form
git init
git add -A
git commit -m base
openspec init --tools claude,codex
python3 -m http.server 8765
```

`EXPECTED.md`, `DESIGN-step3.md` и `stand-form.patch` в рабочую копию не входят: их держи в `/tmp/ui-gate-aux/`. Папка `openspec/changes/stand-form` берётся из репозитория для шага 6 (копируется в копию шага 6). Сервер запускай отдельной фоновой задачей.

## Шаг 3

```
cp -r /tmp/ui-gate-stand /tmp/ui-gate-stand-3
cd /tmp/ui-gate-stand-3
cp /tmp/ui-gate-aux/DESIGN-step3.md DESIGN.md
```

Папка `tests/` с `keep.txt` уже в стенде; её целость проверяется после `/ui-check`.

## Шаг 6

```
cp -r /tmp/ui-gate-stand /tmp/ui-gate-stand-6
cd /tmp/ui-gate-stand-6
cp -r /путь/к/solo-sdd/tests/stands/ui-gate-stand/openspec/changes/stand-form openspec/changes/stand-form
git apply /tmp/ui-gate-aux/stand-form.patch
git add -A
git commit -m "stand-form"
```

## Шаг 7

Сервер не запускать, браузер не подключать; в копии `/tmp/ui-gate-stand` запустить `/ui-check`.
