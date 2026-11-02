import { useEffect, useState } from "react";
import { problemOf, send } from "../api";
import { ErrorLine } from "../ErrorLine";
import { useT, type Problem } from "../i18n";
import { libraryHref, parseLibrary } from "../shell/routes";
import { LibraryPage } from "./LibraryPage";

interface Missing {
  suggestions: { id: string; ref: string }[];
}

function RefPage({ target }: { target: string }) {
  const t = useT();
  const [error, setError] = useState<Problem | null>(null);
  const [missing, setMissing] = useState<Missing | null>(null);

  useEffect(() => {
    let live = true;
    send(`/api/library/refs/resolve?ref=${encodeURIComponent(target)}`, "GET").then((r) => {
      if (!live) return;
      if (r.ok) {
        window.location.replace(libraryHref((r.body.asset as { id: string }).id));
        return;
      }
      setError(problemOf(r.body));
      const found = Array.isArray(r.body.suggestions) ? (r.body.suggestions as { id: string; ref: string }[]) : [];
      setMissing({ suggestions: found.map((a) => ({ id: a.id, ref: a.ref })) });
    });
    return () => {
      live = false;
    };
  }, [target]);

  return (
    <main className="doc">
      <h1>
        <code>{target}</code>
      </h1>
      {error ? <ErrorLine error={error} /> : <p className="muted">{t("common.loading")}</p>}
      {missing && missing.suggestions.length > 0 && (
        <>
          <p>{t("library.didYouMean")}</p>
          <ul>
            {missing.suggestions.map((s) => (
              <li key={s.id}>
                <a href={libraryHref(s.id)}>{s.ref}</a>
              </li>
            ))}
          </ul>
        </>
      )}
      <p>
        <a href={libraryHref()}>{t("library.back")}</a>
      </p>
    </main>
  );
}

export function libraryRoute(hash: string) {
  const route = parseLibrary(hash);
  if (!route) {
    return null;
  }
  if (route.ref !== null) {
    return <RefPage key={route.ref} target={route.ref} />;
  }
  return <LibraryPage id={route.id} query={route.query} />;
}
