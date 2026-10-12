import { useEffect, useState } from "react";
import { researchApi, type Research } from "./api";
import { TopicPage } from "./TopicPage";
import { useT, type Problem } from "../i18n";
import { ErrorLine } from "../ErrorLine";

const PREFIX = "#/research";

const docHref = (path: string) => "#/doc/" + encodeURIComponent(path);

export function ResearchNav({ hash }: { hash: string }) {
  const t = useT();
  return (
    <a href={PREFIX} className={hash === PREFIX || hash.startsWith(PREFIX + "/") ? "nav active" : "nav"}>
      {t("research.nav")}
    </a>
  );
}

export function researchRoute(hash: string) {
  if (hash !== PREFIX && !hash.startsWith(PREFIX + "/")) {
    return null;
  }
  const topic = decodeURIComponent(hash.slice(PREFIX.length + 1));
  return <ResearchPage topic={topic || null} />;
}

function ResearchPage({ topic }: { topic: string | null }) {
  const t = useT();
  const [research, setResearch] = useState<Research | null>(null);
  const [error, setError] = useState<Problem | null>(null);

  useEffect(() => {
    researchApi.research().then(setResearch, setError);
  }, []);

  if (error) {
    return (
      <main className="doc">
        <ErrorLine error={error} />
      </main>
    );
  }
  if (!research) {
    return (
      <main className="doc">
        <p className="muted">{t("common.loading")}</p>
      </main>
    );
  }
  if (topic) {
    const found = research.topics.find((x) => x.id === topic);
    return found ? (
      <TopicPage key={found.id} topic={found} />
    ) : (
      <main className="doc">
        <p className="error">{t("research.noTopic", { topic })}</p>
      </main>
    );
  }

  return (
    <main className="doc">
      <h1>{t("research.title")}</h1>
      {research.topics.length === 0 && <p className="muted">{t("research.empty")}</p>}
      {research.topics.length > 0 && (
        <table className="topics">
          <thead>
            <tr>
              <th>{t("research.col.number")}</th>
              <th>{t("research.col.topic")}</th>
              <th>{t("research.col.files")}</th>
              <th>{t("research.col.status")}</th>
            </tr>
          </thead>
          <tbody>
            {research.topics.map((x) => (
              <tr key={x.id}>
                <td>{x.number}</td>
                <td>
                  <a href={`${PREFIX}/${encodeURIComponent(x.id)}`}>{x.title}</a>
                  <div className="muted">
                    <code>{x.slug}</code>
                  </div>
                </td>
                <td>
                  <div className="flags">
                    <Flag on={x.rules} label="rules" />
                    <Flag on={x.result_a} label="result-a" />
                    <Flag on={x.chatgpt} label="chatgpt" />
                    {x.verification && <Flag on label="verification" />}
                    <Flag on={x.notes.length > 0} label={`notes ${x.notes.length}`} />
                  </div>
                </td>
                <td className="muted">{x.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {(research.synthesis.length > 0 || research.readme) && (
        <>
          <h2>{t("research.synthesis")}</h2>
          <ul>
            {research.synthesis.map((p) => (
              <li key={p}>
                <a href={docHref(p)}>{p.split("/").pop()}</a>
              </li>
            ))}
            {research.readme && (
              <li>
                <a href={docHref(research.readme)}>README.md</a> <span className="muted">{t("research.readOnly")}</span>
              </li>
            )}
          </ul>
        </>
      )}
    </main>
  );
}

function Flag({ on, label }: { on: boolean; label: string }) {
  return <span className={`badge ${on ? "flag-on" : "flag-off"}`}>{label}</span>;
}
