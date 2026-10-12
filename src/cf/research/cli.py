"""Research CLI: ``python -m cf.research <group> <cmd> [--json] [--db PATH]``.

Groups: ``watchlist`` (add, list, show, remove, add-channel,
remove-channel, add-query), ``taxonomy`` (list, approve, reject), ``quota``,
``scout``, ``snapshot``, ``feed``, ``fetch`` (one Reference, deep), ``card``
(validate, save, show), ``ideas`` (add, list, show, shortlist, discard,
restore, note, brief, candidates), ``summary`` (hooks, formats, topics), ``hooks``
(save, remove, list, export: the Hook library of a Format), ``notes`` (list, add,
resolve, delete: Notes from the Author). Every command takes
``--json`` (machine output on stdout) and ``--db`` (default ``CF_FACTORY_DB`` or
``<footage root>/factory.db``). Human output is a Markdown table in Russian.
Errors: one line on stderr, exit 1.

To add a group: write ``register_<group>(sub, common)``, append it to ``GROUPS``; each
handler takes ``(args, store)`` and returns the exit code.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

from cf.research import brief, card, feed, fetch, hooks, ideas, notes, quota, scout, summary, taxonomy, watchlist, youtube
from cf.research.kinds import KINDS
from cf.research.store import StoreError, open_store

# Errors a command reports as one line and exit 1.
USER_ERRORS: tuple[type[Exception], ...] = (
    watchlist.WatchlistError, taxonomy.TaxonomyError, quota.QuotaExceeded,
    youtube.YouTubeError, StoreError, fetch.FetchError, card.CardError, ideas.IdeaError, hooks.HookError,
    notes.NoteError,
)


def emit(args: argparse.Namespace, data: Any, human: Callable[[], str]) -> int:
    """Print ``data`` as JSON with ``--json``, else the human text; return 0."""
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(human())
    return 0


def md_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> str:
    def cell(v: Any) -> str:
        if v is None or v == "":
            return "—"
        if isinstance(v, bool):
            return "да" if v else ""
        if isinstance(v, int):
            return f"{v:,}".replace(",", " ")
        return str(v).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)


# --- watchlist ----------------------------------------------------------------

def _wl_table(ws: list[watchlist.Watchlist]) -> str:
    if not ws:
        return "Watchlist пока нет."
    return md_table(["Watchlist", "Format", "Channel автора", "Язык", "Регион", "Каналов", "Запросы"],
                    [(w.name, w.format_id, w.author_channel, w.language, w.region, w.channel_count,
                      "; ".join(w.queries)) for w in ws])


def _reference_channels_table(chs: list[watchlist.ReferenceChannel]) -> str:
    if not chs:
        return "Reference channel пока нет."
    return md_table(["Хэндл", "Название", "Подписчики", "Видео", "Свой", "ID"],
                    [(c.handle, c.title, c.subscriber_count, c.video_count, c.own, c.external_id)
                     for c in chs])


def cmd_wl_add(args, store) -> int:
    w = watchlist.create(store, args.name, format_id=args.format, author_channel=args.channel,
                         language=args.language, region=args.region, queries=args.query)
    return emit(args, w.to_dict(), lambda: f"Watchlist {w.name} создан.\n\n" + _wl_table([w]))


def cmd_wl_list(args, store) -> int:
    ws = watchlist.list_watchlists(store)
    return emit(args, [w.to_dict() for w in ws], lambda: _wl_table(ws))


def cmd_wl_show(args, store) -> int:
    w = watchlist.get(store, args.name)
    chs = watchlist.channels(store, args.name)
    return emit(args, {"watchlist": w.to_dict(), "channels": [c.to_dict() for c in chs]},
                lambda: _wl_table([w]) + "\n\n" + _reference_channels_table(chs))


def cmd_wl_remove(args, store) -> int:
    watchlist.remove(store, args.name, force=args.force)
    return emit(args, {"removed": args.name}, lambda: f"Watchlist {args.name} удалён.")


def cmd_wl_add_channel(args, store) -> int:
    c = watchlist.add_channel(store, args.name, args.ref, own=args.own, refresh=args.refresh)
    return emit(args, {"watchlist": args.name, "channel": c.to_dict()},
                lambda: f"Канал добавлен в {args.name}.\n\n" + _reference_channels_table([c]))


def cmd_wl_remove_channel(args, store) -> int:
    c = watchlist.remove_channel(store, args.name, args.ref)
    return emit(args, {"watchlist": args.name, "removed": c.to_dict()},
                lambda: f"Канал {c.handle or c.external_id} убран из {args.name}.")


def cmd_wl_add_query(args, store) -> int:
    w = watchlist.add_query(store, args.name, args.query)
    return emit(args, w.to_dict(), lambda: _wl_table([w]))


def register_watchlist(sub, common) -> None:
    g = sub.add_parser("watchlist", help="Watchlists, their Reference channels and queries")
    gs = g.add_subparsers(dest="cmd", required=True)
    p = gs.add_parser("add", parents=[common], help="create a Watchlist")
    p.add_argument("name")
    p.add_argument("--format", required=True, help="Format id: lower case letters, digits, - or _ (e.g. walk-reel, tech-explainer)")
    p.add_argument("--channel", help="the Author's Channel this Watchlist serves (folder name under "
                   "<footage root>/channels/, where its Briefs go); not a Reference channel")
    p.add_argument("--language", default="en")
    p.add_argument("--region", help="ISO 3166-1 alpha-2, e.g. US")
    p.add_argument("--query", action="append", default=[], help="search query (repeatable)")
    p.set_defaults(func=cmd_wl_add)
    p = gs.add_parser("list", parents=[common], help="list Watchlists")
    p.set_defaults(func=cmd_wl_list)
    p = gs.add_parser("show", parents=[common], help="one Watchlist with its Reference channels")
    p.add_argument("name")
    p.set_defaults(func=cmd_wl_show)
    p = gs.add_parser("remove", parents=[common],
                      help="delete a Watchlist and its Ideas (channels, videos and Brief files stay)")
    p.add_argument("name")
    p.add_argument("--force", action="store_true",
                   help="remove it even when one of its Ideas has a Brief (the Ideas are deleted)")
    p.set_defaults(func=cmd_wl_remove)
    p = gs.add_parser("add-channel", parents=[common],
                      help="add a Reference channel by @handle, channel URL or UC… id")
    p.add_argument("name")
    p.add_argument("ref")
    p.add_argument("--own", action="store_true", help="the channel is the Author's")
    p.add_argument("--refresh", action="store_true", help="call channels.list even if the channel is known")
    p.set_defaults(func=cmd_wl_add_channel)
    p = gs.add_parser("remove-channel", parents=[common], help="take a Reference channel out of a Watchlist")
    p.add_argument("name")
    p.add_argument("ref")
    p.set_defaults(func=cmd_wl_remove_channel)
    p = gs.add_parser("add-query", parents=[common], help="attach a search query")
    p.add_argument("name")
    p.add_argument("query")
    p.set_defaults(func=cmd_wl_add_query)


# --- taxonomy -----------------------------------------------------------------

def cmd_tx_list(args, store) -> int:
    vals = taxonomy.values(store, kind=args.kind, status=args.status)
    return emit(args, [v.to_dict() for v in vals], lambda: md_table(
        ["Вид", "Значение", "Название", "Статус", "Источник", "Что это"],
        [(v.kind, v.value, v.label, v.status, v.source, v.note) for v in vals]))


def _tx_change(args, change: taxonomy.TaxonomyChange, verb: str) -> int:
    def human() -> str:
        v = change.value
        head = f"{v.kind} {v.value}: {verb}."
        if not change.cards:
            return head
        what = "Префикс proposed: снят в карточках" if v.status == "approved" else \
            "Эти карточки теперь не проходят валидацию, перепишите их"
        return f"{head}\n{what}: {', '.join(change.cards)}"
    return emit(args, change.to_dict(), human)


def cmd_tx_approve(args, store) -> int:
    return _tx_change(args, taxonomy.approve(store, args.kind, args.value), "одобрено")


def cmd_tx_reject(args, store) -> int:
    return _tx_change(args, taxonomy.reject(store, args.kind, args.value), "отклонено")


def register_taxonomy(sub, common) -> None:
    g = sub.add_parser("taxonomy", help="controlled vocabulary for Reference cards")
    gs = g.add_subparsers(dest="cmd", required=True)
    p = gs.add_parser("list", parents=[common], help="list taxonomy values")
    p.add_argument("--kind", choices=taxonomy.KINDS)
    p.add_argument("--status", choices=taxonomy.STATUSES)
    p.set_defaults(func=cmd_tx_list)
    for name, func, text in (("approve", cmd_tx_approve, "make a value valid for cards (drops proposed: in cards)"),
                             ("reject", cmd_tx_reject, "make a value invalid for cards; it stays rejected")):
        p = gs.add_parser(name, parents=[common], help=text)
        p.add_argument("kind", choices=taxonomy.KINDS)
        p.add_argument("value")
        p.set_defaults(func=func)


# --- quota --------------------------------------------------------------------

def cmd_quota(args, store) -> int:
    u = quota.usage(store, day=args.day)

    def human() -> str:
        head = md_table(["Корзина", "Лимит", "Израсходовано", "Осталось"],
                        [(b.bucket, b.limit, b.used, b.remaining) for b in u.buckets])
        calls = md_table(["Метод", "Вызовов", "Units"], [(m.method, m.calls, m.units) for m in u.by_method]) \
            if u.by_method else "Вызовов не было."
        return f"Квота YouTube Data API на {u.day} (сутки по Тихоокеанскому времени)\n\n{head}\n\n{calls}"
    return emit(args, u.to_dict(), human)


def register_quota(sub, common) -> None:
    p = sub.add_parser("quota", parents=[common], help="today's YouTube Data API quota usage")
    p.add_argument("--day", help="ISO date (Pacific); default today")
    p.set_defaults(func=cmd_quota)


# --- fetch --------------------------------------------------------------------

def _mmss(s: float | None) -> str | None:
    return None if s is None else f"{int(s // 60)}:{s % 60:04.1f}"


def _fetch_human(r: dict) -> str:
    m = r["card"]["measured"]
    cuts = None if m["cut_count"] is None else f"{m['cut_count']} ({m['cuts_per_min']} в минуту)"
    text = None if m["first_text_s"] is None else f"{m['first_text_s']} («{m['first_text']}»)"
    out = [f"Reference {r['video_id']}: {r['title']}", f"Папка: {r['dir']}", f"Канал: {r['channel_source']}",
           f"Субтитры: {', '.join(r['captions']) or 'нет'}", "",
           md_table(["Шаг", "Итог"], r["steps"].items()), "",
           md_table(["Измерение", "Значение"], [
               ("Длительность, с", m["duration_s"]), ("Тип", m["kind"]), ("Склеек", cuts),
               ("Первый шот, с", m["first_shot_s"]), ("Первый текст на экране, с", text),
               ("Первый человек, с", m["first_person_s"]), ("Первое лицо, с", m["first_face_s"]),
               ("Начало речи, с", m["speech_onset_s"]), ("Spoken hook (первые 3 с)", m["spoken_hook"]),
               ("Язык", m["language"]), ("Секций транскрипта", None if m["sections"] is None else len(m["sections"])),
               ("Глав", len(m["chapters"]))])]
    if m["heatmap_peaks"]:
        out += ["", "Пики most replayed:", "",
                md_table(["Окно", "Значение", "Цитата"],
                         [(f"{_mmss(p['start_s'])}–{_mmss(p['end_s'])}", p["value"], p["quote"])
                          for p in m["heatmap_peaks"]])]
    if m["notes"]:
        out += [""] + [f"- {k}: {v}" for k, v in m["notes"].items()]
    return "\n".join(out)


@contextlib.contextmanager
def _stdout_to_stderr():
    """Send everything the tools print (model downloads, ffmpeg) to stderr, so stdout holds only our output."""
    sys.stdout.flush()
    saved = os.dup(1)
    try:
        os.dup2(2, 1)
        with contextlib.redirect_stdout(sys.stderr):
            yield
    finally:
        sys.stderr.flush()
        os.dup2(saved, 1)
        os.close(saved)


def cmd_fetch(args, store) -> int:
    with _stdout_to_stderr():
        r = fetch.fetch(store, args.ref, watchlist=args.watchlist, force=args.force)
    return emit(args, r, lambda: _fetch_human(r))


def register_fetch(sub, common) -> None:
    p = sub.add_parser("fetch", parents=[common],
                       help="deep fetch of one Reference: media, transcript, proxy, Shot log, measured card")
    p.add_argument("ref", help="YouTube video URL or 11-character id")
    p.add_argument("--watchlist", help="Watchlist for the transcript language and the folder of a first fetch "
                        "(a fetched Reference keeps its folder; no membership)")
    p.add_argument("--force", action="store_true", help="download, transcribe and analyse again")
    p.set_defaults(func=cmd_fetch)


# --- scout, snapshot, feed ---------------------------------------------------

def _calls_text(calls: dict[str, int]) -> str:
    return ", ".join(f"{m} × {n}" for m, n in sorted(calls.items())) or "нет"


def _stopped_text(stopped: str | None) -> str:
    return f"\n\nОстановлено по квоте, сделанное сохранено: {stopped}" if stopped else ""


def _candidates_table(cands: list[scout.Candidate]) -> str:
    if not cands:
        return "Кандидатов из поиска нет."
    return md_table(["Хэндл", "Название", "Подписчики", "Находок", "Запросы", "ID"],
                    [(c.handle, c.title, c.subscriber_count, c.hits, "; ".join(c.queries), c.external_id)
                     for c in cands])


def cmd_scout(args, store) -> int:
    r = scout.scout(store, args.name, search=not args.no_search, search_days=args.search_days,
                    search_pages=args.search_pages, video_duration=args.duration)

    def human() -> str:
        mode = {"backfill": "первая загрузка", "new": "только новые"}
        chans = md_table(["Хэндл", "Режим", "Страниц", "Новых видео", "Shorts", "Longs", "История готова"],
                         [(c.handle or c.external_id, mode[c.mode], c.pages, c.new_videos, c.shorts, c.longs,
                           c.backfilled) for c in r.channels]) if r.channels else "Reference channel нет."
        qs = md_table(["Запрос", "Страниц", "Видео"], [(q.query, q.pages, q.results) for q in r.queries]) \
            if r.queries else "Поисковых запросов не было."
        errors = [f"Ошибка канала {c.handle or c.external_id}: {c.error}" for c in r.channels if c.error]
        errors += [f"Ошибка запроса «{q.query}»: {q.error}" for q in r.queries if q.error]
        if r.candidates_error:
            errors.append(f"Ошибка каналов-кандидатов: {r.candidates_error}")
        failed = ("\n\n" + "\n".join(errors)) if errors else ""
        return (f"Scout {r.watchlist} ({r.taken_at})\n\n{chans}\n\n{qs}\n\n"
                f"Кандидаты (каналы из поиска вне Watchlist):\n\n{_candidates_table(r.candidates)}\n\n"
                f"Вызовы API: {_calls_text(r.calls)}{_stopped_text(r.stopped)}{failed}")
    emit(args, r.to_dict(), human)
    return 1 if r.failed() else 0


def register_scout(sub, common) -> None:
    p = sub.add_parser("scout", parents=[common],
                       help="pull uploads of the Watchlist's Reference channels and run its search queries")
    p.add_argument("name")
    p.add_argument("--no-search", action="store_true", help="skip the search queries")
    p.add_argument("--search-days", type=float, default=scout.DEFAULT_SEARCH_DAYS,
                   help="search only videos published in the last N days (default %(default)s)")
    p.add_argument("--search-pages", type=int, default=scout.DEFAULT_SEARCH_PAGES,
                   help="pages of 50 results per query (default %(default)s; 1 search call each)")
    p.add_argument("--duration", choices=("any", "short", "medium", "long"),
                   help="search.list videoDuration: short < 4 min, medium 4-20, long > 20")
    p.set_defaults(func=cmd_scout)


def cmd_snapshot(args, store) -> int:
    r = scout.snapshot(store, args.name)

    def human() -> str:
        gone = f"\n\nПропали с YouTube: {', '.join(r.missing)}" if r.missing else ""
        return (f"Снимок {r.watchlist} на {r.taken_at}: {r.videos} Reference. "
                f"Вызовы API: {_calls_text(r.calls)}{gone}{_stopped_text(r.stopped)}")
    return emit(args, r.to_dict(), human)


def register_snapshot(sub, common) -> None:
    p = sub.add_parser("snapshot", parents=[common],
                       help="record views, likes and comments of every Reference of a Watchlist")
    p.add_argument("name")
    p.set_defaults(func=cmd_snapshot)


def cmd_feed(args, store) -> int:
    rows = feed.feed(store, args.name, lookback_days=args.days, min_outlier=args.min_outlier,
                     min_views=args.min_views, kind=args.kind, max_duration_s=args.max_duration,
                     limit=args.limit)
    data = [{**r.to_dict(), "outlier": None if r.outlier is None else round(r.outlier, 2)} for r in rows]
    filters = "; ".join(f for f in (
        f"outlier ≥ {args.min_outlier:g}" if args.min_outlier is not None else "",
        f"просмотров ≥ {args.min_views}" if args.min_views is not None else "",
        f"kind {args.kind}" if args.kind else "",
        f"до {args.max_duration:g} с" if args.max_duration is not None else "") if f)
    return emit(args, data, lambda: feed.report(args.name, rows, lookback_days=args.days, filters=filters))


def register_feed(sub, common) -> None:
    p = sub.add_parser("feed", parents=[common], help="the Watchlist's Reference ordered by Outlier score")
    p.add_argument("name")
    p.add_argument("--days", type=float, default=feed.DEFAULT_LOOKBACK_DAYS,
                   help="published in the last N days (default %(default)s)")
    p.add_argument("--min-outlier", type=float, help="drop Reference below this Outlier score (and unscored)")
    p.add_argument("--min-views", type=int)
    p.add_argument("--kind", choices=KINDS)
    p.add_argument("--max-duration", type=float, help="seconds, e.g. 60 for Walk Reel work")
    p.add_argument("--limit", type=int, default=20, help="rows (default %(default)s)")
    p.set_defaults(func=cmd_feed)


# --- card ---------------------------------------------------------------------

def _violations(args, target: str, problems: list[str]) -> int:
    """Print violations like cf.script_schema (stdout, one per line) and return 1."""
    if args.json:
        print(json.dumps({"target": target, "ok": False, "violations": problems}, ensure_ascii=False, indent=2))
    else:
        print(f"INVALID {target} ({len(problems)} violation{'s' if len(problems) != 1 else ''})")
        for p in problems:
            print(f"- {p}")
    return 1


def _read_json(path: str) -> dict:
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise card.CardError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise card.CardError(f"{path}: expected a JSON object")
    return data


def _is_card(data: dict) -> bool:
    return "schema" in data and "analysis" in data


def _stored(store, ref: str) -> tuple[dict, dict]:
    v = card.video(store, ref)
    c = card.load(store, v["id"])
    if c is None:
        raise card.CardError(f"Reference {v['external_id']} has no card yet; run fetch first")
    return v, c


def _pending(store, analysis: dict | None) -> list[dict]:
    """Category values of an analysis still awaiting the Author's approval."""
    out = []
    for path, kind in card.category_paths():
        raw = card.field(analysis or {}, path)
        if isinstance(raw, str):
            value = card.split_proposed(raw)[0]
            t = taxonomy.get(store, kind, value)
            if t is not None and t.status == "proposed" and {"kind": kind, "value": value} not in out:
                out.append({"kind": kind, "value": value})
    return out


