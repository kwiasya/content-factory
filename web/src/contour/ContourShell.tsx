import type { ReactNode } from "react";
import { CONTOUR_PREFIX, ideasHref, taxonomyHref } from "./routes";
import { useT, type Key, type Problem } from "../i18n";
import { ErrorLine } from "../ErrorLine";

type Section = "home" | "ideas" | "taxonomy" | null;

export function ContourShell({ active, children }: { active: Section; children: ReactNode }) {
  const t = useT();
  const link = (href: string, id: Section, label: Key) => (
    <a href={href} className={active === id ? "active" : ""}>
      {t(label)}
    </a>
  );
  return (
    <main className="doc contour">
      <nav className="contour-nav">
        {link(CONTOUR_PREFIX, "home", "contour.watchlists")}
        {link(ideasHref(), "ideas", "contour.ideas")}
        {link(taxonomyHref(), "taxonomy", "contour.taxonomy")}
      </nav>
      {children}
    </main>
  );
}

export function Status({ error, loading }: { error: Problem | null; loading: boolean }) {
  const t = useT();
  if (error) {
    return <ErrorLine error={error} />;
  }
  return loading ? <p className="muted">{t("common.loading")}</p> : null;
}

export function Cmd({ children }: { children: string }) {
  return <code className="cmd">{children}</code>;
}
