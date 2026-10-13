"""The Library: Packs of editing material read in place, indexed into Assets with refs ``@<category>/<name>``.

Public surface for the CLI, Desk and the build: ``load`` a ``Library``; ``register_pack``, ``index_pack``,
``set_author`` and ``import_tags`` change it; ``open_readonly`` opens factory.db for readers that never write;
``cf.library.sheets`` holds the agent tag pass (it needs OpenCV). Nothing here imports ``cf.desk``.
"""

from cf.library.author import UNSET, set_author
from cf.library.errors import (AssetNotFound, FieldInvalid, LibraryError, PackError, PackNotFound, RefError,
                               RefNameInvalid, RefTaken)
from cf.library.imports import ImportReport, import_tags
from cf.library.index import Report, index_pack
from cf.library.library import Asset, Library, PackView, card, load
from cf.library.packs import PackInfo, get_pack, list_packs, register_pack, remove_pack
from cf.library.readonly import open_readonly
from cf.library.refs import CATEGORIES, REF_RE, RIGHTS, slug

__all__ = [
    "CATEGORIES", "RIGHTS", "REF_RE", "UNSET", "Asset", "Library", "PackInfo", "PackView", "Report",
    "LibraryError", "PackError", "PackNotFound", "AssetNotFound", "RefError", "RefNameInvalid", "RefTaken",
    "FieldInvalid", "card", "load", "register_pack", "get_pack", "list_packs", "remove_pack", "index_pack",
    "set_author", "slug", "import_tags", "ImportReport", "open_readonly",
]