def cmd_card_validate(args, store) -> int:
    target = args.target
    transcript = None
    if os.path.isfile(target):
        data = _read_json(target)
        if _is_card(data):
            c = data
            sibling = os.path.join(os.path.dirname(os.path.abspath(target)), "transcript.json")
            if os.path.isfile(sibling):
                transcript = _read_json(sibling)
        elif args.video is None:
            return _violations(args, target, ["an analysis without measured needs --video <id|url> "
                                              "(or pass the whole card.json)"])
        else:
            c = {**_stored(store, args.video)[1], "analysis": data}
        if transcript is None and args.video is not None:
            transcript = card.read_transcript(card.video(store, args.video)["external_id"])
    else:
        v, c = _stored(store, target)
        transcript = card.read_transcript(v["external_id"])
    problems = card.validate(c, store, transcript=transcript)
    if problems:
        return _violations(args, target, problems)
    a = c["analysis"]
    pending = _pending(store, a)
    return emit(args, {"target": target, "ok": True, "violations": [], "proposed": pending}, lambda: (
        f"OK {target}: hook {a['hook']['category']}, format {a['storytelling_format']['category']}, "
        f"layout {a['visual_layout']['category']} / {a['visual_layout']['sub_category']}"
        + (f"; ждут одобрения: {', '.join(p['kind'] + ' ' + p['value'] for p in pending)}" if pending else "")))


