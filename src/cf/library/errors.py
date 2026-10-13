"""Library errors. Each carries a stable ``code`` and its ``params`` so Desk can translate the message."""

from __future__ import annotations

from typing import Any


class LibraryError(Exception):
    code = "library_error"

    def __init__(self, message: str, **params: Any) -> None:
        super().__init__(message)
        self.params = params


class PackError(LibraryError):
    code = "pack_invalid"


class PackNotFound(LibraryError):
    code = "pack_not_found"

    def __init__(self, pack_id: str) -> None:
        super().__init__(f"no Pack {pack_id!r} registered; run: python -m cf.library pack add --config FILE",
                         pack=pack_id)


class AssetNotFound(LibraryError):
    code = "asset_not_found"

    def __init__(self, what: str) -> None:
        super().__init__(f"no Asset {what!r}", id=what)


class RefError(LibraryError):
    code = "ref_invalid"

    def __init__(self, ref: str) -> None:
        super().__init__(f"not an Asset ref: {ref!r} (expected @<category>/<name>)", ref=ref)


class RefNameInvalid(LibraryError):
    code = "ref_name_invalid"

    def __init__(self, name: str, slug: str) -> None:
        super().__init__(f"ref name {name!r} is not a clean slug; it would have to be {slug!r}", name=name, slug=slug)


class RefTaken(LibraryError):
    code = "ref_name_taken"

    def __init__(self, ref: str, holder: str) -> None:
        super().__init__(f"{ref} is already the ref of {holder}", ref=ref, holder=holder)


class FieldInvalid(LibraryError):
    def __init__(self, code: str, message: str, **params: Any) -> None:
        super().__init__(message, **params)
        self.code = code
