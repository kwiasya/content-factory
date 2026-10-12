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
| 07 | `prompts/07-retention-long-form.md` | Кривая удержания в лонгах: анатомия, первые 30 с, re-hooking, темп, диагностика | готово: `chatgpt.md`, `result-a.md`, `rules.md` |
| 08 | `prompts/08-hooks-first-30-seconds.md` | Хуки и первые 30 с (лонг) / 3 с (шорт), проверка таксономии хуков | готово: `chatgpt.md`, `result-a.md`, `rules.md` |
| 09 | `prompts/09-storytelling-structures.md` | Структуры сторителлинга по длинам, ставки и payoff, проверка таксономии форматов и стилей | готово: `chatgpt.md`, `result-a.md`, `rules.md` |
| 10 | `prompts/10-emotion-and-attention.md` | Психология внимания и эмоций: curiosity gap, suspense, арки, парасоциальность, нагрузка | готово: `chatgpt.md`, `result-a.md`, `rules.md` |
| 11 | `prompts/11-short-form-shorts-tiktok-reels.md` | Короткий формат: Shorts / TikTok / Reels, первая секунда, loop, safe zone, кросспостинг | готово: `chatgpt.md`, `result-a.md`, `rules.md` |
| 12 | `prompts/12-packaging-titles-thumbnails-ideas.md` | Упаковка и идея: заголовки, превью, CTR, валидация идеи до съёмки | готово: `chatgpt.md`, `result-a.md`, `rules.md` |
| 13 | `prompts/13-creator-playbooks.md` | Плейбуки креаторов: документ MrBeast, другие школы, что переносимо на одного человека | готово: `chatgpt.md`, `result-a.md`, `rules.md` |
| 14 | `prompts/14-analytics-and-iteration.md` | Чтение аналитики, диагностика, программный доступ к удержанию (YouTube, TikTok, Instagram API) | готово: `chatgpt.md`, `result-a.md`, `rules.md` |

Общий блок контекста, вставленный в каждый промпт: `prompts/_context.md`. Если меняется железо или сетап, править там и перегенерировать промпты.

Серия 07–14 (удержание, хуки, сторителлинг, эмоции, упаковка, аналитика) использует свой блок `prompts/_context-content.md`: без железа и Resolve, с иерархией источников и пометкой уровня доказательности (DATA / PRACTITIONER / THEORY) на каждом правиле. Ответы: `NN-тема/chatgpt.md` от ChatGPT Deep Research (получены 2026-10-12, маркеры цитат ChatGPT не экспортировались как ссылки) и `NN-тема/result-a.md` от прогона Opus-агентов (workflow: 3 исследователя, 3 проверяющих, 1 писатель на промпт; заметки в `NN-тема/notes/`). Выжимка каждой пары ответов с нумерованными правилами (R07…R14), вердиктами по таксономии, опровержениями и пробелами: `NN-тема/rules.md`. Сводка серии и решения (правила по стадиям, таксономия, план скиллов, сверка по собственным Reference cards): [SYNTHESIS-content.md](SYNTHESIS-content.md).

## Что не исследуем (решено)

- Распознавание локации и geocoding: делаем по метаданным → vision → вручную, без отдельного ресерча.
- Транскрипция и субтитры: речи пока нет, stable-ts уже установлен в `.venv` на будущее.
- Публикация через API и нарезка на несколько роликов: не в scope v1.
