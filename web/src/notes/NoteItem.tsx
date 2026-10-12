import type { ReactNode } from "react";
import type { Note } from "./notesApi";
import { useT } from "../i18n";
import { formatTime } from "../format";

export function NoteItem({
  note,
  busy,
  onResolve,
  onDelete,
  context,
}: {
  note: Note;
  busy: boolean;
  onResolve: () => void;
  onDelete: () => void;
  context?: ReactNode;
}) {
  const t = useT();
  return (
    <li className="note">
      <div className="note-body">
        {context && <div className="note-context">{context}</div>}
        <p className="note-text">{note.text}</p>
        <span className="muted note-date">
          #{note.id} · {formatTime(note.created_at, t)}
        </span>
      </div>
      <div className="note-actions">
        <button disabled={busy} onClick={onResolve}>
          {t("notes.resolve")}
        </button>
        <button
          disabled={busy}
          onClick={() => {
            if (window.confirm(t("notes.confirmDelete"))) onDelete();
          }}
        >
          {t("notes.delete")}
        </button>
      </div>
    </li>
  );
}
