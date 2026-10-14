import { useCallback, useEffect, useMemo, useState } from "react";
import { ErrorLine } from "../ErrorLine";
import { formatTime } from "../format";
import { useT, type Problem } from "../i18n";
import { libraryHref } from "../shell/routes";
import { AssetTile } from "./AssetCard";
import { AssetDrawer } from "./AssetDrawer";
import { FontFaces } from "./FontSample";
import { libraryApi, type AssetCard, type AssetPage, type Filter, type LibraryInfo } from "./libraryApi";
import { stop } from "./player";
import "./library.css";

function filterOf(query: URLSearchParams): Filter {
  return {
    pack: query.get("pack") ?? undefined,
    category: query.get("category") ?? undefined,
    tags: (query.get("tags") ?? "").split(",").filter(Boolean),
    q: query.get("q") ?? undefined,
    rights: query.get("rights") ?? undefined,
  };
}

function queryOf(filter: Filter): URLSearchParams {
  const p = new URLSearchParams();
  if (filter.pack) p.set("pack", filter.pack);
  if (filter.category) p.set("category", filter.category);
  if (filter.tags?.length) p.set("tags", filter.tags.join(","));
  if (filter.q) p.set("q", filter.q);
  if (filter.rights) p.set("rights", filter.rights);
  return p;
}

function Packs({ info }: { info: LibraryInfo }) {
  const t = useT();
  if (!info.packs.length) {
    return (
      <div className="lib-empty">
        <p>{t("library.noPacks")}</p>
        <pre>python -m cf.library pack add --config .claude/skills/index-pack/packs/davinci-templates.json</pre>
        <p className="muted">{t.rich("library.noPacksSkill", { skill: <code>/index-pack</code> })}</p>
      </div>
    );
  }
  return (
    <ul className="lib-packs" aria-label={t("library.packs")}>
      {info.packs.map((p) => (
        <li key={p.id} className="lib-pack">
          <strong>{p.id}</strong>{" "}
          <span>{t("library.assetsCount", { n: p.assets })}</span>{" "}
          {p.index_missing ? (
            <span className="muted">
              {t.rich("library.notIndexed", { skill: <code>/index-pack</code>, cmd: <code>python -m cf.library index {p.id}</code> })}
            </span>
          ) : (
            <span className="muted">{t("library.indexedAt", { time: p.indexed_at ? formatTime(p.indexed_at, t) : "—" })}</span>
          )}
          {p.fallback > 0 && <span className="muted"> · {t("library.fallbackFolders", { n: p.fallback })}</span>}
        </li>
      ))}
    </ul>
  );
}

function SearchBox({ value, onChange }: { value: string; onChange: (q: string) => void }) {
  const t = useT();
  const [draft, setDraft] = useState(value);
  const [synced, setSynced] = useState(value);
  if (value !== synced) {
    setSynced(value);
    setDraft(value);
  }
  useEffect(() => {
    if (draft === value) return;
    const timer = window.setTimeout(() => onChange(draft), 200);
    return () => window.clearTimeout(timer);
  }, [draft, value, onChange]);
  return (
    <input
      type="search"
      className="lib-search"
      value={draft}
      placeholder={t("library.search")}
      aria-label={t("library.search")}
      onChange={(e) => setDraft(e.target.value)}
    />
  );
}

