import { useEffect, useState } from "react";
import { formatTime } from "../format";
import { videoHref } from "./routes";
import { videosApi, type VideoSummary } from "./videosApi";
import { useT, type Problem } from "../i18n";
import { ErrorLine } from "../ErrorLine";

export function VideosPage() {
  const t = useT();
  const [videos, setVideos] = useState<VideoSummary[] | null>(null);
  const [error, setError] = useState<Problem | null>(null);

  useEffect(() => {
    videosApi.list().then(setVideos, setError);
  }, []);

  return (
    <main className="doc videos">
      <h1>{t("videos.title")}</h1>
      <ErrorLine error={error} />
      {videos === null ? (
        !error && <p className="muted">{t("common.loading")}</p>
      ) : videos.length === 0 ? (
        <p className="muted">{t.rich("videos.empty", { path: <code>videos/&lt;slug&gt;/video.json</code> })}</p>
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
                <td>{v.status ? <span className={`status-pill status-${v.status}`}>{t(`videos.status.${v.status}`)}</span> : "—"}</td>
                <td className="muted when">{formatTime(v.updated, t)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
