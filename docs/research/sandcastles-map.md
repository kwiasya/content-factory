# Sandcastles: карта продукта как образец для нашего исследовательского контура

Дата: 2026-10-11. Источники: sandcastles.ai, sandcastles.ai/mcp, help.sandcastles.ai (video-detail, ideas-detail-differences, scripts-3-paths, channels-4-modes, hooks-watchlist), blog.sandcastles.ai (релизы 2025-09-14), обзоры creatorhouse.app, creatoreconomytools.com, formatfinder.onepeakcreative.com, и два скилла `sandcastles-watchlist-*.skill` из `~/Downloads`. Мы Sandcastles не подключаем (решение в `skills-review.md`); эта карта нужна, чтобы воспроизвести лучшие функции своими данными.

## Границы продукта

- Платформы: Instagram, TikTok, YouTube Shorts. **Длинного YouTube нет.** Удержание не анализируют. Видео не скачивают, только транскрипт.
- Credits: 1 за deep analysis видео, 1 за сценарий, отчёты тоже списывают. Pro: 100 credits/мес, 150 каналов на workspace, 3 workspace, MCP. API только на Titan.

## Сущности

| Их термин | Что это | Наш термин |
|---|---|---|
| Workspace | Одна ниша: свой watchlist, persona, проекты | Watchlist (ниша) |
| Watchlist | 15–20 каналов ниши, против которых идёт исследование | список Reference channel внутри Watchlist |
| Channel | Чужой канал | Reference channel |
| Video | Чужое видео со статистикой: views, engagement rate, outlier score | Reference |
| Outlier score | Во сколько раз видео обошло «обычные» цифры своего канала (формула не опубликована; фильтры 1x, 2x, 5x) | Outlier score |
| Deep analysis | Пять вкладок по одному видео (ниже) | карточка Reference |
| Idea | Карточка-дайджест, порождённая из видео, для триажа: Inbox → Shortlist / Discard → Create script | Idea |
| Persona | Образец текста автора, по которому пишут сценарии | `author/how-i-talk.md` |
| Collections | Закрытые справочники: 22 формата, 30 стилей монтажа, 47 визуальных хуков, 6 signature series | таксономии в `formats/` и Hook library |
| Your Favorite Hooks | Сохранённые hook formats | Hook library |
| Projects | Папки отобранных видео и идей | (пока нет) |
| Scripts | Три пути: from scratch по теме, remix сохранённой Idea (тема + суть + стиль письма), fix своего черновика | Script |
| Reports | Content Strategy Audit, Hook Genius Report | (пока нет) |
| Personal Analytics | Свой верифицированный канал | (нет у них в MCP; у нас через YouTube Analytics API) |

## Поля deep analysis (Video Detail)

- **Шапка:** канал, дата, outlier score, views, engagement rate, Summary.
- **Transcript:** текст, число слов, секции с таймкодами, подпись поста.
- **Idea Analysis:** Topic, Idea Seed, Unique Angle, Common Belief to Challenge, Contrarian Reality, Supporting Evidence.
- **Hook:** Category, Formula, Spoken Hook, Analysis (насколько хук соответствует остальному видео).
- **Storytelling Format:** Category, Description, Analysis.
- **Visual Layout:** Category, Sub-category.
- **Действия:** Create script, Shortlist idea, Add to project, Save hook format, Export for LLM (промпт с разбором), Open, Remove.

## Поля Idea (Idea Detail)

Title, Summary, исходное видео, Your Notes, Content Positioning (уникальный угол), Storytelling Format (категория и почему работает), Contrast Mechanism (общее мнение против контрарной реальности, если есть), Hook Alignment, Personalization (три способа переложить идею на свою нишу). Действия: Shortlist, Discard, Go to Analysis, Turn into script.

## Поиск каналов (4 режима)

Suggested (похожие на watchlist или на persona), Describe (текстовое описание ниши, фильтры платформа и размер аккаунта Nano…Mega), Search (по хэндлу, только уже известные им каналы), Add URL (парсинг ссылок). «More like this» на карточке: похожие по истории, не по ключевым словам.

## Инструменты MCP

| Инструмент | Что делает | Наш аналог |
|---|---|---|
| `/channels-add` | Добавить, перечислить, убрать каналы watchlist | править файл Watchlist |
| `/videos-watchlist` | Топ видео watchlist за окно (по умолчанию view count, фильтры min_outlier_score, min_views, min_engagement, lookback_days, limit, cursor) | лента Reference |
| `/analyze` | Deep analysis одного видео по URL | карточка Reference |
| `/hooks-watchlist` | Паттерны хуков среди **уже проанализированных** видео за окно (по умолчанию 14 дней); флагует непроанализированные выбросы ≥ 2x | Hook library по Watchlist |
| `/formats-watchlist` | То же по форматам | сводка форматов |
| `/topic` | Какие темы сейчас работают | сводка тем |
| `/video-suggest` | Идеи следующих видео из того, что перформит | Idea → Brief |
| `/channels-recap` | Что канал постил и как зашло | рекап Reference channel |
| `/channels-search` | Поиск внутри своих каналов | фильтр |
| `/channels-suggest` | Каналы, похожие на watchlist | поиск новых Reference channel |

Два скачанных скилла (`sandcastles-watchlist-all-recent`, `sandcastles-watchlist-outliers`) это тонкие обёртки над `search_my_videos`: лента за 7 дней без фильтра и лента выбросов ≥ 1x, обе с режимом «поставить на cron 7:00». Полезны только как образец формата отчёта: номер, outlier x, views, заголовок, хэндл, ссылка.

«Creator Breakout Detector» (скилл из Google Drive, не скачан): по URL канала и окну до 2 лет ищет момент прорыва канала и что в контенте изменилось. Требует Sandcastles MCP. Воспроизводится через историю загрузок канала из Data API.

## Что у них нет и где мы можем быть сильнее

1. Длинные видео YouTube: главы, кривая most replayed (`heatmap` из yt-dlp), транскрипт пиков.
2. Структура из самого видео: плотность монтажа, длина первого шота, момент появления текста и лица (наш `analyze-clips`).
3. Динамика: снимки статистики по дням дают скорость набора просмотров, а не только итог.
4. Свой канал: удержание по секундам через YouTube Analytics API, сравнение со своими же Reference.
5. Транскрипт локально (stable-ts), без кредитов и без зависимости от авто-субтитров.
