import { useCallback, useEffect, useState } from "react";
import { cardHref, ideaHref } from "../contour/routes";
import { NoteBox } from "../notes/NoteBox";
import { formatDate, formatSize, formatTime } from "../format";
import { VIDEOS_PREFIX } from "./routes";
import { TextFileEditor } from "./TextFileEditor";
import { mediaUrl } from "../api";
import { videosApi, type VideoDetail, type VideoFile } from "./videosApi";
import { useT, type Key, type Problem } from "../i18n";
import { ErrorLine } from "../ErrorLine";
import { useDeskData } from "../shell/DeskData";

const TABS = ["script", "text", "brief", "subtitles", "renders", "overlays", "sources", "files", "references", "notes"] as const;

type Tab = (typeof TABS)[number];

const byVersion = (a: VideoFile, b: VideoFile) => b.path.localeCompare(a.path, undefined, { numeric: true });

export function VideoPage({ slug }: { slug: string }) {
  const t = useT();
  const [detail, setDetail] = useState<VideoDetail | null>(null);
  const [error, setError] = useState<Problem | null>(null);
  const [tab, setTab] = useState<Tab>("script");
  const { reload } = useDeskData();

  const load = useCallback(() => {
    videosApi.get(slug).then(
      (d) => {
        setDetail(d);
        setError(null);
      },
      setError,
    );
  }, [slug]);

  useEffect(load, [load]);

  if (!detail) {
    return (
      <main className="doc videos">
        <a href={VIDEOS_PREFIX}>{t("videos.back")}</a>
        {error ? <ErrorLine error={error} /> : <p className="muted">{t("common.loading")}</p>}
      </main>
    );
  }

  const { video, files } = detail;
  const ofKind = (kind: VideoFile["kind"]) => files.filter((f) => f.kind === kind);

  return (
    <main className="doc videos">
      <a href={VIDEOS_PREFIX}>{t("videos.back")}</a>
      <div className="doc-head">
        <div>
          <h1>{video.title_working || detail.slug}</h1>
          <code className="path">{detail.folder}</code>
        </div>
        <div className="doc-badges">
          {video.format && <span className="badge">{video.format}</span>}
          {video.channel && <span className="badge">{video.channel}</span>}
          {video.language && <span className="badge">{video.language}</span>}
          {detail.legacy && <span className="badge readonly">{t("videos.legacy")}</span>}
        </div>
      </div>

      <StatusStrip
        detail={detail}
        onChanged={(d) => {
          setDetail(d);
          reload();
        }}
        onReload={load}
      />

      <LinkedResearch references={video.references ?? []} ideas={video.ideas ?? []} />

      <nav className="tabs">
        {TABS.map((id) => (
          <button key={id} className={id === tab ? "active" : ""} onClick={() => setTab(id)}>
            {t(`videos.tab.${id}`)}
          </button>
        ))}
      </nav>

      <ErrorLine error={error} />

      {tab === "script" && <Picker slug={slug} files={ofKind("script")} empty="videos.noScript" onSaved={load} />}
      {tab === "text" && <TextFileEditor key="voiceover" slug={slug} path="voiceover.md" creatable onSaved={load} />}
      {tab === "brief" && <TextFileEditor key="brief" slug={slug} path="brief.md" creatable onSaved={load} />}
      {tab === "subtitles" && (
        <Picker slug={slug} files={ofKind("subtitle")} empty="videos.noSubtitles" onSaved={load} />
      )}
      {tab === "renders" && <MediaList files={ofKind("render").sort(byVersion)} empty="videos.noRenders" />}
      {tab === "overlays" && (
        <MediaList
          files={ofKind("overlay")}
          empty="videos.noOverlays"
          hint="videos.overlayHint"
        />
      )}
      {tab === "sources" && (
        <>
          <MediaList files={ofKind("source")} empty="videos.noSources" />
          <h2 className="section">{t("videos.walkProxies")}</h2>
          {detail.proxies.length === 0 ? (
            <p className="muted">{t("videos.noProxies")}</p>
          ) : (
            <div className="media-grid">
              {detail.proxies.map((p) => (
                <Player key={p.media} title={`${p.walk} / ${p.name}`} media={p.media} meta={formatSize(p.size, t)} />
              ))}
            </div>
          )}
        </>
      )}
      {tab === "files" && <FileTree slug={slug} files={files} onSaved={load} />}
      {tab === "references" &&
        (files.some((f) => f.path === "references.md") ? (
          <TextFileEditor key="references" slug={slug} path="references.md" onSaved={load} />
        ) : (
          <p className="muted">{t("videos.noReferences")}</p>
        ))}
      {tab === "notes" && <TextFileEditor key="notes" slug={slug} path="notes.md" creatable onSaved={load} />}

      <NoteBox kind="video" noteKey={detail.slug} />
    </main>
  );
}