def _card_human(title: str | None, ext: str, c: dict, pending: list[dict]) -> str:
    m, a = c["measured"], c["analysis"]
    out = [f"Карточка {ext}: {title or ''}".rstrip(), "",
           md_table(["Измерение", "Значение"], [
               ("Длительность, с", m.get("duration_s")), ("Склеек в минуту", m.get("cuts_per_min")),
               ("Первый шот, с", m.get("first_shot_s")), ("Начало речи, с", m.get("speech_onset_s")),
               ("Spoken hook (первые 3 с)", m.get("spoken_hook"))])]
    if a is None:
        out += ["", "Анализа пока нет."]
    else:
        out += ["", md_table(["Поле", "Значение"],
                             [(path, card.field(a, path)) for path in card.field_paths()])]
    if pending:
        out += ["", "Ждут одобрения Author (taxonomy approve|reject):"]
        out += [f"- {p['kind']} {p['value']}" for p in pending]
    return "\n".join(out)


def cmd_card_show(args, store) -> int:
    v, c = _stored(store, args.video)
    title = (store.one("SELECT title FROM video WHERE id = ?", (v["id"],)) or {}).get("title")
    return emit(args, c, lambda: _card_human(title, v["external_id"], c, _pending(store, c["analysis"])))


def cmd_card_save(args, store) -> int:
    data = _read_json(args.analysis)
    analysis = data["analysis"] if _is_card(data) else data
    try:
        saved = card.save_analysis(store, args.video, analysis)
    except card.CardError as exc:
        if not exc.violations:
            raise
        return _violations(args, args.analysis, exc.violations)
    v = card.video(store, args.video)
    pending = _pending(store, saved["analysis"])
    title = (store.one("SELECT title FROM video WHERE id = ?", (v["id"],)) or {}).get("title")
    return emit(args, {"video_id": v["external_id"], "card": saved, "proposed": pending},
                lambda: "Сохранено.\n\n" + _card_human(title, v["external_id"], saved, pending))


