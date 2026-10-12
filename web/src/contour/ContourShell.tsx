import type { ReactNode } from "react";
import { CONTOUR_PREFIX, ideasHref, taxonomyHref } from "./routes";

type Section = "home" | "ideas" | "taxonomy" | null;

export function ContourShell({ active, children }: { active: Section; children: ReactNode }) {
  const link = (href: string, id: Section, label: string) => (
    <a href={href} className={active === id ? "active" : ""}>
      {label}
    </a>
  );
  return (
    <main className="doc contour">
      <nav className="contour-nav">
        {link(CONTOUR_PREFIX, "home", "Watchlists")}
        {link(ideasHref(), "ideas", "Ideas")}
        {link(taxonomyHref(), "taxonomy", "Taxonomy")}
      </nav>
      {children}
    </main>
  );
}

export function Status({ error, loading }: { error: string | null; loading: boolean }) {
  if (error) {
    return <p className="error">{error}</p>;
  }
  return loading ? <p className="muted">Loading…</p> : null;
}

export function Cmd({ children }: { children: string }) {
  return <code className="cmd">{children}</code>;
}
