"""The document catalogue: which repo files Desk shows, in which group, and whether the Author may edit them.

Desk reads and writes only paths this catalogue yields; a later group is one more entry in GROUPS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

TEXT_SUFFIXES = (".md", ".json")


def folder_title(depth: int) -> Callable[[str], str]:
    """Title "<folder> · <rest>" where folder is the path part at `depth`; a lone SKILL.md is just the folder."""

    def title(rel: str) -> str:
        parts = rel.split("/")
        name, rest = parts[depth], "/".join(parts[depth + 1:])
        return name if rest == "SKILL.md" else f"{name} · {rest}"

    return title


@dataclass(frozen=True)
class Source:
    glob: str
    editable: bool = True
    exclude: Callable[[str], bool] = lambda rel: False
    title: Callable[[str], str] | None = None
    empty_hint: str | None = None


@dataclass(frozen=True)
class Group:
    id: str
    title: str
    sources: tuple[Source, ...]
    hidden: bool = False


@dataclass(frozen=True)
class Entry:
    path: str
    group: str
    title: str
    kind: str
    editable: bool

    def as_dict(self) -> dict:
        return {"path": self.path, "group": self.group, "title": self.title, "kind": self.kind,
                "editable": self.editable}


@dataclass
class Listing:
    group: Group
    entries: list[Entry] = field(default_factory=list)
    empty: list[dict] = field(default_factory=list)


def is_vendored_skill(rel: str) -> bool:
    return rel.split("/")[2].startswith("remotion-")


skill_title = folder_title(2)

GROUPS: tuple[Group, ...] = (
    Group("skills", "Skills", (
        Source(".claude/skills/*/**/*", exclude=is_vendored_skill, title=skill_title),
    )),
    Group("skills-vendored", "Vendored skills", (
        Source(".claude/skills/remotion-*/**/*", editable=False, title=skill_title),
    ), hidden=True),
    Group("content", "Content", (
        Source("CLAUDE.md"),
        Source("docs/agents/*.md"),
        Source("style.json"),
        Source("research/templates/*.md"),
        Source("research/taxonomy.json"),
        Source("author/*.md", empty_hint="author/ is missing: run /author-setup in Claude Code to create the profile."),
    )),
    Group("formats", "Formats", (
        Source("formats/*/FORMAT.md", title=folder_title(1)),
        Source("formats/*/hook-library.md", editable=False, title=folder_title(1)),
    )),
)


def kind_of(rel: str) -> str:
    return "json" if rel.endswith(".json") else "markdown"


def _matches(repo: Path, source: Source) -> list[str]:
    found = []
    for path in repo.glob(source.glob):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(repo).as_posix()
        if not source.exclude(rel):
            found.append(rel)
    return sorted(set(found))


def _source_root(source: Source) -> str:
    head = source.glob.split("*", 1)[0]
    return head.rsplit("/", 1)[0] if "/" in head else ""


def list_groups(repo: Path, *, include_hidden: bool = False) -> list[Listing]:
    listings = []
    for group in GROUPS:
        if group.hidden and not include_hidden:
            continue
        listing = Listing(group)
        for source in group.sources:
            rels = _matches(repo, source)
            if not rels and source.empty_hint and not (repo / _source_root(source)).is_dir():
                listing.empty.append({"glob": source.glob, "hint": source.empty_hint})
            for rel in rels:
                title = source.title(rel) if source.title else rel
                listing.entries.append(Entry(rel, group.id, title, kind_of(rel), source.editable))
        listings.append(listing)
    return listings


def find(repo: Path, rel: str) -> Entry | None:
    """The catalogue entry for a repo-relative path, hidden groups included; None for anything else."""
    for listing in list_groups(repo, include_hidden=True):
        for entry in listing.entries:
            if entry.path == rel:
                return entry
    return None
