# Проверка result-a по локальному стабу API и окружению

Дата: 2026-10-10. Источник: `DaVinciResolveScript.pyi` из Resolve 21.1.1, ffmpeg 8.0.1, exiftool.

## Подтверждено

- Ключи настроек проекта из шага 2 есть в стабе с документированными значениями:
  - `colorScienceMode`: `'davinciYRGB' | 'davinciYRGBColorManaged' | 'davinciYRGBColorManagedv2' | 'acescc' | 'acescct'`
  - `isAutoColorManage`, `separateColorSpaceAndGamma`: `'0' | '1'`
  - `inputDRT`, `outputDRT`, `colorSpaceOutputToneMapping`: `'None' | 'Simple' | 'Luminance Mapping' | 'DaVinci' | 'Saturation Preserving' | 'RED IPP2'`
  - `timelineWorkingLuminanceMode`: `'SDR 100' | 'HDR 1000' | …`
- Свойство клипа `'Input Color Space'` есть. Ресерч прав, что строка должна точно совпадать с выпадающим списком.
- `Graph.SetLUT(nodeIndex, path)`, `Graph.GetLUT`, `TimelineItem.SetCDL`, `TimelineItem.GetNodeGraph(layerIdx)`, `Project.RefreshLUTList`, `TimelineItem.ExportLUT` есть.
- `Graph.ApplyGradeFromDRX(path, gradeMode, applyToAllLayers=False)`: опция «все слои нод» из 21.1.1 **есть в стабе**. Значит стаб свежее, чем я думал при проверке ресерча 01, и отсутствие async-методов в нём ещё показательнее.
- Render settings содержат `ColorSpaceTag` и `GammaTag` (строки, например `'Same as Project'`). Rec.709-A как тег гаммы выставляется скриптом, точную строку читать из сохранённого пресета.
- exiftool и ffprobe стоят, детект по метаданным (шаг 1) делать есть чем.

## Уточнения к ресерчу

- **Гамма и цветовое пространство клипа задаются раздельно.** Ресерч (шаг 3) говорит «Input Gamma isn't separately settable», поэтому советует `separateColorSpaceAndGamma=0`. В стабе у клипа есть и `'Input Color Space'`, и `'Input Gamma'` (например `'Gamma 2.4'`). Работает ли раздельная запись при `separateColorSpaceAndGamma=1`, проверить smoke-тестом. Пока план ресерча (комбинированные пресеты) остаётся безопасным вариантом.
- **LUT как атрибут клипа.** В стабе есть свойство клипа `'Input LUT'` (имя файла). Это альтернатива ноде 1 для D-Log M: один раз на MediaPoolItem, а не на каждом TimelineItem. Проверить, применяется ли оно в color-managed проекте.
- **Timeline color space разделён на два ключа**: `colorSpaceTimeline` (например `'Rec.709'`) и `colorSpaceTimelineGamma` (`'Gamma 2.4'`). Ресерч пишет одну строку `"DaVinci WG/Intermediate"`, на деле это скорее `colorSpaceTimeline='DaVinci WG'` + `colorSpaceTimelineGamma='DaVinci Intermediate'`. Ресерч сам советует снять значения с руками настроенного проекта через `GetSetting()`. Так и сделаем.
- Python 3.12 и `imp`: опровергнуто, см. verification ресерча 06. Импорт работает.

## Не проверялось

- ffprobe-вывод для реальных файлов iPhone HDR, Apple Log, Osmo D-Log M и HLG: **нужны по одному файлу с каждого устройства**. Ресерч сам считает это главной непроверенной частью. Это единственный пункт, где нужна ты.
- Поведение Instagram с HDR, битрейт 25 Mbps, Rec.709-A против 1-2-1: внешние факты.
- Точные строки выпадающего списка Input Color Space в 21.1.1 (`'Rec.2100 HLG (Scene)'`, `'Apple Log'`): снять с живого Resolve.

## Расхождения с другими ресерчами

- Ресерч 01 советовал LUT для D-Log M на ноде через `SetLUT`, ресерч 03 то же самое, плюс вариант DCTL в DWG. Согласны.
- Ресерч 04 строит прокси для анализа через `zscale`+`tonemap`; текущий ffmpeg без `zscale` (см. verification 04). Детект по метаданным из ресерча 03 от этого не зависит.

## Вывод для плана

- Pipeline «детект → тег → (только D-Log M через LUT) → нормализация → один look через DRX → один output transform» принять. Он полностью покрыт API.
- Первый практический шаг по цвету: получить по файлу с каждого устройства и в каждом профиле, прогнать ffprobe + exiftool, зафиксировать таблицу детекта как данные в репо.
- Look строится один раз руками, хранится как `.drx` в репо, агент только применяет.
