import { useCallback, useEffect, useState } from "react";
import { api, type CatalogEntry, type CatalogGroup, type Meta } from "../api";
import { DocPage } from "../DocPage";
import { ErrorLine } from "../ErrorLine";
import { GitBadge } from "../GitBadge";
import { formatSize, formatTime } from "../format";
import { LintBadge } from "../formats/SkillLint";
import { useT, type Problem, type T } from "../i18n";
import { RESEARCH_PREFIX, parseResearch, researchRoute } from "../research/ResearchPage";
import { AGENT_HASH, docHref, parseDoc } from "../shell/routes";

function entryTooltip(d: CatalogEntry, t: T): string {
  const lines = [d.path];
  if (d.description) {
    lines.push(d.description);
  }
  if (d.mtime !== undefined && d.size !== undefined) {
    lines.push(t("app.lastChangeSize", { time: formatTime(d.mtime, t), size: formatSize(d.size, t) }));
  }
  return lines.join("\n");
}

function Catalogue({
  groups,
  path,
  showVendored,
  onShowVendored,
}: {
  groups: CatalogGroup[];
  path: string | null;
  showVendored: boolean;
  onShowVendored: (show: boolean) => void;
}) {
  const t = useT();
  return (
    <aside className="sidebar catalogue">
      <label className="toggle">
        <input type="checkbox" checked={showVendored} onChange={(e) => onShowVendored(e.target.checked)} />
        {t("app.showVendored")}
      </label>
      {groups.map((g) => (
        <section key={g.id} className="group">
          <h2>{t.or(`group.${g.id}`, g.title)}</h2>
          {g.empty.map((e) => (
            <p key={e.glob} className="empty">
              {t.or(`empty.${e.code}`, e.hint)}
            </p>
          ))}
          <ul>
            {g.docs.map((d) => (
              <li key={d.path}>
                <a
                  href={docHref(d.path)}
                  className={d.path === path ? "active" : ""}
                  aria-current={d.path === path ? "page" : undefined}
                  title={entryTooltip(d, t)}
                >
                  <span className="name">{d.title}</span>
                  {!d.editable && <span className="lock">{t("common.readOnlyShort")}</span>}
                  <GitBadge state={d.git} compact />
                  <LintBadge entry={d} />
                </a>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </aside>
  );
}

function AgentOverview({ meta, error }: { meta: Meta | null; error: Problem | null }) {
  const t = useT();
  return (
    <main className="doc agent-overview">
      <h1>{t("agent.title")}</h1>
      <p className="muted">{t("agent.intro")}</p>
      <ErrorLine error={error} />
      {meta && (
        <dl className="facts">
          <div>
            <dt>{t("agent.repo")}</dt>
            <dd>
              <code>{meta.repo}</code>
            </dd>
          </div>
          <div>
            <dt>{t("agent.branch")}</dt>
            <dd>{meta.branch ? <span className="branch">{meta.branch}</span> : "—"}</dd>
          </div>
          <div>
            <dt>{t("agent.localRoot")}</dt>
            <dd>
              <code>{meta.local_root}</code>
            </dd>
          </div>
          <div>
            <dt>{t("agent.sharedRoot")}</dt>
            <dd>
              <code>{meta.shared_root}</code>
              {!meta.shared_available && (
                <p className="error">{t("agent.sharedMissing", { root: meta.shared_root })}</p>
              )}
            </dd>
          </div>
          <div>
            <dt>{t("agent.person")}</dt>
            <dd>
              <code>{meta.person}</code>
            </dd>
          </div>
          <div>
            <dt>{t("agent.db")}</dt>
            <dd>
              <code>{meta.db_path}</code>
            </dd>
          </div>
        </dl>
      )}
      <p>
        <a href={RESEARCH_PREFIX}>{t("agent.researchDocs")}</a>
      </p>
    </main>
  );
}

function AgentLayout({ hash }: { hash: string }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [groups, setGroups] = useState<CatalogGroup[]>([]);
  const [showVendored, setShowVendored] = useState(false);
  const [error, setError] = useState<Problem | null>(null);
  const path = parseDoc(hash);

  useEffect(() => {
    api.meta().then(setMeta, setError);
  }, []);

  const refresh = useCallback(() => {
    api.catalog(showVendored).then(setGroups, setError);
  }, [showVendored]);

  useEffect(refresh, [refresh]);

  return (
    <div className="agent">
      <Catalogue groups={groups} path={path} showVendored={showVendored} onShowVendored={setShowVendored} />
      {path ? (
        <DocPage key={path} path={path} onSaved={refresh} />
      ) : parseResearch(hash) ? (
        researchRoute(hash)
      ) : (
        <AgentOverview meta={meta} error={error} />
      )}
    </div>
  );
}

export function agentRoute(hash: string) {
  if (hash !== AGENT_HASH && parseDoc(hash) === null && parseResearch(hash) === null) {
    return null;
  }
  return <AgentLayout hash={hash} />;
}
