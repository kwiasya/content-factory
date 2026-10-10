# Проверка result-a по локальному стабу API

Дата: 2026-10-10. Источник: `DaVinciResolveScript.pyi` из Resolve 21.1.1.

## Подтверждено

- `Project.GetFairlightPresets() -> list[str]` и `Timeline.ApplyFairlightPresetToCurrentTimeline(name)` есть.
- `Timeline.AddMarker(frameId, color, name, note, duration, customData)` и такой же на `TimelineItem`: beat-маркеры для ревью ставить можно.
- `Timeline.SetVoiceIsolationState(trackIndex, state)` есть.
- `Timeline.NormalizeAudioLevel(items, options)` с режимами LKFS / dBFS: см. verification ресерча 01.
- Project settings содержат `limitAudioMeterLUFS`, `limitAudioMeterLoudnessScale`, `limitAudioMeterAlignLevel`: измеритель громкости настраивается скриптом.

## Опровергнуто: громкость клипа всё-таки скриптуется

Ресерч (TL;DR, таблица C, секция E) утверждает: «Clip volume, fades, EQ and dynamics are not scriptable». В стабе 21.1 у `TimelineItem.SetProperty` есть свойства:

```
AudioVolumeEnabled: bool
AudioVolume: float        # -100.0 to 30.0 (dB)
AudioPanEnabled: bool
AudioPan: float           # -100.0 to 100.0
AudioPitchEnabled / AudioPitchSemiTones / AudioPitchCents
```

Плюс `SetFades({FadeIn, FadeOut})` работает и для аудио-фейдера (докстринг: «for the item's video or audio fader»). Значит статический уровень эмбиенса под музыкой (−18…−24 dB) и фейды на стыках можно ставить прямо в Resolve, а не только через ffmpeg. Чего по-прежнему нет: автоматизации громкости по кривой, EQ, компрессора, FairlightFX на клипе. Для них остаётся ffmpeg-препроцесс или Fairlight-пресет целиком.

Вывод: цепочку ffmpeg из ресерча (highpass, afftdn, afade, loudnorm) оставить для чистки и мастеринга, а уровни и фейды внутри таймлайна делать через API. Это проще пересобирать, чем пере-рендерить WAV.

## Не проверялось

- Установка `beat-this`, `librosa 1.0`, `all-in-one-infer` на Python 3.12: ставить будем в рамках плана, не сейчас.
- Epidemic Sound MCP, цены, лицензии, судебные дела Suno/Udio, GEMA: внешние факты.
- Утверждение, что Resolve Beat Detector и AI Music Editor не скриптуются: в стабе методов с «Beat» или «Music» не нашёл, совпадает с ресерчем.

## Вывод для плана

- Музыка: решение между Epidemic Sound (подписка, MCP) и ElevenLabs Music (API) остаётся за пользователем, это вопрос денег и вкуса. Оба автоматизируются. Трендовые звуки Instagram: только ручной Flow 2.
- Beat sync: Beat This! + librosa, нарезка по энергии, маркеры в Resolve. Совпадает с тем, что ресерч 01 назвал «plan layer».
- Звук: ffmpeg для чистки, API 21.1 для уровней и фейдов, `NormalizeAudioLevel` или ffmpeg `loudnorm` для −14 LUFS.
