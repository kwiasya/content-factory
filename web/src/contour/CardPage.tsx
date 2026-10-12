import { useCallback, useRef, type ReactNode } from "react";
import { mediaUrl } from "../api";
import { contourApi, type Measured } from "./api";
import { Cmd, ContourShell, Status } from "./ContourShell";
import { plain, seconds, secondsText, outlierText, viewsText } from "./format";
import { useT, type T } from "../i18n";
import { formatDate } from "../format";
import { Heatmap } from "./Heatmap";
import { NoteBox } from "../notes/NoteBox";
import { CONTOUR_PREFIX, taxonomyHref } from "./routes";
import { useLoad } from "./useLoad";

const PROPOSED = "proposed:";

export function kindText(kind: string | null | undefined, t: T): string {
  return kind ? t.or(`card.kind.${kind}`, kind) : "—";
}

function measuredRows(m: Measured, t: T): [string, ReactNode][] {
  return [
    [t("card.duration"), seconds(m.duration_s)],
    [t("card.kind"), kindText(m.kind, t)],
    [t("card.cuts"), plain(m.cut_count)],
    [t("card.cutsPerMinute"), plain(m.cuts_per_min)],
    [t("card.firstShot"), secondsText(m.first_shot_s, t)],
    [
      t("card.firstText"),
      m.first_text ? (
        <>
          «{m.first_text}» <span className="muted">{t("card.at", { s: secondsText(m.first_text_s, t) })}</span>
        </>
      ) : (
        "—"
      ),
    ],
    [t("card.firstPerson"), secondsText(m.first_person_s, t)],
    [t("card.firstFace"), secondsText(m.first_face_s, t)],
    [t("card.speechOnset"), secondsText(m.speech_onset_s, t)],
    [t("card.spokenHook"), m.spoken_hook ? `«${m.spoken_hook}»` : "—"],
    [t("card.language"), plain(m.language)],
  ];
}

function label(key: string): string {
  const text = key.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function AnalysisValue({ value }: { value: unknown }) {
  const t = useT();
  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    return (
      <dl className="facts nested">
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <div key={k}>
            <dt>{t.or(`analysis.${k}`, label(k))}</dt>
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
        <code>{value.slice(PROPOSED.length)}</code> <span className="flag pending">{t("card.proposed")}</span>
      </>
    );
  }
  return <>{plain(value)}</>;
}

export function CardPage({ id }: { id: string }) {
  const t = useT();
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
        <a href={CONTOUR_PREFIX}>{t("contour.back")}</a>
        <Status error={error} loading={!error} />
        {error && (
          <p className="muted">{t.rich("card.hint", { cmd: <Cmd>/analyze-reference</Cmd> })}</p>
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
      <a href={CONTOUR_PREFIX}>{t("contour.back")}</a>
      <div className="doc-head">
        <div>
          <h1>{ref?.title || data.external_id}</h1>
          <span className="muted">
            <code>{data.external_id}</code>
            {ref && (
              <>
                {" "}
                · {ref.handle ?? ref.channel_title ?? "—"} · {formatDate(ref.date, t)} ·{" "}
                {t("card.views", { views: viewsText(ref.views, t) })} · <strong>{outlierText(ref.outlier, t)}</strong>
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
          {card.analysis === null && <span className="flag pending">{t("card.notAnalyzed")}</span>}
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
          <h2 className="section">{t("card.measured")}</h2>
          <dl className="facts">
            {measuredRows(m, t).map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>

          <h2 className="section">{t("card.peaks")}</h2>
          {peaks.length > 0 && duration ? (
            <Heatmap duration={duration} peaks={peaks} chapters={chapters} onSeek={media ? seek : undefined} />
          ) : (
            <p className="muted">{t("card.noHeatmap")}</p>
          )}

          <h2 className="section">{t("card.sections")}</h2>
          {sections.length === 0 ? (
            <p className="muted">{t("card.noSections")}</p>
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

          <h2 className="section">{t("card.chapters")}</h2>
          {chapters.length === 0 ? (
            <p className="muted">{t("card.noChapters")}</p>
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
              <h2 className="section">{t("card.measurementNotes")}</h2>
              <ul className="muted">
                {m.notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      <h2 className="section">{t("card.analysis")}</h2>
      {card.analysis === null ? (
        <p className="muted">
          {t.rich("card.notAnalyzedYet", { cmd: <Cmd>/analyze-reference</Cmd>, id: <code>{data.external_id}</code> })}
        </p>
      ) : (
        <AnalysisValue value={card.analysis} />
      )}
      {proposed.length > 0 && (
        <p className="warn-box">
          {t.rich("card.awaiting", {
            values: proposed.map((p) => (
              <code key={`${p.kind}:${p.value}`}>
                {p.kind} {p.value}{" "}
              </code>
            )),
            link: <a href={taxonomyHref()}>{t("contour.taxonomy")}</a>,
          })}
        </p>
      )}
      <NoteBox kind="card" noteKey={data.external_id} />
    </ContourShell>
  );
}
