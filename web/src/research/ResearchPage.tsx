import { useEffect, useState } from "react";
import { researchApi, type Research } from "./api";
import { TopicPage } from "./TopicPage";

const PREFIX = "#/research";

const docHref = (path: string) => "#/doc/" + encodeURIComponent(path);

export function researchRoute(hash: string) {
  if (hash !== PREFIX && !hash.startsWith(PREFIX + "/")) {
    return null;
  }
  const topic = decodeURIComponent(hash.slice(PREFIX.length + 1));
  return <ResearchPage topic={topic || null} />;
}

function ResearchPage({ topic }: { topic: string | null }) {
  const [research, setResearch] = useState<Research | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    researchApi.research().then(setResearch, (e: Error) => setError(e.message));
  }, []);

  if (error) {
    return (
      <main className="doc">
        <p className="error">{error}</p>
      </main>
    );
  }
  if (!research) {
    return (
      <main className="doc">
        <p className="muted">Loading…</p>
      </main>
    );
  }
  if (topic) {
    const found = research.topics.find((t) => t.id === topic);
    return found ? (
      <TopicPage key={found.id} topic={found} />
    ) : (
      <main className="doc">
        <p className="error">No research topic {topic}.</p>
      </main>
    );
  }

  return (
    <main className="doc">
      <h1>Research</h1>
      {research.topics.length === 0 && <p className="muted">No docs/research/NN-topic/ folders in this checkout.</p>}
      {research.topics.length > 0 && (
        <table className="topics">
          <thead>
            <tr>
              <th>#</th>
              <th>Topic</th>
              <th>Files</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {research.topics.map((t) => (
              <tr key={t.id}>
                <td>{t.number}</td>
                <td>
                  <a href={`${PREFIX}/${encodeURIComponent(t.id)}`}>{t.title}</a>
                  <div className="muted">
                    <code>{t.slug}</code>
                  </div>
                </td>
                <td>
                  <div className="flags">
                    <Flag on={t.rules} label="rules" />
                    <Flag on={t.result_a} label="result-a" />
                    <Flag on={t.chatgpt} label="chatgpt" />
                    {t.verification && <Flag on label="verification" />}
                    <Flag on={t.notes.length > 0} label={`notes ${t.notes.length}`} />
                  </div>
                </td>
                <td className="muted">{t.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {(research.synthesis.length > 0 || research.readme) && (
        <>
          <h2>Synthesis</h2>
          <ul>
            {research.synthesis.map((p) => (
              <li key={p}>
                <a href={docHref(p)}>{p.split("/").pop()}</a>
              </li>
            ))}
            {research.readme && (
              <li>
                <a href={docHref(research.readme)}>README.md</a> <span className="muted">(read-only)</span>
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
