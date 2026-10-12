import { useEffect, useState, type ReactNode } from "react";
import { VideoPage } from "./VideoPage";
import { VideosPage } from "./VideosPage";
import { VIDEOS_PREFIX, videosRoute } from "./routes";
import "./videos.css";

function useHash(): string {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onHash = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return hash;
}

export function VideosNav() {
  const onVideos = videosRoute(useHash()) !== null;
  return (
    <nav className="top-nav">
      <a href="#/" className={onVideos ? "" : "active"}>
        Documents
      </a>
      <a href={VIDEOS_PREFIX} className={onVideos ? "active" : ""}>
        Videos
      </a>
    </nav>
  );
}

export function VideosRoute({ children }: { children: ReactNode }) {
  const current = videosRoute(useHash());
  if (current === null) {
    return <>{children}</>;
  }
  return (
    <div className="body">
      {current.slug === null ? <VideosPage /> : <VideoPage key={current.slug} slug={current.slug} />}
    </div>
  );
}
