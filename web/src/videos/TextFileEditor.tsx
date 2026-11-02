import { useCallback, useEffect, useState } from "react";
import { CodeEditor } from "../CodeEditor";
import { Preview } from "../Preview";
import { NotFound } from "../api";
import { videosApi, type TextFile } from "./videosApi";
import { useT, type Problem } from "../i18n";
import { ErrorLine } from "../ErrorLine";
import { ConflictBox } from "../ConflictBox";

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
  const t = useT();
  const [file, setFile] = useState<TextFile | null>(null);
  const [missing, setMissing] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<Problem | null>(null);
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
          setError(e);
        }
      },
    );
  }, [slug, path, creatable]);

  useEffect(load, [load]);

  if (!file) {
    return error ? <ErrorLine error={error} /> : <p className="muted">{t("common.loading")}</p>;
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
      setError(result.problem);
      setViolations(result.violations);
    } else {
      setError(result.problem);
    }
  };

  const editor =
    file.format === "text" ? (
      <textarea className="plain-editor" value={draft} spellCheck={false} onChange={(e) => setDraft(e.target.value)} />
    ) : (
      <CodeEditor value={draft} kind={file.format} readOnly={false} onChange={setDraft} refs={file.format === "markdown"} />
    );

  return (
    <div className="text-file">
      {conflict && (
        <ConflictBox
          title="conflict.file"
          fresh={conflict.text}
          onReload={load}
          onOverwrite={() => save(conflict.hash)}
        />
      )}
      <ErrorLine error={error} />
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
              {saving ? t("common.saving") : missing ? t("common.create") : t("common.save")}
            </button>
            <button disabled={!dirty || saving} onClick={() => setDraft(file.text)}>
              {t("common.revert")}
            </button>
            <code className="path">{path}</code>
            <span className="muted">{missing ? t("common.notCreated") : dirty ? t("common.unsaved") : t("common.saved")}</span>
          </div>
          {editor}
        </section>
      </div>
    </div>
  );
}
