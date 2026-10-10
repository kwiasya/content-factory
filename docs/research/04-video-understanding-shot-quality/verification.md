# Проверка result-a по локальному окружению

Дата: 2026-10-10. Проверялось то, что ресерч предлагает запускать локально на M2.

## Что есть

| Что | Статус |
|---|---|
| ffmpeg 8.0.1 (homebrew 8.0.1_4) | есть, `videotoolbox` hwaccel есть |
| фильтры `signalstats`, `blurdetect`, `scdet`, `lut3d`, `tonemap`, `tile` | есть |
| exiftool | есть (`/opt/homebrew/bin/exiftool`) |
| Swift 6.3.3 + Command Line Tools, macOS 26.6 | есть, Apple Vision aesthetics API (macOS 15+) доступен, Swift CLI собрать можно |
| torch 2.14.1 в `.venv`, MPS доступен | есть (приехал вместе с stable-ts), YOLO и pyiqa встанут |

## Чего нет

| Что | Последствие | Что делать |
|---|---|---|
| ffmpeg без `drawtext` (нет libfreetype) | нельзя жечь таймкоды на contact sheets | пересобрать ffmpeg с freetype, или рисовать таймкоды через OpenCV/Pillow |
| ffmpeg без `zscale` (нет libzimg) | HDR→SDR тонмап для прокси через `zscale`+`tonemap` не соберётся | есть `tonemap`, но без zscale нужна цепочка `colorspace`/`format`, качество хуже; проще поставить полный ffmpeg |
| ffmpeg без `subtitles` (нет libass) | не нужно в v1, но понадобится если появятся субтитры | то же |
| ffmpeg без `vidstabdetect` | не критично, ресерч и так советует OpenCV | ничего |
| `cv2` (OpenCV) в `.venv` | нет | `uv pip install opencv-python-headless` когда дойдём |
| mediainfo | нет | не нужен, ffprobe + exiftool достаточно |

Установленный homebrew ffmpeg собран минимально: только svtav1, opus, x264, mp3lame, dav1d, vpx, x265. Для пайплайна нужен сборка с freetype, zimg, libass. Варианты: tap `homebrew-ffmpeg/ffmpeg` с опциями, или статический билд. Решать в плане.

## Что не проверялось

- Цены и названия моделей (Gemini 3.5 Flash-Lite, 3.8 Flash, Claude Sonnet 5, TwelveLabs Pegasus 1.5): это внешние факты, проверять по официальным страницам в момент подключения, ресерч сам отмечает дрейф цен.
- Утверждение, что Claude API не принимает видео: верно на момент моих знаний, но проверять по актуальной документации при реализации.
- Осмо Pocket без гиро-данных: не проверялось, у нас пока нет файла с Osmo.

## Вывод для плана

Двухуровневая схема (локальные метрики на 540p прокси → Gemini для описания и кандидатов) реализуема на этой машине. Единственный блокер в окружении: минимальный ffmpeg, его нужно заменить. JSON shot-log из секции C взять как основу схемы, он же станет входом для Script.
