import { formatTime } from "../format";
import { videoHref } from "./routes";
import { useT } from "../i18n";
import { ErrorLine } from "../ErrorLine";
import { useDeskData } from "../shell/DeskData";
import { NEW_VIDEO_HASH } from "../shell/routes";

export function VideosPage() {
  const t = useT();
  const { videos, error } = useDeskData();

  return (
    <main className="doc videos">
      <h1>{t("videos.title")}</h1>
      <ErrorLine error={error} />
      {videos === null ? (
        !error && <p className="muted">{t("common.loading")}</p>
      ) : videos.length === 0 ? (
        <p className="muted">{t.rich("videos.empty", { link: <a href={NEW_VIDEO_HASH}>{t("nav.newVideo")}</a> })}</p>
      ) : (
        <table className="video-table">
          <thead>
            <tr>
              <th>{t("videos.col.title")}</th>
              <th>{t("videos.col.format")}</th>
              <th>{t("videos.col.channel")}</th>
              <th>{t("videos.col.status")}</th>
              <th>{t("videos.col.updated")}</th>
            </tr>
          </thead>
          <tbody>
            {videos.map((v) => (
              <tr key={v.slug}>
                <td>
                  <a href={videoHref(v.slug)}>{v.title}</a>
                  {v.legacy && <span className="badge">{t("videos.legacy")}</span>}
                  {v.error && <div className="error">{t.problem({ message: v.error, code: v.error_code ?? undefined })}</div>}
                </td>
                <td>{v.format ?? "—"}</td>
                <td>{v.channel ?? "—"}</td>
                <td>
                  <span className={`stage-dot stage-${v.stage ?? "none"}`} aria-hidden="true" />{" "}
                  {v.status ? <span className={`status-pill status-${v.status}`}>{t(`videos.status.${v.status}`)}</span> : "—"}
                </td>
                <td className="muted when">{formatTime(v.updated, t)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
