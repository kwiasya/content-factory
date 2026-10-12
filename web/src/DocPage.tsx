import { useCallback, useEffect, useState } from "react";
import { api, type Doc, type GitState, type LogEntry } from "./api";
import { CodeEditor } from "./CodeEditor";
import { DiffView } from "./DiffView";
import { GitBadge } from "./GitBadge";
import { Preview } from "./Preview";
import { SkillLinks } from "./skills/SkillLinks";
import { SkillLint } from "./formats/SkillLint";
import { NoteBox } from "./notes/NoteBox";

type Tab = "edit" | "diff" | "history";

interface Conflict {
  text: string;
  hash: string;
}

export function DocPage({ path, onSaved }: { path: string; onSaved: () => void }) {
  const [doc, setDoc] = useState<Doc | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<Conflict | null>(null);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState<Tab>("edit");
  const [diff, setDiff] = useState<string | null>(null);
  const [log, setLog] = useState<LogEntry[] | null>(null);

  const load = useCallback(() => {
    api
      .doc(path)
      .then((d) => {
        setDoc(d);
        setDraft(d.text);
        setConflict(null);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [path]);

  useEffect(load, [load]);

  useEffect(() => {
    if (tab === "diff") {
      api.diff(path).then((d) => setDiff(d.diff), (e: Error) => setError(e.message));
    } else if (tab === "history") {
      api.log(path).then(setLog, (e: Error) => setError(e.message));
    }
  }, [tab, path, doc?.hash]);

  if (!doc) {
    return <main className="doc">{error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>}</main>;
  }

  const dirty = draft !== doc.text;

  const save = async (hash: string) => {
    setSaving(true);
    setError(null);
    const result = await api.save(doc.path, draft, hash);
    setSaving(false);
    if (result.status === "saved") {
      setDoc({ ...doc, text: draft, hash: result.hash, git: result.git as GitState });
      setConflict(null);
      onSaved();
    } else if (result.status === "conflict") {
      setConflict({ text: result.text, hash: result.hash });
    } else {
      setError(result.message);
    }
  };

  return (
    <main className="doc">
      <div className="doc-head">
        <div>
          <h1>{doc.title}</h1>
          <code className="path">{doc.path}</code>
        </div>
        <div className="doc-badges">
          <GitBadge state={doc.git} />
          {!doc.editable && <span className="badge readonly">read-only</span>}
        </div>
      </div>
      <SkillLint path={doc.path} version={doc.hash} />

      <SkillLinks path={doc.path} />

      <nav className="tabs">
        {(["edit", "diff", "history"] as Tab[]).map((t) => (
          <button key={t} className={t === tab ? "active" : ""} onClick={() => setTab(t)}>
            {t === "edit" ? (doc.editable ? "Edit" : "View") : t === "diff" ? "Diff vs HEAD" : "History"}
          </button>
        ))}
      </nav>

      {error && <p className="error">{error}</p>}

      {conflict && (
        <div className="conflict">
          <p>
            <strong>The file changed on disk since you opened it.</strong> Your text is still in the editor.
          </p>
          <div className="actions">
            <button onClick={load}>Load the fresh version (drop my edit)</button>
            <button onClick={() => save(conflict.hash)}>Overwrite with my edit</button>
          </div>
          <details>
            <summary>Fresh version on disk</summary>
            <pre>{conflict.text}</pre>
          </details>
        </div>
      )}

      {tab === "edit" && (
        <div className="split">
          <section className="pane preview">
            <Preview text={draft} kind={doc.kind} />
          </section>
          <section className="pane editor">
            <div className="toolbar">
              {doc.editable ? (
                <>
                  <button className="primary" disabled={!dirty || saving} onClick={() => save(doc.hash)}>
                    {saving ? "Saving…" : "Save"}
                  </button>
                  <button disabled={!dirty || saving} onClick={() => setDraft(doc.text)}>
                    Revert
                  </button>
                  <span className="muted">{dirty ? "unsaved changes" : "saved"}</span>
                </>
              ) : (
                <span className="muted">Read-only in Desk</span>
              )}
            </div>
            <CodeEditor value={draft} kind={doc.kind} readOnly={!doc.editable} onChange={setDraft} />
          </section>
        </div>
      )}

      {tab === "diff" && (diff === null ? <p className="muted">Loading…</p> : <DiffView diff={diff} />)}

      {tab === "history" &&
        (log === null ? (
          <p className="muted">Loading…</p>
        ) : log.length === 0 ? (
          <p className="muted">No commits touch this file.</p>
        ) : (
          <table className="log">
            <tbody>
              {log.map((e) => (
                <tr key={e.hash}>
                  <td>
                    <code>{e.hash.slice(0, 7)}</code>
                  </td>
                  <td>{e.date.slice(0, 10)}</td>
                  <td>{e.subject}</td>
                  <td className="muted">{e.author}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ))}

      <NoteBox kind="document" noteKey={doc.path} />
    </main>
  );
}
