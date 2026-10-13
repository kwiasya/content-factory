"""Refs that keep resolving: rename aliases written after an index run."""

from __future__ import annotations

from cf.research.store import Store


def after_index(store: Store, pack_id: str, built: list[dict], prev_assets: dict[str, dict]) -> int:
    return 0
