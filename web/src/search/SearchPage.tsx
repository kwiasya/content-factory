import { useEffect, useState, type FormEvent } from "react";
import { searchApi, type SearchResult } from "./api";

const PREFIX = "#/search/";

export const searchHref = (q: string) => PREFIX + encodeURIComponent(q);

export function searchRoute(hash: string) {
  if (!hash.startsWith(PREFIX)) {
    return null;
  }
  const q = decodeURIComponent(hash.slice(PREFIX.length));
  return <SearchPage key={q} q={q} />;
}

export function SearchBox() {
  const [q, setQ] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (q.trim()) {
      window.location.hash = searchHref(q.trim());
    }
  };
  return (
    <form className="search-box" onSubmit={submit} role="search">
      <input type="search" placeholder="Search documents" value={q} onChange={(e) => setQ(e.target.value)} />
    </form>
  );
}

function SearchPage({ q }: { q: string }) {
  const [all, setAll] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    searchApi.search(q, all).then(
      (r) => {
        setResult(r);
        setError(null);
      },
      (e: Error) => setError(e.message),
    );
  }, [q, all]);

  return (
    <main className="doc">
      <div className="doc-head">
        <h1>Search: {q}</h1>
        <label className="toggle">
          <input type="checkbox" checked={all} onChange={(e) => setAll(e.target.checked)} />
          Include hidden groups
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      {!result && !error && <p className="muted">Searching…</p>}
      {result && (
        <>
          <p className="muted">
            {result.total === 0
              ? "No document contains this text."
              : `${result.total} document${result.total === 1 ? "" : "s"}${result.truncated ? " (first 200 shown)" : ""}`}
          </p>
          {result.groups.map((g) => (
            <section key={g.id} className="search-group">
              <h2>{g.title}</h2>
              {g.hits.map((h) => (
                <div key={h.path} className="hit">
                  <a href={"#/doc/" + encodeURIComponent(h.path)}>{h.title}</a>{" "}
                  <span className="muted">
                    <code>{h.path}</code> · {h.count} match{h.count === 1 ? "" : "es"}
                  </span>
                  {h.snippets.map((s) => (
                    <div key={s.line} className="snippet">
                      <span className="line-no">{s.line}</span>
                      <Highlight text={s.text} q={result.q.trim()} />
                    </div>
                  ))}
                </div>
              ))}
            </section>
          ))}
        </>
      )}
    </main>
  );
}

function Highlight({ text, q }: { text: string; q: string }) {
  const lower = text.toLowerCase();
  const needle = q.toLowerCase();
  const parts = [];
  let from = 0;
  let at = lower.indexOf(needle);
  while (needle && at >= 0) {
    parts.push(text.slice(from, at));
    parts.push(<mark key={at}>{text.slice(at, at + needle.length)}</mark>);
    from = at + needle.length;
    at = lower.indexOf(needle, from);
  }
  parts.push(text.slice(from));
  return <span>{parts}</span>;
}
