import { useCallback, useEffect, useState } from "react";
import { NoteItem } from "./NoteItem";
import { NOTE_KINDS, notesApi, type Note, type NoteKind } from "./notesApi";
import { useT, type Problem } from "../i18n";
import { ErrorLine } from "../ErrorLine";
import "./notes.css";

export const NOTES_HASH = "#/notes";

export function notesRoute(hash: string) {
  return hash === NOTES_HASH ? <NotesPage /> : null;
}

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

function NotesPage() {
  const t = useT();
  const [notes, setNotes] = useState<Note[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Problem | null>(null);
  const [kind, setKind] = useState<NoteKind>("general");
  const [key, setKey] = useState("");
  const [text, setText] = useState("");

  const load = useCallback(() => {
    notesApi.list().then(setNotes, setError);
  }, []);

  useEffect(load, [load]);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      load();
    } catch (e) {
      setError(e as Error);
    } finally {
      setBusy(false);
    }
  };

  const needsKey = kind !== "general";
  const ready = text.trim() !== "" && (!needsKey || key.trim() !== "");

  return (
    <main className="doc notes-page">
      <div className="doc-head">
        <h1>{t("notes.title")}</h1>
      </div>
      <ErrorLine error={error} />

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
                {t(`notes.kind.${k}`)}
              </option>
            ))}
          </select>
          {needsKey && (
            <input
              value={key}
              placeholder={t(kind === "skill" ? "notes.keySkill" : kind === "document" ? "notes.keyDocument" : "notes.keyId")}
              onChange={(e) => setKey(e.target.value)}
            />
          )}
        </div>
        <textarea value={text} rows={2} placeholder={t("notes.placeholder")} onChange={(e) => setText(e.target.value)} />
        <button type="submit" className="primary" disabled={busy || !ready}>
          {t("notes.add")}
        </button>
      </form>

      {notes === null ? (
        <p className="muted">{t("common.loading")}</p>
      ) : notes.length === 0 ? (
        <p className="muted">{t("notes.empty")}</p>
      ) : (
        ORDER.filter((k) => notes.some((n) => n.kind === k)).map((k) => (
          <section key={k} className="note-group">
            <h2>{t(`notes.group.${k}`)}</h2>
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
