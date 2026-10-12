import { useCallback, useEffect, useState } from "react";
import { api, type Doc } from "../api";
import { CodeEditor } from "../CodeEditor";
import { GitBadge } from "../GitBadge";
import { Preview } from "../Preview";

export function RulesSection({ path }: { path: string }) {
  const [doc, setDoc] = useState<Doc | null>(null);
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [conflict, setConflict] = useState<{ text: string; hash: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.doc(path).then(
      (d) => {
        setDoc(d);
        setDraft(d.text);
        setConflict(null);
        setError(null);
      },
      (e: Error) => setError(e.message),
    );
  }, [path]);

  useEffect(load, [load]);

  if (!doc) {
    return error ? <p className="error">{error}</p> : <p className="muted">Loading rules…</p>;
  }

  const dirty = draft !== doc.text;

  const save = async (hash: string) => {
    setSaving(true);
    setError(null);
    const result = await api.save(doc.path, draft, hash);
    setSaving(false);
    if (result.status === "saved") {
      setDoc({ ...doc, text: draft, hash: result.hash, git: result.git });
      setConflict(null);
      setEditing(false);
    } else if (result.status === "conflict") {
      setConflict({ text: result.text, hash: result.hash });
    } else {
      setError(result.message);
    }
  };

  return (
    <section className="rules">
      <div className="toolbar">
        <strong>rules.md</strong>
        <GitBadge state={doc.git} />
        {editing ? (
          <>
            <button className="primary" disabled={!dirty || saving} onClick={() => save(doc.hash)}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              disabled={saving}
              onClick={() => {
                setDraft(doc.text);
                setEditing(false);
              }}
            >
              Cancel
            </button>
            <span className="muted">{dirty ? "unsaved changes" : "no changes"}</span>
          </>
        ) : (
          doc.editable && <button onClick={() => setEditing(true)}>Edit</button>
        )}
        <a className="muted" href={"#/doc/" + encodeURIComponent(doc.path)}>
          open as document
        </a>
      </div>
      {error && <p className="error">{error}</p>}
      {conflict && (
        <div className="conflict">
          <p>
            <strong>rules.md changed on disk since you opened it.</strong> Your text is still in the editor.
          </p>
          <div className="actions">
            <button onClick={load}>Load the fresh version (drop my edit)</button>
            <button onClick={() => save(conflict.hash)}>Overwrite with my edit</button>
          </div>
        </div>
      )}
      {editing ? (
        <div className="split">
          <section className="pane preview">
            <Preview text={draft} kind="markdown" />
          </section>
          <section className="pane editor">
            <CodeEditor value={draft} kind="markdown" readOnly={false} onChange={setDraft} />
          </section>
        </div>
      ) : (
        <div className="pane preview rules-view">
          <Preview text={doc.text} kind="markdown" />
        </div>
      )}
    </section>
  );
}
