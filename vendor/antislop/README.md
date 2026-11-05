# Закреплённая копия anti-slop

Копия правил anti-slop (https://github.com/miqdadbadjuber/anti-slop), лицензия MIT — в `LICENSE`. Нужна скиллу `ui-check`.

Откуда: релиз и коммит записаны в `VERSION` (две строки).

Что взято: `antislop.md`, `skills/antislop-ui`, `skills/antislop-human` (без `contrast-mcp.py`), `skills/antislop-layoutmobile`. Не взяты: `contrast-mcp.py`, `antislop-code`, установщик, плагины.

Как раскладывается: `sync.py push` по `targets.json["files"]` кладёт файлы в `<корень>/ui-check/antislop/` под именами `core.md`, `ui.md`, `human.md`, `layoutmobile.md`, `contrast-check.py`, `references/…`. Лицензии, `README.md` и `VERSION` не раскладываются.

Как обновлять: целиком заменить копию файлами нового релиза, обновить `VERSION`, дифф оставить в коммите, прогнать `python3 tests/test_vendor_antislop.py`. Во время работы ничего из сети не скачивается. Текст копии не правится.
