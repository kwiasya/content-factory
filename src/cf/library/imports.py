"""Importing the old catalog's ``tags.json`` (``{sha256(relpath)[:12]: {label, tags, category?}}``) as Author fields.

A caption is set only where the Author has none, tags are appended when missing, the category becomes one more
tag. With ``names`` the label also becomes the Author ref name of an Asset that has none (the file-derived ref
stays an alias). Running it twice changes nothing.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from cf.library import author, refs
from cf.library.errors import FieldInvalid, LibraryError, PackNotFound
from cf.library.library import Library
from cf.research.store import Store

NUMBERED = re.compile(r"^\s*\d+\s*[—–-]\s*")


@dataclass
class ImportReport:
    entries: int = 0
    matched: int = 0
    changed: int = 0
    named: int = 0
    skipped_tags: list = field(default_factory=list)
    unmatched: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def old_id(rel: str) -> str:
    return hashlib.sha256(rel.encode("utf-8")).hexdigest()[:12]


def _clean_tags(raw: list, label: str, report: ImportReport) -> list[str]:
    out = []
    for t in raw:
        if not isinstance(t, str) or t.strip().lower() == label.strip().lower():
            continue
        try:
            out += author.normalise_tags([t])
        except FieldInvalid:
            report.skipped_tags.append(t)
    return out


def import_tags(store: Store, library: Library, pack_id: str, tags_json: Path, base: str, *,
                names: bool = False) -> ImportReport:
    if library.pack(pack_id) is None:
        raise PackNotFound(pack_id)
    try:
        data = json.loads(Path(tags_json).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LibraryError(f"cannot read {tags_json}: {exc}") from exc
    if not isinstance(data, dict):
        raise LibraryError(f"{tags_json}: expected an object of id → {{label, tags}}")
    prefix = base.strip("/") + "/" if base.strip("/") else ""
    by_old: dict[str, str] = {}
    for a in library.assets:
        if a.pack != pack_id:
            continue
        for v in a.variants:
            if v["path"].startswith(prefix):
                by_old[old_id(v["path"][len(prefix):])] = a.id
    report = ImportReport(entries=len(data))
    rows = author.rows(store)
    taken: dict[str, str] = {}
    for key, entry in data.items():
        aid = by_old.get(key)
        if aid is None or not isinstance(entry, dict):
            report.unmatched.append(key)
            continue
        report.matched += 1
        asset = library.get(aid)
        row = rows.get(aid) or {}
        label = " ".join(str(entry.get("label") or "").split())
        fields: dict = {}
        if label and not row.get("caption"):
            fields["caption"] = label
        tags = list(row.get("tags") or [])
        have = {t.lower() for t in tags}
        extra = _clean_tags(list(entry.get("tags") or []), label, report)
        cat = entry.get("category")
        if isinstance(cat, str) and cat.strip():
            extra += _clean_tags([NUMBERED.sub("", cat)], label, report)
        added = []
        for t in extra:
            if t.lower() not in have:
                have.add(t.lower())
                added.append(t)
        if added:
            fields["tags"] = tags + added
        if names and label and not row.get("name"):
            name = _free_name(library, asset, refs.slug(label), taken)
            if name and name != asset.name:
                fields["name"] = name
                taken[refs.make(asset.category, name)] = aid
                author.add_alias(store, asset.file_ref, aid, "import")
                report.named += 1
        if fields:
            author.write(store, aid, pack_id, fields)
            report.changed += 1
    return report


def _free_name(library: Library, asset, base: str, taken: dict[str, str]) -> str | None:
    def busy(name: str) -> bool:
        ref = refs.make(asset.category, name)
        if taken.get(ref, asset.id) != asset.id:
            return True
        hit = library.lookup(ref)
        return hit is not None and hit[0].id != asset.id
    return refs.numbered(base, busy)
