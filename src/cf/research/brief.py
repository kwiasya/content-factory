"""Brief: a shortlisted Idea turned into the plan of one video, as a Markdown file.

``create`` fills ``research/templates/brief.md`` (``string.Template``, ``$name``
placeholders) and writes it to
``<footage root>/channels/<channel>/briefs/<idea id>-<slug>.md``, where the
channel is the argument, else the Watchlist's Channel, else ``_unassigned``.
Then the Idea moves shortlisted → brief with ``brief_path``. One Brief per
Idea: a second call, or an existing file at the target, refuses.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from string import Template

from cf.research import feed, ideas, outlier
from cf.research.ideas import IdeaError
from cf.research.store import Store, footage_root, now_iso
from cf.research.taxonomy import REPO_ROOT
from cf.research.watchlist import get as get_watchlist

TEMPLATE_PATH = REPO_ROOT / "research" / "templates" / "brief.md"
UNASSIGNED = "_unassigned"
SLUG_MAX = 60


def slug(title: str) -> str:
    """Lower-case words of ``title`` joined by ``-`` (letters of any script kept), at most ``SLUG_MAX`` chars."""
    s = re.sub(r"['’]", "", title.lower())
    s = re.sub(r"[\W_]+", "-", s).strip("-")
    if len(s) > SLUG_MAX:
        s = s[:SLUG_MAX].rsplit("-", 1)[0] if "-" in s[:SLUG_MAX] else s[:SLUG_MAX]
    return s or "idea"


def _folder(name: str) -> str:
    n = (name or "").strip()
    if not n or "/" in n or "\\" in n or n.startswith("."):
        raise IdeaError(f"Channel {name!r} is not a folder name (no slashes, not starting with '.')")
    return n


def path_for(idea: ideas.Idea, channel: str, root: Path | None = None) -> Path:
    return Path(root or footage_root()) / "channels" / _folder(channel) / "briefs" / f"{idea.id}-{slug(idea.title)}.md"


def _analysis(store: Store, video_id: int) -> dict | None:
    row = store.one("SELECT analysis FROM card WHERE video_id = ?", (video_id,))
    return json.loads(row["analysis"]) if row and row["analysis"] else None


def _hook(idea: ideas.Idea, cards: list[tuple[dict, dict | None]]) -> str:
    lines = [idea.fields["hook_alignment"], "", "Формулы хуков Reference:"]
    for src, a in cards:
        if a is None:
            lines.append(f"- {src['external_id']}: анализа нет")
            continue
        h = a.get("hook") or {}
        said = f" Сказано: «{h['spoken_hook']}»." if h.get("spoken_hook") else ""
        lines.append(f"- {h.get('formula')} (`{h.get('category')}`, {src['external_id']}).{said}")
    return "\n".join(lines)


def _structure(idea: ideas.Idea, cards: list[tuple[dict, dict | None]]) -> str:
    sf = idea.fields["storytelling_format"]
    lines = [f"**`{sf['category']}`**: {sf['why']}"]
    told = [(src, a["storytelling_format"]) for src, a in cards if a and a.get("storytelling_format")]
    if told:
        lines += ["", "Как это сделано в Reference:"]
        lines += [f"- {src['external_id']} (`{f.get('category')}`): {f.get('description')}" for src, f in told]
    return "\n".join(lines)


def _references(store: Store, idea: ideas.Idea) -> str:
    rows = ["| Reference | Outlier | Просмотры | Название | Ссылка |", "|---|---|---|---|---|"]
    for src in idea.sources:
        ext = src["external_id"]
        r = feed.reference(store, ext) if ext else None
        title = " ".join((src.get("title") or "—").split()).replace("|", "\\|")
        rows.append(f"| {ext} | {feed.outlier_text(outlier.score(store, ext) if ext else None)} | "
                    f"{feed.views_text(r.views if r else None)} | {title} | {src.get('url') or '—'} |")
    return "\n".join(rows)


def render(store: Store, idea: ideas.Idea, *, channel: str, format_id: str) -> str:
    """The Brief text of ``idea`` from the template."""
    f = idea.fields
    cards = [(src, _analysis(store, src["id"])) for src in idea.sources]
    cm = f.get("contrast_mechanism")
    contrast = (f"Принято думать: {cm['common_belief']}. На деле: {cm['contrarian_reality']}."
                if cm else "нет: идея ничего не опровергает.")
    notes = "\n".join(f"- {n['at']}: {n['text']}" for n in idea.notes) or "Заметок нет."
    return Template(TEMPLATE_PATH.read_text(encoding="utf-8")).substitute(
        title=idea.title, idea_id=idea.id, watchlist=idea.watchlist, channel=channel, format=format_id,
        created=now_iso(), summary=f["summary"], positioning=f["content_positioning"], contrast=contrast,
        hook=_hook(idea, cards), structure=_structure(idea, cards),
        personalizations="\n".join(f"{n}. {p}" for n, p in enumerate(f["personalizations"], 1)),
        references=_references(store, idea), notes=notes)


def create(store: Store, idea_id: int, *, channel: str | None = None, format_id: str | None = None,
           root: Path | None = None) -> Path:
    """Write the Brief of a shortlisted Idea and mark the Idea ``brief``; return the file's path."""
    idea = ideas.get(store, idea_id)
    if idea.status == "brief":
        raise IdeaError(f"Idea {idea.id} already has a Brief: {idea.brief_path}")
    if idea.status != "shortlisted":
        raise IdeaError(f"Idea {idea.id} is {idea.status}; brief needs an Idea that is shortlisted")
    w = get_watchlist(store, idea.watchlist)
    ch = channel if channel is not None else (w.channel_id or UNASSIGNED)
    path = path_for(idea, ch, root)
    if path.exists():
        raise IdeaError(f"Brief file already exists, not overwriting: {path}")
    text = render(store, idea, channel=ch.strip(), format_id=format_id or w.format_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:
        fh.write(text)
    try:
        ideas.mark_brief(store, idea.id, str(path))
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path
