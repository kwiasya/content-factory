import { useCallback, useEffect, useState } from "react";
import { api, type CatalogEntry, type CatalogGroup, type Meta } from "./api";
import { DocPage } from "./DocPage";
import { GitBadge } from "./GitBadge";
import { formatSize, formatTime } from "./format";
import { LangSwitch, useT, type Problem, type T } from "./i18n";
import { ErrorLine } from "./ErrorLine";
import { ResearchNav, researchRoute } from "./research/ResearchPage";
import { SearchBox, searchRoute } from "./search/SearchPage";
import { FormatsNav, FormatsRoute } from "./formats/FormatsRoute";
import { LintBadge } from "./formats/SkillLint";
import { NotesNav, notesRoute } from "./notes/NotesPage";
import { VideosNav, videosRoute } from "./videos/VideosRoute";
import { ContourNav, contourRoute } from "./contour/ContourRoute";

const PREFIX = "#/doc/";

function currentPath(): string | null {
  return window.location.hash.startsWith(PREFIX) ? decodeURIComponent(window.location.hash.slice(PREFIX.length)) : null;
}

function entryTooltip(d: CatalogEntry, t: T): string {
  const lines = [d.path];
  if (d.description) {
    lines.push(d.description);
  }
  if (d.mtime !== undefined && d.size !== undefined) {
    lines.push(t("app.lastChangeSize", { time: formatTime(d.mtime, t), size: formatSize(d.size, t) }));
  }
  return lines.join("\n");
}

export function App() {
  const t = useT();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [groups, setGroups] = useState<CatalogGroup[]>([]);
  const [showVendored, setShowVendored] = useState(false);
  const [path, setPath] = useState<string | null>(currentPath);
  const [hash, setHash] = useState(window.location.hash);
  const [error, setError] = useState<Problem | null>(null);

  useEffect(() => {
    api.meta().then(setMeta, setError);
  }, []);

  const refresh = useCallback(() => {
    api.catalog(showVendored).then(setGroups, setError);
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
        <strong>{t("app.title")}</strong>
        <ResearchNav hash={hash} />
        <VideosNav hash={hash} />
        <ContourNav hash={hash} />
        <SearchBox />
        {meta && (
          <span className="checkout" title={t("app.checkout", { footage: meta.footage_root, db: meta.db_path })}>
            <code>{meta.repo}</code>
            {meta.branch && <span className="branch">{meta.branch}</span>}
          </span>
        )}
        <NotesNav hash={hash} />
        <LangSwitch />
      </header>
      <div className="body">
        <aside className="sidebar">
          <label className="toggle">
            <input type="checkbox" checked={showVendored} onChange={(e) => setShowVendored(e.target.checked)} />
            {t("app.showVendored")}
          </label>
          {groups.map((g) => (
            <section key={g.id} className="group">
              <h2>{t.or(`group.${g.id}`, g.title)}</h2>
              {g.empty.map((e) => (
                <p key={e.glob} className="empty">
                  {t.or(`empty.${e.code}`, e.hint)}
                </p>
              ))}
              <ul>
                {g.docs.map((d) => (
                  <li key={d.path}>
                    <a
                      href={PREFIX + encodeURIComponent(d.path)}
                      className={d.path === path ? "active" : ""}
                      title={entryTooltip(d, t)}
                    >
                      <span className="name">{d.title}</span>
                      {!d.editable && <span className="lock">{t("common.readOnlyShort")}</span>}
                      <GitBadge state={d.git} compact />
                      <LintBadge entry={d} />
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          ))}
          <FormatsNav hash={hash} />
        </aside>
        {!path && <ErrorLine error={error} />}
        {path ? (
          <DocPage key={path} path={path} onSaved={refresh} />
        ) : (
          (notesRoute(hash) ??
          researchRoute(hash) ??
          searchRoute(hash) ??
          videosRoute(hash) ??
          contourRoute(hash) ?? (
            <FormatsRoute
              hash={hash}
              fallback={
                <main className="doc">
                  <p className="muted">{t("app.pick")}</p>
                </main>
              }
            />
          ))
        )}
      </div>
    </div>
  );
}
