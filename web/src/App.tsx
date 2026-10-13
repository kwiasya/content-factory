import { useEffect, useRef, useState } from "react";
import { agentRoute } from "./agent/AgentPage";
import { contourRoute } from "./contour/ContourRoute";
import { FormatsRoute } from "./formats/FormatsRoute";
import { libraryRoute } from "./library/LibraryPage";
import { notesRoute } from "./notes/NotesPage";
import { searchRoute } from "./search/SearchPage";
import { DeskDataProvider, useDeskData } from "./shell/DeskData";
import { Header } from "./shell/Header";
import { Sidebar } from "./shell/Sidebar";
import { newVideoRoute } from "./videos/NewVideoPage";
import { parseVideos } from "./videos/routes";
import { VideosPage } from "./videos/VideosPage";
import { videosRoute } from "./videos/VideosRoute";

function useHash(): string {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onHash = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return hash;
}

function useReloadOnUnknownVideo(hash: string) {
  const { videos, reload } = useDeskData();
  const tried = useRef<string | null>(null);
  useEffect(() => {
    const slug = parseVideos(hash)?.slug;
    if (!slug || videos === null || tried.current === slug) {
      return;
    }
    if (!videos.some((v) => v.slug === slug)) {
      tried.current = slug;
      reload();
    }
  }, [hash, videos, reload]);
}

function Shell() {
  const hash = useHash();
  useReloadOnUnknownVideo(hash);
  return (
    <div className="app">
      <div className="body">
        <Sidebar hash={hash} />
        <div className="main">
          <Header hash={hash} />
          {notesRoute(hash) ??
            searchRoute(hash) ??
            newVideoRoute(hash) ??
            videosRoute(hash) ??
            contourRoute(hash) ??
            libraryRoute(hash) ??
            agentRoute(hash) ?? <FormatsRoute hash={hash} fallback={<VideosPage />} />}
        </div>
      </div>
    </div>
  );
}

export function App() {
  return (
    <DeskDataProvider>
      <Shell />
    </DeskDataProvider>
  );
}
