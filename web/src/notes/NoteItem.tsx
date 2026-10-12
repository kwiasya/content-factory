import type { ReactNode } from "react";
import type { Note } from "./notesApi";

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
  return (
    <li className="note">
      <div className="note-body">
        {context && <div className="note-context">{context}</div>}
        <p className="note-text">{note.text}</p>
        <span className="muted note-date">
          #{note.id} · {note.created_at.slice(0, 16).replace("T", " ")}
        </span>
      </div>
      <div className="note-actions">
        <button disabled={busy} onClick={onResolve}>
          Resolve
        </button>
        <button
          disabled={busy}
          onClick={() => {
            if (window.confirm("Delete this Note?")) onDelete();
          }}
        >
          Delete
        </button>
      </div>
    </li>
  );
}
