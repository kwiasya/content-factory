import { useCallback, useEffect, useState } from "react";
import { CodeEditor } from "../CodeEditor";
import { Preview } from "../Preview";
import { contourApi, type Brief } from "./api";

interface Conflict {
  text: string;
  hash: string;
}

export function BriefEditor({ ideaId }: { ideaId: number }) {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<Conflict | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    contourApi.brief(ideaId).then(
      (b) => {
        setBrief(b);
        setDraft(b.text);
        setConflict(null);
        setError(null);
      },
      (e: Error) => setError(e.message),
    );
  }, [ideaId]);

  useEffect(load, [load]);

  if (!brief) {
    return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>;
  }

  const dirty = draft !== brief.text;

  const save = async (hash: string) => {
    setSaving(true);
    setError(null);
    const result = await contourApi.saveBrief(ideaId, draft, hash);
    setSaving(false);
    if (result.status === "saved") {
      setBrief({ ...brief, text: draft, hash: result.hash });
      setConflict(null);
    } else if (result.status === "conflict") {
      setConflict({ text: result.text, hash: result.hash });
    } else {
      setError(result.message);
    }
  };

  return (
    <div className="text-file">
      {conflict && (
        <div className="conflict">
          <p>
            <strong>The Brief changed on disk since you opened it.</strong> Your text is still in the editor.
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
      {error && <p className="error">{error}</p>}
      <div className="split">
        <section className="pane preview">
          <Preview text={draft} kind="markdown" />
        </section>
        <section className="pane editor">
          <div className="toolbar">
            <button className="primary" disabled={!dirty || saving} onClick={() => save(brief.hash)}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button disabled={!dirty || saving} onClick={() => setDraft(brief.text)}>
              Revert
            </button>
            <code className="path brief-path" title={brief.path}>
              {brief.path}
            </code>
            <span className="muted">{dirty ? "unsaved changes" : "saved"}</span>
          </div>
          <CodeEditor value={draft} kind="markdown" readOnly={false} onChange={setDraft} />
        </section>
      </div>
    </div>
  );
}
