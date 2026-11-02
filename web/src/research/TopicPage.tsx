import { useEffect, useState } from "react";
import { api, type Doc } from "../api";
import { RulesSection } from "./RulesSection";
import { TocDocument } from "./TocDocument";
import type { Topic } from "./api";
import { useT, type Problem, type T } from "../i18n";
import { ErrorLine } from "../ErrorLine";

const LABELS: Record<string, string> = {
  "chatgpt.md": "ChatGPT",
  "result-a.md": "Opus (result-a)",
};

function tabLabel(path: string, t: T): string {
  const name = path.split("/").pop() ?? path;
  if (path.includes("/notes/")) {
    return `notes/${name}`;
  }
  return name === "verification.md" ? t("research.tab.verification") : (LABELS[name] ?? name);
}

export function TopicPage({ topic }: { topic: Topic }) {
  const t = useT();
  const rules = topic.docs.find((p) => p.endsWith("/rules.md")) ?? null;
  const tabs = [...topic.docs.filter((p) => p !== rules), ...topic.notes];
  const [tab, setTab] = useState<string | null>(tabs[0] ?? null);

  return (
    <main className="doc">
      <p>
        <a href="#/research">{t("research.back")}</a>
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

      {rules ? <RulesSection path={rules} /> : <p className="muted">{t("research.noRules")}</p>}

      {tabs.length > 0 && (
        <>
          <nav className="tabs">
            {tabs.map((p) => (
              <button key={p} className={p === tab ? "active" : ""} onClick={() => setTab(p)}>
                {tabLabel(p, t)}
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
  const t = useT();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [error, setError] = useState<Problem | null>(null);

  useEffect(() => {
    api.doc(path).then(setDoc, setError);
  }, [path]);

  if (error) {
    return <ErrorLine error={error} />;
  }
  if (!doc) {
    return <p className="muted">{t("common.loading")}</p>;
  }
  return (
    <>
      <p className="muted">
        {t.rich("research.answerReadOnly", {
          link: <a href={"#/doc/" + encodeURIComponent(path)}>{t("research.openAsDocument")}</a>,
        })}
      </p>
      <TocDocument text={doc.text} prefix={path.replace(/[^a-z0-9]+/gi, "-")} />
    </>
  );
}
