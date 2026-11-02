# Ниша: инструменты для Claude Code × поиск работы

Watchlist `claude-code-tools` (Format Tech explainer, язык en, регион US), собран 2026-10-12: 17 Reference channel, 3237 Reference, один снимок просмотров. Лента: `.venv/bin/python -m cf.research feed claude-code-tools --kind long|short --days 90`. Разобранные карточки: `card show <id>`. Правила, на которые ссылается текст: `NN-тема/rules.md` (R07…R12).

## Две аудитории, два поведения

| | Claude Code power users | Соискатели |
|---|---|---|
| Каналы | Matt Pocock 407k, RoboNuggets 198k, Sharbel 40k, AI LABS 170k, Chase AI 178k, IndyDevDan 151k | AI With Abhijay 71k, Yudi J 316k, Jeff Su 1.9M |
| Где аутлаеры | Лонги 11–20 мин: 300–800 тыс. просмотров при 5–10x | Shorts: «5 Tools To Land A Job in 30 Days» 930 тыс., 112x; «Best to worst job portals» 409 тыс., 49x |
| Лонг про автоматизацию поиска работы | нет прямых | «Can this free AI automation get you the first interview?» 8 тыс. просмотров (9x для канала, но абсолют мал) |

Вывод: видео сидит на пересечении. Лонг заходит у девелоперов, которые уже в Claude Code; соискатели как аудитория есть, но смотрят короткое и списки. Один лонг для первой аудитории плюс 2–3 Shorts, нарезанных из него, для второй (черновик `reels/short-01` уже есть).

## Что общего у аутлаеров лонгов (90 дней, outlier ≥ 4.5)

1. **Заголовок = названный объект + обещанный результат.** «Jev will 10x your Claude Code», «9 NEW Claude Mods that can truly change how you work», «Paste This Into Claude Code, Never Run Out Of Tokens Again», «This 1 Claude Skill fully replaces your Higgsfield Subscription». Нет «I built», нет вопросов (R12-11), число всегда привязано к объекту (R08-10).
2. **«Бесплатно» и «весь сетап целиком».** Short «This Anthropic Hackathon Winner Just Released His Entire Claude Code Setup for Free» 1,8 млн, 49x. «10 Github Repos That Will Kill Your Monthly Subscriptions» 8,5x. Open source как обещание работает сильнее, чем «я сделал».
3. **Открытие: обещание первой фразой, био после и не дольше 10 с.** RoboNuggets: новость → «the idea is simple» → «nine mods worth installing» → 10 с кто я → «but first, what are mods». Sharbel: личная боль в первой фразе («Claude Code told me to come back in five hours»). Единственный лонг с био и историей ДО обещания (Abhijay, 50 с интро) набрал 8 тыс.
4. **Пики повторов сидят на моментах «сделай вот это».** Jev: 3:32–3:46 (setup) и 4:42–5:46 (level 1). Sharbel: 2:46–4:09 (fix 1–2) и 7:07–7:19 (fix 4). Matt Pocock: 4:30–4:50 (setup and configuration) и 10:01–10:12 (creating specs and tickets). Зритель перематывает к команде на экране, а не к рассказу. Значит, установка и первый запуск должны быть в кадре с текстом команды, а не «ссылка в описании».
5. **Главы через каждые 40–120 с, первая содержательная не позже 0:40.** У всех трёх: «What is X» к 0:32–0:54, «How to set up» к 3:00–4:34.
6. **Длина 11–20 мин.** Matt 17:17, Jev 11:46, Mods 12:47, Sharbel 19:47. Короче 10 мин среди аутлаеров нет.

## Что это значит для видео про autopilot-jobsearch

**Контракт (R09-01, R08-01).** Обещание: «мой поиск работы идёт сам, дважды в день, вот сетап, он бесплатный, ставится за две минуты». Ставки: 637 заявок, 18 собеседований, 93 прогона, всё публично на JobCubby. Переменная прогресса: от отчёта за утро к тому, как это поставить себе. Payoff: зритель видит свой первый отчёт.

**Что держать в первых 30 с (R07-01, R08-02, R07-05).** Утренний отчёт на экране в кадре 1, цифры 637 / 18, фраза «it is a Claude Code plugin, free, two minutes» до любого «кто я». Никакого «в этом видео мы…».

**Что показать как доказательство в первой минуте (R09-06).** Публичная страница JobCubby с воронкой, обновляемая самим свипом. Это то, чего нет ни у одного конкурента: аутлаеры показывают инструмент, а не свой результат.

**Честность (R08-16).** Свип стоит 15–100 $ на Sonnet-классе, в среднем 40. Это говорится в середине как ограничение, не прячется в описание: в нише Sharbel собрал 322 тыс. именно на «сколько стоят токены».

**Упаковка (R12-18, R12-08).** Три разных пакета, не варианты одного:

| # | Заголовок | Текст на превью | Кадр |
|---|---|---|---|
| A | My Claude Code plugin applied to 637 jobs while I slept | 18 interviews | утренний отчёт + лицо |
| B | I gave my job search to Claude Code. Free plugin, 2-minute setup | 637 applied | страница JobCubby с воронкой |
| C | autopilot-jobsearch: the Claude Code setup that runs my job hunt twice a day | runs itself | терминал с `/sweep` |

A ближе к аутлаерам ниши (число + объект + результат), B ближе к соискателям, C для подписчиков Claude Code. Рекомендация: A как основной, B и C в Test & Compare (R12-22).

**Риски.** Соискатель без Claude Code отваливается на «plugin»: одна фраза «Claude Code is Anthropic's terminal agent, 20 $ a month» нужна до установки. Ниша быстро копирует: «released entire setup for free» уже было, отличие здесь это реальные цифры и публичный трекер, их и ставим в заголовок.

## Карточки

- Matt Pocock, «mattpocock/skills: A complete AI Coding workflow, end-to-end» (M6mYodf0dJM): скачан, транскрибирован, разобран, см. `card show`. Остальные аутлаеры выше читались по метаданным, главам, heatmap и первым 50 с автосубтитров без скачивания; карточек у них нет.
