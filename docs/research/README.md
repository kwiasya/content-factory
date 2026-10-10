# Research

Deep research для сборки Editor. Промпты лежат в `prompts/`, результаты кладутся сюда.

## Как запускать

1. Открыть `prompts/NN-тема.md`, скопировать всё между линиями `---`.
2. Запустить в ChatGPT Deep Research и в Claude Research.
3. Сохранить ответы как `NN-тема/chatgpt.md` и `NN-тема/claude.md`.
4. Когда все шесть готовы, агент сверяет ответы и сводит в план скиллов и инструментов.

## Сводка

Все шесть ответов получены (по одному, второй инструмент не запускался) и сведены в [SYNTHESIS.md](SYNTHESIS.md): закрытые решения, открытые вопросы, smoke-тесты, фазы v1.

## Промпты

| # | Файл | Тема | Статус |
|---|------|------|--------|
| 01 | `prompts/01-resolve-scripting-api.md` | Что агент может делать в Resolve Studio через API, готовые MCP и обёртки | 1 ответ получен (`01-resolve-scripting-api/result-a.md`), проверен по стабу (`verification.md`), ждёт второй |
| 02 | `prompts/02-overlays-and-motion-graphics.md` | Текстовые оверлеи, переходы, Remotion vs Fusion, safe zones | 1 ответ получен (`02-overlays-and-motion-graphics/result-a.md`), проверен (`verification.md`), ждёт второй |
| 03 | `prompts/03-color-iphone-osmo.md` | Цвет для iPhone HDR / Apple Log и Osmo D-Log M, экспорт под Instagram | 1 ответ получен (`03-color-iphone-osmo/result-a.md`), проверен (`verification.md`), ждёт второй |
| 04 | `prompts/04-video-understanding-shot-quality.md` | Как агент «видит» клипы: лучшие моменты, тряска, экспозиция, описание | 1 ответ получен (`04-video-understanding-shot-quality/result-a.md`), окружение проверено (`verification.md`), ждёт второй |
| 05 | `prompts/05-music-and-sound.md` | Откуда музыка, beat sync, чистка живого звука, громкость под Instagram | 1 ответ получен (`05-music-and-sound/result-a.md`), проверен (`verification.md`), ждёт второй |
| 06 | `prompts/06-reels-scripts-and-ai-landscape.md` | Как писать Script для travel Reels, обзор всех AI-инструментов 2026 | 1 ответ получен (`06-reels-scripts-and-ai-landscape/result-a.md`), проверен (`verification.md`), ждёт второй |

Общий блок контекста, вставленный в каждый промпт: `prompts/_context.md`. Если меняется железо или сетап, править там и перегенерировать промпты.

## Что не исследуем (решено)

- Распознавание локации и geocoding: делаем по метаданным → vision → вручную, без отдельного ресерча.
- Транскрипция и субтитры: речи пока нет, stable-ts уже установлен в `.venv` на будущее.
- Публикация через API и нарезка на несколько роликов: не в scope v1.
