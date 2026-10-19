---
status: accepted
date: 2026-10-15
---

# Meme cut собирается ffmpeg-ом, а не в Resolve

Первый Meme cut («Свидание — мой мозг») собран разовым скриптом ffmpeg: мем низкого разрешения стоит целиком по ширине кадра поверх своей размытой, затемнённой, увеличенной копии. В Resolve это эффект Resolve FX или композиция Fusion на каждом клипе, а Resolve FX на клипе вне scripting API (`docs/resolve-rules.md`, Known gaps), смоук S11 с картинками на V4/V5 ещё не прогнан. Решение: у Meme cut свой сборщик `cf.memecut`, который по Script `cf-memecut/1` делает одно видео одним вызовом ffmpeg (сетап из mezzanine Apple, оверлеи из Remotion, вставки, финал, тихая дорожка) и проверяет его `cf.render_check`. Математика размещения (`blur-fill` / `fill`, `trim` краёв, без растяжения) чистая и покрыта тестами. Отвергнуто: режим `fit: "blur-fill"` у картинки-Cue на V4/V5 в `cf.build`; он требовал бы Fusion-композиции через API, которые нельзя прочитать обратно, а Meme cut не пользуется ничем из Resolve (ни Track, ни Look, ни Super Scale, ни правки Author на таймлайне).

## Consequences

- Meme cut не открывается в Resolve для ручной правки: правится Script, ролик пересобирается (ADR 0001 в той же логике: таймлайн из плана).
- `cf.render_check` принимает тихую дорожку для Format без музыки (`audio.music: false` в его профиле, `--silent`, `--format`).
- Desk проверяет `script*.json` со схемой `cf-memecut/1` валидатором `cf.memecut` (без Library; правило совпадения проверяет `cf.memecut validate`).
- Если Resolve позже понадобится (например, звук мемов под Track), размещение уже описано в `cf.memecut.place` и переносится в Cue без изменения правил.
