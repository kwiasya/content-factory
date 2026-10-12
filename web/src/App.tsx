import { useCallback, useEffect, useState } from "react";
import { api, type CatalogGroup, type Meta } from "./api";
import { DocPage } from "./DocPage";
import { GitBadge } from "./GitBadge";
import { NOTES_HASH, NotesPage, useNotesRoute } from "./notes/NotesPage";

const PREFIX = "#/doc/";

function currentPath(): string | null {
  return window.location.hash.startsWith(PREFIX) ? decodeURIComponent(window.location.hash.slice(PREFIX.length)) : null;
}

export function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [groups, setGroups] = useState<CatalogGroup[]>([]);
  const [showVendored, setShowVendored] = useState(false);
  const [path, setPath] = useState<string | null>(currentPath);
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
    const onHash = () => setPath(currentPath());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <div className="app">
      <header className="top">
        <strong>Desk</strong>
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
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </aside>
        {error && !path && <p className="error">{error}</p>}
        {path ? (
          <DocPage key={path} path={path} onSaved={refresh} />
        ) : onNotes ? (
          <NotesPage />
        ) : (
          <main className="doc">
            <p className="muted">Pick a document on the left.</p>
          </main>
        )}
      </div>
    </div>
  );
}
