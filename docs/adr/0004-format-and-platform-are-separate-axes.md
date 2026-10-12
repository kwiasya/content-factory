---
status: accepted
date: 2026-10-11
---

# Format и Platform это разные оси; репо устроено по Format

Content Factory начиналась как фабрика одного Reel для Instagram, и пайплайн `/reel` был единственным. Теперь Author ведёт несколько Channel на нескольких Platform и хочет экспериментировать с формами видео. Решили: **Format** (длина, структура, лицо и голос, источник материала, от сценария или от материала) и **Platform** (куда публикуем) независимы. Один вертикальный Reel выходит на Instagram Reels, YouTube Shorts и TikTok как один Format с разными подписями и safe zone, а не как три пайплайна. Каждый Format заводится файлом `formats/<name>/format.md` плюс свой Style profile, Hook library и карта скиллов; общие модули `cf.*` (Resolve, цвет, Shot log, транскрипт) переиспользуются. Альтернатива «пайплайн на платформу» отвергнута: 95 % шагов дублировались бы, а эксперимент с новым форматом стоил бы неделю вместо получаса.

## Consequences

- `/reel` становится картой Format Walk Reel; у Tech explainer и Travel long появляются свои карты.
- `style.json` и `script-schema.md` в нынешнем виде описывают Walk Reel; при вводе второго Format общие поля выносятся, остальное уезжает в `formats/<name>/`.
- Исследование (Watchlist, Hook library) тоже делится по Format: хуки лонгов и хуки шортсов не смешиваются.
