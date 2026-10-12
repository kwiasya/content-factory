import { contourApi } from "./api";
import { Cmd, ContourShell, Status } from "./ContourShell";
import { ideasHref, summaryHref, watchlistHref } from "./routes";
import { useLoad } from "./useLoad";
import { useT } from "../i18n";
import { formatDate, formatNumber } from "../format";

export function ContourHome() {
  const t = useT();
  const watchlists = useLoad(contourApi.watchlists);
  const quota = useLoad(contourApi.quota);

  return (
    <ContourShell active="home">
      <h1>{t("contour.home.title")}</h1>
      <Status error={watchlists.error} loading={watchlists.data === null} />
      {watchlists.data?.length === 0 && (
        <p className="muted">
          {t.rich("contour.home.empty", {
            a: <Cmd>/research-watchlist</Cmd>,
            b: <Cmd>python -m cf.research watchlist add &lt;name&gt; --format &lt;format&gt;</Cmd>,
            c: <Cmd>/scout-references</Cmd>,
          })}
        </p>
      )}
      {watchlists.data && watchlists.data.length > 0 && (
        <table className="contour-table">
          <thead>
            <tr>
              <th>{t("contour.col.watchlist")}</th>
              <th>{t("contour.col.format")}</th>
              <th>{t("contour.col.channel")}</th>
              <th>{t("contour.col.language")}</th>
              <th className="num">{t("contour.col.referenceChannels")}</th>
              <th className="num">{t("contour.col.queries")}</th>
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
                  <a href={summaryHref(w.name)}>{t("contour.summaries")}</a> · <a href={ideasHref()}>{t("contour.ideas")}</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2 className="section">{t("contour.quota.title")}</h2>
      <Status error={quota.error} loading={quota.data === null} />
      {quota.data && (
        <>
          <p className="muted">{t("contour.quota.day", { day: formatDate(quota.data.day, t) })}</p>
          <table className="contour-table narrow">
            <thead>
              <tr>
                <th>{t("contour.quota.bucket")}</th>
                <th className="num">{t("contour.quota.limit")}</th>
                <th className="num">{t("contour.quota.used")}</th>
                <th className="num">{t("contour.quota.remaining")}</th>
              </tr>
            </thead>
            <tbody>
              {quota.data.buckets.map((b) => (
                <tr key={b.bucket}>
                  <td>{b.bucket}</td>
                  <td className="num">{formatNumber(b.limit, t)}</td>
                  <td className="num">{formatNumber(b.used, t)}</td>
                  <td className="num">{formatNumber(b.remaining, t)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {quota.data.by_method.length === 0 ? (
            <p className="muted">{t("contour.quota.noCalls")}</p>
          ) : (
            <table className="contour-table narrow">
              <thead>
                <tr>
                  <th>{t("contour.quota.method")}</th>
                  <th className="num">{t("contour.quota.calls")}</th>
                  <th className="num">{t("contour.quota.units")}</th>
                </tr>
              </thead>
              <tbody>
                {quota.data.by_method.map((m) => (
                  <tr key={m.method}>
                    <td>
                      <code>{m.method}</code>
                    </td>
                    <td className="num">{formatNumber(m.calls, t)}</td>
                    <td className="num">{formatNumber(m.units, t)}</td>
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
