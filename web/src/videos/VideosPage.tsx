import { useEffect, useState } from "react";
import { formatTime } from "../format";
import { videoHref } from "./routes";
import { videosApi, type VideoSummary } from "./videosApi";

export function VideosPage() {
  const [videos, setVideos] = useState<VideoSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    videosApi.list().then(setVideos, (e: Error) => setError(e.message));
  }, []);

  return (
    <main className="doc videos">
      <h1>Videos</h1>
      {error && <p className="error">{error}</p>}
      {videos === null ? (
        !error && <p className="muted">Loading…</p>
      ) : videos.length === 0 ? (
        <p className="muted">
          No Videos yet: create <code>videos/&lt;slug&gt;/video.json</code> in the footage root.
        </p>
      ) : (
        <table className="video-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Format</th>
              <th>Channel</th>
              <th>Status</th>
              <th>Last change</th>
            </tr>
          </thead>
          <tbody>
            {videos.map((v) => (
              <tr key={v.slug}>
                <td>
                  <a href={videoHref(v.slug)}>{v.title}</a>
                  {v.legacy && <span className="badge">legacy Reel</span>}
                  {v.error && <div className="error">{v.error}</div>}
                </td>
                <td>{v.format ?? "—"}</td>
                <td>{v.channel ?? "—"}</td>
                <td>{v.status ? <span className={`status-pill status-${v.status}`}>{v.status}</span> : "—"}</td>
                <td className="muted when">{formatTime(v.updated)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
