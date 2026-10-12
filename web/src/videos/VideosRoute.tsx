import { VideoPage } from "./VideoPage";
import { VideosPage } from "./VideosPage";
import { VIDEOS_PREFIX, parseVideos } from "./routes";
import "./videos.css";

export function VideosNav({ hash }: { hash: string }) {
  return (
    <a href={VIDEOS_PREFIX} className={parseVideos(hash) ? "nav active" : "nav"}>
      Videos
    </a>
  );
}

export function videosRoute(hash: string) {
  const current = parseVideos(hash);
  if (current === null) {
    return null;
  }
  return current.slug === null ? <VideosPage /> : <VideoPage key={current.slug} slug={current.slug} />;
}
