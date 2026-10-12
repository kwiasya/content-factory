import { useCallback, useEffect, useState } from "react";
import { cardHref, ideaHref } from "../contour/routes";
import { NoteBox } from "../notes/NoteBox";
import { formatSize, formatTime } from "../format";
import { VIDEOS_PREFIX } from "./routes";
import { TextFileEditor } from "./TextFileEditor";
import { mediaUrl, videosApi, type VideoDetail, type VideoFile } from "./videosApi";

type Tab = "script" | "brief" | "subtitles" | "renders" | "overlays" | "sources" | "files" | "references" | "notes";

const TABS: { id: Tab; label: string }[] = [
  { id: "script", label: "Script" },
  { id: "brief", label: "Brief" },
  { id: "subtitles", label: "Subtitles" },
  { id: "renders", label: "Renders" },
  { id: "overlays", label: "Overlays" },
  { id: "sources", label: "Sources & proxies" },
  { id: "files", label: "Files" },
  { id: "references", label: "References" },
  { id: "notes", label: "Notes" },
];

const byVersion = (a: VideoFile, b: VideoFile) => b.path.localeCompare(a.path, undefined, { numeric: true });

export function VideoPage({ slug }: { slug: string }) {
  const [detail, setDetail] = useState<VideoDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("script");

  const load = useCallback(() => {
    videosApi.get(slug).then(
      (d) => {
        setDetail(d);
        setError(null);
      },
      (e: Error) => setError(e.message),
    );
  }, [slug]);

  useEffect(load, [load]);

  if (!detail) {
    return (
      <main className="doc videos">
        <a href={VIDEOS_PREFIX}>← Videos</a>
        {error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>}
      </main>
    );
  }

  const { video, files } = detail;
  const ofKind = (kind: VideoFile["kind"]) => files.filter((f) => f.kind === kind);

  return (
    <main className="doc videos">
      <a href={VIDEOS_PREFIX}>← Videos</a>
      <div className="doc-head">
        <div>
          <h1>{video.title_working || detail.slug}</h1>
          <code className="path">{detail.folder}</code>
        </div>
        <div className="doc-badges">
          {video.format && <span className="badge">{video.format}</span>}
          {video.channel && <span className="badge">{video.channel}</span>}
          {video.language && <span className="badge">{video.language}</span>}
          {detail.legacy && <span className="badge readonly">legacy Reel</span>}
        </div>
      </div>

      <StatusStrip detail={detail} onChanged={setDetail} onReload={load} />

      <LinkedResearch references={video.references ?? []} ideas={video.ideas ?? []} />

      <nav className="tabs">
        {TABS.map((t) => (
          <button key={t.id} className={t.id === tab ? "active" : ""} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      {error && <p className="error">{error}</p>}

      {tab === "script" && <Picker slug={slug} files={ofKind("script")} empty="No script.* in this folder yet." onSaved={load} />}
      {tab === "brief" && <TextFileEditor key="brief" slug={slug} path="brief.md" creatable onSaved={load} />}
      {tab === "subtitles" && (
        <Picker slug={slug} files={ofKind("subtitle")} empty="No .srt or .vtt files in this folder." onSaved={load} />
      )}
      {tab === "renders" && <MediaList files={ofKind("render").sort(byVersion)} empty="No renders yet." />}
      {tab === "overlays" && (
        <MediaList
          files={ofKind("overlay")}
          empty="No overlays yet."
          hint="ProRes 4444 .mov overlays play in Safari; other browsers may only offer the download."
        />
      )}
      {tab === "sources" && (
        <>
          <MediaList files={ofKind("source")} empty="No sources in sources/." />
          <h2 className="section">Walk proxies</h2>
          {detail.proxies.length === 0 ? (
            <p className="muted">No proxies in the linked Walks.</p>
          ) : (
            <div className="media-grid">
              {detail.proxies.map((p) => (
                <Player key={p.media} title={`${p.walk} / ${p.name}`} media={p.media} meta={formatSize(p.size)} />
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
          <p className="muted">No references.md in this folder.</p>
        ))}
      {tab === "notes" && <TextFileEditor key="notes" slug={slug} path="notes.md" creatable onSaved={load} />}

      <NoteBox kind="video" noteKey={detail.slug} />
    </main>
  );
}

function LinkedResearch({ references, ideas }: { references: string[]; ideas: string[] }) {
  return (
    <dl className="facts linked">
      <div>
        <dt>References</dt>
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
        <dt>Ideas</dt>
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
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
      setError("video.json changed on disk; reloaded it, check the status and try again.");
      onReload();
    } else {
      setError(result.message);
    }
  };

  return (
    <section className="status-box">
      <ol className="status-strip">
        {detail.statuses.map((s, i) => (
          <li key={s} className={i < index ? "done" : i === index ? "current" : ""}>
            {s}
          </li>
        ))}
      </ol>
      {detail.legacy ? (
        <p className="muted">
          Legacy Reel: the status is derived from its folder (script → edit with cuts.json or overlays → review with a
          render in out/).
        </p>
      ) : next ? (
        <div className="advance">
          <input
            type="text"
            placeholder="Note (optional)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && advance()}
          />
          <button className="primary" disabled={busy} onClick={advance}>
            {busy ? "Saving…" : `Advance to ${next}`}
          </button>
        </div>
      ) : (
        <p className="muted">Published.</p>
      )}
      {error && <p className="error">{error}</p>}
      {history.length > 0 && (
        <details className="history">
          <summary>History ({history.length})</summary>
          <table className="log">
            <tbody>
              {history.map((h, i) => (
                <tr key={i}>
                  <td>{h.at}</td>
                  <td>
                    <span className={`status-pill status-${h.status}`}>{h.status}</span>
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
  empty: string;
  onSaved: () => void;
}) {
  const [picked, setPicked] = useState<string | null>(null);
  const path = picked && files.some((f) => f.path === picked) ? picked : (files[0]?.path ?? null);
  if (path === null) {
    return <p className="muted">{empty}</p>;
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

function MediaList({ files, empty, hint }: { files: VideoFile[]; empty: string; hint?: string }) {
  if (files.length === 0) {
    return <p className="muted">{empty}</p>;
  }
  return (
    <>
      {hint && <p className="muted">{hint}</p>}
      <div className="media-grid">
        {files.map((f) =>
          f.media ? (
            <Player key={f.path} title={f.path} media={f.media} meta={`${formatSize(f.size)} · ${formatTime(f.mtime)}`} />
          ) : (
            <p key={f.path} className="muted">
              {f.path} is not served
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
  if (files.length === 0) {
    return <p className="muted">The folder is empty.</p>;
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
              <span className="badge">{f.kind}</span>
              <span className="muted">{formatSize(f.size)}</span>
            </li>
          );
        })}
      </ul>
      {openFile && <TextFileEditor key={openFile.path} slug={slug} path={openFile.path} onSaved={onSaved} />}
    </>
  );
}
