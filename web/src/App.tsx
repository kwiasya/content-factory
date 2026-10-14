import { useEffect, useState } from "react";
import { agentRoute } from "./agent/AgentPage";
import { contourRoute } from "./contour/ContourRoute";
import { FormatsRoute } from "./formats/FormatsRoute";
import { libraryRoute } from "./library/LibraryRoute";
import { notesRoute } from "./notes/NotesPage";
import { searchRoute } from "./search/SearchPage";
import { DeskDataProvider } from "./shell/DeskData";
import { Header } from "./shell/Header";
import { Sidebar } from "./shell/Sidebar";
import { newVideoRoute } from "./videos/NewVideoPage";
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

function Shell() {
  const hash = useHash();
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
