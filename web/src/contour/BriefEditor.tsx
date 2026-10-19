import { useCallback, useEffect, useState } from "react";
import { CodeEditor } from "../CodeEditor";
import { Preview } from "../Preview";
import { contourApi, type Brief } from "./api";
import { useT, type Problem } from "../i18n";
import { ErrorLine } from "../ErrorLine";
import { ConflictBox } from "../ConflictBox";

interface Conflict {
  text: string;
  hash: string;
}

export function BriefEditor({ ideaId }: { ideaId: number }) {
  const t = useT();
  const [brief, setBrief] = useState<Brief | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<Problem | null>(null);
  const [conflict, setConflict] = useState<Conflict | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    contourApi.brief(ideaId).then((b) => {
      setBrief(b);
      setDraft(b.text);
      setConflict(null);
      setError(null);
    }, setError);
  }, [ideaId]);

  useEffect(load, [load]);

  if (!brief) {
    return error ? (
      <ErrorLine error={error} />
    ) : (
      <p className="muted">{t("common.loading")}</p>
    );
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
      setError(result.problem);
    }
  };

  return (
    <div className="text-file">
      {conflict && (
        <ConflictBox
          title="conflict.brief"
          fresh={conflict.text}
          onReload={load}
          onOverwrite={() => save(conflict.hash)}
        />
      )}
      <ErrorLine error={error} />
      <div className="split">
        <section className="pane preview">
          <Preview text={draft} kind="markdown" />
        </section>
        <section className="pane editor">
          <div className="toolbar">
            <button
              className="primary"
              disabled={!dirty || saving}
              onClick={() => save(brief.hash)}
            >
              {saving ? t("common.saving") : t("common.save")}
            </button>
            <button
              disabled={!dirty || saving}
              onClick={() => setDraft(brief.text)}
            >
              {t("common.revert")}
            </button>
            <code className="path brief-path" title={brief.path}>
              {brief.path}
            </code>
            <span className="muted">
              {dirty ? t("common.unsaved") : t("common.saved")}
            </span>
          </div>
          <CodeEditor
            value={draft}
            kind="markdown"
            readOnly={false}
            onChange={setDraft}
          />
        </section>
      </div>
    </div>
  );
}
