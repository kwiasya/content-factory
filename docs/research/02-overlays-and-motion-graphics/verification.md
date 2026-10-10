# Проверка result-a по локальному стабу и окружению

Дата: 2026-10-10. Источник: стаб `DaVinciResolveScript.pyi` (31 Aug 2026), macOS 26.6.2, Node 24.

## Подтверждено

- `Timeline.InsertTitleIntoTimeline(titleName) -> TimelineItem` и `InsertFusionTitleIntoTimeline(titleName) -> TimelineItem` есть. Докстринг говорит только "Inserts a Fusion title into the timeline", ни позиции, ни трека, ни ripple. Значит заявленное ripple-поведение на V1 стабом не опровергается и не подтверждается, это только сообщество.
- `AppendClipInfo`: `mediaPoolItem`, `startFrame`, `endFrame`, `mediaType` (1 video, 2 audio), `trackIndex`, `recordFrame`. Все опциональны. Значит оверлеи на V2/V3 через `recordFrame` + `trackIndex` действительно возможны, как и предлагает ресерч.
- `TimelineItem.GetFusionCompByIndex`, `GetFusionCompByName`, `ImportFusionComp(path)`, `ExportFusionComp` есть.
- `TransitionOptions.alignment` в стабе **опционален** (`total=False`). Ресерч утверждает, что без него `AddTransition` молча возвращает `None`. Стаб это не подтверждает, проверять smoke-тестом. Пока всегда передавать `alignment`.
- Remotion требует macOS 15+: у нас macOS 26.6.2, Node 24, подходит.

## Не подтверждено

- Имена типов переходов кроме 'Cross Dissolve' в стабе не перечислены. Список нужно получить эмпирически.
- 21.1.1 async API: как и в ресерче 01, в стабе их нет.
- Все утверждения про Fusion "success-without-write" и ripple insert: только из сообщества.

## Расхождения с ресерчем 01

- Ресерч 01 считает Fusion Text+ через API рабочим основным путём. Ресерч 02 считает его рискованным и предлагает Remotion как основной путь, Fusion как запасной. Оба согласны, что переходы, фейды и скорость делаются нативно через API 21.1.
- Решение между ними принимать после smoke-теста: один раз вставить Text+ через API на тестовом таймлайне и посмотреть, куда он встаёт и рендерится ли.

## Вывод для плана

Главная рекомендация: Remotion рендерит оверлеи как ProRes 4444 с альфой, агент кладёт их на V2/V3 через `AppendToTimeline`. Стаб это допускает. Safe zone 269/672/65 px взять как рабочее правило в Style profile. Remotion ставить через официальные Agent Skills, не через MCP.
