---
status: accepted
date: 2026-10-15
---

# Walk переименован в Footage, у данных два именованных корня

Пул Clip из одного места назывался Walk, потому что первым Format был Walk Reel. С Travel long и будущими Format пул перестал быть прогулкой: это просто снятый материал поездки. Поэтому доменный термин теперь Footage (Футаж), а Format Walk Reel сохраняет имя, потому что в нём речь о настоящих прогулках. Одновременно «footage root» (`CF_FOOTAGE_ROOT`, `footage_root()`) столкнулся бы с новым термином, а следующий шаг разделит данные между двумя Маками: поэтому корень не переименован в одно новое имя, а сразу назван двумя. Локальный корень `CF_LOCAL_ROOT` хранит Footage, `videos/` и `channels/`, общий корень `CF_SHARED_ROOT` хранит `factory.db`, `references/` и кэш `library/`. Пока оба по умолчанию `~/Movies/content-factory`. Команды `cf.*` уже берут каждую папку из своего корня (Library и `factory.db` из общего, Footage из локального), а Desk пока обслуживает один корень: `python -m cf.desk` завершается с ошибкой, а `create_app` отказывается, если корни указывают в разные папки. Оставить Walk было бы дешевле сегодня, но каждый новый Format и каждый новый читатель кода спотыкался бы о «прогулку», которая не прогулка.

## Consequences

- Ключи данных `walks` (`video.json`) и `walk` (`clip_manifest.json`, `script.json`, `build-report.json`) стали `footage`. Код читает оба, пишет новый; Desk переписывает `video.json` при смене статуса. Схема `cf-script/1` не меняется, Shot log стал `reel-shotlog/1.3` (`speech.footage_ref_dbfs`).
- Старые имена живут как скрытые псевдонимы до раздела корней: `python -m cf.walk`, `--walk`, `--footage-root` и переменная `CF_FOOTAGE_ROOT` (запасной вариант для обоих корней). Скилл `/ingest-walk` стал `/ingest-footage` без псевдонима; Note к нему переезжают миграцией store V9.
- Категория Asset `footage` (`@footage/<имя>`) остаётся: это часть грамматики Asset ref, в Desk она подписана «Стоковое видео», а в `GLOSSARY.md` отделена от Footage.
- Папки Footage, их id `<место>-<ГГГГ-ММ-ДД>`, старые адреса Reel `<id>~<reel>` и проекты Resolve `cf-<id>-<reel>` не меняются.
- ADR 0001–0011 остаются как есть: они пишут Walk, и их решения этим ADR не отменяются.
