import { useCallback, useEffect, useState } from "react";
import { api, type Doc } from "../api";
import { CodeEditor } from "../CodeEditor";
import { GitBadge } from "../GitBadge";
import { Preview } from "../Preview";
import { useT, type Problem } from "../i18n";
import { ErrorLine } from "../ErrorLine";
import { ConflictBox } from "../ConflictBox";

export function RulesSection({ path }: { path: string }) {
  const t = useT();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [conflict, setConflict] = useState<{ text: string; hash: string } | null>(null);
  const [error, setError] = useState<Problem | null>(null);

  const load = useCallback(() => {
    api.doc(path).then(
      (d) => {
        setDoc(d);
        setDraft(d.text);
        setConflict(null);
        setError(null);
      },
      setError,
    );
  }, [path]);

  useEffect(load, [load]);

  if (!doc) {
    return error ? <ErrorLine error={error} /> : <p className="muted">{t("research.loadingRules")}</p>;
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
      setError(result.problem);
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
              {saving ? t("common.saving") : t("common.save")}
            </button>
            <button
              disabled={saving}
              onClick={() => {
                setDraft(doc.text);
                setEditing(false);
              }}
            >
              {t("common.cancel")}
            </button>
            <span className="muted">{dirty ? t("common.unsaved") : t("common.noChanges")}</span>
          </>
        ) : (
          doc.editable && <button onClick={() => setEditing(true)}>{t("common.edit")}</button>
        )}
        <a className="muted" href={"#/doc/" + encodeURIComponent(doc.path)}>
          {t("common.openAsDocument")}
        </a>
      </div>
      <ErrorLine error={error} />
      {conflict && <ConflictBox title="conflict.rules" onReload={load} onOverwrite={() => save(conflict.hash)} />}
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
