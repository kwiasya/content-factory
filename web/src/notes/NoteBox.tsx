import { useCallback, useEffect, useState } from "react";
import { NoteItem } from "./NoteItem";
import { notesApi, type Note, type NoteKind } from "./notesApi";
import "./notes.css";

export function NoteBox({ kind, noteKey }: { kind: NoteKind; noteKey: string }) {
  const [notes, setNotes] = useState<Note[] | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    notesApi.list({ kind, key: noteKey }).then(setNotes, (e: Error) => setError(e.message));
  }, [kind, noteKey]);

  useEffect(load, [load]);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const add = () =>
    run(async () => {
      await notesApi.add(kind, noteKey, draft);
      setDraft("");
    });

  return (
    <section className="note-box">
      <h2>
        Notes for the Editor
        {notes && notes.length > 0 && <span className="note-count">{notes.length}</span>}
      </h2>
      {error && <p className="error">{error}</p>}
      {notes && notes.length > 0 && (
        <ul className="note-list">
          {notes.map((n) => (
            <NoteItem
              key={n.id}
              note={n}
              busy={busy}
              onResolve={() => run(() => notesApi.resolve(n.id))}
              onDelete={() => run(() => notesApi.remove(n.id))}
            />
          ))}
        </ul>
      )}
      <form
        className="note-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (draft.trim()) add();
        }}
      >
        <textarea
          value={draft}
          rows={2}
          placeholder="What should the Editor change here?"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && draft.trim()) {
              e.preventDefault();
              add();
            }
          }}
        />
        <button type="submit" className="primary" disabled={busy || !draft.trim()}>
          Add Note
        </button>
      </form>
    </section>
  );
}