function LinkedResearch({ references, ideas }: { references: string[]; ideas: Array<string | number> }) {
  const t = useT();
  return (
    <dl className="facts linked">
      <div>
        <dt>{t("videos.references")}</dt>
        <dd>
          {references.length === 0
            ? "—"
            : references.map((id) => (
                <a key={id} href={cardHref(id)}>
                  <code>{id}</code>
                </a>
              ))}
        </dd>
      </div>
      <div>
        <dt>{t("videos.ideas")}</dt>
        <dd>
          {ideas.length === 0
            ? "—"
            : ideas.map((id) => (
                <a key={id} href={ideaHref(id)}>
                  #{id}
                </a>
              ))}
        </dd>
      </div>
    </dl>
  );
}

function StatusStrip({
  detail,
  onChanged,
  onReload,
}: {
  detail: VideoDetail;
  onChanged: (d: VideoDetail) => void;
  onReload: () => void;
}) {
  const t = useT();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Problem | null>(null);
  const current = detail.video.status ?? null;
  const index = current ? detail.statuses.indexOf(current) : -1;
  const next = index + 1 < detail.statuses.length ? detail.statuses[index + 1] : null;
  const history = detail.video.history ?? [];

  const advance = async () => {
    if (!next || detail.hash === null) {
      return;
    }
    setBusy(true);
    setError(null);
    const result = await videosApi.setStatus(detail.slug, next, note, detail.hash);
    setBusy(false);
    if (result.status === "saved") {
      setNote("");
      onChanged(result.detail);
    } else if (result.status === "conflict") {
      setError({ message: "", code: "statusConflict" });
      onReload();
    } else {
      setError(result.problem);
    }
  };

  return (
    <section className="status-box">
      <ol className="status-strip">
        {detail.statuses.map((s, i) => (
          <li key={s} className={i < index ? "done" : i === index ? "current" : ""}>
            {t(`videos.status.${s}`)}
          </li>
        ))}
      </ol>
      {detail.legacy ? (
        <p className="muted">
          {t("videos.legacyStatus", {
            script: t("videos.status.script"),
            edit: t("videos.status.edit"),
            review: t("videos.status.review"),
          })}
        </p>
      ) : next ? (
        <div className="advance">
          <input
            type="text"
            placeholder={t("videos.notePlaceholder")}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && advance()}
          />
          <button className="primary" disabled={busy} onClick={advance}>
            {busy ? t("common.saving") : t("videos.advance", { status: t(`videos.status.${next}`) })}
          </button>
        </div>
      ) : (
        <p className="muted">{t("videos.published")}</p>
      )}
      <ErrorLine error={error} />
      {history.length > 0 && (
        <details className="history">
          <summary>{t("videos.history", { n: history.length })}</summary>
          <table className="log">
            <tbody>
              {history.map((h, i) => (
                <tr key={i}>
                  <td>{formatDate(h.at, t)}</td>
                  <td>
                    <span className={`status-pill status-${h.status}`}>{t.or(`videos.status.${h.status}`, h.status)}</span>
                  </td>
                  <td>{h.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </section>
  );
}

function Picker({
  slug,
  files,
  empty,
  onSaved,
}: {
  slug: string;
  files: VideoFile[];
  empty: Key;
  onSaved: () => void;
}) {
  const t = useT();
  const [picked, setPicked] = useState<string | null>(null);
  const path = picked && files.some((f) => f.path === picked) ? picked : (files[0]?.path ?? null);
  if (path === null) {
    return <p className="muted">{t(empty)}</p>;
  }
  return (
    <>
      {files.length > 1 && (
        <div className="picker">
          {files.map((f) => (
            <button key={f.path} className={f.path === path ? "active" : ""} onClick={() => setPicked(f.path)}>
              {f.path}
            </button>
          ))}
        </div>
      )}
      <TextFileEditor key={path} slug={slug} path={path} onSaved={onSaved} />
    </>
  );
}

function Player({ title, media, meta }: { title: string; media: string; meta: string }) {
  return (
    <figure className="player">
      <video controls preload="metadata" src={mediaUrl(media)} />
      <figcaption>
        <a href={mediaUrl(media)} target="_blank" rel="noreferrer">
          {title}
        </a>
        <span className="muted">{meta}</span>
      </figcaption>
    </figure>
  );
}

function MediaList({ files, empty, hint }: { files: VideoFile[]; empty: Key; hint?: Key }) {
  const t = useT();
  if (files.length === 0) {
    return <p className="muted">{t(empty)}</p>;
  }
  return (
    <>
      {hint && <p className="muted">{t(hint)}</p>}
      <div className="media-grid">
        {files.map((f) =>
          f.media ? (
            <Player key={f.path} title={f.path} media={f.media} meta={`${formatSize(f.size, t)} · ${formatTime(f.mtime, t)}`} />
          ) : (
            <p key={f.path} className="muted">
              {t("videos.notServed", { path: f.path })}
            </p>
          ),
        )}
      </div>
    </>
  );
}

type TreeRow = { dir: string; depth: number; key: string } | { file: VideoFile; depth: number; key: string };

function treeRows(files: VideoFile[]): TreeRow[] {
  const rows: TreeRow[] = [];
  let previous: string[] = [];
  for (const file of files) {
    const dirs = file.path.split("/").slice(0, -1);
    let shared = 0;
    while (shared < dirs.length && dirs[shared] === previous[shared]) {
      shared += 1;
    }
    for (let i = shared; i < dirs.length; i += 1) {
      rows.push({ dir: dirs[i], depth: i, key: `dir:${dirs.slice(0, i + 1).join("/")}` });
    }
    rows.push({ file, depth: dirs.length, key: file.path });
    previous = dirs;
  }
  return rows;
}

function FileTree({ slug, files, onSaved }: { slug: string; files: VideoFile[]; onSaved: () => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const openFile = files.find((f) => f.path === open && f.editable) ?? null;
  const t = useT();
  if (files.length === 0) {
    return <p className="muted">{t("videos.emptyFolder")}</p>;
  }
  return (
    <>
      <ul className="file-tree">
        {treeRows(files).map((row) => {
          const indent = { paddingLeft: `${row.depth * 16}px` };
          if ("dir" in row) {
            return (
              <li key={row.key} className="dir" style={indent}>
                {row.dir}/
              </li>
            );
          }
          const f = row.file;
          const name = f.path.split("/").pop();
          return (
            <li key={row.key} style={indent}>
              {f.editable ? (
                <button className={`link ${f.path === open ? "active" : ""}`} onClick={() => setOpen(f.path)}>
                  {name}
                </button>
              ) : f.media ? (
                <a href={mediaUrl(f.media)} target="_blank" rel="noreferrer">
                  {name}
                </a>
              ) : (
                <span>{name}</span>
              )}
              <span className="badge">{t.or(`videos.kind.${f.kind}`, f.kind)}</span>
              <span className="muted">{formatSize(f.size, t)}</span>
            </li>
          );
        })}
      </ul>
      {openFile && <TextFileEditor key={openFile.path} slug={slug} path={openFile.path} onSaved={onSaved} />}
    </>
  );
}
