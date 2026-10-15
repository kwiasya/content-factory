"""Reference cards, schema ``cf-reference-card/1``.

A card has two sections: ``measured`` (computed by ``measure`` from the
Reference folder's artifacts, rewritten on every fetch) and ``analysis``
(written by the Editor with the Sandcastles fields; None until then). Measuring
again never touches the analysis. The store row (table ``card``) is the source
of truth; ``card.json`` in the Reference folder is a copy for humans.

``validate`` checks an analysis (required fields, categories against the
taxonomy or ``proposed:<value>``, the spoken hook quoted from the transcript);
``save_analysis`` validates, stores and proposes new taxonomy values. Field
reference: ``docs/research/reference-card.md``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from cf.research import measure, taxonomy
from cf.research.store import Store, dumps, footage_root, now_iso

SCHEMA = "cf-reference-card/1"


class CardError(Exception):
    """A card cannot be saved: no measured card yet, or the analysis breaks rules (``violations``)."""

    def __init__(self, message: str, violations: list[str] | None = None):
        super().__init__(message)
        self.violations = violations or []


def _card(row: dict) -> dict:
    return {"schema": row["schema"], "measured": json.loads(row["measured"]),
            "analysis": None if row["analysis"] is None else json.loads(row["analysis"])}


def load(store: Store, video_id: int) -> dict | None:
    """The card of a video (store id), or None."""
    row = store.one("SELECT schema, measured, analysis FROM card WHERE video_id = ?", (video_id,))
    return None if row is None else _card(row)


def save(store: Store, video_id: int, measured: dict, *, path: Path | None = None) -> dict:
    """Write the measured section (analysis kept, or None for a new card); also to ``path`` if given."""
    with store.transaction() as c:
        c.execute("INSERT INTO card (video_id, schema, measured, analysis, written_at) VALUES (?, ?, ?, NULL, ?) "
                  "ON CONFLICT (video_id) DO UPDATE SET schema = excluded.schema, measured = excluded.measured, "
                  "written_at = excluded.written_at",
                  (video_id, SCHEMA, dumps(measured), now_iso()))
    saved = load(store, video_id)
    if path is not None:
        write_json(saved, path)
    return saved


def write_json(card: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(card, ensure_ascii=False, indent=1) + "\n")
    tmp.replace(path)


# --- analysis -------------------------------------------------------------------
# Field reference: docs/research/reference-card.md. Leaves are "text" (non-empty string),
# "nullable" (non-empty string or null) or a taxonomy kind (approved value or ``proposed:<value>``).

TEXT, NULLABLE = "text", "nullable"
PROPOSED = "proposed:"
ANALYSIS_FIELDS: dict = {
    "summary": TEXT,
    "idea_analysis": {
        "topic": TEXT, "idea_seed": TEXT, "unique_angle": TEXT,
        "common_belief": NULLABLE, "contrarian_reality": NULLABLE, "supporting_evidence": TEXT,
    },
    "hook": {"category": "hook_category", "formula": TEXT, "spoken_hook": NULLABLE, "alignment": TEXT},
    "storytelling_format": {"category": "storytelling_format", "description": TEXT, "analysis": TEXT},
    "visual_layout": {"category": "visual_layout", "sub_category": "editing_style"},
}


def _walk(node: Any, spec: dict, where: str, out: list[str], leaves: dict[str, Any]) -> None:
    if not isinstance(node, dict):
        out.append(f"{where or 'analysis'}: must be an object")
        return
    for key in node:
        if key not in spec:
            out.append(f"{where + '.' if where else ''}{key}: unknown field")
    for key, rule in spec.items():
        path = f"{where}.{key}" if where else key
        if key not in node:
            out.append(f"{path}: missing")
            continue
        value = node[key]
        if isinstance(rule, dict):
            _walk(value, rule, path, out, leaves)
            continue
        if value is None and rule == NULLABLE:
            leaves[path] = None
            continue
        if not isinstance(value, str):
            out.append(f"{path}: must be a string, got {value!r}")
        elif not value.strip():
            out.append(f"{path}: empty")
        else:
            leaves[path] = value


def validate(card: dict, store: Store, *, transcript: str | dict | None = None) -> list[str]:
    """Violations of the card's analysis section, one string per rule broken (empty: valid)."""
    out: list[str] = []
    if card.get("schema") != SCHEMA:
        out.append(f"schema: {card.get('schema')!r}, expected {SCHEMA!r}")
    a = card.get("analysis")
    if a is None:
        return out + ["analysis: missing"]
    leaves: dict[str, Any] = {}
    _walk(a, ANALYSIS_FIELDS, "", out, leaves)
    belief, reality = "idea_analysis.common_belief", "idea_analysis.contrarian_reality"
    if belief in leaves and reality in leaves and (leaves[belief] is None) != (leaves[reality] is None):
        empty, other = (belief, reality) if leaves[belief] is None else (reality, belief)
        out.append(f"{empty}: null while {other.split('.')[-1]} is set; give both or neither")
    for path, kind in category_paths():
        if leaves.get(path) is not None:
            problem = category_problem(store, kind, leaves[path])
            if problem:
                out.append(f"{path}: {problem}")
    if "hook.spoken_hook" in leaves:
        problem = _spoken_hook_problem(leaves["hook.spoken_hook"], card.get("measured") or {}, transcript)
        if problem:
            out.append(f"hook.spoken_hook: {problem}")
    return out