def register_card(sub, common) -> None:
    g = sub.add_parser("card", help="Reference cards: validate, save and show the analysis section")
    gs = g.add_subparsers(dest="cmd", required=True)
    p = gs.add_parser("validate", parents=[common],
                      help="check a card (stored, card.json, or an analysis file with --video); violations exit 1")
    p.add_argument("target", help="card.json, analysis.json (with --video), or a YouTube id/URL of a stored card")
    p.add_argument("--video", help="YouTube id or URL whose measured card and transcript to check against")
    p.set_defaults(func=cmd_card_validate)
    p = gs.add_parser("save", parents=[common],
                      help="validate and store the analysis; proposed: values enter the taxonomy as proposed")
    p.add_argument("video", help="YouTube id or URL (fetched already)")
    p.add_argument("analysis", help="analysis.json (the analysis object, or a whole card)")
    p.set_defaults(func=cmd_card_save)
    p = gs.add_parser("show", parents=[common], help="one card: measured and analysis")
    p.add_argument("video", help="YouTube id or URL")
    p.set_defaults(func=cmd_card_show)


# --- ideas --------------------------------------------------------------------

def _sources_text(idea: ideas.Idea) -> str:
    return ", ".join(s["external_id"] or f"#{s['id']}" for s in idea.sources)


