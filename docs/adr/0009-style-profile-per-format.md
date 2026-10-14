---
status: accepted
date: 2026-10-14
---

# У каждого Format один полный файл Style profile

ADR 0004 говорил: когда появится второй Format, общие для всех Format поля выносятся из `style.json`, остальное уезжает в `formats/<name>/`. Travel long и есть этот второй Format с пайплайном от материала: 16:9 при 29.97 fps, Author в кадре, минуты вместо секунд. Решение: каждому Format принадлежит `formats/<id>/style.json` (`cf-style/1`), полный профиль без слоя наследования. Корневой `style.json` остаётся профилем Walk Reel, пока не переедет в `formats/walk-reel/style.json` (фаза 3 работы над Travel long); тогда все его читатели переходят на выбор пути стиля по `format` из `video.json`: `cf.build`, `cf.render`, `cf.canvas`, `cf.render_check` (`STYLE_PATH`), `cf.script_schema` (`DEFAULT_STYLE`), проверка Script при сохранении в Desk (`cf/desk/videos_api.py`) и спека оверлеев (`style_path` в `overlays/render.mjs`). Два полных файла дешевле правила слияния, которое пришлось бы применять каждому читателю. Это заменяет пункт ADR 0004 «общие поля выносятся».

## Consequences

- `formats/travel-long/style.json` начинается как неполный черновик, который пока не читает никакой код: незаданные поля не решены, а не унаследованы; фаза 3 дописывает полный профиль раньше, чем его кто-то прочтёт. Desk показывает и правит его рядом с `FORMAT.md`.
- Риск: `cf.canvas.Canvas.fps` целое число и обрезает 29.97 до 29; фаза 3 сначала делает fps дробным.
- Изменение, нужное всем Format, вносится в каждый файл.
