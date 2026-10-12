"""Desk Notes API: the Author's Notes in factory.db, the only channel from Desk to the Editor (ADR 0005).

Stores are opened through `cf.desk.storeuse`; listing Notes before factory.db exists gives an empty list.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cf.research import notes
from cf.desk import storeuse
from cf.desk.problems import Problem
from cf.research.store import Store


class NoteIn(BaseModel):
    kind: str
    key: str = ""
    text: str


def router(db_path: Path) -> APIRouter:
    r = APIRouter(prefix="/api/notes")

    @contextmanager
    def store(write: bool = True, note_id: int | None = None) -> Iterator[Store]:
        with (storeuse.writing if write else storeuse.reading)(db_path) as s:
            try:
                yield s
            except notes.NoteNotFound as e:
                raise Problem(404, "note_not_found", str(e), id=note_id) from None
            except notes.NoteError as e:
                raise HTTPException(422, str(e)) from None

    @r.get("")
    def list_notes(kind: str | None = None, key: str | None = None, all: int = 0) -> dict:
        if not storeuse.exists(db_path):
            return {"notes": []}
        with store(write=False) as s:
            return {"notes": [n.to_dict() for n in notes.list(s, kind=kind or None, key=key,
                                                               include_resolved=bool(all))]}

    @r.post("", status_code=201)
    def add_note(body: NoteIn) -> dict:
        with store() as s:
            return notes.add(s, body.kind, body.key, body.text).to_dict()

    @r.post("/{note_id}/resolve")
    def resolve_note(note_id: int) -> dict:
        with store(note_id=note_id) as s:
            return notes.resolve(s, note_id).to_dict()

    @r.delete("/{note_id}")
    def delete_note(note_id: int) -> dict:
        with store(note_id=note_id) as s:
            return notes.delete(s, note_id).to_dict()

    return r
