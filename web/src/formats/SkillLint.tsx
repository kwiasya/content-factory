import { useEffect, useState } from "react";
import { ownSkill, ownSkillPage, type CatalogEntry } from "../api";
import { formatsApi, type BrokenRef, type SkillLint as Lint } from "./api";
import { refreshLintSummary, useLintCount } from "./lintStore";
import { useT, type Key } from "../i18n";
import "./formats.css";

export function LintBadge({ entry }: { entry: CatalogEntry }) {
  const skill = ownSkillPage(entry);
  const count = useLintCount(skill);
  const t = useT();
  if (!count) {
    return null;
  }
  return (
    <span className="badge lint-broken" title={t("lint.badge", { n: count })}>
      {count}
    </span>
  );
}

function RefList({ title, refs }: { title: Key; refs: BrokenRef[] }) {
  const t = useT();
  if (refs.length === 0) {
    return null;
  }
  return (
    <>
      <h3>{t(title)}</h3>
      <ul>
        {refs.map((r) => (
          <li key={`${r.file}:${r.ref}`}>
            <code>{r.ref}</code>{" "}
            <span className="muted">
              {r.file}:{r.line}
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}

export function SkillLint({ entry, version }: { entry: CatalogEntry; version: string }) {
  const skill = ownSkill(entry);
  const t = useT();
  const [lint, setLint] = useState<Lint | null>(null);

  useEffect(() => {
    if (!skill) {
      return;
    }
    let live = true;
    formatsApi.lint(skill).then(
      (l) => {
        if (live) {
          setLint(l);
        }
      },
      () => undefined,
    );
    refreshLintSummary();
    return () => {
      live = false;
    };
  }, [skill, version]);

  if (!skill || !lint || lint.missing_paths.length + lint.missing_skills.length === 0) {
    return null;
  }
  return (
    <details className="lint" open>
      <summary>
        {t("lint.summary", { name: lint.name, n: lint.missing_paths.length + lint.missing_skills.length })}
      </summary>
      <RefList title="lint.paths" refs={lint.missing_paths} />
      <RefList title="lint.skills" refs={lint.missing_skills} />
    </details>
  );
}
