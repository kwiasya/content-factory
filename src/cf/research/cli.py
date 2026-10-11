"""Research CLI: ``python -m cf.research <group> <cmd> [--json] [--db PATH]``.

Groups so far: ``watchlist`` (add, list, show, remove, add-channel,
remove-channel, add-query), ``taxonomy list``, ``quota``, ``scout``,
``snapshot``, ``feed``. Every command takes
``--json`` (machine output on stdout) and ``--db`` (default ``CF_FACTORY_DB`` or
``<footage root>/factory.db``). Human output is a Markdown table in Russian.
Errors: one line on stderr, exit 1.

Later tickets register their group with a ``register_<group>(sub, common)``
function added to ``GROUPS``; a handler takes ``(args, store)`` and returns the
exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable, Iterable

from cf.research import feed, quota, scout, taxonomy, watchlist, youtube
from cf.research.kinds import KINDS
from cf.research.store import StoreError, open_store

# Errors a command reports as one line and exit 1.
USER_ERRORS: tuple[type[Exception], ...] = (
    watchlist.WatchlistError, taxonomy.TaxonomyError, quota.QuotaExceeded,
    youtube.YouTubeError, StoreError,
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
    return md_table(["Watchlist", "Format", "Channel", "Язык", "Регион", "Каналов", "Запросы"],
                    [(w.name, w.format_id, w.channel_id, w.language, w.region, w.channel_count,
                      "; ".join(w.queries)) for w in ws])


def _ch_table(chs: list[watchlist.Channel]) -> str:
    if not chs:
        return "Reference channel пока нет."
    return md_table(["Хэндл", "Название", "Подписчики", "Видео", "Свой", "ID"],
                    [(c.handle, c.title, c.subscriber_count, c.video_count, c.own, c.external_id)
                     for c in chs])


def cmd_wl_add(args, store) -> int:
    w = watchlist.create(store, args.name, format_id=args.format, channel_id=args.channel,
                         language=args.language, region=args.region, queries=args.query)
    return emit(args, w.to_dict(), lambda: f"Watchlist {w.name} создан.\n\n" + _wl_table([w]))


def cmd_wl_list(args, store) -> int:
    ws = watchlist.list_watchlists(store)
    return emit(args, [w.to_dict() for w in ws], lambda: _wl_table(ws))


def cmd_wl_show(args, store) -> int:
    w = watchlist.get(store, args.name)
    chs = watchlist.channels(store, args.name)
    return emit(args, {"watchlist": w.to_dict(), "channels": [c.to_dict() for c in chs]},
                lambda: _wl_table([w]) + "\n\n" + _ch_table(chs))


def cmd_wl_remove(args, store) -> int:
    watchlist.remove(store, args.name)
    return emit(args, {"removed": args.name}, lambda: f"Watchlist {args.name} удалён.")


def cmd_wl_add_channel(args, store) -> int:
    c = watchlist.add_channel(store, args.name, args.ref, own=args.own, refresh=args.refresh)
    return emit(args, {"watchlist": args.name, "channel": c.to_dict()},
                lambda: f"Канал добавлен в {args.name}.\n\n" + _ch_table([c]))


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
    p.add_argument("--format", required=True, help="Format id, e.g. tech_explainer, walk_reel, travel_long")
    p.add_argument("--channel", help="the Author's Channel id this Watchlist serves")
    p.add_argument("--language", default="en")
    p.add_argument("--region", help="ISO 3166-1 alpha-2, e.g. US")
    p.add_argument("--query", action="append", default=[], help="search query (repeatable)")
    p.set_defaults(func=cmd_wl_add)
    p = gs.add_parser("list", parents=[common], help="list Watchlists")
    p.set_defaults(func=cmd_wl_list)
    p = gs.add_parser("show", parents=[common], help="one Watchlist with its Reference channels")
    p.add_argument("name")
    p.set_defaults(func=cmd_wl_show)
    p = gs.add_parser("remove", parents=[common], help="delete a Watchlist (channels stay in the store)")
    p.add_argument("name")
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


def register_taxonomy(sub, common) -> None:
    g = sub.add_parser("taxonomy", help="controlled vocabulary for Reference cards")
    gs = g.add_subparsers(dest="cmd", required=True)
    p = gs.add_parser("list", parents=[common], help="list taxonomy values")
    p.add_argument("--kind", choices=taxonomy.KINDS)
    p.add_argument("--status", choices=taxonomy.STATUSES)
    p.set_defaults(func=cmd_tx_list)


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
        return (f"Scout {r.watchlist} ({r.taken_at})\n\n{chans}\n\n{qs}\n\n"
                f"Кандидаты (каналы из поиска вне Watchlist):\n\n{_candidates_table(r.candidates)}\n\n"
                f"Вызовы API: {_calls_text(r.calls)}{_stopped_text(r.stopped)}")
    return emit(args, r.to_dict(), human)


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


GROUPS: list[Callable] = [register_watchlist, register_taxonomy, register_quota,
                          register_scout, register_snapshot, register_feed]


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
