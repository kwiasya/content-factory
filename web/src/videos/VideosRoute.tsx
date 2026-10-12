import { VideoPage } from "./VideoPage";
import { VideosPage } from "./VideosPage";
import { VIDEOS_PREFIX, videosRoute as parse } from "./routes";
import "./videos.css";

export function VideosNav({ hash }: { hash: string }) {
  return (
    <a href={VIDEOS_PREFIX} className={parse(hash) ? "nav active" : "nav"}>
      Videos
    </a>
  );
}

export function videosRoute(hash: string) {
  const current = parse(hash);
  if (current === null) {
    return null;
  }
  return current.slug === null ? <VideosPage /> : <VideoPage key={current.slug} slug={current.slug} />;
}
