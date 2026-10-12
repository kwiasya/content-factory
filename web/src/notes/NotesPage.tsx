import { useCallback, useEffect, useState } from "react";
import { NoteItem } from "./NoteItem";
import { NOTE_KINDS, notesApi, type Note, type NoteKind } from "./notesApi";
import "./notes.css";

export const NOTES_HASH = "#/notes";

export function useNotesRoute(): boolean {
  const [active, setActive] = useState(() => window.location.hash === NOTES_HASH);
  useEffect(() => {
    const onHash = () => setActive(window.location.hash === NOTES_HASH);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return active;
}

const KIND_TITLES: Record<NoteKind, string> = {
  general: "General (every skill)",
  skill: "Skills",
  document: "Documents",
  video: "Videos",
  card: "Cards",
  idea: "Ideas",
};

const ORDER: NoteKind[] = ["general", "skill", "document", "video", "card", "idea"];

function Target({ note }: { note: Note }) {
  if (note.kind === "general") return null;
  if (note.kind === "document") {
    return (
      <a href={`#/doc/${encodeURIComponent(note.key)}`}>
        <code>{note.key}</code>
      </a>
    );
  }
  return <code>{note.key}</code>;
}

export function NotesPage() {
  const [notes, setNotes] = useState<Note[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [kind, setKind] = useState<NoteKind>("general");
  const [key, setKey] = useState("");
  const [text, setText] = useState("");

  const load = useCallback(() => {
    notesApi.list().then(setNotes, (e: Error) => setError(e.message));
  }, []);

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

  const needsKey = kind !== "general";
  const ready = text.trim() !== "" && (!needsKey || key.trim() !== "");

  return (
    <main className="doc notes-page">
      <div className="doc-head">
        <h1>Open Notes</h1>
      </div>
      {error && <p className="error">{error}</p>}

      <form
        className="note-form wide"
        onSubmit={(e) => {
          e.preventDefault();
          if (!ready) return;
          run(async () => {
            await notesApi.add(kind, needsKey ? key : "", text);
            setText("");
          });
        }}
      >
        <div className="note-target">
          <select value={kind} onChange={(e) => setKind(e.target.value as NoteKind)}>
            {NOTE_KINDS.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
          {needsKey && (
            <input
              value={key}
              placeholder={kind === "skill" ? "skill name, e.g. write-script" : kind === "document" ? "repo path" : "id"}
              onChange={(e) => setKey(e.target.value)}
            />
          )}
        </div>
        <textarea value={text} rows={2} placeholder="What should the Editor change?" onChange={(e) => setText(e.target.value)} />
        <button type="submit" className="primary" disabled={busy || !ready}>
          Add Note
        </button>
      </form>

      {notes === null ? (
        <p className="muted">Loading…</p>
      ) : notes.length === 0 ? (
        <p className="muted">No open Notes. The Editor has acted on everything.</p>
      ) : (
        ORDER.filter((k) => notes.some((n) => n.kind === k)).map((k) => (
          <section key={k} className="note-group">
            <h2>{KIND_TITLES[k]}</h2>
            <ul className="note-list">
              {notes
                .filter((n) => n.kind === k)
                .map((n) => (
                  <NoteItem
                    key={n.id}
                    note={n}
                    busy={busy}
                    context={<Target note={n} />}
                    onResolve={() => run(() => notesApi.resolve(n.id))}
                    onDelete={() => run(() => notesApi.remove(n.id))}
                  />
                ))}
            </ul>
          </section>
        ))
      )}
    </main>
  );
}
