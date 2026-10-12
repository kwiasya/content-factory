import { useCallback, useEffect, useState } from "react";
import { api, type Doc, type GitState, type LogEntry } from "./api";
import { CodeEditor } from "./CodeEditor";
import { DiffView } from "./DiffView";
import { GitBadge } from "./GitBadge";
import { Preview } from "./Preview";
import { SkillLinks } from "./skills/SkillLinks";
import { SkillLint } from "./formats/SkillLint";
import { NoteBox } from "./notes/NoteBox";
import { formatDate, formatTime } from "./format";
import { useT, type Problem } from "./i18n";
import { ErrorLine } from "./ErrorLine";
import { ConflictBox } from "./ConflictBox";

type Tab = "edit" | "diff" | "history";

interface Conflict {
  text: string;
  hash: string;
}

export function DocPage({ path, onSaved }: { path: string; onSaved: () => void }) {
  const t = useT();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<Problem | null>(null);
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
      .catch(setError);
  }, [path]);

  useEffect(load, [load]);

  useEffect(() => {
    if (tab === "diff") {
      api.diff(path).then((d) => setDiff(d.diff), setError);
    } else if (tab === "history") {
      api.log(path).then(setLog, setError);
    }
  }, [tab, path, doc?.hash]);

  if (!doc) {
    return <main className="doc">{error ? <ErrorLine error={error} /> : <p className="muted">{t("common.loading")}</p>}</main>;
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
      setError(result.problem);
    }
  };

  return (
    <main className="doc">
      <div className="doc-head">
        <div>
          <h1>{doc.title}</h1>
          <code className="path">{doc.path}</code>
          {doc.description && <p className="muted">{doc.description}</p>}
          {doc.mtime && <p className="muted">{t("app.lastChange", { time: formatTime(doc.mtime, t) })}</p>}
        </div>
        <div className="doc-badges">
          <GitBadge state={doc.git} />
          {!doc.editable && <span className="badge readonly">{t("common.readOnly")}</span>}
        </div>
      </div>
      <SkillLint entry={doc} version={doc.hash} />

      <SkillLinks entry={doc} />

      <nav className="tabs">
        {(["edit", "diff", "history"] as Tab[]).map((id) => (
          <button key={id} className={id === tab ? "active" : ""} onClick={() => setTab(id)}>
            {id === "edit" ? t(doc.editable ? "doc.tab.edit" : "doc.tab.view") : t(id === "diff" ? "doc.tab.diff" : "doc.tab.history")}
          </button>
        ))}
      </nav>

      <ErrorLine error={error} />

      {conflict && (
        <ConflictBox
          title="conflict.file"
          fresh={conflict.text}
          onReload={load}
          onOverwrite={() => save(conflict.hash)}
        />
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
                    {saving ? t("common.saving") : t("common.save")}
                  </button>
                  <button disabled={!dirty || saving} onClick={() => setDraft(doc.text)}>
                    {t("common.revert")}
                  </button>
                  <span className="muted">{dirty ? t("common.unsaved") : t("common.saved")}</span>
                </>
              ) : (
                <span className="muted">{t("doc.readOnlyInDesk")}</span>
              )}
            </div>
            <CodeEditor value={draft} kind={doc.kind} readOnly={!doc.editable} onChange={setDraft} />
          </section>
        </div>
      )}

      {tab === "diff" && (diff === null ? <p className="muted">{t("common.loading")}</p> : <DiffView diff={diff} />)}

      {tab === "history" &&
        (log === null ? (
          <p className="muted">{t("common.loading")}</p>
        ) : log.length === 0 ? (
          <p className="muted">{t("doc.noCommits")}</p>
        ) : (
          <table className="log">
            <tbody>
              {log.map((e) => (
                <tr key={e.hash}>
                  <td>
                    <code>{e.hash.slice(0, 7)}</code>
                  </td>
                  <td>{formatDate(e.date, t)}</td>
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