export function LibraryPage({ id, query }: { id: string | null; query: URLSearchParams }) {
  const t = useT();
  const queryString = query.toString();
  const filter = useMemo(() => filterOf(new URLSearchParams(queryString)), [queryString]);
  const [info, setInfo] = useState<LibraryInfo | null>(null);
  const [page, setPage] = useState<AssetPage | null>(null);
  const [error, setError] = useState<Problem | null>(null);
  const [notice, setNotice] = useState<Problem | null>(null);

  useEffect(() => {
    libraryApi.info().then(setInfo, setError);
  }, []);

  useEffect(() => {
    let live = true;
    libraryApi.assets(filter).then(
      (p) => {
        if (live) {
          setPage(p);
          setError(null);
        }
      },
      (e: Error) => live && setError(e),
    );
    return () => {
      live = false;
    };
  }, [filter]);

  useEffect(() => stop, []);

  const go = useCallback(
    (next: Filter, nextId: string | null = id) => {
      window.location.hash = libraryHref(nextId, queryOf(next));
    },
    [id],
  );
  const setQ = useCallback((q: string) => go({ ...filter, q: q || undefined }), [go, filter]);

  const reveal = (asset: AssetCard) => {
    setNotice(null);
    libraryApi.reveal(asset.id).then(() => undefined, (e: Error) => setNotice(e));
  };
  const changed = (asset: AssetCard) => {
    setPage((p) => (p ? { ...p, assets: p.assets.map((a) => (a.id === asset.id ? { ...a, ...asset } : a)) } : p));
  };

  const byCategory = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const p of info?.packs ?? []) {
      if (filter.pack && p.id !== filter.pack) continue;
      for (const [c, n] of Object.entries(p.by_category)) counts[c] = (counts[c] ?? 0) + n;
    }
    return counts;
  }, [info, filter.pack]);
  const total = Object.values(byCategory).reduce((a, b) => a + b, 0);
  const activeTags = filter.tags ?? [];
  const toggleTag = (tag: string) =>
    go({ ...filter, tags: activeTags.includes(tag) ? activeTags.filter((x) => x !== tag) : [...activeTags, tag] });
  const facetTags = page
    ? [...activeTags.filter((a) => !page.tags.some((f) => f.tag === a)).map((tag) => ({ tag, n: 0, author: true })), ...page.tags]
    : [];

  return (
    <div className={id ? "lib with-drawer" : "lib"}>
      <main className="doc lib-main">
        <h1>{t("library.title")}</h1>
        <ErrorLine error={error} />
        {info && <Packs info={info} />}
        {info && info.packs.length > 0 && (
          <>
            <div className="lib-filters">
              <div className="lib-cats" role="group" aria-label={t("library.categories")}>
                <button className={!filter.category ? "chip active" : "chip"} aria-pressed={!filter.category} onClick={() => go({ ...filter, category: undefined })}>
                  {t("library.all")} <span className="muted">{total}</span>
                </button>
                {info.categories.map((c) => (
                  <button
                    key={c}
                    className={filter.category === c ? "chip active" : "chip"}
                    aria-pressed={filter.category === c}
                    disabled={!byCategory[c] && filter.category !== c}
                    onClick={() => go({ ...filter, category: filter.category === c ? undefined : c })}
                  >
                    {t.or(`library.category.${c}`, c)} <span className="muted">{byCategory[c] ?? 0}</span>
                  </button>
                ))}
              </div>
              <div className="lib-row">
                <SearchBox value={filter.q ?? ""} onChange={setQ} />
                <select
                  value={filter.rights ?? ""}
                  aria-label={t("library.card.rights")}
                  onChange={(e) => go({ ...filter, rights: e.target.value || undefined })}
                >
                  <option value="">{t("library.rights.any")}</option>
                  {info.rights.map((r) => (
                    <option key={r} value={r}>{t(`library.rights.${r}`)}</option>
                  ))}
                </select>
                {info.packs.length > 1 && (
                  <select value={filter.pack ?? ""} aria-label={t("library.packs")} onChange={(e) => go({ ...filter, pack: e.target.value || undefined })}>
                    <option value="">{t("library.allPacks")}</option>
                    {info.packs.map((p) => <option key={p.id} value={p.id}>{p.id}</option>)}
                  </select>
                )}
              </div>
              {facetTags.length > 0 && (
                <div className="lib-facets" role="group" aria-label={t("library.card.tags")}>
                  {facetTags.map((f) => (
                    <button
                      key={f.tag}
                      className={activeTags.includes(f.tag) ? "chip small active" : f.author ? "chip small" : "chip small agent"}
                      aria-pressed={activeTags.includes(f.tag)}
                      onClick={() => toggleTag(f.tag)}
                    >
                      {f.tag} {f.n > 0 && <span className="muted">{f.n}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <ErrorLine error={notice} />
            {page && (
              <>
                <p className="muted">{t("library.shown", { n: page.total })}</p>
                <FontFaces assets={page.assets} />
                {page.assets.length ? (
                  <ul className="lib-grid">
                    {page.assets.map((a) => (
                      <AssetTile
                        key={a.id}
                        asset={a}
                        selected={a.id === id}
                        onOpen={() => go(filter, a.id)}
                        onReveal={() => reveal(a)}
                      />
                    ))}
                  </ul>
                ) : (
                  <p className="muted">{t(total ? "library.noMatch" : "library.empty")}</p>
                )}
              </>
            )}
          </>
        )}
      </main>
      {id && (
        <AssetDrawer key={id} id={id} onClose={() => go(filter, null)} onChanged={changed} onReveal={reveal} />
      )}
    </div>
  );
}
