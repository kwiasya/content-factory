import { useCallback, useRef, type ReactNode } from "react";
import { contourApi, mediaUrl, type Measured } from "./api";
import { Cmd, ContourShell, Status } from "./ContourShell";
import { plain, seconds, outlierText, viewsText } from "./format";
import { Heatmap } from "./Heatmap";
import { CONTOUR_PREFIX, taxonomyHref } from "./routes";
import { useLoad } from "./useLoad";

const PROPOSED = "proposed:";

function measuredRows(m: Measured): [string, ReactNode][] {
  return [
    ["Duration", seconds(m.duration_s)],
    ["Kind", plain(m.kind)],
    ["Cuts", plain(m.cut_count)],
    ["Cuts per minute", plain(m.cuts_per_min)],
    ["First shot", m.first_shot_s === null || m.first_shot_s === undefined ? "—" : `${m.first_shot_s} s`],
    [
      "First text",
      m.first_text ? (
        <>
          «{m.first_text}» <span className="muted">at {m.first_text_s ?? "—"} s</span>
        </>
      ) : (
        "—"
      ),
    ],
    ["First person", m.first_person_s === null || m.first_person_s === undefined ? "—" : `${m.first_person_s} s`],
    ["First face", m.first_face_s === null || m.first_face_s === undefined ? "—" : `${m.first_face_s} s`],
    ["Speech onset", m.speech_onset_s === null || m.speech_onset_s === undefined ? "—" : `${m.speech_onset_s} s`],
    ["Spoken hook (first 3 s)", m.spoken_hook ? `«${m.spoken_hook}»` : "—"],
    ["Language", plain(m.language)],
  ];
}

function label(key: string): string {
  const text = key.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function AnalysisValue({ value }: { value: unknown }) {
  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    return (
      <dl className="facts nested">
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <div key={k}>
            <dt>{label(k)}</dt>
            <dd>
              <AnalysisValue value={v} />
            </dd>
          </div>
        ))}
      </dl>
    );
  }
  if (typeof value === "string" && value.startsWith(PROPOSED)) {
    return (
      <>
        <code>{value.slice(PROPOSED.length)}</code> <span className="flag pending">proposed</span>
      </>
    );
  }
  return <>{plain(value)}</>;
}

export function CardPage({ id }: { id: string }) {
  const loader = useCallback(() => contourApi.card(id), [id]);
  const { data, error } = useLoad(loader);
  const video = useRef<HTMLVideoElement>(null);

  const seek = (s: number) => {
    if (video.current) {
      video.current.currentTime = s;
      void video.current.play();
    }
  };

  if (!data) {
    return (
      <ContourShell active={null}>
        <a href={CONTOUR_PREFIX}>← Watchlists</a>
        <Status error={error} loading={!error} />
        {error && (
          <p className="muted">
            A card appears once the Reference is fetched and measured: <Cmd>/analyze-reference</Cmd>.
          </p>
        )}
      </ContourShell>
    );
  }

  const { reference: ref, card, sections, proposed, media } = data;
  const m = card.measured;
  const peaks = m.heatmap_peaks ?? [];
  const chapters = m.chapters ?? [];
  const duration = m.duration_s ?? ref?.duration_s ?? null;

  return (
    <ContourShell active={null}>
      <a href={CONTOUR_PREFIX}>← Watchlists</a>
      <div className="doc-head">
        <div>
          <h1>{ref?.title || data.external_id}</h1>
          <span className="muted">
            <code>{data.external_id}</code>
            {ref && (
              <>
                {" "}
                · {ref.handle ?? ref.channel_title ?? "—"} · {ref.date ?? "—"} · {viewsText(ref.views)} views ·{" "}
                <strong>{outlierText(ref.outlier)}</strong>
              </>
            )}
          </span>
        </div>
        <div className="doc-badges">
          {ref?.url && (
            <a href={ref.url} target="_blank" rel="noreferrer">
              YouTube
            </a>
          )}
          {card.analysis === null && <span className="flag pending">без разбора</span>}
        </div>
      </div>

      <div className={media ? "card-grid" : ""}>
        {media && (
          <figure className="player card-player">
            <video ref={video} src={mediaUrl(media)} controls preload="metadata" />
            <figcaption className="muted">
              <code>{media}</code>
            </figcaption>
          </figure>
        )}
        <div>
          <h2 className="section">Measured</h2>
          <dl className="facts">
            {measuredRows(m).map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>

          <h2 className="section">Heatmap peaks</h2>
          {peaks.length > 0 && duration ? (
            <Heatmap duration={duration} peaks={peaks} chapters={chapters} onSeek={media ? seek : undefined} />
          ) : (
            <p className="muted">No heatmap: YouTube shows one only for videos with enough replays.</p>
          )}

          <h2 className="section">Transcript sections</h2>
          {sections.length === 0 ? (
            <p className="muted">No transcript sections (no speech, or the transcript was not made).</p>
          ) : (
            <ol className="sections">
              {sections.map((s) => (
                <li key={s.start_s}>
                  <button className="link time" disabled={!media} onClick={() => seek(s.start_s)}>
                    {seconds(s.start_s)}
                  </button>{" "}
                  {s.text}
                </li>
              ))}
            </ol>
          )}

          <h2 className="section">Chapters</h2>
          {chapters.length === 0 ? (
            <p className="muted">No chapters.</p>
          ) : (
            <ol className="sections">
              {chapters.map((c) => (
                <li key={c.start_s}>
                  <button className="link time" disabled={!media} onClick={() => seek(c.start_s)}>
                    {seconds(c.start_s)}
                  </button>{" "}
                  {c.title}
                </li>
              ))}
            </ol>
          )}

          {m.notes && m.notes.length > 0 && (
            <>
              <h2 className="section">Measurement notes</h2>
              <ul className="muted">
                {m.notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      <h2 className="section">Analysis</h2>
      {card.analysis === null ? (
        <p className="muted">
          Not analyzed yet: run <Cmd>/analyze-reference</Cmd> with <code>{data.external_id}</code>.
        </p>
      ) : (
        <AnalysisValue value={card.analysis} />
      )}
      {proposed.length > 0 && (
        <p className="warn-box">
          Values awaiting approval:{" "}
          {proposed.map((p) => (
            <code key={`${p.kind}:${p.value}`}>
              {p.kind} {p.value}{" "}
            </code>
          ))}
          — decide on the <a href={taxonomyHref()}>Taxonomy</a> page.
        </p>
      )}
    </ContourShell>
  );
}
