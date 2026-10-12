import { useCallback, useEffect, useState } from "react";
import { CodeEditor } from "../CodeEditor";
import { Preview } from "../Preview";
import { NotFound } from "../api";
import { videosApi, type TextFile } from "./videosApi";

interface Props {
  slug: string;
  path: string;
  creatable?: boolean;
  onSaved?: () => void;
}

interface Conflict {
  text: string;
  hash: string;
}

function formatOf(path: string): TextFile["format"] {
  return path.endsWith(".md") ? "markdown" : path.endsWith(".json") ? "json" : "text";
}

export function TextFileEditor({ slug, path, creatable = false, onSaved }: Props) {
  const [file, setFile] = useState<TextFile | null>(null);
  const [missing, setMissing] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<Conflict | null>(null);
  const [violations, setViolations] = useState<string[] | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    videosApi.file(slug, path).then(
      (f) => {
        setFile(f);
        setDraft(f.text);
        setMissing(false);
        setConflict(null);
        setViolations(null);
        setError(null);
      },
      (e: Error) => {
        if (e instanceof NotFound && creatable) {
          setFile({ path, kind: "other", format: formatOf(path), text: "", hash: "" });
          setDraft("");
          setMissing(true);
        } else {
          setError(e.message);
        }
      },
    );
  }, [slug, path, creatable]);

  useEffect(load, [load]);

  if (!file) {
    return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>;
  }

  const dirty = draft !== file.text;

  const save = async (hash: string) => {
    setSaving(true);
    setError(null);
    setViolations(null);
    const result = await videosApi.saveFile(slug, path, draft, hash);
    setSaving(false);
    if (result.status === "saved") {
      setFile({ ...file, text: draft, hash: result.hash });
      setMissing(false);
      setConflict(null);
      onSaved?.();
    } else if (result.status === "conflict") {
      setConflict({ text: result.text, hash: result.hash });
    } else if (result.status === "invalid") {
      setError(result.message);
      setViolations(result.violations);
    } else {
      setError(result.message);
    }
  };

  const editor =
    file.format === "text" ? (
      <textarea className="plain-editor" value={draft} spellCheck={false} onChange={(e) => setDraft(e.target.value)} />
    ) : (
      <CodeEditor value={draft} kind={file.format} readOnly={false} onChange={setDraft} />
    );

  return (
    <div className="text-file">
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
      {error && <p className="error">{error}</p>}
      {violations && (
        <ul className="violations">
          {violations.map((v) => (
            <li key={v}>{v}</li>
          ))}
        </ul>
      )}
      <div className={file.format === "markdown" ? "split" : ""}>
        {file.format === "markdown" && (
          <section className="pane preview">
            <Preview text={draft} kind="markdown" />
          </section>
        )}
        <section className="pane editor">
          <div className="toolbar">
            <button className="primary" disabled={(!dirty && !missing) || saving} onClick={() => save(file.hash)}>
              {saving ? "Saving…" : missing ? "Create" : "Save"}
            </button>
            <button disabled={!dirty || saving} onClick={() => setDraft(file.text)}>
              Revert
            </button>
            <code className="path">{path}</code>
            <span className="muted">{missing ? "not created yet" : dirty ? "unsaved changes" : "saved"}</span>
          </div>
          {editor}
        </section>
      </div>
    </div>
  );
}
