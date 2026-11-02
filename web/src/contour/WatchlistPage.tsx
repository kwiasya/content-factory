import { useCallback, useState, type FormEvent } from "react";
import {
  channelUrl,
  contourApi,
  DEFAULT_FILTERS,
  platformName,
  type FeedFilters,
  type FeedRow,
} from "./api";
import { PlatformBadge } from "./PlatformBadge";
import { Cmd, ContourShell, Status } from "./ContourShell";
import { outlierText, seconds, viewsText } from "./format";
import { CONTOUR_PREFIX, cardHref, ideasHref, summaryHref } from "./routes";
import { useLoad } from "./useLoad";
import { useT, type Key } from "../i18n";
import { ErrorLine } from "../ErrorLine";
import { formatDate, formatNumber } from "../format";
import { kindText } from "./CardPage";

const FIELDS: {
  key: keyof FeedFilters;
  label: Key;
  placeholder: string | null;
}[] = [
  { key: "days", label: "watchlist.filter.days", placeholder: "30" },
  {
    key: "min_outlier",
    label: "watchlist.filter.minOutlier",
    placeholder: null,
  },
  { key: "min_views", label: "watchlist.filter.minViews", placeholder: null },
  {
    key: "max_duration",
    label: "watchlist.filter.maxDuration",
    placeholder: null,
  },
  { key: "limit", label: "watchlist.filter.limit", placeholder: "20" },
];

