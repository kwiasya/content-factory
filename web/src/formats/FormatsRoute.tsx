import { useEffect, useState, type ReactNode } from "react";
import { formatsApi, type Format, type FormatSummary, type Rule } from "./api";
import { Preview } from "../Preview";
import { videoHref } from "../videos/routes";
import { useT, type Problem } from "../i18n";
import { ErrorLine } from "../ErrorLine";
import "./formats.css";

const ROOT = "#/formats";
const DOC = "#/doc/";

function route(hash: string): { id: string | null } | null {
  if (hash === ROOT) {
    return { id: null };
  }
  return hash.startsWith(ROOT + "/") ? { id: decodeURIComponent(hash.slice(ROOT.length + 1)) } : null;
}

export function FormatsNav({ hash }: { hash: string }) {
  const active = route(hash) !== null;
  const t = useT();
  return (
    <section className="group">
      <h2>{t("formats.shelves")}</h2>
      <ul>
        <li>
          <a href={ROOT} className={active ? "active" : ""}>
            <span className="name">{t("formats.nav")}</span>
          </a>
        </li>
      </ul>
    </section>
  );
}

export function FormatsRoute({ hash, fallback }: { hash: string; fallback: ReactNode }) {
  const current = route(hash);
  if (!current) {
    return <>{fallback}</>;
  }
  return (
    <main className="doc formats">
      {current.id ? <FormatPage key={current.id} id={current.id} /> : <FormatList />}
    </main>
  );
}

function FormatList() {
  const t = useT();
  const [formats, setFormats] = useState<FormatSummary[] | null>(null);
  const [error, setError] = useState<Problem | null>(null);

  useEffect(() => {
    formatsApi.list().then(setFormats, setError);
  }, []);

  if (error) {
    return <ErrorLine error={error} />;
  }
  if (!formats) {
    return <p className="muted">{t("common.loading")}</p>;
  }
  return (
    <>
      <h1>{t("formats.title")}</h1>
      {formats.length === 0 ? (
        <p className="muted">{t.rich("formats.empty", { glob: <code>formats/*/FORMAT.md</code> })}</p>
      ) : (
        <ul className="format-cards">
          {formats.map((f) => (
            <li key={f.id}>
              <a href={`${ROOT}/${encodeURIComponent(f.id)}`}>
                <strong>{f.title}</strong>
                <code className="path">{f.id}</code>
                <span className="muted">{t(f.has_hook_library ? "formats.hookLibraryExported" : "formats.noHookLibrary")}</span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function FormatPage({ id }: { id: string }) {
  const t = useT();
  const [format, setFormat] = useState<Format | null>(null);
  const [error, setError] = useState<Problem | null>(null);

  useEffect(() => {
    formatsApi.get(id).then(setFormat, setError);
  }, [id]);

  if (error) {
    return <ErrorLine error={error} />;
  }
  if (!format) {
    return <p className="muted">{t("common.loading")}</p>;
  }
  return (
    <>
      <p className="crumbs">
        <a href={ROOT}>{t("formats.title")}</a> / {format.id}
      </p>
      <div className="doc-head">
        <div>
          <h1>{format.title}</h1>
          <code className="path">{format.format.path}</code>
        </div>
        <a className="button" href={DOC + encodeURIComponent(format.format.path)}>
          {t("formats.editFormat")}
        </a>
      </div>

      <section className="format-section">
        <Preview text={format.format.text} kind="markdown" />
      </section>

      <section className="format-section">
        <h2>{t("formats.hookLibrary")}</h2>
        {format.hook_library ? (
          <>
            <p className="muted">
              {t.rich("formats.hookLibraryMeta", {
                path: <code>{format.hook_library.path}</code>,
                cmd: <code>hooks export</code>,
              })}
            </p>
            <Preview text={format.hook_library.text} kind="markdown" />
          </>
        ) : (
          <p className="muted">
            {t.rich("formats.notExported", { cmd: <code>python -m cf.research hooks export {format.id}</code> })}
          </p>
        )}
      </section>

      <RulesSection format={format} />

      <section className="format-section">
        <h2>{t("formats.videos", { n: format.videos.length })}</h2>
        {format.videos.length === 0 ? (
          <p className="muted">
            {t.rich("formats.noVideos", { glob: <code>videos/*/video.json</code>, id: <code>{format.id}</code> })}
          </p>
        ) : (
          <table className="grid">
            <thead>
              <tr>
                <th>{t("formats.col.video")}</th>
                <th>{t("formats.col.status")}</th>
                <th>{t("formats.col.channel")}</th>
                <th>{t("formats.col.folder")}</th>
              </tr>
            </thead>
            <tbody>
              {format.videos.map((v) => (
                <tr key={v.slug}>
                  <td>
                    <a href={videoHref(v.slug)}>{v.title}</a>
                  </td>
                  <td>{v.status ? t.or(`videos.status.${v.status}`, v.status) : "—"}</td>
                  <td>{v.channel ?? "—"}</td>
                  <td>
                    <code className="path">{v.path}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}

function RulesSection({ format }: { format: Format }) {
  const [topic, setTopic] = useState<string>("all");
  const shown = topic === "all" ? format.rules : format.rules.filter((r) => r.topic === topic);
  const missing = format.topics.filter((x) => !x.path);
  const t = useT();

  return (
    <section className="format-section">
      <h2>{t("formats.rules", { n: format.rules.length })}</h2>
      <div className="chips">
        {["all", ...format.topics.filter((x) => x.path).map((x) => x.topic)].map((x) => (
          <button key={x} className={x === topic ? "active" : ""} onClick={() => setTopic(x)}>
            {x === "all" ? t("formats.rulesAll") : x}
          </button>
        ))}
      </div>
      {missing.length > 0 && (
        <p className="muted">{t("formats.noRulesFile", { topics: missing.map((x) => x.topic).join(", ") })}</p>
      )}
      {format.topics.length === 0 ? (
        <p className="muted">{t("formats.noTopics")}</p>
      ) : (
        <table className="grid rules">
          <thead>
            <tr>
              <th>{t("formats.col.id")}</th>
              <th>{t("formats.col.rule")}</th>
              <th>{t("formats.col.scope")}</th>
              <th>{t("formats.col.tag")}</th>
              <th>{t("formats.col.confidence")}</th>
              <th>{t("formats.col.source")}</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.id}>
                <td>
                  <code>{r.id}</code>
                </td>
                <td>{r.rule}</td>
                <td>{r.scope}</td>
                <td>{r.tag}</td>
                <td>{r.confidence}</td>
                <td>
                  <Source rule={r} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="muted">
        {t.rich("formats.editRules", {
          links: format.topics
            .filter((x) => x.path)
            .map((x, i) => (
              <span key={x.topic}>
                {i > 0 && ", "}
                <a href={DOC + encodeURIComponent(x.path as string)}>{x.path}</a>
              </span>
            )),
        })}
      </p>
    </section>
  );
}

const LINK = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g;

function Source({ rule }: { rule: Rule }) {
  const parts: ReactNode[] = [];
  let last = 0;
  for (const m of rule.source.matchAll(LINK)) {
    parts.push(rule.source.slice(last, m.index));
    parts.push(
      <a key={m.index} href={m[2]} target="_blank" rel="noreferrer">
        {m[1]}
      </a>,
    );
    last = (m.index ?? 0) + m[0].length;
  }
  parts.push(rule.source.slice(last));
  return <>{parts}</>;
}
