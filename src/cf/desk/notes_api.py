"""Desk Notes API: the Author's Notes in factory.db, the only channel from Desk to the Editor (ADR 0005).

A Store is opened per request: sqlite connections stay on the thread that made them.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cf.research import notes
from cf.research.store import Store, open_store


class NoteIn(BaseModel):
    kind: str
    key: str = ""
    text: str


def router(db_path: Path) -> APIRouter:
    r = APIRouter(prefix="/api/notes")

    @contextmanager
    def store() -> Iterator[Store]:
        with open_store(db_path) as s:
            try:
                yield s
            except notes.NoteNotFound as e:
                raise HTTPException(404, str(e)) from None
            except notes.NoteError as e:
                raise HTTPException(422, str(e)) from None

    @r.get("")
    def list_notes(kind: str | None = None, key: str | None = None, all: int = 0) -> dict:
        with store() as s:
            return {"notes": [n.to_dict() for n in notes.list(s, kind=kind or None, key=key,
                                                               include_resolved=bool(all))]}

    @r.post("", status_code=201)
    def add_note(body: NoteIn) -> dict:
        with store() as s:
            return notes.add(s, body.kind, body.key, body.text).to_dict()

    @r.post("/{note_id}/resolve")
    def resolve_note(note_id: int) -> dict:
        with store() as s:
            return notes.resolve(s, note_id).to_dict()

    @r.delete("/{note_id}")
    def delete_note(note_id: int) -> dict:
        with store() as s:
            return notes.delete(s, note_id).to_dict()

    return r