def _ideas_table(rows: list[ideas.Idea]) -> str:
    if not rows:
        return "Idea нет."
    return md_table(["ID", "Статус", "Название", "Reference", "Заметок", "Brief"],
                    [(i.id, i.status, i.title, _sources_text(i), len(i.notes) or None, i.brief_path)
                     for i in rows])


def _idea_human(i: ideas.Idea) -> str:
    f = i.fields
    sf, cm = f["storytelling_format"], f.get("contrast_mechanism")
    lines = [f"# Idea #{i.id}: {i.title}", "",
             f"Статус: {i.status} · Watchlist {i.watchlist} · создана {i.created_at} · изменена {i.updated_at}"]
    if i.brief_path:
        lines.append(f"Brief: {i.brief_path}")
    lines += ["", "## Суть", "", f["summary"],
              "", "## Позиционирование", "", f["content_positioning"],
              "", "## Формат повествования", "", f"`{sf['category']}`: {sf['why']}",
              "", "## Контраст", "",
              f"Принято думать: {cm['common_belief']}\nНа деле: {cm['contrarian_reality']}" if cm else "нет",
              "", "## Хук", "", f["hook_alignment"],
              "", "## Как переложить на свой Channel", ""]
    lines += [f"{n}. {p}" for n, p in enumerate(f["personalizations"], 1)]
    lines += ["", "## Reference", ""]
    lines += [f"- {s['external_id']}: {s['title'] or '—'} {s['url'] or ''}".rstrip() for s in i.sources]
    lines += ["", "## Заметки", ""]
    lines += [f"- {n['at']}: {n['text']}" for n in i.notes] or ["Заметок нет."]
    return "\n".join(lines)


