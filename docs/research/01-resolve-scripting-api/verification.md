# Проверка result-a по локальному стабу API

Дата: 2026-10-10. Источник истины: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/` (README.md от 31 Aug 2026, CHANGELOG.md от 1 Sep 2026, `DaVinciResolveScript.pyi`). Установлен Resolve Studio 21.1.1.

## Подтверждено стабом

Все заявленные новинки 21.1 есть в `.pyi` и в CHANGELOG:

- `TimelineItem.AddTransition(TransitionOptions) -> TimelineItem | None`. Поля: `type`, `category` ('simple' | 'fusion' | 'ofx' | 'audio'), `position` ('start' | 'end'), `alignment` ('left' | 'center' | 'right'), `duration` (кадры, по умолчанию авто).
- `TimelineItem.SetSpeed(SpeedOptions)` / `GetSpeed()`. Поля: `Percentage` (0.0 = freeze frame), `PitchCorrection`, `StretchKeyframesToFit`, `RippleTimeline`. Значит freeze frame всё-таки заявлен в стабе, ресерч считал его непроверенным.
- `TimelineItem.SetFades(FadeInfo)` / `GetFades()`: `{FadeIn, FadeOut}` в кадрах.
- `Timeline.NormalizeAudioLevel(items, NormalizeAudioOptions)` и `GetNormalizeAudioModes()`. Поля: `normalizationMode`, `targetLevel` (dBFS), `targetLoudness` (LKFS), `setLevelMode`.
- `MediaPoolItem.GetTranscription`, `CreateMulticamClip`, `AutoAlignClips`, `InsertFusionTitleIntoTimeline`, `ImportTimelineFromFile`, `RenderWithQuickExport`, `DetectSceneCuts`, `SmartReframe`, `SetLUT`, `ApplyGradeFromDRX`, `SetCDL`, `CreateSubtitlesFromAudio`: все присутствуют.
- `GetCDL` отсутствует: CDL действительно write-only.
- Inspector-свойства `ZoomX`, `CropTop`, `RetimeProcess`, `AudioVolume`, `AudioVolumeEnabled` есть в TypedDict свойств TimelineItem. Константы `RETIME_NEAREST / FRAME_BLEND / OPTICAL_FLOW` есть.
- Свойство клипа `'Input Color Space': str` есть в TypedDict свойств MediaPoolItem.
- CHANGELOG 21.1 подтверждает: Python 2 убран, перегруженные сигнатуры deprecated, добавлены пресеты настроек проекта, рендера и клавиатуры, output blanking, audio mapping, clone media, `ValidateDCTL`/`EncryptDCTL`.

## Не подтверждено

- **Async-варианты в 21.1.1** (Quick Export, транскрипция, scene cut, Smart Reframe, субтитры): в стабе ноль упоминаний `Async`, CHANGELOG не содержит записи 21.1.1. Либо документация на диске отстаёт от приложения, либо утверждение ресерча ошибочно. Считать несуществующими, пока не увидим в стабе.
- Опция "all node layers" для `ApplyGradeFromDRX` в 21.1.1: **есть в стабе** как `Graph.ApplyGradeFromDRX(path, gradeMode, applyToAllLayers=False)` (найдено при проверке ресерча 03). Значит стаб соответствует 21.1.1, и отсутствие в нём async-методов тем более показательно.
- Все утверждения о поведении (возвраты `None` для "Dip to Color", потеря фейдов при экспорте, зависания IPC) из сообщества, стабом не проверяются. Проверять smoke-тестом.

## Вывод для плана

Ресерч в части API точен. Ключевая рекомендация (свой тонкий `resolve_driver.py` поверх официального `.pyi`, таймлайн пересобирается из JSON-плана, read-back после каждой записи) ничем не опровергнута. Стаб в 21.1 типизирован, его можно класть агенту в контекст целиком.
