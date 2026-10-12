import { useEffect, useState } from "react";
import { ownSkill, ownSkillPage, type CatalogEntry } from "../api";
import { formatsApi, type BrokenRef, type SkillLint as Lint } from "./api";
import { refreshLintSummary, useLintCount } from "./lintStore";
import "./formats.css";

export function LintBadge({ entry }: { entry: CatalogEntry }) {
  const skill = ownSkillPage(entry);
  const count = useLintCount(skill);
  if (!count) {
    return null;
  }
  return (
    <span className="badge lint-broken" title={`${count} broken reference${count === 1 ? "" : "s"}`}>
      {count}
    </span>
  );
}

function RefList({ title, refs }: { title: string; refs: BrokenRef[] }) {
  if (refs.length === 0) {
    return null;
  }
  return (
    <>
      <h3>{title}</h3>
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
        Broken references in /{lint.name}: {lint.missing_paths.length + lint.missing_skills.length}
      </summary>
      <RefList title="Paths that do not exist" refs={lint.missing_paths} />
      <RefList title="Skills that do not exist" refs={lint.missing_skills} />
    </details>
  );
}
