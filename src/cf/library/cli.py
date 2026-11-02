"""Library CLI: ``python -m cf.library <group> <cmd> [--json] [--db PATH] [--shared-root PATH]``.

Groups: ``pack`` (add, list, remove), ``index``, ``show``, ``suggest``, ``query``, ``author`` (set, orphans),
``import-tags``, ``tags`` (todo, apply).
Every command takes ``--json`` (machine output on stdout), ``--db`` (default ``CF_FACTORY_DB`` or
``<shared root>/factory.db``) and ``--shared-root`` (default ``CF_SHARED_ROOT`` or ``/Users/Shared/content-factory``,
which must be mounted; the cache lives in its ``library/``). Human output is Markdown in Russian. Errors: one line on stderr, exit 1.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

from cf.library import author as author_mod
from cf.library import imports, packs, sheets
from cf.library import index as index_mod
from cf.library.errors import AssetNotFound, LibraryError, PackError
from cf.library.library import Asset, card, load
from cf.library.refs import CATEGORIES, RIGHTS
from cf.research import backup
from cf.research.store import BUSY_MESSAGE, StoreError, ensure_shared_root, is_busy, open_store

USER_ERRORS: tuple[type[Exception], ...] = (LibraryError, StoreError)


def emit(args: argparse.Namespace, data: Any, human: Callable[[], str]) -> int:
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
        return str(v).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)


def _root(args) -> Path:
    return Path(args.shared_root).expanduser() if args.shared_root else ensure_shared_root()


def _assets_table(assets: list[Asset]) -> str:
    if not assets:
        return "Ничего не найдено."
    return md_table(["Ref", "Вид", "Длительность", "Права", "Подпись", "Теги", "Файл"],
                    [(a.ref, a.kind, f"{a.duration_s:.2f} с" if a.duration_s else None, a.rights,
                      a.caption or a.agent_caption, ", ".join(a.all_tags()), a.primary["path"]) for a in assets])


def _find(lib, ref_or_id: str) -> tuple[Asset, bool]:
    if ref_or_id.startswith("@"):
        hit = lib.lookup(ref_or_id)
        if hit is None:
            raise AssetNotFound(ref_or_id)
        return hit
    a = lib.get(ref_or_id)
    if a is None:
        raise AssetNotFound(ref_or_id)
    return a, False


# --- pack -----------------------------------------------------------------------

def _read_config(path: str) -> dict:
    try:
        return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except OSError as exc:
        raise PackError(f"cannot read {path}: {exc.strerror}") from exc
    except ValueError as exc:
        raise PackError(f"{path} is not JSON: {exc}") from exc


def _packs_table(infos: list[packs.PackInfo]) -> str:
    if not infos:
        return "Pack пока не подключены."
    return md_table(["Pack", "Папка", "Подключён", "Проиндексирован"],
                    [(p.id, p.root, p.created_at, p.indexed_at) for p in infos])


def cmd_pack_add(args, store) -> int:
    info = packs.register_pack(store, _read_config(args.config), root=Path(args.root) if args.root else None)
    return emit(args, info.to_dict(), lambda: f"Pack {info.id} подключён.\n\n" + _packs_table([info]))


def cmd_pack_list(args, store) -> int:
    infos = packs.list_packs(store)
    return emit(args, [p.to_dict() for p in infos], lambda: _packs_table(infos))


def cmd_pack_remove(args, store) -> int:
    packs.remove_pack(store, args.id)
    return emit(args, {"removed": args.id}, lambda: f"Pack {args.id} отключён (кэш остался).")


def register_pack(sub, common) -> None:
    g = sub.add_parser("pack", help="register Packs (folders of editing material read in place)")
    gs = g.add_subparsers(dest="cmd", required=True)
    p = gs.add_parser("add", parents=[common], help="register or update a Pack from a cf-pack/1 config")
    p.add_argument("--config", required=True)
    p.add_argument("--root", help="the Pack folder, overriding the config's root")
    p.set_defaults(func=cmd_pack_add)
    p = gs.add_parser("list", parents=[common], help="registered Packs")
    p.set_defaults(func=cmd_pack_list)
    p = gs.add_parser("remove", parents=[common], help="unregister a Pack (its cache stays)")
    p.add_argument("id")
    p.set_defaults(func=cmd_pack_remove, backup="pre-pack-remove")


# --- index ----------------------------------------------------------------------

def _report_human(pack_id: str, r: dict) -> str:
    d = r["derived"]
    lines = [f"Pack {pack_id}: {r['assets']} материалов ({r['new']} новых, {r['changed']} изменено, "
             f"{r['removed']} удалено, {r['unchanged']} без изменений), {r['scanned']} файлов, "
             f"probe {r['probed']}, {r['seconds']} с.",
             f"Производные: keyed {d['keyed']}, converted {d['converted']}, png {d['png']}, "
             f"previews {d['previews']}, loudness {d['loudness']}; сирот удалено {r['orphans_removed']}.",
             f"Мусор: {r['junk']}, симлинки: {r['symlinks']}, дубликаты: {r['duplicates']}, алиасы: {r['aliases']}."]
    if r.get("author_orphans"):
        lines.append(f"Поля Author без материала: {r['author_orphans']} (см. `author orphans`).")
    if r.get("skipped"):
        lines.append("Пропущено флагами: " + ", ".join(r["skipped"]) + " (следующий запуск без флага доделает).")
    if r["fallback"]:
        lines.append("\nПапки без категории в маппинге (категория по виду файла):\n\n"
                     + md_table(["Папка", "Файлов"], r["fallback"].items()))
    if r["errors"]:
        lines.append("\nОшибки:\n\n" + md_table(["Файл", "Шаг", "Сообщение"],
                                                 [(e["ref"], e["step"], e["stderr"]) for e in r["errors"]]))
    return "\n".join(lines)


def cmd_index(args, store) -> int:
    log = (lambda m: print(m, file=sys.stderr)) if not args.quiet else (lambda m: None)
    rep = index_mod.index_pack(store, _root(args), args.pack, key=not args.no_key,
                               previews=not args.no_previews, loudness=not args.no_loudness,
                               only=tuple(args.only or ()), log=log).to_dict()
    return emit(args, rep, lambda: _report_human(args.pack, rep))


def register_index(sub, common) -> None:
    p = sub.add_parser("index", parents=[common], help="index one Pack into <shared root>/library/<pack>/")
    p.add_argument("pack")
    p.add_argument("--no-key", action="store_true", help="skip chroma keying of green-screen folders")
    p.add_argument("--no-previews", action="store_true", help="skip posters, preview mp4s, png and gif conversions")
    p.add_argument("--no-loudness", action="store_true", help="skip loudness measurement")
    p.add_argument("--only", action="append", metavar="REL", help="index only this subtree (repeatable)")
    p.add_argument("--quiet", action="store_true", help="no progress lines on stderr")
    p.set_defaults(func=cmd_index, backup="pre-index")


# --- show / suggest / query --------------------------------------------------------

def _card_human(a: Asset) -> str:
    rows = [("Ref", a.ref), ("По файлу", a.file_ref), ("Алиасы", ", ".join(a.aliases)), ("Категория", a.category),
            ("Вид", a.kind), ("Папка", a.folder), ("Файл", a.primary["path"]),
            ("Длительность", f"{a.duration_s:.3f} с" if a.duration_s else None),
            ("Размер", f"{a.width}×{a.height}" if a.width else None), ("fps", a.fps), ("Альфа", a.alpha),
            ("Хромакей", a.green_screen),
            ("Громкость", f"{a.loudness['i']} LUFS ({a.loudness['method']})" if a.loudness else None),
            ("Права", f"{a.rights} (по умолчанию {a.rights_default})"), ("Подпись", a.caption),
            ("Теги", ", ".join(a.tags)), ("Подпись агента", a.agent_caption), ("Теги агента", ", ".join(a.agent_tags)),
            ("Скрытые теги агента", ", ".join(a.hidden_agent_tags)),
            ("Варианты", "; ".join(f"{v['role']}: {v['path']}" for v in a.variants)), ("id", a.id)]
    return md_table(["Поле", "Значение"], rows)


def cmd_show(args, store) -> int:
    lib = load(_root(args), store)
    a, alias = _find(lib, args.ref)
    return emit(args, {"asset": card(a), "canonical": a.ref, "alias": alias}, lambda: _card_human(a))


def register_show(sub, common) -> None:
    p = sub.add_parser("show", parents=[common], help="one Asset by ref or id")
    p.add_argument("ref")
    p.set_defaults(func=cmd_show)


def cmd_suggest(args, store) -> int:
    found = load(_root(args), store).suggest(args.q, args.limit)
    return emit(args, {"suggestions": [card(a, full=False) for a in found]}, lambda: _assets_table(found))


def register_suggest(sub, common) -> None:
    p = sub.add_parser("suggest", parents=[common], help="refs for a prefix, a name part, a caption or a tag")
    p.add_argument("q")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_suggest)


def cmd_query(args, store) -> int:
    found = load(_root(args), store).query(pack=args.pack, category=args.category, tags=args.tag or (),
                                              text=args.q or "", rights=args.rights)
    return emit(args, {"assets": [card(a, full=False) for a in found], "total": len(found)},
                lambda: _assets_table(found))


def register_query(sub, common) -> None:
    p = sub.add_parser("query", parents=[common], help="Assets by Pack, category, tags (AND), text and rights")
    p.add_argument("--pack")
    p.add_argument("--category", choices=CATEGORIES)
    p.add_argument("--tag", action="append")
    p.add_argument("--q")
    p.add_argument("--rights", choices=RIGHTS)
    p.set_defaults(func=cmd_query)


# --- author ------------------------------------------------------------------------

def cmd_author_set(args, store) -> int:
    lib = load(_root(args), store)
    a, _ = _find(lib, args.ref)
    kw: dict[str, Any] = {}
    if args.caption is not None:
        kw["caption"] = args.caption
    if args.clear_tags or args.tag:
        kw["tags"] = ([] if args.clear_tags else list(a.tags)) + list(args.tag or ())
    if args.hide_agent_tag or args.show_agent_tag:
        shown = {t.lower() for t in args.show_agent_tag or ()}
        kw["hidden_agent_tags"] = [t for t in (*a.hidden_agent_tags, *(args.hide_agent_tag or ()))
                                   if t.lower() not in shown]
    if args.rights is not None:
        kw["rights"] = None if args.rights == "default" else args.rights
    if args.name is not None:
        kw["name"] = args.name or None
    fresh = author_mod.set_author(store, lib, a.id, **kw)
    return emit(args, {"asset": card(fresh), "canonical": fresh.ref}, lambda: _card_human(fresh))


def cmd_author_orphans(args, store) -> int:
    lib = load(_root(args), store)
    rows = [r for r in author_mod.rows(store).values()
            if lib.get(r["asset_id"]) is None and (not args.pack or r["pack_id"] == args.pack)]
    return emit(args, {"orphans": rows},
                lambda: md_table(["id", "Pack", "Имя", "Подпись", "Теги"],
                                 [(r["asset_id"], r["pack_id"], r["name"], r["caption"], ", ".join(r["tags"]))
                                  for r in rows]) if rows else "Сирот нет.")


def register_author(sub, common) -> None:
    g = sub.add_parser("author", help="the Author's fields of an Asset (kept in factory.db)")
    gs = g.add_subparsers(dest="cmd", required=True)
    p = gs.add_parser("set", parents=[common], help="caption, tags, rights or ref name of one Asset")
    p.add_argument("ref", help="a ref or an Asset id")
    p.add_argument("--caption")
    p.add_argument("--tag", action="append", help="add a tag (repeatable)")
    p.add_argument("--clear-tags", action="store_true", help="drop the current tags first")
    p.add_argument("--hide-agent-tag", action="append", help="hide a wrong agent tag (repeatable)")
    p.add_argument("--show-agent-tag", action="append", help="bring a hidden agent tag back (repeatable)")
    p.add_argument("--rights", choices=(*RIGHTS, "default"), help="'default' goes back to the Pack default")
    p.add_argument("--name", help="the Author's ref name inside the category; empty clears it")
    p.set_defaults(func=cmd_author_set)
    p = gs.add_parser("orphans", parents=[common], help="Author rows whose Asset is in no index")
    p.add_argument("pack", nargs="?")
    p.set_defaults(func=cmd_author_orphans)


# --- import-tags / tags -------------------------------------------------------------

def cmd_import_tags(args, store) -> int:
    lib = load(_root(args), store)
    rep = imports.import_tags(store, lib, args.pack, Path(args.file), args.base, names=args.names).to_dict()
    return emit(args, rep, lambda: (
        f"Записей {rep['entries']}: найдено {rep['matched']}, изменено {rep['changed']}, имён {rep['named']}; "
        f"не найдено {len(rep['unmatched'])}" + (": " + ", ".join(rep["unmatched"]) if rep["unmatched"] else "")
        + (f"; пропущено тегов {len(rep['skipped_tags'])}" if rep["skipped_tags"] else "") + "."))


def register_import_tags(sub, common) -> None:
    p = sub.add_parser("import-tags", parents=[common],
                       help="import an old catalog tags.json ({sha256(relpath)[:12]: {label, tags}}) as Author fields")
    p.add_argument("pack")
    p.add_argument("file")
    p.add_argument("--base", required=True, help="the folder (relative to the Pack root) the old ids are relative to")
    p.add_argument("--names", action="store_true", help="also make each label the Asset's ref name when it has none")
    p.set_defaults(func=cmd_import_tags)


def cmd_tags_todo(args, store) -> int:
    lib = load(_root(args), store)
    todo = sheets.tag_todo(lib, args.pack)
    written = [str(p) for p in sheets.write_sheets(_root(args), lib, args.pack)] if args.sheets else []
    return emit(args, {"todo": len(todo), "sheets": written},
                lambda: f"Без тегов агента: {len(todo)}." + ("\n" + "\n".join(written) if written else ""))


def cmd_tags_apply(args, store) -> int:
    try:
        proposals = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LibraryError(f"cannot read {args.file}: {exc}") from exc
    if not isinstance(proposals, dict):
        raise LibraryError(f"{args.file}: expected an object of asset id → {{caption, tags}}")
    applied, unknown = sheets.apply_tags(_root(args), args.pack, proposals)
    return emit(args, {"applied": applied, "unknown": unknown},
                lambda: f"Применено: {applied}." + (" Неизвестные id: " + ", ".join(unknown) if unknown else ""))


def register_tags(sub, common) -> None:
    g = sub.add_parser("tags", help="the agent tag pass: contact sheets and proposals")
    gs = g.add_subparsers(dest="cmd", required=True)
    p = gs.add_parser("todo", parents=[common], help="Assets without agent caption and tags")
    p.add_argument("pack")
    p.add_argument("--sheets", action="store_true", help="write library/<pack>/sheets/NN.jpg and NN.json")
    p.set_defaults(func=cmd_tags_todo)
    p = gs.add_parser("apply", parents=[common], help="merge a proposals JSON into index.json (agent fields only)")
    p.add_argument("pack")
    p.add_argument("file")
    p.set_defaults(func=cmd_tags_apply)


GROUPS: list[Callable] = [register_pack, register_index, register_show, register_suggest, register_query,
                          register_author, register_import_tags, register_tags]


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine output (JSON on stdout)")
    common.add_argument("--db", help="the store (default: CF_FACTORY_DB or <shared root>/factory.db)")
    common.add_argument("--shared-root", dest="shared_root", help="shared root holding library/ (default: CF_SHARED_ROOT)")
    common.add_argument("--footage-root", dest="shared_root", help=argparse.SUPPRESS)
    ap = argparse.ArgumentParser(prog="python -m cf.library", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="group", required=True)
    for register in GROUPS:
        register(sub, common)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with open_store(args.db, seed=False) as store:
            backup.ensure_daily(store)
            if getattr(args, "backup", None):
                backup.before(store, args.backup)
            return args.func(args, store)
    except USER_ERRORS as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except sqlite3.OperationalError as exc:
        if not is_busy(exc):
            raise
        print(f"error: {BUSY_MESSAGE}", file=sys.stderr)
        return 1
