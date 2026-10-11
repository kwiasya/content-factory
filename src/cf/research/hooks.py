"""The Hook library: proven hooks saved from Reference cards, per Format.

A hook is saved per Format, not per Watchlist (spec #1, "Hook library"; ADR
0004): every Watchlist of a Format feeds and reads the same library. Each entry
copies from the card's analysis the hook category (bare, without a leftover
``proposed:`` prefix), the formula and the spoken hook (the measured opening
when the analysis has none), and keeps a link to its source Reference.

``export`` writes the library as ``formats/<format_id>/hook-library.md`` in the
repo, which ``write-script`` reads. The file is generated: the same store
state gives the same bytes, and every export overwrites it.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from cf.research import card, outlier, taxonomy
from cf.research.feed import outlier_text
from cf.research.store import Store

REPO_ROOT = Path(__file__).resolve().parents[3]
FORMAT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
EXPORT_COMMAND = "python -m cf.research hooks export"
SAVE_COMMAND = "python -m cf.research hooks save"


class HookError(Exception):
    """A Hook library request that cannot be carried out; the message says why."""


@dataclass(frozen=True)
class Hook:
    """One entry of a Format's Hook library."""
    id: int
    format_id: str
    category: str
    proposed: bool  # the category is not an approved hook_category (yet)
    formula: str | None
    text: str  # the spoken hook; empty for a Reference without speech
    source: str | None  # YouTube id of the source Reference; None once it left the store
    source_title: str | None
    source_url: str | None
    outlier: float | None  # the source's Outlier score now
    saved_at: str

    def to_dict(self) -> dict:
        return {**asdict(self), "outlier": None if self.outlier is None else round(self.outlier, 2)}


def check_format(format_id: str) -> str:
    """``format_id`` if it can name a folder under ``formats/``; else HookError."""
    if not isinstance(format_id, str) or not FORMAT_ID_RE.match(format_id):
        raise HookError(f"Format id {format_id!r} must be lower case letters, digits, - or _ (e.g. walk-reel)")
    return format_id


def library_path(format_id: str) -> Path:
    """Where the Hook library of a Format lives in the repo: ``formats/<format_id>/hook-library.md``."""
    return REPO_ROOT / "formats" / check_format(format_id) / "hook-library.md"


