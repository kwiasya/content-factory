# Обзор скачанных скиллов: что берём, что нет

Дата: 2026-10-10. Просмотрены архивы из `~/Downloads` (8 штук, все от 10 октября) и два `.skill` из iCloud `AI/_Библиотека/Промпты`. Распакованы в scratchpad, в репо не копировались.

## Вердикт одной строкой

Все восемь скиллов из Downloads построены вокруг платного сервиса **Sandcastles** (MCP, анализирует чужие и свои каналы за кредиты) и методики Kane Kallaway (Short Form Academy). Без Sandcastles они не работают, и мы его не подключаем. Два скилла из iCloud (banana-pro-director, cinema-worldbuilder) пишут промпты для генерации картинок и видео в Higgsfield и Seedance, то есть для софта, которым мы не пользуемся. **Ни один не ставим целиком.** Берём из них четыре вещи, перечислены ниже.

## По каждому

| Скилл | Что делает | Зависит от | Берём |
|---|---|---|---|
| audience-bullseye-builder (topic-bullseye-builder v4) | 5 колец аудитории, микс тем 3-2-1, плотит видео канала на кольца | Sandcastles | Идею «одна конкретная зрительница в центре, темы на кольцах 3–4». В Style profile поле `audience` |
| content-formula-miner | Скорит формулы «тема × структура × визуальный лейаут» по истории канала | Sandcastles | Триаду «тема · структура · лейаут» как поля Script |
| cta-analyzer (cta-strategist) | Какие CTA «comment X» дают лиды | Sandcastles; про лид-магниты и ManyChat | Ничего, у нас CTA на отправку, не лиды |
| format-finder v2 | Матрица форматов × стилей монтажа по чужим каналам | Sandcastles | Таксономию форматов (listicle, levels, day-in-the-life, challenge…) и стилей (vlog_pov, vlog_music, vlog_timelapse, faceless) как словарь для `hook.type` и `format` в Script |
| hook-genius (hook-playbook) | Из отчёта Sandcastles строит плейбук хуков с правилами | Sandcastles, отчёт Hook Genius | Правила хуков с цифрами: без восклицательных знаков, без «one of the best», 11–16 слов для устных, число только вместе с механизмом, название после ставки. Переносим в правила Script как «writing rules» |
| niche-interviewer-standalone | 6 вопросов → позиционирование и Niche Card | **Ничего** (standalone), но нацелен на бизнес-владельцев и лиды | Можно прогнать один раз для Style profile (`audience`, `promise`). Паттерн «ровно шесть вопросов, по одному, reflect-back после каждого» |
| strategy-analysis-coach | История канала по эрам | Sandcastles | Ничего в v1 |
| brand-positioning-canvas-pack (8 скиллов) | Kallaway positioning: игра, ниша, contrarian vault, ассоциации, уникальность, формулы | Sandcastles (competitor-scout тратит кредиты) | Структуру пакета: оркестратор `brand-positioning` + подскиллы с одним артефактом каждый. Так же устроим наши фазы |
| banana-pro-director | Промпты для Higgsfield (персонажи, сцены) | Higgsfield | Ничего |
| cinema-worldbuilder | Промпты для Seedance, пять «режимов кино» с камерой, оптикой, движением, светом и диегетическим звуком | Seedance | Словарь описания кадра: движение (locked-off, slow push-in, drift, handheld), свет, текстура, «только диегетический звук». Пригодится для тегов в Shot log и для описания стиля в Style profile |

## Что переносим в репо

1. **Писательские правила хуков** из hook-playbook в `write-script`: положительно сформулированные (хук 5–8 слов на экране, ставка раньше названия, число только с механизмом).
2. **Словарь форматов и стилей** из format-finder как enum-ы в схеме Script: `format` (listicle, pov, levels, day_in_the_life, challenge…) и `editing_style` (vlog_pov, vlog_music, vlog_timelapse, faceless).
3. **Словарь кадра** из cinema-worldbuilder как теги в Shot log: `motion` (locked, push_in, pull_back, drift, pan, forward_walk, handheld), `light` (golden_hour, overcast, blue_hour, night, interior).
4. **Паттерн пакета**: оркестратор + подскиллы, у каждого один артефакт и чёткий критерий завершения. Скрипты в `scripts/`, справочники в `references/`, шаблоны в `assets/`.

## Что не переносим

- Любую зависимость от Sandcastles, Higgsfield, Seedance.
- HTML-отчёты «в фирменном стиле»: наши артефакты это JSON и проект в Resolve.
- Лид-генерацию, CTA под ManyChat, бизнес-позиционирование под продажи.
