import { useCallback, useState, type FormEvent } from "react";
import { contourApi, type Summary, type SummaryKind } from "./api";
import { Cmd, ContourShell, Status } from "./ContourShell";
import { outlierText, viewsText } from "./format";
import { cardHref, watchlistHref } from "./routes";
import { useLoad } from "./useLoad";

const TABS: { id: SummaryKind; label: string }[] = [
  { id: "hooks", label: "Hooks" },
  { id: "formats", label: "Formats" },
  { id: "topics", label: "Topics" },
];

const SECTION_TITLES: Record<string, string> = {
  hook_category: "Hook categories",
  hook_formula: "Hook formulas",
  storytelling_format: "Storytelling formats",
  visual_layout: "Visual layouts",
  topic: "Topics",
};

export function SummariesPage({ name }: { name: string }) {
  const [tab, setTab] = useState<SummaryKind>("hooks");
  const [draft, setDraft] = useState("14");
  const [days, setDays] = useState("14");
  const loader = useCallback(() => contourApi.summary(name, tab, days), [name, tab, days]);
  const { data, error } = useLoad(loader);

  const apply = (e: FormEvent) => {
    e.preventDefault();
    setDays(draft);
  };

  return (
    <ContourShell active={null}>
      <a href={watchlistHref(name)}>← {name}</a>
      <h1>Summaries: {name}</h1>
      <nav className="tabs">
        {TABS.map((t) => (
          <button key={t.id} className={t.id === tab ? "active" : ""} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>
      <form className="filters" onSubmit={apply}>
        <label>
          Days
          <input type="number" min="0" step="any" value={draft} onChange={(e) => setDraft(e.target.value)} />
        </label>
        <button type="submit">Apply</button>
      </form>
      <Status error={error} loading={data === null && !error} />
      {data && data.summary === tab && <SummaryView summary={data} />}
    </ContourShell>
  );
}

function SummaryView({ summary }: { summary: Summary }) {
  return (
    <>
      <p className="muted">
        {summary.references} Reference since {summary.since.slice(0, 10)}, {summary.carded} with an analysis. Weight:{" "}
        {summary.weight}. Save the hooks worth keeping with <Cmd>/mine-hooks</Cmd>.
      </p>
      {summary.carded === 0 && (
        <p className="muted">
          No analyzed Reference in this window: analyze the outliers below with <Cmd>/analyze-reference</Cmd>.
        </p>
      )}
      {summary.sections.map((sec) => (
        <section key={sec.kind}>
          <h2 className="section">{SECTION_TITLES[sec.kind] ?? sec.kind}</h2>
          {sec.groups.length === 0 && <p className="muted">Nothing yet.</p>}
          {sec.groups.map((g) => (
            <div key={g.value} className="summary-group">
              <div className="summary-head">
                <strong>{g.label || g.value}</strong>
                {g.label && g.label.toLowerCase() !== g.value && <code>{g.value}</code>}
                {g.proposed && <span className="flag pending">proposed</span>}
                <span className="muted">
                  {g.count} Reference · weight {g.weight} · best {outlierText(g.best_outlier)}
                </span>
              </div>
              <ul className="examples">
                {g.examples.map((e) => (
                  <li key={e.external_id}>
                    <strong>{outlierText(e.outlier)}</strong> · {viewsText(e.views)} · {e.date ?? "—"} ·{" "}
                    <a href={cardHref(e.external_id)}>{e.title || e.external_id}</a> · {e.handle ?? "—"}
                    {(e.spoken_hook || e.formula) && (
                      <div className="muted small">
                        {e.spoken_hook && <>«{e.spoken_hook}»</>}
                        {e.spoken_hook && e.formula && " · "}
                        {e.formula && <>formula: {e.formula}</>}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      ))}
      <h2 className="section">Outliers without analysis (≥ {summary.min_outlier}x)</h2>
      {summary.uncarded.length === 0 ? (
        <p className="muted">None: the summary covers every outlier of the window.</p>
      ) : (
        <ul className="examples">
          {summary.uncarded.map((u) => (
            <li key={u.external_id}>
              <strong>{outlierText(u.outlier)}</strong> · {viewsText(u.views)} · {u.date ?? "—"} ·{" "}
              <a href={cardHref(u.external_id)}>{u.title || u.external_id}</a> · {u.handle ?? "—"} ·{" "}
              <span className="flag pending">{u.measured ? "measured, no analysis" : "no card"}</span>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
