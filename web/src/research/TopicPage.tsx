import { useEffect, useState } from "react";
import { api, type Doc } from "../api";
import { RulesSection } from "./RulesSection";
import { TocDocument } from "./TocDocument";
import type { Topic } from "./api";

const LABELS: Record<string, string> = {
  "chatgpt.md": "ChatGPT",
  "result-a.md": "Opus (result-a)",
  "verification.md": "Verification",
};

function tabLabel(path: string): string {
  const name = path.split("/").pop() ?? path;
  return path.includes("/notes/") ? `notes/${name}` : (LABELS[name] ?? name);
}

export function TopicPage({ topic }: { topic: Topic }) {
  const rules = topic.docs.find((p) => p.endsWith("/rules.md")) ?? null;
  const tabs = [...topic.docs.filter((p) => p !== rules), ...topic.notes];
  const [tab, setTab] = useState<string | null>(tabs[0] ?? null);

  return (
    <main className="doc">
      <p>
        <a href="#/research">← Research</a>
      </p>
      <div className="doc-head">
        <div>
          <h1>
            {topic.number} · {topic.title}
          </h1>
          <code className="path">docs/research/{topic.id}/</code>
          {topic.status && <p className="muted">{topic.status}</p>}
        </div>
      </div>

      {rules ? <RulesSection path={rules} /> : <p className="muted">This topic has no rules.md.</p>}

      {tabs.length > 0 && (
        <>
          <nav className="tabs">
            {tabs.map((p) => (
              <button key={p} className={p === tab ? "active" : ""} onClick={() => setTab(p)}>
                {tabLabel(p)}
              </button>
            ))}
          </nav>
          {tab && <Answer key={tab} path={tab} />}
        </>
      )}
    </main>
  );
}

function Answer({ path }: { path: string }) {
  const [doc, setDoc] = useState<Doc | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.doc(path).then(setDoc, (e: Error) => setError(e.message));
  }, [path]);

  if (error) {
    return <p className="error">{error}</p>;
  }
  if (!doc) {
    return <p className="muted">Loading…</p>;
  }
  return (
    <>
      <p className="muted">
        Read-only. <a href={"#/doc/" + encodeURIComponent(path)}>Open as document</a> for diff and history.
      </p>
      <TocDocument text={doc.text} prefix={path.replace(/[^a-z0-9]+/gi, "-")} />
    </>
  );
}
