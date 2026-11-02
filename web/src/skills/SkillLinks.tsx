import { useEffect, useState, type ReactNode } from "react";
import { ownSkillPage, type CatalogEntry } from "../api";
import { skillsApi, type SkillLinks as Links } from "./api";
import { useT } from "../i18n";

const docHref = (path: string) => "#/doc/" + encodeURIComponent(path);
const skillHref = (name: string) => docHref(`.claude/skills/${name}/SKILL.md`);

export function SkillLinks({ entry }: { entry: CatalogEntry }) {
  const name = ownSkillPage(entry);
  return name ? <SkillLinksOf key={name} name={name} /> : null;
}

function SkillLinksOf({ name }: { name: string }) {
  const t = useT();
  const [links, setLinks] = useState<Links | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    skillsApi.links(name).then(setLinks, setError);
  }, [name]);

  if (error) {
    return null;
  }
  if (!links) {
    return <p className="muted">{t("links.loading")}</p>;
  }

  const catalogued = new Set(links.catalogued);
  const nothing =
    links.paths.length + links.commands.length + links.tables.length + links.skills.length === 0;

  return (
    <section className="skill-links">
      <div>
        <h3>{t("links.mentions")}</h3>
        {nothing && <p className="muted">{t("links.nothing")}</p>}
        <Row label={t("links.files")}>
          {links.paths.map((p) =>
            catalogued.has(p) ? (
              <a key={p} href={docHref(p)}>
                <code>{p}</code>
              </a>
            ) : (
              <code key={p}>{p}</code>
            ),
          )}
        </Row>
        <Row label={t("links.commands")}>
          {links.commands.map((c) => (
            <code key={c}>{c}</code>
          ))}
        </Row>
        <Row label={t("links.tables")}>
          {links.tables.map((t) => (
            <code key={t}>{t}</code>
          ))}
        </Row>
        <Row label={t("links.skills")}>
          {links.skills.map((s) => (
            <a key={s} href={skillHref(s)}>
              /{s}
            </a>
          ))}
        </Row>
      </div>
      <div>
        <h3>{t("links.mentionedBy")}</h3>
        {links.mentioned_by.length === 0 ? (
          <p className="muted">{t("links.noneMention", { name })}</p>
        ) : (
          <Row label={t("links.skills")}>
            {links.mentioned_by.map((s) => (
              <a key={s} href={skillHref(s)}>
                /{s}
              </a>
            ))}
          </Row>
        )}
      </div>
    </section>
  );
}

function Row({ label, children }: { label: string; children: ReactNode[] }) {
  if (children.length === 0) {
    return null;
  }
  return (
    <div className="link-row">
      <span className="muted">{label}</span>
      <span className="chips">{children}</span>
    </div>
  );
}