def normalize(text: str) -> str:
    """Lower case, apostrophes dropped, other punctuation as spaces, single spaces."""
    text = re.sub(r"['’ʼ`]", "", text.casefold())
    return " ".join(re.sub(r"[\W_]+", " ", text).split())


def transcript_text(transcript: str | dict | None) -> str | None:
    """Plain text of a transcript given as text or as a stable-ts result (None stays None)."""
    if transcript is None or isinstance(transcript, str):
        return transcript
    return measure.join_words(measure.words(transcript))


def quotes(hook: str, text: str | None) -> bool:
    """True when ``hook`` appears in ``text`` as whole words, ignoring case and punctuation."""
    needle = normalize(hook)
    return bool(needle) and f" {needle} " in f" {normalize(text or '')} "


def spoken_hook_problem(card: dict, transcript: str | dict | None) -> str | None:
    """Why the analysis' ``hook.spoken_hook`` does not hold against ``transcript`` (None: it holds or there is none)."""
    hook = ((card.get("analysis") or {}).get("hook") or {})
    if "spoken_hook" not in hook:
        return None
    return _spoken_hook_problem(hook["spoken_hook"], card.get("measured") or {}, transcript)


def _spoken_hook_problem(hook: str | None, measured: dict, transcript: str | dict | None) -> str | None:
    full = transcript_text(transcript)
    opening = measured.get("spoken_hook")
    has_speech = bool(normalize(full or "")) or bool(normalize(opening or ""))
    if hook is None:
        return "null, but the Reference has speech; quote its opening words" if has_speech else None
    if full is None and not opening:
        return "no transcript to check against (fetch the Reference or pass the transcript)"
    if quotes(hook, full) or quotes(hook, opening):
        return None
    return f"not found in the transcript: {hook!r}"


def _leaves(spec: dict = ANALYSIS_FIELDS, where: str = "") -> list[tuple[str, str]]:
    out = []
    for key, rule in spec.items():
        path = f"{where}.{key}" if where else key
        out += _leaves(rule, path) if isinstance(rule, dict) else [(path, rule)]
    return out


def field_paths() -> list[str]:
    """Dotted paths of every analysis field, in reading order."""
    return [path for path, _ in _leaves()]


def category_paths() -> list[tuple[str, str]]:
    """``(field path, taxonomy kind)`` of every category field."""
    return [(path, rule) for path, rule in _leaves() if rule not in (TEXT, NULLABLE)]


def split_proposed(value: str) -> tuple[str, bool]:
    """``("x", True)`` for ``proposed:x``, else ``(value, False)``."""
    if value.startswith(PROPOSED):
        return value[len(PROPOSED):], True
    return value, False


def _status(store: Store, kind: str, value: str) -> str | None:
    t = taxonomy.get(store, kind, value)
    return None if t is None else t.status


def category_problem(store: Store, kind: str, raw: str) -> str | None:
    """Why ``raw`` (a value or ``proposed:<value>``) cannot stand in a field of taxonomy ``kind``; None when it can."""
    value, proposed = split_proposed(raw)
    status = _status(store, kind, value)
    if proposed:
        if not taxonomy.VALUE_RE.fullmatch(value):
            return f"proposed value {value!r} must be snake_case (a-z, 0-9, _)"
        if status == "rejected":
            return f"{value!r} was rejected as {kind}; pick an approved value"
        return None
    if status == "approved":
        return None
    if status == "proposed":
        return f"{value!r} is a proposed {kind} awaiting approval; write {PROPOSED}{value} until it is approved"
    if status == "rejected":
        return f"{value!r} was rejected as {kind}; pick an approved value"
    return f"{value!r} is not an approved {kind}; use one or write {PROPOSED}{value}"


# --- saving the analysis ----------------------------------------------------------


