import { useCallback, useState, type FormEvent } from "react";
import { contourApi, type Summary, type SummaryKind } from "./api";
import { Cmd, ContourShell, Status } from "./ContourShell";
import { outlierText, viewsText } from "./format";
import { cardHref, watchlistHref } from "./routes";
import { useLoad } from "./useLoad";
import { useT } from "../i18n";
import { formatDate, formatNumber } from "../format";

const TABS: SummaryKind[] = ["hooks", "formats", "topics"];

export function SummariesPage({ name }: { name: string }) {
  const t = useT();
  const [tab, setTab] = useState<SummaryKind>("hooks");
  const [draft, setDraft] = useState("14");
  const [days, setDays] = useState("14");
  const loader = useCallback(
    () => contourApi.summary(name, tab, days),
    [name, tab, days],
  );
  const { data, error } = useLoad(loader);

  const apply = (e: FormEvent) => {
    e.preventDefault();
    setDays(draft);
  };

  return (
    <ContourShell active={null}>
      <a href={watchlistHref(name)}>← {name}</a>
      <h1>{t("summary.title", { name })}</h1>
      <nav className="tabs">
        {TABS.map((id) => (
          <button
            key={id}
            className={id === tab ? "active" : ""}
            onClick={() => setTab(id)}
          >
            {t(`summary.tab.${id}`)}
          </button>
        ))}
      </nav>
      <form className="filters" onSubmit={apply}>
        <label>
          {t("summary.days")}
          <input
            type="number"
            min="0"
            step="any"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
        </label>
        <button type="submit">{t("common.apply")}</button>
      </form>
      <Status error={error} loading={data === null && !error} />
      {data && data.summary === tab && <SummaryView summary={data} />}
    </ContourShell>
  );
}

function SummaryView({ summary }: { summary: Summary }) {
  const t = useT();
  return (
    <>
      <p className="muted">
        {t.rich("summary.intro", {
          refs: t("unit.references", { n: summary.references }),
          since: formatDate(summary.since, t),
          carded: formatNumber(summary.carded, t),
          weight: t.or(`summary.weight.${summary.weight_code}`, summary.weight),
          cmd: <Cmd>/mine-hooks</Cmd>,
        })}
      </p>
      {summary.carded === 0 && (
        <p className="muted">
          {t.rich("summary.noneCarded", { cmd: <Cmd>/analyze-reference</Cmd> })}
        </p>
      )}
      {summary.sections.map((sec) => (
        <section key={sec.kind}>
          <h2 className="section">
            {t.or(`summary.section.${sec.kind}`, sec.kind)}
          </h2>
          {sec.groups.length === 0 && (
            <p className="muted">{t("summary.nothing")}</p>
          )}
          {sec.groups.map((g) => (
            <div key={g.value} className="summary-group">
              <div className="summary-head">
                <strong>
                  {t.taxonomyLabel(sec.kind, g.value, g.label) || g.value}
                </strong>
                {g.label && g.label.toLowerCase() !== g.value && (
                  <code>{g.value}</code>
                )}
                {g.proposed && (
                  <span className="flag pending">{t("card.proposed")}</span>
                )}
                <span className="muted">
                  {t("summary.groupMeta", {
                    refs: t("unit.references", { n: g.count }),
                    weight: formatNumber(g.weight, t),
                    best: outlierText(g.best_outlier, t),
                  })}
                </span>
              </div>
              <ul className="examples">
                {g.examples.map((e) => (
                  <li key={e.external_id}>
                    <strong>{outlierText(e.outlier, t)}</strong> ·{" "}
                    {viewsText(e.views, t)} · {formatDate(e.date, t)} ·{" "}
                    <a href={cardHref(e.external_id)}>
                      {e.title || e.external_id}
                    </a>{" "}
                    · {e.handle ?? "—"}
                    {(e.spoken_hook || e.formula) && (
                      <div className="muted small">
                        {e.spoken_hook && <>«{e.spoken_hook}»</>}
                        {e.spoken_hook && e.formula && " · "}
                        {e.formula &&
                          t("summary.formula", { formula: e.formula })}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      ))}
      <h2 className="section">
        {t("summary.uncarded", { n: outlierText(summary.min_outlier, t) })}
      </h2>
      {summary.uncarded.length === 0 ? (
        <p className="muted">{t("summary.allCarded")}</p>
      ) : (
        <ul className="examples">
          {summary.uncarded.map((u) => (
            <li key={u.external_id}>
              <strong>{outlierText(u.outlier, t)}</strong> ·{" "}
              {viewsText(u.views, t)} · {formatDate(u.date, t)} ·{" "}
              <a href={cardHref(u.external_id)}>{u.title || u.external_id}</a> ·{" "}
              {u.handle ?? "—"} ·{" "}
              <span className="flag pending">
                {t(u.measured ? "summary.measuredOnly" : "summary.noCard")}
              </span>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
