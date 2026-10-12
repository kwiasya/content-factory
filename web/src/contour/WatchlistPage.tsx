import { useCallback, useState, type FormEvent } from "react";
import { contourApi, DEFAULT_FILTERS, type FeedFilters, type FeedRow } from "./api";
import { Cmd, ContourShell, Status } from "./ContourShell";
import { outlierText, seconds, viewsText } from "./format";
import { CONTOUR_PREFIX, cardHref, ideasHref, summaryHref } from "./routes";
import { useLoad } from "./useLoad";

const FIELDS: { key: keyof FeedFilters; label: string; placeholder: string }[] = [
  { key: "days", label: "Days", placeholder: "30" },
  { key: "min_outlier", label: "Min outlier", placeholder: "any" },
  { key: "min_views", label: "Min views", placeholder: "any" },
  { key: "max_duration", label: "Max duration, s", placeholder: "any" },
  { key: "limit", label: "Limit", placeholder: "20" },
];

export function WatchlistPage({ name }: { name: string }) {
  const loadWatchlist = useCallback(() => contourApi.watchlist(name), [name]);
  const watchlist = useLoad(loadWatchlist);
  const [draft, setDraft] = useState<FeedFilters>(DEFAULT_FILTERS);
  const [applied, setApplied] = useState<FeedFilters>(DEFAULT_FILTERS);
  const loadFeed = useCallback(() => contourApi.feed(name, applied), [name, applied]);
  const feed = useLoad(loadFeed);

  const apply = (e: FormEvent) => {
    e.preventDefault();
    setApplied(draft);
  };

  const reset = () => {
    setDraft(DEFAULT_FILTERS);
    setApplied(DEFAULT_FILTERS);
  };

  if (watchlist.missing) {
    return (
      <ContourShell active={null}>
        <a href={CONTOUR_PREFIX}>← Watchlists</a>
        <p className="error">{watchlist.error}</p>
      </ContourShell>
    );
  }

  const w = watchlist.data?.watchlist;
  const channels = watchlist.data?.channels ?? [];

  return (
    <ContourShell active={null}>
      <a href={CONTOUR_PREFIX}>← Watchlists</a>
      <div className="doc-head">
        <div>
          <h1>{name}</h1>
          {w && (
            <span className="muted">
              Format <code>{w.format_id}</code>
              {w.author_channel && (
                <>
                  {" "}
                  · Channel <code>{w.author_channel}</code>
                </>
              )}{" "}
              · {w.language}
              {w.region ? ` / ${w.region}` : ""}
            </span>
          )}
        </div>
        <div className="doc-badges">
          <a href={summaryHref(name)}>Summaries</a>
          <a href={ideasHref()}>Ideas</a>
        </div>
      </div>
      <Status error={watchlist.error} loading={watchlist.data === null} />

      <h2 className="section">Reference channels</h2>
      {watchlist.data && channels.length === 0 && (
        <p className="muted">
          No Reference channels: <Cmd>{`python -m cf.research watchlist add-channel ${name} <handle>`}</Cmd>.
        </p>
      )}
      {channels.length > 0 && (
        <table className="contour-table">
          <thead>
            <tr>
              <th>Handle</th>
              <th>Title</th>
              <th className="num">Subscribers</th>
              <th className="num">Videos</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {channels.map((c) => (
              <tr key={c.external_id}>
                <td>
                  <a href={`https://www.youtube.com/channel/${c.external_id}`} target="_blank" rel="noreferrer">
                    {c.handle ?? c.external_id}
                  </a>
                </td>
                <td>{c.title ?? "—"}</td>
                <td className="num">{viewsText(c.subscriber_count)}</td>
                <td className="num">{c.video_count?.toLocaleString() ?? "—"}</td>
                <td>{c.own && <span className="badge">own</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2 className="section">Search queries</h2>
      {w && w.queries.length === 0 && <p className="muted">No search queries.</p>}
      {w && w.queries.length > 0 && (
        <ul className="queries">
          {w.queries.map((q) => (
            <li key={q}>
              <code>{q}</code>
            </li>
          ))}
        </ul>
      )}

      <h2 className="section">Feed</h2>
      <form className="filters" onSubmit={apply}>
        {FIELDS.map((f) => (
          <label key={f.key}>
            {f.label}
            <input
              type="number"
              min="0"
              step="any"
              value={draft[f.key]}
              placeholder={f.placeholder}
              onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })}
            />
          </label>
        ))}
        <label>
          Kind
          <select value={draft.kind} onChange={(e) => setDraft({ ...draft, kind: e.target.value })}>
            <option value="">any</option>
            <option value="short">short</option>
            <option value="long">long</option>
          </select>
        </label>
        <button className="primary" type="submit">
          Apply
        </button>
        <button type="button" onClick={reset}>
          Reset
        </button>
      </form>
      <Status error={feed.error} loading={feed.data === null} />
      {feed.data && <FeedTable name={name} rows={feed.data} days={applied.days || DEFAULT_FILTERS.days} />}
    </ContourShell>
  );
}

function FeedTable({ name, rows, days }: { name: string; rows: FeedRow[]; days: string }) {
  if (rows.length === 0) {
    return (
      <p className="muted">
        Nothing in the last {days} days with these filters. Refresh the Watchlist with <Cmd>/scout-references</Cmd>{" "}
        (<Cmd>{`python -m cf.research scout ${name}`}</Cmd>).
      </p>
    );
  }
  const pending = rows.filter((r) => !r.analyzed).length;
  return (
    <>
      <p className="muted">
        {rows.length} Reference, {pending} without analysis. Analyze one with <Cmd>/analyze-reference</Cmd>.
      </p>
      <table className="contour-table feed">
        <thead>
          <tr>
            <th className="num">#</th>
            <th className="num">Outlier</th>
            <th className="num">Views</th>
            <th>Date</th>
            <th>Title</th>
            <th>Handle</th>
            <th>Link</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.external_id}>
              <td className="num muted">{i + 1}</td>
              <td className="num">
                <strong>{outlierText(r.outlier)}</strong>
              </td>
              <td className="num">{viewsText(r.views)}</td>
              <td className="when">{r.date ?? "—"}</td>
              <td>
                <a href={cardHref(r.external_id)}>{r.title || "untitled"}</a>
                <div className="muted small">
                  {r.kind ?? "—"} · {seconds(r.duration_s)}
                </div>
              </td>
              <td>{r.handle ?? r.channel_title ?? "—"}</td>
              <td>
                {r.url ? (
                  <a href={r.url} target="_blank" rel="noreferrer">
                    YouTube
                  </a>
                ) : (
                  "—"
                )}
              </td>
              <td className="feed-flags">
                {!r.analyzed && <span className="flag pending">без разбора</span>}
                {r.candidate && <span className="flag candidate">кандидат</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