export function WatchlistPage({ name }: { name: string }) {
  const t = useT();
  const loadWatchlist = useCallback(() => contourApi.watchlist(name), [name]);
  const watchlist = useLoad(loadWatchlist);
  const [draft, setDraft] = useState<FeedFilters>(DEFAULT_FILTERS);
  const [applied, setApplied] = useState<FeedFilters>(DEFAULT_FILTERS);
  const loadFeed = useCallback(
    () => contourApi.feed(name, applied),
    [name, applied],
  );
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
        <a href={CONTOUR_PREFIX}>{t("contour.back")}</a>
        <ErrorLine error={watchlist.error} />
      </ContourShell>
    );
  }

  const w = watchlist.data?.watchlist;
  const channels = watchlist.data?.channels ?? [];

  return (
    <ContourShell active={null}>
      <a href={CONTOUR_PREFIX}>{t("contour.back")}</a>
      <div className="doc-head">
        <div>
          <h1>{name}</h1>
          {w && (
            <span className="muted">
              {t.rich("watchlist.format", {
                format: <code>{w.format_id}</code>,
              })}
              {w.author_channel && (
                <>
                  {" "}
                  ·{" "}
                  {t.rich("watchlist.channel", {
                    channel: <code>{w.author_channel}</code>,
                  })}
                </>
              )}{" "}
              · {w.language}
              {w.region ? ` / ${w.region}` : ""}
            </span>
          )}
        </div>
        <div className="doc-badges">
          <a href={summaryHref(name)}>{t("contour.summaries")}</a>
          <a href={ideasHref()}>{t("contour.ideas")}</a>
        </div>
      </div>
      <Status error={watchlist.error} loading={watchlist.data === null} />

      <h2 className="section">{t("watchlist.referenceChannels")}</h2>
      {watchlist.data && channels.length === 0 && (
        <p className="muted">
          {t.rich("watchlist.noChannels", {
            cmd: (
              <Cmd>{`python -m cf.research watchlist add-channel ${name} <handle>`}</Cmd>
            ),
          })}
        </p>
      )}
      {channels.length > 0 && (
        <table className="contour-table">
          <thead>
            <tr>
              <th>{t("watchlist.col.handle")}</th>
              <th>{t("watchlist.col.title")}</th>
              <th className="num">{t("watchlist.col.subscribers")}</th>
              <th className="num">{t("watchlist.col.videos")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {channels.map((c) => (
              <tr key={c.external_id}>
                <td>
                  <PlatformBadge platform={c.platform} />
                  <a href={channelUrl(c)} target="_blank" rel="noreferrer">
                    {c.handle ?? c.external_id}
                  </a>
                </td>
                <td>{c.title ?? "—"}</td>
                <td className="num">{viewsText(c.subscriber_count, t)}</td>
                <td className="num">
                  {c.video_count === null
                    ? "—"
                    : formatNumber(c.video_count, t)}
                </td>
                <td>
                  {c.own && <span className="badge">{t("watchlist.own")}</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2 className="section">{t("watchlist.queries")}</h2>
      {w && w.queries.length === 0 && (
        <p className="muted">{t("watchlist.noQueries")}</p>
      )}
      {w && w.queries.length > 0 && (
        <ul className="queries">
          {w.queries.map((q) => (
            <li key={q}>
              <code>{q}</code>
            </li>
          ))}
        </ul>
      )}

      <h2 className="section">{t("watchlist.feed")}</h2>
      <form className="filters" onSubmit={apply}>
        {FIELDS.map((f) => (
          <label key={f.key}>
            {t(f.label)}
            <input
              type="number"
              min="0"
              step="any"
              value={draft[f.key]}
              placeholder={f.placeholder ?? t("common.any")}
              onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })}
            />
          </label>
        ))}
        <label>
          {t("watchlist.filter.kind")}
          <select
            value={draft.kind}
            onChange={(e) => setDraft({ ...draft, kind: e.target.value })}
          >
            <option value="">{t("common.any")}</option>
            <option value="short">{t("card.kind.short")}</option>
            <option value="long">{t("card.kind.long")}</option>
          </select>
        </label>
        <button className="primary" type="submit">
          {t("common.apply")}
        </button>
        <button type="button" onClick={reset}>
          {t("common.reset")}
        </button>
      </form>
      <Status error={feed.error} loading={feed.data === null} />
      {feed.data && (
        <FeedTable
          name={name}
          rows={feed.data}
          days={applied.days || DEFAULT_FILTERS.days}
        />
      )}
    </ContourShell>
  );
}

function FeedTable({
  name,
  rows,
  days,
}: {
  name: string;
  rows: FeedRow[];
  days: string;
}) {
  const t = useT();
  if (rows.length === 0) {
    return (
      <p className="muted">
        {t.rich("watchlist.feedEmpty", {
          days: t("unit.days", { n: Number(days) }),
          cmd: <Cmd>/scout-references</Cmd>,
          cli: <Cmd>{`python -m cf.research scout ${name}`}</Cmd>,
        })}
      </p>
    );
  }
  const pending = rows.filter((r) => !r.analyzed).length;
  return (
    <>
      <p className="muted">
        {t.rich("watchlist.feedSummary", {
          refs: t("unit.references", { n: rows.length }),
          pending: formatNumber(pending, t),
          cmd: <Cmd>/analyze-reference</Cmd>,
        })}
      </p>
      <table className="contour-table feed">
        <thead>
          <tr>
            <th className="num">{t("research.col.number")}</th>
            <th className="num">{t("watchlist.col.outlier")}</th>
            <th className="num">{t("watchlist.col.views")}</th>
            <th>{t("watchlist.col.date")}</th>
            <th>{t("watchlist.col.title")}</th>
            <th>{t("watchlist.col.handle")}</th>
            <th>{t("watchlist.col.link")}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.external_id}>
              <td className="num muted">{i + 1}</td>
              <td className="num">
                <strong>{outlierText(r.outlier, t)}</strong>
                {r.outlier_basis === "likes" && r.outlier !== null && (
                  <div className="muted small">{t("watchlist.byLikes")}</div>
                )}
              </td>
              <td className="num">{viewsText(r.views, t)}</td>
              <td className="when">{formatDate(r.date, t)}</td>
              <td>
                <a href={cardHref(r.external_id)}>
                  {r.title || t("watchlist.untitled")}
                </a>
                <div className="muted small">
                  {kindText(r.kind, t)} · {seconds(r.duration_s)}
                </div>
              </td>
              <td>
                <PlatformBadge platform={r.platform} />
                {r.handle ?? r.channel_title ?? "—"}
              </td>
              <td>
                {r.url ? (
                  <a href={r.url} target="_blank" rel="noreferrer">
                    {platformName(r.platform)}
                  </a>
                ) : (
                  "—"
                )}
              </td>
              <td className="feed-flags">
                {!r.analyzed && (
                  <span className="flag pending">{t("card.notAnalyzed")}</span>
                )}
                {r.candidate && (
                  <span className="flag candidate">{t("card.candidate")}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