def _read_ideas(path: str) -> tuple[list[dict], bool]:
    """The Idea objects of ``path`` and whether the file held a list."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ideas.IdeaError(f"{path}: {exc}") from exc
    items = data if isinstance(data, list) else [data]
    if not items or not all(isinstance(x, dict) for x in items):
        raise ideas.IdeaError(f"{path}: expected an Idea object or a non-empty list of them")
    return [dict(x) for x in items], isinstance(data, list)


def cmd_ideas_add(args, store) -> int:
    items, many = _read_ideas(args.file)
    watchlist.get(store, args.watchlist)
    sources = [item.pop("sources", None) for item in items]
    problems = [f"[{n}] {p}" if many else p
                for n, (src, item) in enumerate(zip(sources, items)) for p in ideas.check(store, src, item)]
    if problems:
        return _violations(args, args.file, problems)
    added = [ideas.add(store, args.watchlist, src, item) for src, item in zip(sources, items)]
    return emit(args, [i.to_dict() for i in added],
                lambda: f"В инбокс {args.watchlist} добавлено Idea: {len(added)}.\n\n" + _ideas_table(added))


def cmd_ideas_list(args, store) -> int:
    rows = ideas.list(store, args.watchlist, status=args.status)
    return emit(args, [i.to_dict() for i in rows], lambda: _ideas_table(rows))


def cmd_ideas_show(args, store) -> int:
    i = ideas.get(store, args.id)
    return emit(args, i.to_dict(), lambda: _idea_human(i))


def _ideas_move(args, store, move) -> int:
    before = ideas.get(store, args.id).status
    i = move(store, args.id)
    return emit(args, i.to_dict(), lambda: f"Idea {i.id}: {before} → {i.status}")


def cmd_ideas_note(args, store) -> int:
    i = ideas.note(store, args.id, args.text)
    return emit(args, i.to_dict(), lambda: f"Заметка добавлена к Idea {i.id} (всего {len(i.notes)}).")


def cmd_ideas_brief(args, store) -> int:
    path = brief.create(store, args.id, channel=args.channel, format_id=args.format)
    i = ideas.get(store, args.id)
    return emit(args, i.to_dict(), lambda: f"Idea {i.id}: shortlisted → brief\nBrief: {path}")


def cmd_ideas_candidates(args, store) -> int:
    rows = ideas.candidates(store, args.watchlist, days=args.days, min_outlier=args.min_outlier,
                            limit=args.limit)
    data = [{**r.to_dict(), "outlier": None if r.outlier is None else round(r.outlier, 2)} for r in rows]

    def human() -> str:
        if not rows:
            return f"Нет проанализированных Reference без Idea за {args.days:g} дн."
        return md_table(["№", "Outlier", "Просмотры", "Дата", "Название", "Хэндл", "Ссылка"],
                        [(n, feed.outlier_text(r.outlier), feed.views_text(r.views), r.date, r.title,
                          r.handle, r.url) for n, r in enumerate(rows, 1)])
    return emit(args, data, human)


def register_ideas(sub, common) -> None:
    g = sub.add_parser("ideas", help="Ideas: inbox, triage (shortlist, discard, restore, note) and Briefs")
    gs = g.add_subparsers(dest="cmd", required=True)
    p = gs.add_parser("add", parents=[common], help="add Ideas to a Watchlist's inbox from a JSON file")
    p.add_argument("watchlist")
    p.add_argument("file", help="idea.json: {sources: [...], title, summary, …} or a list of them")
    p.set_defaults(func=cmd_ideas_add)
    p = gs.add_parser("list", parents=[common], help="Ideas of a Watchlist")
    p.add_argument("watchlist")
    p.add_argument("--status", choices=ideas.STATUSES)
    p.set_defaults(func=cmd_ideas_list)
    p = gs.add_parser("show", parents=[common], help="one Idea with every field and note")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_ideas_show)
    for name, move, text in (("shortlist", ideas.shortlist, "inbox → shortlisted"),
                             ("discard", ideas.discard, "inbox → discarded"),
                             ("restore", ideas.restore, "discarded → inbox")):
        p = gs.add_parser(name, parents=[common], help=text)
        p.add_argument("id", type=int)
        p.set_defaults(func=lambda args, store, move=move: _ideas_move(args, store, move))
    p = gs.add_parser("note", parents=[common], help="append an Author's note")
    p.add_argument("id", type=int)
    p.add_argument("text")
    p.set_defaults(func=cmd_ideas_note)
    p = gs.add_parser("brief", parents=[common],
                      help="write the Brief of a shortlisted Idea under <footage root>/channels/<channel>/briefs/")
    p.add_argument("id", type=int)
    p.add_argument("--channel", help="the Author's Channel folder (default: the Watchlist's Author's Channel, "
                   "else _unassigned)")
    p.add_argument("--format", help="Format id (default: the Watchlist's)")
    p.set_defaults(func=cmd_ideas_brief)
    p = gs.add_parser("candidates", parents=[common],
                      help="analyzed top outliers of the window that no Idea uses yet (input of suggest-ideas)")
    p.add_argument("watchlist")
    p.add_argument("--days", type=float, default=ideas.DEFAULT_CANDIDATE_DAYS,
                   help="published in the last N days (default %(default)s)")
    p.add_argument("--min-outlier", type=float)
    p.add_argument("--limit", type=int, default=ideas.DEFAULT_CANDIDATE_LIMIT, help="rows (default %(default)s)")
    p.set_defaults(func=cmd_ideas_candidates)


# --- summary ------------------------------------------------------------------

_SUMMARY_NAMES = {"hooks": "хуков", "formats": "форматов", "topics": "тем"}
_SECTION_NAMES = {"hook_category": "Категории хуков", "hook_formula": "Формулы хуков",
                  "storytelling_format": "Форматы повествования",
                  "visual_layout": "Визуальная подача", "topic": "Темы"}


def _weight_text(w: float) -> str:
    return f"{w:.1f}".replace(".", ",")


def _example_line(e: summary.Example) -> str:
    title = " ".join((e.title or "без названия").split())
    parts = [f"**{feed.outlier_text(e.outlier)}**", feed.views_text(e.views), e.date or "—", f"«{title}»",
             e.handle or "без хэндла", e.url or "—"]
    if e.spoken_hook:
        parts.append(f"хук: «{' '.join(e.spoken_hook.split())}»")
    if e.formula:
        parts.append(f"формула: {' '.join(e.formula.split())}")
    return "- " + " · ".join(parts)


def _summary_human(r: summary.Summary) -> str:
    out = [f"Сводка {_SUMMARY_NAMES[r.summary]} {r.watchlist} (Format {r.format_id}) за "
           f"{feed._decimal(r.days)} дн.: {r.references} Reference, с карточкой {r.carded}. "
           "Вес группы: сумма Outlier score её Reference, без оценки считается как 1."]
    for sec in r.sections:
        out += ["", f"### {_SECTION_NAMES.get(sec.kind, sec.kind)}", ""]
        if not sec.groups:
            out.append("Карточек с этим полем в окне нет.")
            continue
        out.append(md_table(["#", "Значение", "Название", "Карточек", "Вес", "Лучший outlier"],
                            [(i, g.value + (" (предложено)" if g.proposed else ""), g.label, g.count,
                              _weight_text(g.weight), feed.outlier_text(g.best_outlier))
                             for i, g in enumerate(sec.groups, 1)]))
        for g in sec.groups:
            out += ["", f"**{g.label or g.value}**" + (" (предложено)" if g.proposed else "")]
            out += [_example_line(e) for e in g.examples]
    out += ["", f"### Выбросы без разбора (outlier ≥ {feed._decimal(r.min_outlier)}x)", ""]
    if not r.uncarded:
        out.append("Нет: сводка опирается на все выбросы окна.")
    for i, u in enumerate(r.uncarded, 1):
        title = " ".join((u.title or "без названия").split())
        out.append(" · ".join([f"{i}. **{feed.outlier_text(u.outlier)}**", feed.views_text(u.views), u.date or "—",
                               f"«{title}»", u.handle or "без хэндла", u.url or "—",
                               "замерен, без анализа" if u.measured else "без карточки"]))
    return "\n".join(out)


def cmd_summary(args, store) -> int:
    r = summary.summarize(store, args.name, args.cmd, days=args.days, min_outlier=args.min_outlier,
                          limit=args.limit, examples=args.examples)
    return emit(args, r.to_dict(), lambda: _summary_human(r))


def register_summary(sub, common) -> None:
    g = sub.add_parser("summary", help="hooks, formats and topics that work in a Watchlist, from its cards")
    gs = g.add_subparsers(dest="cmd", required=True)
    for name, text in (("hooks", "hook categories, then hook formulas (case and spaces folded), with examples"),
                       ("formats", "storytelling formats and visual layouts"),
                       ("topics", "topics (idea_analysis.topic), case and spaces folded")):
        p = gs.add_parser(name, parents=[common], help=text)
        p.add_argument("name", help="Watchlist")
        p.add_argument("--days", type=float, default=summary.DEFAULT_DAYS,
                       help="published in the last N days (default %(default)s)")
        p.add_argument("--min-outlier", type=float, default=summary.DEFAULT_MIN_OUTLIER,
                       help="list uncarded Reference from this Outlier score up (default %(default)s)")
        p.add_argument("--limit", type=int, default=10, help="groups per section and uncarded rows (default %(default)s)")
        p.add_argument("--examples", type=int, default=summary.DEFAULT_EXAMPLES,
                       help="examples per group (default %(default)s)")
        p.set_defaults(func=cmd_summary)


# --- hooks (Hook library) -------------------------------------------------------

def _hooks_table(hs: list[hooks.Hook]) -> str:
    if not hs:
        return "Хуков пока нет."
    return md_table(["Категория", "Хук", "Формула", "Источник", "Outlier", "Ссылка", "Сохранён"],
                    [(h.category + (" (предложено)" if h.proposed else ""), h.text or "без речи", h.formula,
                      h.source_title or ("удалён из базы" if h.source is None else None),
                      feed.outlier_text(h.outlier), h.source_url, h.saved_at[:10]) for h in hs])


def cmd_hooks_save(args, store) -> int:
    h = hooks.save(store, args.format, args.video)
    return emit(args, h.to_dict(), lambda: f"Хук сохранён в Hook library {h.format_id}. "
                f"Обновите файл: python -m cf.research hooks export {h.format_id}\n\n" + _hooks_table([h]))


def cmd_hooks_remove(args, store) -> int:
    hooks.remove(store, args.format, args.video)
    return emit(args, {"format_id": args.format, "removed": args.video},
                lambda: f"Хук {args.video} убран из Hook library {args.format}.")


def cmd_hooks_list(args, store) -> int:
    hs = hooks.list_hooks(store, args.format)
    return emit(args, [h.to_dict() for h in hs], lambda: f"Hook library {args.format}\n\n" + _hooks_table(hs))


def cmd_hooks_export(args, store) -> int:
    path = hooks.export(store, args.format, args.out)
    n = len(hooks.list_hooks(store, args.format))
    return emit(args, {"format_id": args.format, "path": str(path), "hooks": n},
                lambda: f"Hook library {args.format} ({n}) записана в {path}")


def register_hooks(sub, common) -> None:
    g = sub.add_parser("hooks", help="the Hook library of a Format: proven hooks saved from cards")
    gs = g.add_subparsers(dest="cmd", required=True)
    for name, func, text in (("save", cmd_hooks_save, "save the hook of a carded Reference into a Format's library"),
                             ("remove", cmd_hooks_remove, "take a Reference's hook out of a Format's library")):
        p = gs.add_parser(name, parents=[common], help=text)
        p.add_argument("format", help="Format id, e.g. walk-reel (the Watchlist's Format)")
        p.add_argument("video", help="YouTube id or URL of the carded Reference")
        p.set_defaults(func=func)
    p = gs.add_parser("list", parents=[common], help="the Hook library of a Format")
    p.add_argument("format")
    p.set_defaults(func=cmd_hooks_list)
    p = gs.add_parser("export", parents=[common], help="write formats/<format>/hook-library.md (generated, overwritten)")
    p.add_argument("format")
    p.add_argument("--out", help="write here instead of formats/<format>/hook-library.md in the repo")
    p.set_defaults(func=cmd_hooks_export)


# --- notes (Notes from the Author) ------------------------------------------------

def _notes_table(ns: list[notes.Note]) -> str:
    if not ns:
        return "Note нет."
    return md_table(["ID", "Kind", "Key", "Текст", "Создана", "Закрыта"],
                    [(str(n.id), n.kind, n.key, n.text, n.created_at, n.resolved_at) for n in ns])


def cmd_notes_list(args, store) -> int:
    ns = notes.list(store, kind=args.kind, key=args.key, include_resolved=args.all)
    return emit(args, [n.to_dict() for n in ns], lambda: _notes_table(ns))


def cmd_notes_add(args, store) -> int:
    n = notes.add(store, args.kind, args.key, args.text)
    return emit(args, n.to_dict(), lambda: f"Note #{n.id} ({n.kind} {n.key}) добавлена")


def cmd_notes_resolve(args, store) -> int:
    n = notes.resolve(store, args.id)
    return emit(args, n.to_dict(), lambda: f"Note #{n.id} закрыта")


def cmd_notes_delete(args, store) -> int:
    n = notes.delete(store, args.id)
    return emit(args, n.to_dict(), lambda: f"Note #{n.id} удалена")


def register_notes(sub, common) -> None:
    g = sub.add_parser("notes", help="Notes the Author left on skills, documents, videos, cards and Ideas")
    gs = g.add_subparsers(dest="cmd", required=True)
    p = gs.add_parser("list", parents=[common], help="open Notes, optionally of one kind and key")
    p.add_argument("--kind", choices=notes.KINDS)
    p.add_argument("--key", help="repo-relative path, skill name or id")
    p.add_argument("--all", action="store_true", help="include resolved Notes")
    p.set_defaults(func=cmd_notes_list)
    p = gs.add_parser("add", parents=[common], help="leave a Note on one entity")
    p.add_argument("kind", choices=notes.KINDS)
    p.add_argument("key", help='repo-relative path, skill name or id; "" for a general Note')
    p.add_argument("text")
    p.set_defaults(func=cmd_notes_add)
    for name, func, text in (("resolve", cmd_notes_resolve, "close a Note after acting on it"),
                             ("delete", cmd_notes_delete, "remove a Note")):
        p = gs.add_parser(name, parents=[common], help=text)
        p.add_argument("id", type=int)
        p.set_defaults(func=func)


GROUPS: list[Callable] = [register_watchlist, register_taxonomy, register_quota,
                          register_scout, register_snapshot, register_feed, register_fetch, register_card,
                          register_ideas, register_summary, register_hooks, register_notes]


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine output (JSON on stdout)")
    common.add_argument("--db", help="research database (default: CF_FACTORY_DB or <footage root>/factory.db)")
    ap = argparse.ArgumentParser(prog="python -m cf.research", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="group", required=True)
    for register in GROUPS:
        register(sub, common)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with open_store(args.db) as store:
            return args.func(args, store)
    except USER_ERRORS as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
