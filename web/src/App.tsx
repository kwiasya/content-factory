import { useCallback, useEffect, useState } from "react";
import { api, type CatalogGroup, type Meta } from "./api";
import { DocPage } from "./DocPage";
import { GitBadge } from "./GitBadge";
import { researchRoute } from "./research/ResearchPage";
import { SearchBox, searchRoute } from "./search/SearchPage";
import { FormatsNav, FormatsRoute } from "./formats/FormatsRoute";
import { LintBadge } from "./formats/SkillLint";
import { NOTES_HASH, NotesPage, useNotesRoute } from "./notes/NotesPage";
import { VideosNav, videosRoute } from "./videos/VideosRoute";
import { ContourNav, contourRoute } from "./contour/ContourRoute";

const PREFIX = "#/doc/";

function currentPath(): string | null {
  return window.location.hash.startsWith(PREFIX) ? decodeURIComponent(window.location.hash.slice(PREFIX.length)) : null;
}

export function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [groups, setGroups] = useState<CatalogGroup[]>([]);
  const [showVendored, setShowVendored] = useState(false);
  const [path, setPath] = useState<string | null>(currentPath);
  const [hash, setHash] = useState(window.location.hash);
  const [error, setError] = useState<string | null>(null);
  const onNotes = useNotesRoute();

  useEffect(() => {
    api.meta().then(setMeta, (e: Error) => setError(e.message));
  }, []);

  const refresh = useCallback(() => {
    api.catalog(showVendored).then(setGroups, (e: Error) => setError(e.message));
  }, [showVendored]);

  useEffect(refresh, [refresh]);

  useEffect(() => {
    const onHash = () => {
      setPath(currentPath());
      setHash(window.location.hash);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <div className="app">
      <header className="top">
        <strong>Desk</strong>
        <a href="#/research" className={hash.startsWith("#/research") ? "nav active" : "nav"}>Research</a>
        <VideosNav hash={hash} />
        <ContourNav hash={hash} />
        <SearchBox />
        {meta && (
          <span className="checkout" title={`footage: ${meta.footage_root}\ndb: ${meta.db_path}`}>
            <code>{meta.repo}</code>
            {meta.branch && <span className="branch">{meta.branch}</span>}
          </span>
        )}
        <a href={NOTES_HASH} className="nav-notes">Notes</a>
      </header>
      <div className="body">
        <aside className="sidebar">
          <label className="toggle">
            <input type="checkbox" checked={showVendored} onChange={(e) => setShowVendored(e.target.checked)} />
            Show vendored skills
          </label>
          {groups.map((g) => (
            <section key={g.id} className="group">
              <h2>{g.title}</h2>
              {g.empty.map((e) => (
                <p key={e.glob} className="empty">
                  {e.hint}
                </p>
              ))}
              <ul>
                {g.docs.map((d) => (
                  <li key={d.path}>
                    <a
                      href={PREFIX + encodeURIComponent(d.path)}
                      className={d.path === path ? "active" : ""}
                      title={d.path}
                    >
                      <span className="name">{d.title}</span>
                      {!d.editable && <span className="lock">ro</span>}
                      <GitBadge state={d.git} compact />
                      <LintBadge path={d.path} />
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          ))}
          <FormatsNav />
        </aside>
        {error && !path && <p className="error">{error}</p>}
        {path ? (
          <DocPage key={path} path={path} onSaved={refresh} />
        ) : onNotes ? (
          <NotesPage />
        ) : (
          (researchRoute(hash) ??
          searchRoute(hash) ??
          videosRoute(hash) ??
          contourRoute(hash) ?? (
            <FormatsRoute
              fallback={
                <main className="doc">
                  <p className="muted">Pick a document on the left.</p>
                </main>
              }
            />
          ))
        )}
      </div>
    </div>
  );
}
