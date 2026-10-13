import { useT } from "../i18n";
import { LIBRARY_HASH } from "../shell/routes";

function LibraryPage() {
  const t = useT();
  return (
    <main className="doc">
      <h1>{t("library.title")}</h1>
      <p className="muted">{t("library.soon")}</p>
    </main>
  );
}

export function libraryRoute(hash: string) {
  return hash === LIBRARY_HASH ? <LibraryPage /> : null;
}
