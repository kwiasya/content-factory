import { VideoPage } from "./VideoPage";
import { VideosPage } from "./VideosPage";
import { parseVideos } from "./routes";
import "./videos.css";

export function videosRoute(hash: string) {
  const current = parseVideos(hash);
  if (current === null) {
    return null;
  }
  return current.slug === null ? <VideosPage /> : <VideoPage key={current.slug} slug={current.slug} />;
}
