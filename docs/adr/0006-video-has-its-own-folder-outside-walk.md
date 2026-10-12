---
status: accepted
date: 2026-10-12
---

# У Video своя папка вне Walk, а у Format свой файл описания

Готовое видео до сих пор жило внутри съёмки: `~/Movies/content-factory/<walk>/reels/<reel>/`. Это держалось, пока единственным Format был Walk Reel: один Walk, один или несколько Reel из него. Первый лонг про плагин autopilot-jobsearch не имеет Walk вовсе и лёг в «прогулку без клипов»; Travel long собирается из нескольких Walk (Вена, Майорка) и не вкладывается ни в одну из них. Author хочет видеть в Desk список видео как проектов, открывать одно и видеть всё, что для него сделано, структурированно.

Решение: сущность Video (`GLOSSARY.md`) получает свою папку `~/Movies/content-factory/videos/<slug>/` с фиксированной структурой: `video.json` (Format, Channel, Walk-источники, статус жизненного цикла с датами переходов, URL публикации), `brief.md`, `script.*`, `voiceover.md` (Voice-over: только произносимый текст, без указаний по кадру), `sources/` (ссылки или копии Clip, скринкасты, запись лица), `overlays/`, `subtitles/`, `renders/` (по версиям, проверенный рендер не перезаписывается), `references.md`, `notes.md`. Walk остаётся пулом Clip (`<walk>/raw`, `proxy`, `shotlog`) и ничего готового не содержит. Format получает `formats/<id>/FORMAT.md` в репо: описание формата, которое читают скиллы сценария и Desk, рядом с его Hook library.

Альтернатива, отвергнутая: оставить вложение в Walk и заводить «Walk без клипов» для форматов от сценария. Это ломается на первом лонге из двух прогулок и смешивает «что снято» с «что выпущено».

## Consequences

- `build-reel`, `render-reel`, `beat-grid`, `write-script`, `reel`, `ingest-walk`, `docs/script-schema.md`, `style.json`, `cf.build`, `cf.render` читают путь `videos/<slug>/` вместо `<walk>/reels/<reel>/`; существующие Reel переезжают скриптом миграции с сохранением рендеров.
- Статус Video живёт в его папке, не в `factory.db`: папку можно унести целиком. В базе только Note и связи Video ↔ Reference ↔ Idea.
- Desk строит список проектов по `videos/*/video.json`; экран Format по `formats/<id>/FORMAT.md`, Hook library и списку Video этого Format.
- Пока миграция не сделана, новое видео без Walk заводится сразу в `videos/`, а Reel остаются на старом пути.
