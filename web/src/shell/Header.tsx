import { Fragment } from "react";
import { useT } from "../i18n";
import { crumbs } from "./crumbs";
import { useDeskData } from "./DeskData";

export function Header({ hash }: { hash: string }) {
  const t = useT();
  const { videos, formats } = useDeskData();
  const trail = crumbs(hash, { videos, formats, t });
  return (
    <header className="top">
      <nav className="crumbs" aria-label={t("crumb.label")}>
        {trail.map((c, i) => {
          const last = i === trail.length - 1;
          return (
            <Fragment key={i}>
              {i > 0 && <span className="sep">›</span>}
              {last ? (
                <strong aria-current="page">{c.label}</strong>
              ) : c.href ? (
                <a href={c.href}>{c.label}</a>
              ) : (
                <span>{c.label}</span>
              )}
            </Fragment>
          );
        })}
      </nav>
    </header>
  );
}
