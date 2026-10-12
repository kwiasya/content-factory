import { contourApi } from "./api";
import { Cmd, ContourShell, Status } from "./ContourShell";
import { ideasHref, summaryHref, watchlistHref } from "./routes";
import { useLoad } from "./useLoad";

export function ContourHome() {
  const watchlists = useLoad(contourApi.watchlists);
  const quota = useLoad(contourApi.quota);

  return (
    <ContourShell active="home">
      <h1>Research contour</h1>
      <Status error={watchlists.error} loading={watchlists.data === null} />
      {watchlists.data?.length === 0 && (
        <p className="muted">
          No Watchlists yet: run <Cmd>/research-watchlist</Cmd> (or{" "}
          <Cmd>python -m cf.research watchlist add &lt;name&gt; --format &lt;format&gt;</Cmd>), then{" "}
          <Cmd>/scout-references</Cmd>.
        </p>
      )}
      {watchlists.data && watchlists.data.length > 0 && (
        <table className="contour-table">
          <thead>
            <tr>
              <th>Watchlist</th>
              <th>Format</th>
              <th>Channel</th>
              <th>Language</th>
              <th className="num">Reference channels</th>
              <th className="num">Queries</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {watchlists.data.map((w) => (
              <tr key={w.name}>
                <td>
                  <a href={watchlistHref(w.name)}>{w.name}</a>
                </td>
                <td>{w.format_id}</td>
                <td>{w.author_channel ?? "—"}</td>
                <td>
                  {w.language}
                  {w.region ? ` / ${w.region}` : ""}
                </td>
                <td className="num">{w.channel_count}</td>
                <td className="num">{w.queries.length}</td>
                <td className="links">
                  <a href={summaryHref(w.name)}>Summaries</a> · <a href={ideasHref()}>Ideas</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2 className="section">YouTube Data API quota</h2>
      <Status error={quota.error} loading={quota.data === null} />
      {quota.data && (
        <>
          <p className="muted">Day {quota.data.day} (Pacific time; resets at midnight Pacific).</p>
          <table className="contour-table narrow">
            <thead>
              <tr>
                <th>Bucket</th>
                <th className="num">Limit</th>
                <th className="num">Used</th>
                <th className="num">Remaining</th>
              </tr>
            </thead>
            <tbody>
              {quota.data.buckets.map((b) => (
                <tr key={b.bucket}>
                  <td>{b.bucket}</td>
                  <td className="num">{b.limit.toLocaleString()}</td>
                  <td className="num">{b.used.toLocaleString()}</td>
                  <td className="num">{b.remaining.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {quota.data.by_method.length === 0 ? (
            <p className="muted">No calls today.</p>
          ) : (
            <table className="contour-table narrow">
              <thead>
                <tr>
                  <th>Method</th>
                  <th className="num">Calls</th>
                  <th className="num">Units</th>
                </tr>
              </thead>
              <tbody>
                {quota.data.by_method.map((m) => (
                  <tr key={m.method}>
                    <td>
                      <code>{m.method}</code>
                    </td>
                    <td className="num">{m.calls.toLocaleString()}</td>
                    <td className="num">{m.units.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </ContourShell>
  );
}