def video(store: Store, ref: int | str) -> dict:
    """``{"id", "external_id"}`` of a video given by store id, YouTube id or URL.

    Only an int (not a bool) or a str is a reference; anything else is a ``CardError``."""
    if type(ref) is not int and not isinstance(ref, str):
        raise CardError(f"{ref!r} is not a Reference: give a store id, YouTube id or URL")
    if type(ref) is int or (ref.isdigit() and len(ref) != 11):
        row = store.one("SELECT id, external_id FROM video WHERE id = ?", (int(ref),))
    else:
        from cf.research.fetch import FetchError, parse_video_ref
        try:
            ext = parse_video_ref(ref)
        except FetchError as exc:
            raise CardError(str(exc)) from exc
        row = store.one("SELECT id, external_id FROM video WHERE platform = 'youtube' AND external_id = ?", (ext,))
    if row is None:
        raise CardError(f"no Reference {ref!r} in the store; run fetch first")
    return row


def reference_dirs(external_id: str, root: Path | None = None) -> list[Path]:
    """Every Reference folder of a video: ``<footage root>/references/*/<external_id>/``."""
    base = Path(root or footage_root()) / "references"
    return sorted(p for p in base.glob(f"*/{external_id}") if p.is_dir())


def read_transcript(external_id: str, root: Path | None = None) -> dict | None:
    """``transcript.json`` (stable-ts result) from the Reference folder, or None."""
    for d in reference_dirs(external_id, root):
        path = d / "transcript.json"
        if path.exists():
            return json.loads(path.read_text())
    return None


def _set(analysis: dict, path: str, value: str) -> None:
    *head, last = path.split(".")
    node = analysis
    for k in head:
        node = node[k]
    node[last] = value


def field(analysis: dict, path: str) -> Any:
    node: Any = analysis
    for k in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(k)
    return node


def _write(store: Store, video_id: int, external_id: str, analysis: dict, root: Path | None) -> dict:
    with store.transaction() as c:
        c.execute("UPDATE card SET analysis = ?, written_at = ? WHERE video_id = ?",
                  (dumps(analysis), now_iso(), video_id))
    saved = load(store, video_id)
    for d in reference_dirs(external_id, root):
        write_json(saved, d / "card.json")
    return saved


def save_analysis(store: Store, video_id: int | str, analysis: dict, *,
                  transcript: str | dict | None = None, root: Path | None = None) -> dict:
    """Validate and store the analysis section; ``proposed:`` values enter the taxonomy as proposed.

    The transcript defaults to ``transcript.json`` of the Reference folder. Refuses with
    ``CardError`` (``violations`` set) when the analysis breaks a rule; nothing is written then.
    The card row and every ``card.json`` of the video are rewritten; the measured section stays.
    """
    v = video(store, video_id)
    current = load(store, v["id"])
    if current is None:
        raise CardError(f"Reference {v['external_id']} has no measured card yet; run fetch first")
    if transcript is None:
        transcript = read_transcript(v["external_id"], root)
    candidate = {**current, "analysis": analysis}
    problems = validate(candidate, store, transcript=transcript)
    if problems:
        raise CardError(f"analysis of {v['external_id']} breaks {len(problems)} rule(s)", problems)
    analysis = json.loads(json.dumps(analysis))
    for path, kind in category_paths():
        value, proposed = split_proposed(field(analysis, path) or "")
        if not proposed:
            continue
        if _status(store, kind, value) == "approved":
            _set(analysis, path, value)
        else:
            taxonomy.propose(store, kind, value, source=f"card:{v['external_id']}")
    return _write(store, v["id"], v["external_id"], analysis, root)


def cards_using(store: Store, kind: str, value: str) -> list[dict]:
    """Cards whose analysis carries ``value`` or ``proposed:value`` in a field of ``kind``:
    ``{"video_id", "external_id", "path", "proposed"}`` per field."""
    paths = [p for p, k in category_paths() if k == kind]
    out = []
    rows = store.query("SELECT c.video_id, v.external_id, c.analysis FROM card c JOIN video v ON v.id = c.video_id "
                       "WHERE c.analysis IS NOT NULL ORDER BY v.external_id")
    for r in rows:
        a = json.loads(r["analysis"])
        for path in paths:
            raw = field(a, path)
            if isinstance(raw, str) and split_proposed(raw)[0] == value:
                out.append({"video_id": r["video_id"], "external_id": r["external_id"], "path": path,
                            "proposed": split_proposed(raw)[1]})
    return out


def drop_proposed_prefix(store: Store, kind: str, value: str, *, root: Path | None = None) -> list[str]:
    """Rewrite ``proposed:value`` to ``value`` in every card (store and card.json); return their YouTube ids."""
    hits = [h for h in cards_using(store, kind, value) if h["proposed"]]
    done: list[str] = []
    for h in hits:
        a = load(store, h["video_id"])["analysis"]
        _set(a, h["path"], value)
        _write(store, h["video_id"], h["external_id"], a, root)
        if h["external_id"] not in done:
            done.append(h["external_id"])
    return done