def _iso(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _approved(store: Store, category: str) -> bool:
    t = taxonomy.get(store, "hook_category", category)
    return t is not None and t.status == "approved"


_SELECT = ("SELECT h.id, h.format_id, h.category, h.formula, h.text, h.saved_at, h.source_video_id, "
           "v.external_id, v.title, v.url FROM hook h LEFT JOIN video v ON v.id = h.source_video_id")


def _hooks(store: Store, rows: list[dict], now: datetime | None) -> list[Hook]:
    scores = outlier.scores(store, [r["source_video_id"] for r in rows if r["source_video_id"] is not None],
                            now=now)
    return [Hook(id=r["id"], format_id=r["format_id"], category=r["category"],
                 proposed=not _approved(store, r["category"]), formula=r["formula"], text=r["text"],
                 source=r["external_id"], source_title=r["title"], source_url=r["url"],
                 outlier=scores.get(r["source_video_id"]), saved_at=r["saved_at"]) for r in rows]


def save(store: Store, format_id: str, video_id: str, *, now: datetime | None = None) -> Hook:
    """Save the hook of a carded Reference (YouTube id or URL) into the Hook library of ``format_id``.

    Saving a Reference already in that library updates its category, formula and
    text from the card and keeps the first saved date.
    """
    check_format(format_id)
    v = card.video(store, video_id)
    c = card.load(store, v["id"])
    if c is None or c["analysis"] is None:
        raise HookError(f"Reference {v['external_id']} has no analysis yet; run analyze-reference first")
    a, m = c["analysis"], c["measured"] or {}
    category = card.split_proposed((card.field(a, "hook.category") or "").strip())[0]
    if not category:
        raise HookError(f"the card of {v['external_id']} has no hook category")
    formula = card.field(a, "hook.formula")
    text = card.field(a, "hook.spoken_hook") or m.get("spoken_hook") or ""
    with store.transaction() as conn:
        row = conn.execute("SELECT id FROM hook WHERE format_id = ? AND source_video_id = ?",
                           (format_id, v["id"])).fetchone()
        if row is None:
            hid = conn.execute("INSERT INTO hook (format_id, category, formula, text, source_video_id, saved_at) "
                               "VALUES (?, ?, ?, ?, ?, ?)",
                               (format_id, category, formula, text, v["id"], _iso(now))).lastrowid
        else:
            hid = row[0]
            conn.execute("UPDATE hook SET category = ?, formula = ?, text = ? WHERE id = ?",
                         (category, formula, text, hid))
    return _hooks(store, store.query(_SELECT + " WHERE h.id = ?", (hid,)), now)[0]


def remove(store: Store, format_id: str, video_id: str) -> None:
    """Take the hook of a Reference out of the Hook library of ``format_id``."""
    check_format(format_id)
    v = card.video(store, video_id)
    with store.transaction() as conn:
        n = conn.execute("DELETE FROM hook WHERE format_id = ? AND source_video_id = ?",
                         (format_id, v["id"])).rowcount
    if not n:
        raise HookError(f"Reference {v['external_id']} is not in the Hook library of {format_id}")


def _order(h: Hook) -> tuple:
    return (h.category, h.outlier is None, -(h.outlier or 0), h.saved_at, h.id)


def list_hooks(store: Store, format_id: str, *, now: datetime | None = None) -> list[Hook]:
    """The Hook library of ``format_id``: by category, then the source's Outlier score (best first)."""
    check_format(format_id)
    return sorted(_hooks(store, store.query(_SELECT + " WHERE h.format_id = ?", (format_id,)), now), key=_order)


def render(store: Store, format_id: str, *, now: datetime | None = None) -> str:
    """The Hook library of ``format_id`` as the Markdown ``export`` writes."""
    hs = list_hooks(store, format_id, now=now)
    out = [f"# Hook library: {format_id}", "",
           f"Сгенерировано командой `{EXPORT_COMMAND} {format_id}` из базы исследования. "
           "Не правьте руками: следующий экспорт перезапишет файл. "
           f"Сохранить хук из карточки: `{SAVE_COMMAND} {format_id} <video_id>`.", ""]
    if not hs:
        return "\n".join(out + ["Хуков пока нет.", ""])
    cats = list(dict.fromkeys(h.category for h in hs))
    out += [f"Хуков: {len(hs)}, категорий: {len(cats)}. "
            "Внутри категории сначала больший Outlier score (на момент экспорта).", ""]
    for cat in cats:
        group = [h for h in hs if h.category == cat]
        t = taxonomy.get(store, "hook_category", cat)
        head = f"## {cat}" + (f": {t.label}" if t is not None and t.label else "")
        out += [head + (" (предложено)" if group[0].proposed else ""), ""]
        for h in group:
            text = " ".join(h.text.split())
            out.append(f"- **«{text}»**" if text else "- **без речи**")
            if h.formula:
                out.append(f"  - Формула: {' '.join(h.formula.split())}")
            if h.source is None:
                out.append("  - Источник: удалён из базы")
            else:
                title = " ".join((h.source_title or "без названия").split())
                out.append(f"  - Источник: «{title}» · {outlier_text(h.outlier)} · {h.source_url or '—'}")
            out.append(f"  - Сохранён: {h.saved_at[:10]}")
        out.append("")
    return "\n".join(out[:-1]) + "\n"


def export(store: Store, format_id: str, path: str | Path | None = None, *,
           now: datetime | None = None) -> Path:
    """Write the Hook library of ``format_id`` (default ``formats/<format_id>/hook-library.md``); return the path."""
    target = Path(path) if path is not None else library_path(format_id)
    text = render(store, check_format(format_id), now=now)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target
