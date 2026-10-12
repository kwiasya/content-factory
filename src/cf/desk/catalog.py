"""The document catalogue: which repo files Desk shows, in which group, and whether the Author may edit them.

Desk reads and writes only paths this catalogue yields; a later group is one more entry in GROUPS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from cf.desk import skills

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
    empty_code: str | None = None
    skill: bool = False


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
    skill: dict | None = None

    def as_dict(self) -> dict:
        return {"path": self.path, "group": self.group, "title": self.title, "kind": self.kind,
                "editable": self.editable, **(self.skill or {})}


@dataclass
class Listing:
    group: Group
    entries: list[Entry] = field(default_factory=list)
    empty: list[dict] = field(default_factory=list)


def is_vendored_skill(rel: str) -> bool:
    return skills.is_vendored(rel.split("/")[2])


skill_title = folder_title(2)

GROUPS: tuple[Group, ...] = (
    Group("skills", "Skills", (
        Source(".claude/skills/*/**/*", exclude=is_vendored_skill, title=skill_title, skill=True),
    )),
    Group("skills-vendored", "Vendored skills", (
        Source(f".claude/skills/{skills.VENDORED_PREFIX}*/**/*", editable=False, title=skill_title, skill=True),
    ), hidden=True),
    Group("content", "Content", (
        Source("CLAUDE.md"),
        Source("docs/agents/*.md"),
        Source("style.json"),
        Source("research/templates/*.md"),
        Source("research/taxonomy.json"),
        Source("author/*.md", empty_hint="author/ is missing: run /author-setup in Claude Code to create the profile.",
               empty_code="author_missing"),
    )),
    Group("formats", "Formats", (
        Source("formats/*/FORMAT.md", title=folder_title(1)),
        Source("formats/*/hook-library.md", editable=False, title=folder_title(1)),
    )),
    Group("research", "Research", (
        Source("docs/research/SYNTHESIS*.md", title=lambda rel: rel.rsplit("/", 1)[1]),
        Source("docs/research/README.md", editable=False, title=lambda rel: rel.rsplit("/", 1)[1]),
        Source("docs/research/[0-9][0-9]-*/rules.md", title=folder_title(2)),
        Source("docs/research/[0-9][0-9]-*/*.md", editable=False, title=folder_title(2),
               exclude=lambda rel: rel.endswith("/rules.md")),
        Source("docs/research/[0-9][0-9]-*/notes/*.md", editable=False, title=folder_title(2)),
    )),
)


def frontmatter_description(text: str) -> str | None:
    """The `description` of a SKILL.md YAML frontmatter: one line, quoted, or a folded/literal block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return None
        if not line.startswith("description:"):
            continue
        value = line[len("description:"):].strip()
        if value[:1] in (">", "|"):
            block = []
            for more in lines[i + 1:]:
                if more.strip() == "---" or (more and not more[0].isspace()):
                    break
                block.append(more.strip())
            value = " ".join(b for b in block if b)
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        return value or None
    return None


def skill_facts(repo: Path, rel: str) -> dict:
    path = repo / rel
    st = path.stat()
    name = skills.name_of(rel) or ""
    description = frontmatter_description(path.read_text(encoding="utf-8")) if path.name == "SKILL.md" else None
    return {"skill": name, "vendored": skills.is_vendored(name), "description": description, "size": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds")}


def kind_of(rel: str) -> str:
    return "json" if rel.endswith(".json") else "markdown"


def _matches(repo: Path, source: Source) -> list[str]:
    found = []
    for path in repo.glob(source.glob):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if not path.resolve().is_relative_to(repo):
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
                listing.empty.append({"glob": source.glob, "hint": source.empty_hint, "code": source.empty_code})
            for rel in rels:
                title = source.title(rel) if source.title else rel
                facts = skill_facts(repo, rel) if source.skill else None
                listing.entries.append(Entry(rel, group.id, title, kind_of(rel), source.editable, facts))
        listings.append(listing)
    return listings


def find(repo: Path, rel: str) -> Entry | None:
    """The catalogue entry for a repo-relative path, hidden groups included; None for anything else."""
    for listing in list_groups(repo, include_hidden=True):
        for entry in listing.entries:
            if entry.path == rel:
                return entry
    return None
